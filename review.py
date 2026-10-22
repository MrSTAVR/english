# -*- coding: utf-8 -*-
"""Повторение слов по системе Лейтнера (интервальное повторение).

Слово из пройденного урока попадает в «коробку 0». Верный ответ двигает его в
следующую коробку — и оно возвращается всё реже (через 1, 2, 4, 8, 16 дней),
ошибка возвращает слово в коробку 0. Так выученное закрепляется надолго."""

import random
import re
import zlib
from datetime import date, datetime, timedelta

from curriculum import ALL_LESSONS
from practice import pool_from as _pool_from

INTERVALS = [0, 1, 2, 4, 8, 16]      # через сколько дней слово вернётся из коробки N
MAX_BOX = len(INTERVALS) - 1
MASTERED_BOX = 4                      # «выучено», когда слово дошло до этой коробки
ROUND_SIZE = 10


_ALL_WORDS = None


def all_words():
    """Все слова курса — запасной источник неправильных вариантов."""
    global _ALL_WORDS
    if _ALL_WORDS is None:
        _ALL_WORDS = _pool_from(ALL_LESSONS)
    return _ALL_WORDS


def learned_pool(stats):
    """Слова из пройденных уроков; недавно пройденные — раньше."""
    done = stats["completed_ids"]
    best = stats["best_by_lesson"]

    def when(lid):
        r = best.get(lid)
        return (r["finished_at"] if r is not None else "") or ""
    order = sorted((l for l in ALL_LESSONS if l["id"] in done), key=lambda l: when(l["id"]), reverse=True)
    return _pool_from(order)


def state(db, student_id):
    return {r["key"]: r for r in db.execute(
        "SELECT * FROM word_review WHERE student_id=?", (student_id,)).fetchall()}


def counts(pool, st, today=None):
    """(к повторению сегодня, новых, выучено)."""
    today = (today or date.today()).isoformat()
    due = sum(1 for w in pool if w["key"] in st and st[w["key"]]["due"] <= today)
    new = sum(1 for w in pool if w["key"] not in st)
    mastered = sum(1 for w in pool if w["key"] in st and st[w["key"]]["box"] >= MASTERED_BOX)
    return due, new, mastered


def pick_due(pool, st, today=None, n=ROUND_SIZE, extra=False, rng=None):
    """Что повторять: просроченные (слабые коробки вперёд), затем новые.
    extra=True — «ещё потренироваться», когда на сегодня всё сделано."""
    today = (today or date.today()).isoformat()
    rng = rng or random.Random()
    due = [w for w in pool if w["key"] in st and st[w["key"]]["due"] <= today]
    due.sort(key=lambda w: (st[w["key"]]["due"], st[w["key"]]["box"]))
    new = [w for w in pool if w["key"] not in st]
    chosen = (due + new)[:n]
    if extra and len(chosen) < n:
        rest = [w for w in pool if w not in chosen]
        rest.sort(key=lambda w: (st[w["key"]]["box"] if w["key"] in st else 0, rng.random()))
        chosen += rest[:n - len(chosen)]
    return chosen


def record(db, student_id, key, ok, today=None):
    """Записывает ответ и двигает слово по коробкам. Возвращает новую коробку."""
    today = today or date.today()
    row = db.execute("SELECT * FROM word_review WHERE student_id=? AND key=?", (student_id, key)).fetchone()
    box = row["box"] if row else 0
    box = min(MAX_BOX, box + 1) if ok else 0
    due = (today + timedelta(days=INTERVALS[box] if ok else 0)).isoformat()
    now = datetime.now().isoformat(timespec="seconds")
    if row:
        db.execute("UPDATE word_review SET box=?, due=?, n_ok=n_ok+?, n_bad=n_bad+?, last_at=? "
                   "WHERE student_id=? AND key=?", (box, due, int(ok), int(not ok), now, student_id, key))
    else:
        db.execute("INSERT INTO word_review (student_id, key, box, due, n_ok, n_bad, last_at) "
                   "VALUES (?, ?, ?, ?, ?, ?, ?)", (student_id, key, box, due, int(ok), int(not ok), now))
    db.commit()
    return box


def review_stats(db, student_id=None):
    if student_id is None:
        rows = db.execute("SELECT key, box, n_ok FROM word_review").fetchall()
    else:
        rows = db.execute("SELECT key, box, n_ok FROM word_review WHERE student_id=?", (student_id,)).fetchall()
    return {"review_correct": sum(r["n_ok"] for r in rows),
            "review_mastered": sum(1 for r in rows if r["box"] >= MASTERED_BOX)}


def _distractors(rng, word, pool, field, n=3):
    cand, seen = [], {word[field]}
    for src in (pool, all_words()):
        size = len(word[field].split())
        items = [w for w in src if w["key"] != word["key"] and abs(len(w[field].split()) - size) <= 1]
        rng.shuffle(items)
        for w in items:
            if w[field] not in seen:
                seen.add(w[field])
                cand.append(w[field])
            if len(cand) >= n:
                return cand
    return cand


def _choice(rng, word, pool, mode):
    if mode == "listen":
        opts = _distractors(rng, word, pool, "ru") + [word["ru"]]
        q, audio = "🔊 Послушай и выбери перевод", word["en"]
        right = word["ru"]
    elif mode == "en_ru":
        opts = _distractors(rng, word, pool, "ru") + [word["ru"]]
        q, audio = f"Что значит «{word['en']}»?", None
        right = word["ru"]
    else:   # ru_en
        opts = _distractors(rng, word, pool, "en") + [word["en"]]
        q, audio = f"Как по-английски: «{word['ru']}»?", None
        right = word["en"]
    rng.shuffle(opts)
    d = {"type": "choice", "q": q, "options": opts, "answer": opts.index(right),
         "explain": f"{word['en']} — {word['ru']}"}
    if audio:
        d["audio"] = audio
    return d


def make_question(word, pool, box, rng):
    """Задание зависит от «взрослости» слова: чем выше коробка, тем труднее."""
    typed_ok = "/" not in word["en"] and len(word["en"].split()) <= 3
    scr_ok = word["en"].isalpha() and 4 <= len(word["en"]) <= 9
    if box <= 1:
        q = _choice(rng, word, pool, rng.choice(["listen", "en_ru"]))
    elif box <= 3:
        q = _choice(rng, word, pool, rng.choice(["ru_en", "listen", "ru_en"]))
    else:
        kind = rng.choice(["dict", "scramble", "ru_en"])
        if kind == "dict" and typed_ok:
            q = {"type": "type_in", "q": "🔊 Послушай и напиши по-английски", "audio": word["en"],
                 "answer": word["en"], "explain": f"{word['en']} — {word['ru']}"}
        elif kind == "scramble" and scr_ok:
            letters = list(word["en"].lower())
            for _ in range(10):
                rng.shuffle(letters)
                if "".join(letters) != word["en"].lower():
                    break
            q = {"type": "scramble", "q": f"Собери слово: {word['ru']}", "letters": letters,
                 "answer": word["en"].lower(), "explain": f"{word['en']} — {word['ru']}"}
        else:
            q = _choice(rng, word, pool, "ru_en")
    q["key"] = word["key"]
    q["en"] = word["en"]
    q["ru"] = word["ru"]
    q["hint"] = word["hint"]
    q["pic"] = word.get("pic", "")
    q["box"] = box
    return q


def build_round(pool, st, today=None, extra=False, rng=None):
    rng = rng or random.Random()
    words = pick_due(pool, st, today, extra=extra, rng=rng)
    rng.shuffle(words)
    return [make_question(w, pool, st[w["key"]]["box"] if w["key"] in st else 0, rng) for w in words]


def hard_words(pool, st, n=ROUND_SIZE):
    """Слова, в которых были ошибки и которые ещё не выучены надолго (самые сложные — первыми)."""
    rows = [w for w in pool if w["key"] in st and st[w["key"]]["n_bad"] > 0 and st[w["key"]]["box"] < MASTERED_BOX]
    rows.sort(key=lambda w: (st[w["key"]]["n_ok"] - st[w["key"]]["n_bad"], st[w["key"]]["box"]))
    return rows[:n] if n else rows


def build_hard_round(pool, st, rng=None):
    rng = rng or random.Random()
    words = hard_words(pool, st)
    rng.shuffle(words)
    return [make_question(w, pool, st[w["key"]]["box"], rng) for w in words]


def word_of_day(pool, st, student_id, today=None):
    """Слово дня: одно и то же весь день; предпочитаем слабые и новые слова."""
    if not pool:
        return None
    today = today or date.today()
    weak = [w for w in pool if w["key"] not in st or st[w["key"]]["box"] <= 1] or pool
    seed = zlib.crc32(f"{student_id}-{today.isoformat()}".encode())
    return weak[seed % len(weak)]


def words_in_mistakes(results, lesson_id, limit_per_question=2):
    """Слова курса, на которых ученик ошибся в тесте (вопросы «выбери» и «напиши»).

    Слово ищем в правильном ответе и в тексте вопроса: по-английски — целым словом,
    по-русски — по переводу («Как по-английски «синий»?» → blue)."""
    pool = all_words()
    keys = []
    for res in results:
        if res.get("correct") or res.get("type") not in ("choice", "type_in"):
            continue
        text = f"{res.get('q', '')} {res.get('correct_answer', '')}".lower()
        found = []
        for w in sorted(pool, key=lambda w: (w["lesson"] != lesson_id, -len(w["key"]))):
            if len(w["key"]) < 3 or w["key"] in keys or w["key"] in found:
                continue
            if re.search(r"(?<![a-z])" + re.escape(w["key"]) + r"(?![a-z])", text) or \
                    (len(w["ru"]) >= 3 and re.search(r"(?<![а-яё])" + re.escape(w["ru"].lower()) + r"(?![а-яё])", text)):
                found.append(w["key"])
            if len(found) >= limit_per_question:
                break
        keys.extend(found)
    return keys


def send_mistakes(db, student_id, results, lesson_id):
    """Слова из ошибок теста — в коробку 0 (повторить сегодня). Возвращает список английских слов."""
    keys = words_in_mistakes(results, lesson_id)
    for k in keys:
        record(db, student_id, k, ok=False)
    by_key = {w["key"]: w["en"] for w in all_words()}
    return [by_key[k] for k in keys]
