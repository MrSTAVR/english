# -*- coding: utf-8 -*-
"""Друзья: рекорды в играх, дуэли, лента «Что нового» с реакциями, «нравится» саду и замку.

Участвуют ученики с students.competitions=1 (переключатель в кабинете администратора).
Другим ученикам видны только имя и аватарка. Тексты ленты — без имени и без глаголов
прошедшего времени («Урок пройден: …»), чтобы не гадать с родом.
"""

import json
import random
from datetime import datetime, timedelta

from garden import get_garden
from review import all_words, learned_pool
from stats import compute_stats
from template_filters import noemoji

GAME_TITLES = {"pairs": "Найди пару", "memory": "Мемори", "blitz": "Блиц 60 секунд",
               "listen": "Услышь и выбери", "runner": "Бег с препятствиями"}

# Как считается рекорд: lower — чем меньше, тем лучше; max — защита от мусора.
RECORDS = {
    "pairs": {"lower": True, "max": 3600, "unit": ("секунда", "секунды", "секунд")},
    "memory": {"lower": True, "max": 500, "unit": ("ход", "хода", "ходов")},
    "blitz": {"lower": False, "max": 300, "unit": ("слово", "слова", "слов")},
    "listen": {"lower": False, "max": 20, "unit": ("слово", "слова", "слов")},
    "runner": {"lower": False, "max": 20, "unit": ("препятствие", "препятствия", "препятствий")},
}

DUEL_GAMES = {"blitz": 20, "pairs": 6, "memory": 6}    # игра → сколько слов
DUEL_MIN_WORDS = 6
DUEL_DAYS = 7                                           # столько ждём соперника
DUEL_MAX_OPEN = 3                                       # незаконченных вызовов от одного ученика
DUEL_COINS_PLAY, DUEL_COINS_WIN, DUEL_COINS_DRAW = 2, 3, 1
DUEL_COINS_PER_DAY = 3                                  # монетки — за первые 3 дуэли в день

REACTIONS = {"bravo": "Молодец!", "wow": "Ого!", "catch": "Догоню!"}
LIKE_WHAT = {"garden": "сад", "house": "замок"}
FEED_LIMIT = 12


def _now():
    return datetime.now().isoformat(timespec="microseconds")    # «что нового» сравнивает время точно


def plural(n, forms):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forms[1]
    return forms[2]


def score_text(game, score):
    return f"{score} {plural(score, RECORDS[game]['unit'])}"


def _better(game, a, b):
    """a лучше b?"""
    return a < b if RECORDS[game]["lower"] else a > b


# ---------- кто участвует ----------

def competing(student):
    return bool(student is not None and student["competitions"])


def friends(db, student_id):
    """Другие ученики, которые участвуют в соревнованиях: только id, имя и аватарка."""
    return [{"id": r["id"], "name": r["display_name"], "emoji": r["emoji"] or "🎒"}
            for r in db.execute("SELECT id, display_name, emoji FROM students "
                                "WHERE competitions=1 AND id<>? ORDER BY display_name", (student_id,))]


def friend(db, student_id, friend_id):
    return next((f for f in friends(db, student_id) if f["id"] == friend_id), None)


def _people(db):
    return {r["id"]: {"id": r["id"], "name": r["display_name"], "emoji": r["emoji"] or "🎒"}
            for r in db.execute("SELECT id, display_name, emoji FROM students WHERE competitions=1")}


# ---------- лента ----------

def post(db, student_id, kind, text):
    db.execute("INSERT INTO feed (student_id, kind, text, at) VALUES (?, ?, ?, ?)",
               (student_id, kind, noemoji(text), _now()))
    db.commit()


def feed_view(db, student_id, limit=FEED_LIMIT):
    people = _people(db)
    if student_id not in people:
        return []
    ids = list(people)
    marks = ",".join("?" * len(ids))
    rows = db.execute(f"SELECT * FROM feed WHERE student_id IN ({marks}) ORDER BY id DESC LIMIT ?",
                      (*ids, limit)).fetchall()
    reacts = {}
    if rows:
        fmarks = ",".join("?" * len(rows))
        for r in db.execute(f"SELECT * FROM feed_reactions WHERE feed_id IN ({fmarks}) ORDER BY at",
                            [r["id"] for r in rows]):
            if r["student_id"] in people:
                reacts.setdefault(r["feed_id"], []).append(r)
    out = []
    for r in rows:
        mine = None
        groups = {}
        for x in reacts.get(r["id"], []):
            groups.setdefault(x["kind"], []).append(people[x["student_id"]]["name"])
            if x["student_id"] == student_id:
                mine = x["kind"]
        out.append({"id": r["id"], "who": people[r["student_id"]], "me": r["student_id"] == student_id,
                    "text": r["text"], "at": r["at"], "mine": mine,
                    "reactions": [{"kind": k, "label": REACTIONS[k], "names": groups[k]}
                                  for k in REACTIONS if k in groups]})
    return out


def react(db, student_id, feed_id, kind):
    """Реакция на новость друга; повторное нажатие той же реакции — убрать."""
    if kind not in REACTIONS:
        return False
    row = db.execute("SELECT student_id FROM feed WHERE id=?", (feed_id,)).fetchone()
    if not row or not friend(db, student_id, row["student_id"]):
        return False
    old = db.execute("SELECT kind FROM feed_reactions WHERE feed_id=? AND student_id=?",
                     (feed_id, student_id)).fetchone()
    if old and old["kind"] == kind:
        db.execute("DELETE FROM feed_reactions WHERE feed_id=? AND student_id=?", (feed_id, student_id))
    else:
        db.execute("INSERT OR REPLACE INTO feed_reactions (feed_id, student_id, kind, at) VALUES (?, ?, ?, ?)",
                   (feed_id, student_id, kind, _now()))
    db.commit()
    return True


# ---------- рекорды ----------

def save_record(db, student, game, score):
    """Сохраняет результат игры. Возвращает {'personal': новый личный рекорд, 'top': лучший среди друзей}."""
    rule = RECORDS.get(game)
    if rule is None or not 1 <= score <= rule["max"]:
        return {"personal": False, "top": False}
    sid = student["id"]
    old = db.execute("SELECT score FROM game_records WHERE student_id=? AND game=?", (sid, game)).fetchone()
    if old is not None and not _better(game, score, old["score"]):
        return {"personal": False, "top": False}
    db.execute("INSERT OR REPLACE INTO game_records (student_id, game, score, at) VALUES (?, ?, ?, ?)",
               (sid, game, score, _now()))
    db.commit()
    top = False
    if competing(student):
        others = [r["score"] for r in db.execute(
            "SELECT r.score FROM game_records r JOIN students s ON s.id=r.student_id "
            "WHERE r.game=? AND r.student_id<>? AND s.competitions=1", (game, sid))]
        top = bool(others) and all(_better(game, score, o) for o in others)
        if top:
            post(db, sid, "record", f"Новый рекорд среди друзей: «{GAME_TITLES[game]}» — {score_text(game, score)}")
    return {"personal": True, "top": top}


def records_table(db, student_id):
    """Для каждой игры — список участников от лучшего к худшему."""
    people = _people(db)
    rows = db.execute("SELECT * FROM game_records").fetchall()
    out = []
    for game, rule in RECORDS.items():
        items = [r for r in rows if r["game"] == game and r["student_id"] in people]
        items.sort(key=lambda r: (r["score"] if rule["lower"] else -r["score"], r["at"]))
        out.append({"game": game, "title": GAME_TITLES[game],
                    "rows": [{"who": people[r["student_id"]], "me": r["student_id"] == student_id,
                              "text": score_text(game, r["score"])} for r in items]})
    return out


def best_by_game(db, student):
    """Для карточек игр: свой рекорд и рекорд среди друзей."""
    mine = {r["game"]: r["score"] for r in db.execute(
        "SELECT game, score FROM game_records WHERE student_id=?", (student["id"],))}
    out = {g: {"mine": score_text(g, mine[g]) if g in mine else None, "top": None} for g in RECORDS}
    if competing(student) and friends(db, student["id"]):
        for t in records_table(db, student["id"]):
            if t["rows"]:
                out[t["game"]]["top"] = t["rows"][0]
    return out


# ---------- дуэли ----------

def _cutoff():
    return (datetime.now() - timedelta(days=DUEL_DAYS)).isoformat(timespec="seconds")


def _open_sql():
    return "finished_at IS NULL AND created_at >= ?"


def common_words(db, a_id, b_id):
    a = learned_pool(compute_stats(db, a_id))
    b_keys = {w["key"] for w in learned_pool(compute_stats(db, b_id))}
    return [w for w in a if w["key"] in b_keys]


def create_duel(db, student_id, friend_id, game):
    """Вызов на дуэль. Возвращает (id дуэли или None, сообщение)."""
    if game not in DUEL_GAMES:
        return None, "Такой игры для дуэли нет."
    f = friend(db, student_id, friend_id)
    if not f:
        return None, "Такого друга нет."
    open_mine = db.execute(f"SELECT COUNT(*) FROM duels WHERE from_id=? AND {_open_sql()}",
                           (student_id, _cutoff())).fetchone()[0]
    if open_mine >= DUEL_MAX_OPEN:
        return None, f"Сначала дождись ответов на свои вызовы — сразу можно не больше {DUEL_MAX_OPEN}."
    pair = db.execute(f"SELECT 1 FROM duels WHERE ((from_id=? AND to_id=?) OR (from_id=? AND to_id=?)) "
                      f"AND {_open_sql()}", (student_id, friend_id, friend_id, student_id, _cutoff())).fetchone()
    if pair:
        return None, f"Дуэль с другом ({f['name']}) ещё не закончена — сначала доиграйте её."
    words = common_words(db, student_id, friend_id)
    if len(words) < DUEL_MIN_WORDS:
        return None, "Пока мало слов, которые знаете вы оба. Пройдите ещё уроки — и можно будет сразиться!"
    pick = random.sample(words, min(DUEL_GAMES[game], len(words)))
    cur = db.execute("INSERT INTO duels (from_id, to_id, game, words, created_at) VALUES (?, ?, ?, ?, ?)",
                     (student_id, friend_id, game, json.dumps([w["key"] for w in pick]), _now()))
    db.commit()
    return cur.lastrowid, ""


def duel_to_play(db, student_id, duel_id):
    """Дуэль, в которой ученику сейчас можно сыграть свою часть (или None)."""
    d = db.execute(f"SELECT * FROM duels WHERE id=? AND {_open_sql()}", (duel_id, _cutoff())).fetchone()
    if not d:
        return None
    if d["from_id"] == student_id and d["from_score"] is None:
        return d
    if d["to_id"] == student_id and d["from_score"] is not None and d["to_score"] is None:
        return d
    return None


def duel_words(d):
    by_key = {w["key"]: w for w in all_words()}
    return [by_key[k] for k in json.loads(d["words"]) if k in by_key]


def _winner(d):
    a, b = d["from_score"], d["to_score"]
    if a == b:
        return None
    return d["from_id"] if _better(d["game"], a, b) else d["to_id"]


def _give_coins(db, student_id, coins):
    today = datetime.now().date().isoformat()
    done_today = db.execute("SELECT COUNT(*) FROM duels WHERE (from_id=? OR to_id=?) AND finished_at >= ?",
                            (student_id, student_id, today)).fetchone()[0]
    if done_today > DUEL_COINS_PER_DAY:      # текущая дуэль уже посчитана
        return 0
    get_garden(db, student_id)
    db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?", (coins, student_id))
    return coins


def finish_part(db, student_id, duel_id, score):
    """Записывает результат ученика в дуэли. Возвращает текст для экрана итогов (или None)."""
    d = duel_to_play(db, student_id, duel_id)
    rule = RECORDS[d["game"]] if d else None
    if not d or not 0 <= score <= rule["max"]:
        return None
    people = {r["id"]: r for r in db.execute("SELECT id, display_name FROM students WHERE id IN (?, ?)",
                                              (d["from_id"], d["to_id"]))}
    if d["from_id"] == student_id:
        db.execute("UPDATE duels SET from_score=? WHERE id=?", (score, duel_id))
        db.commit()
        return f"Твой результат: {score_text(d['game'], score)}. Теперь очередь соперника — {people[d['to_id']]['display_name']}!"
    db.execute("UPDATE duels SET to_score=?, finished_at=? WHERE id=?", (score, _now(), duel_id))
    d = db.execute("SELECT * FROM duels WHERE id=?", (duel_id,)).fetchone()
    win = _winner(d)
    coins = {}
    for sid in (d["from_id"], d["to_id"]):
        bonus = DUEL_COINS_DRAW if win is None else DUEL_COINS_WIN if win == sid else 0
        coins[sid] = _give_coins(db, sid, DUEL_COINS_PLAY + bonus)
    db.commit()
    a, b = people[d["from_id"]]["display_name"], people[d["to_id"]]["display_name"]
    res = "ничья!" if win is None else f"победа — {people[win]['display_name']}!"
    post(db, d["to_id"], "duel", f"Дуэль «{GAME_TITLES[d['game']]}»: {a} — {d['from_score']}, {b} — {d['to_score']}, {res}")
    you = "Ничья — отличная игра у обоих!" if win is None else "Победа! Ты молодец!" if win == student_id \
        else "В этот раз победа у соперника — в следующий раз получится!"
    tail = f" +{coins[student_id]} монеток." if coins[student_id] else ""
    return f"{you} {a} — {d['from_score']}, {b} — {d['to_score']}.{tail}"


def duels_view(db, student_id):
    people = {r["id"]: {"id": r["id"], "name": r["display_name"], "emoji": r["emoji"] or "🎒"}
              for r in db.execute("SELECT id, display_name, emoji FROM students")}
    cutoff = _cutoff()
    rows = db.execute("SELECT * FROM duels WHERE (from_id=? OR to_id=?) AND (finished_at IS NOT NULL OR created_at >= ?) "
                      "ORDER BY id DESC LIMIT 40", (student_id, student_id, cutoff)).fetchall()
    view = {"incoming": [], "mine_unplayed": [], "waiting": [], "finished": []}
    for d in rows:
        other = d["to_id"] if d["from_id"] == student_id else d["from_id"]
        if other not in people:
            continue
        item = {"id": d["id"], "game": d["game"], "title": GAME_TITLES[d["game"]], "other": people[other]}
        if d["finished_at"]:
            if len(view["finished"]) >= 5:
                continue
            me_from = d["from_id"] == student_id
            win = _winner(d)
            item.update(my=score_text(d["game"], d["from_score"] if me_from else d["to_score"]),
                        their=score_text(d["game"], d["to_score"] if me_from else d["from_score"]),
                        result="draw" if win is None else "win" if win == student_id else "lose")
            view["finished"].append(item)
        elif d["from_id"] == student_id:
            view["mine_unplayed" if d["from_score"] is None else "waiting"].append(item)
        elif d["from_score"] is not None:
            view["incoming"].append(item)
    return view


# ---------- «нравится» ----------

def toggle_like(db, student_id, owner_id, what):
    if what not in LIKE_WHAT or not friend(db, student_id, owner_id):
        return False
    if db.execute("SELECT 1 FROM likes WHERE owner_id=? AND from_id=? AND what=?", (owner_id, student_id, what)).fetchone():
        db.execute("DELETE FROM likes WHERE owner_id=? AND from_id=? AND what=?", (owner_id, student_id, what))
    else:
        db.execute("INSERT INTO likes (owner_id, from_id, what, at) VALUES (?, ?, ?, ?)", (owner_id, student_id, what, _now()))
    db.commit()
    return True


def likes_of(db, owner_id, what):
    """Имена тех, кому понравилось (только участники соревнований)."""
    return [r["display_name"] for r in db.execute(
        "SELECT s.display_name FROM likes l JOIN students s ON s.id=l.from_id "
        "WHERE l.owner_id=? AND l.what=? AND s.competitions=1 ORDER BY l.at", (owner_id, what))]


# ---------- что нового ----------

def _seen(db, student_id):
    r = db.execute("SELECT seen_at FROM friend_seen WHERE student_id=?", (student_id,)).fetchone()
    return r["seen_at"] if r else ""


def mark_seen(db, student_id):
    db.execute("INSERT OR REPLACE INTO friend_seen (student_id, seen_at) VALUES (?, ?)", (student_id, _now()))
    db.commit()


def news_count(db, student_id):
    """Сколько нового для ученика: вызовы, результаты дуэлей, реакции, «нравится»."""
    seen, cutoff = _seen(db, student_id), _cutoff()
    incoming = db.execute(f"SELECT COUNT(*) FROM duels WHERE to_id=? AND from_score IS NOT NULL AND {_open_sql()}",
                          (student_id, cutoff)).fetchone()[0]
    results = db.execute("SELECT COUNT(*) FROM duels WHERE from_id=? AND finished_at > ?", (student_id, seen)).fetchone()[0]
    reacts = db.execute("SELECT COUNT(*) FROM feed_reactions r JOIN feed f ON f.id=r.feed_id "
                        "WHERE f.student_id=? AND r.student_id<>? AND r.at > ?", (student_id, student_id, seen)).fetchone()[0]
    likes = db.execute("SELECT COUNT(*) FROM likes WHERE owner_id=? AND at > ?", (student_id, seen)).fetchone()[0]
    return incoming + results + reacts + likes


def incoming_count(db, student_id):
    return db.execute(f"SELECT COUNT(*) FROM duels WHERE to_id=? AND from_score IS NOT NULL AND {_open_sql()}",
                      (student_id, _cutoff())).fetchone()[0]


def forget_student(db, student_id):
    """Удаление ученика: чистим всё, что связано с «Друзьями»."""
    db.execute("DELETE FROM feed_reactions WHERE student_id=? OR feed_id IN (SELECT id FROM feed WHERE student_id=?)",
               (student_id, student_id))
    db.execute("DELETE FROM feed WHERE student_id=?", (student_id,))
    db.execute("DELETE FROM likes WHERE owner_id=? OR from_id=?", (student_id, student_id))
    db.execute("DELETE FROM duels WHERE from_id=? OR to_id=?", (student_id, student_id))
    for table in ("game_records", "friend_seen"):
        db.execute(f"DELETE FROM {table} WHERE student_id=?", (student_id,))
