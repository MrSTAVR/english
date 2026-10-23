# -*- coding: utf-8 -*-
"""Замок Чик-чика (вместо домика): комнаты-темы, кирпичики за учёбу, постройка и улучшение комнат.

Кирпичики — журнал castle_bricks (одна строка = одно начисление или трата; UNIQUE не даёт начислить
дважды за одно и то же). Комнаты — castle_rooms (уровень 1–3). При первом входе ученик «переезжает»:
монетки за купленное в старом домике возвращаются, вещи домика стираются, спальня строится бесплатно.
"""

from datetime import date, datetime

from house import ITEMS_BY_KEY

LEVEL_MAX = 3
# цена: уровень → (кирпичики, монетки); уровень 1 — постройка комнаты
COST = {1: (6, 20), 2: (8, 40), 3: (12, 60)}
BRICKS_LESSON = 3            # первый сданный урок основного курса
BRICKS_CASTLE_LESSON = 5     # урок замка
BRICKS_GOAL = 2              # цель дня выполнена
START_PER_LESSON, START_MAX = 1, 20   # при переезде — за уже пройденные уроки

# Порядок — снизу вверх по этажам замка (FLOORS — сверху вниз, как рисуем).
ROOMS = {
    "bedroom": {"name": "Спальня", "theme": "дом и мебель", "lesson": 20001, "who": None},
    "kitchen": {"name": "Кухня", "theme": "еда и посуда", "lesson": 20002, "who": "Benny"},
    "library": {"name": "Библиотека", "theme": "книги и истории", "lesson": None, "who": "Olly",
                "words": ["book", "map", "letter", "pencil", "shelf", "lamp", "armchair", "plant"]},
    "living": {"name": "Гостиная", "theme": "дом и гости", "lesson": 20005, "who": "Mia"},
    "classroom": {"name": "Класс", "theme": "школа", "lesson": 46, "who": "Felix",
                  "words": ["book", "notebook", "pencil", "ruler", "rubber", "desk", "computer", "map", "clock"]},
    "workshop": {"name": "Мастерская", "theme": "поделки", "lesson": 20006, "who": None,
                 "words": ["paper", "scissors", "glue", "paint", "brush", "box"]},
    "music": {"name": "Музыкальная", "theme": "музыка", "lesson": 20003, "who": None},
    "gym": {"name": "Спортзал", "theme": "спорт и игры", "lesson": 20004, "who": "Max"},
    "roof": {"name": "Сад на крыше", "theme": "природа", "lesson": None, "who": "Bella",
             "words": ["flower", "grass", "sun", "bee", "butterfly", "bird", "bench"]},
}
FLOORS = [["roof"], ["music", "gym"], ["workshop", "classroom"], ["library", "living"], ["bedroom", "kitchen"]]
RESIDENT_RU = {"Benny": "медвежонок Benny", "Olly": "совёнок Olly", "Mia": "кошечка Mia", "Felix": "лисёнок Felix",
               "Max": "щенок Max", "Bella": "зайка Bella"}
ROOF_STREAK = 7
NOT_THINGS = {"under", "this", "that", "these", "those", "sing", "dance", "throw", "catch", "loud", "quiet", "song", "concert",
              "teacher", "classroom", "maths", "english", "art", "music", "pe"}


def _now():
    return datetime.now().isoformat(timespec="seconds")


# ---------- кирпичики ----------

def bricks(db, student_id):
    return db.execute("SELECT COALESCE(SUM(amount), 0) FROM castle_bricks WHERE student_id=?", (student_id,)).fetchone()[0]


def earn(db, student_id, reason, ref, amount):
    """Начислить (или списать, amount < 0) один раз за (reason, ref). True — если записали."""
    cur = db.execute("INSERT OR IGNORE INTO castle_bricks (student_id, reason, ref, amount, at) VALUES (?, ?, ?, ?, ?)",
                     (student_id, reason, str(ref), amount, _now()))
    db.commit()
    return cur.rowcount > 0


def set_bricks(db, student_id, n):
    """Администратор задаёт число кирпичиков: в журнал пишется поправка на разницу."""
    diff = n - bricks(db, student_id)
    if diff:
        earn(db, student_id, "admin", datetime.now().isoformat(timespec="microseconds"), diff)
    return diff


def lesson_bricks(lesson):
    return BRICKS_CASTLE_LESSON if lesson.get("castle") else BRICKS_LESSON


def on_lesson_passed(db, student_id, lesson):
    """Урок впервые сдан — кирпичики. Возвращает, сколько начислено (0, если уже было)."""
    n = lesson_bricks(lesson)
    return n if earn(db, student_id, "lesson", lesson["id"], n) else 0


def on_goal_done(db, student_id, day=None):
    return BRICKS_GOAL if earn(db, student_id, "goal", (day or date.today()).isoformat(), BRICKS_GOAL) else 0


# ---------- переезд из домика ----------

def ensure(db, student_id, completed_ids=()):
    """Создаёт замок при первом обращении: возврат монеток за домик, спальня, стартовые кирпичики.
    Возвращает строку castle."""
    row = db.execute("SELECT * FROM castle WHERE student_id=?", (student_id,)).fetchone()
    if row:
        return row
    owned = [r["item_key"] for r in db.execute("SELECT item_key FROM house_items WHERE student_id=?", (student_id,))]
    refund = sum(ITEMS_BY_KEY[k]["cost"] for k in owned if k in ITEMS_BY_KEY)
    if refund:
        from garden import get_garden
        get_garden(db, student_id)
        db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?", (refund, student_id))
    db.execute("DELETE FROM house_items WHERE student_id=?", (student_id,))
    db.execute("DELETE FROM house_place WHERE student_id=?", (student_id,))
    db.execute("INSERT OR IGNORE INTO castle (student_id, moved_coins, note_seen, created_at) VALUES (?, ?, ?, ?)",
               (student_id, refund, 0 if (refund or owned) else 1, _now()))
    db.execute("INSERT OR IGNORE INTO castle_rooms (student_id, room, level, at) VALUES (?, 'bedroom', 1, ?)", (student_id, _now()))
    start = min(START_MAX, START_PER_LESSON * len(completed_ids))
    if start:
        db.execute("INSERT OR IGNORE INTO castle_bricks (student_id, reason, ref, amount, at) VALUES (?, 'start', '', ?, ?)",
                   (student_id, start, _now()))
    db.commit()
    return db.execute("SELECT * FROM castle WHERE student_id=?", (student_id,)).fetchone()


def take_move_note(db, student_id):
    """Сообщение о переезде (один раз): сколько монеток вернули."""
    row = db.execute("SELECT moved_coins, note_seen FROM castle WHERE student_id=?", (student_id,)).fetchone()
    if not row or row["note_seen"]:
        return None
    db.execute("UPDATE castle SET note_seen=1 WHERE student_id=?", (student_id,))
    db.commit()
    return row["moved_coins"]


# ---------- комнаты ----------

def levels(db, student_id):
    return {r["room"]: r["level"] for r in db.execute("SELECT room, level FROM castle_rooms WHERE student_id=?", (student_id,))}


def builds_count(db, student_id):
    """Сколько раз строили или улучшали (без бесплатной спальни) — для наград."""
    return db.execute("SELECT COUNT(*) FROM castle_bricks WHERE student_id=? AND reason='build'", (student_id,)).fetchone()[0]


def lock_reason(db, student_id, key, stats, garden_row):
    """None — комнату можно строить; иначе — что сделать, чтобы открыть."""
    r = ROOMS[key]
    if key == "library":
        return None if stats.get("stories_done", 0) >= 1 else "Прочитай первую историю"
    if key == "roof":
        return None if (garden_row["best_streak"] if garden_row else 0) >= ROOF_STREAK else f"Занимайся {ROOF_STREAK} дней подряд"
    if r["lesson"] and r["lesson"] not in stats["completed_ids"]:
        from curriculum import LESSONS_BY_ID
        title = LESSONS_BY_ID[r["lesson"]]["title"]
        if r["lesson"] >= 20000:
            title = title.split(":", 1)[-1].split("—")[0].strip()
            return f"Пройди урок замка «{title}»"
        return f"Пройди урок «{_clean(title)}»"
    return None


def _clean(t):
    from template_filters import noemoji
    return noemoji(t)


def room_words(key, level):
    """Слова-предметы комнаты: чем выше уровень, тем больше (1 → 6, 2 → 10, 3 → все)."""
    from curriculum import LESSONS_BY_ID
    from review import all_words
    r = ROOMS[key]
    if r.get("words"):
        by_en = {w["en"].lower(): w for w in all_words()}
        words = [dict(by_en[w], en=w) for w in r["words"] if w in by_en]
    else:
        words = [w for w in LESSONS_BY_ID[r["lesson"]]["material"]
                 if " " not in w["en"].strip() and w["en"].lower() not in NOT_THINGS]   # предметы, без фраз и грамматики
    limit = {0: 0, 1: 6, 2: 10}.get(level)
    return words if limit is None else words[:limit]


def scene(key, level):
    """Рисунок комнаты с предметами текущего уровня и метки слов (x, y — проценты от рисунка)."""
    from castle_art import POS, items_svg, level_deco, level_floor, room_svg
    words = room_words(key, max(level, 1))
    pins = [{"en": w["en"], "ru": w["ru"], "x": round(POS[key][w["en"].lower()][0] / 3, 2),
             "y": round(POS[key][w["en"].lower()][1] / 1.8, 2)} for w in words if w["en"].lower() in POS[key]]
    return room_svg(key, extra=level_deco(level) + items_svg(key, words), under=level_floor(key, level), words=[w["en"] for w in words]), pins


BRICKS_FIND = 1   # «Find the…!» в комнате — раз в день за каждую комнату


def on_find_done(db, student_id, key, day=None):
    return BRICKS_FIND if earn(db, student_id, "find", f"{key}:{(day or date.today()).isoformat()}", BRICKS_FIND) else 0


def cost(level_to):
    return COST[level_to]


def build(db, student_id, key, stats, garden_row):
    """Построить комнату или улучшить на уровень. Возвращает (ok, сообщение)."""
    if key not in ROOMS:
        return False, "Такой комнаты нет."
    lv = levels(db, student_id).get(key, 0)
    if lv >= LEVEL_MAX:
        return False, "Эта комната уже самого высокого уровня!"
    if lv == 0:
        why = lock_reason(db, student_id, key, stats, garden_row)
        if why:
            return False, f"Комната пока закрыта: {why[0].lower() + why[1:]}."
    b, c = COST[lv + 1]
    have_b = bricks(db, student_id)
    coins = garden_row["coins"] if garden_row else 0
    if have_b < b or coins < c:
        need = []
        if have_b < b:
            need.append(f"ещё {b - have_b} кирпичиков")
        if coins < c:
            need.append(f"ещё {c - coins} монеток")
        return False, "Не хватает: " + " и ".join(need) + "."
    if not earn(db, student_id, "build", f"{key}:{lv + 1}", -b):
        return False, "Уже построено."
    db.execute("UPDATE garden SET coins=coins-? WHERE student_id=?", (c, student_id))
    db.execute("INSERT INTO castle_rooms (student_id, room, level, at) VALUES (?, ?, ?, ?) "
               "ON CONFLICT(student_id, room) DO UPDATE SET level=excluded.level, at=excluded.at", (student_id, key, lv + 1, _now()))
    db.commit()
    name = ROOMS[key]["name"]
    who = ROOMS[key]["who"]
    if lv == 0:
        return True, f"Комната «{name}» построена!" + (f" В неё переехал(а) {RESIDENT_RU[who]}." if who else "")
    return True, f"«{name}» — теперь уровень {lv + 1}! Новые предметы ждут тебя."


def view(db, student_id, stats, garden_row):
    """Всё для страницы замка: этажи с комнатами, баланс."""
    lv = levels(db, student_id)
    rooms = {}
    for key, r in ROOMS.items():
        level = lv.get(key, 0)
        item = {"key": key, "name": r["name"], "theme": r["theme"], "level": level, "who": r["who"] if level else None,
                "who_ru": RESIDENT_RU.get(r["who"]) if r["who"] else None, "words": len(room_words(key, level)) if level else 0}
        if level == 0:
            item["lock"] = lock_reason(db, student_id, key, stats, garden_row)
            item["state"] = "locked" if item["lock"] else "build"
            item["lesson"] = r["lesson"] if item["lock"] and r["lesson"] else None
        else:
            item["state"] = "built"
        nxt = level + 1
        item["next_cost"] = COST.get(nxt) if nxt <= LEVEL_MAX else None
        rooms[key] = item
    return {"floors": [[rooms[k] for k in fl] for fl in FLOORS], "rooms": rooms, "bricks": bricks(db, student_id),
            "coins": garden_row["coins"] if garden_row else 0}


# ---------- доход комнат и поручения соседей ----------

INCOME = {1: 1, 2: 2, 3: 3}    # монеток в день от комнаты с соседом (по уровню), если ученик занимался
TASK_COINS = 3
TASKS_PER_DAY = 3              # сколько соседей дают поручение в день
# вид поручения: (фраза соседа, что сделать, страница)
TASKS = {
    "find": ("Find things in my room!", "Сыграй в «Find the…!» в этой комнате", None),
    "lesson": ("Let's learn something new!", "Сдай любой урок", "student.course_map"),
    "game": ("Let's play a game!", "Сыграй в любую игру", "games.games_hub"),
    "story": ("Read me a story, please!", "Прочитай или послушай историю", "stories.stories_page"),
    "words": ("Help me remember words!", "Повтори 5 слов", "review.review_page"),
    "dialog": ("Let's talk!", "Поговори с героем в диалоге", "games.dialogs_page"),
}
TASK_ORDER = ["find", "lesson", "game", "words", "find", "story", "dialog"]
WORDS_TASK = 5


def _day(day=None):
    return (day or date.today()).isoformat()


def studied(db, student_id, day=None):
    """Занимался ли ученик в этот день (урок, игра, история, письмо, диалог, повторение слов)."""
    d = _day(day)
    if db.execute("SELECT 1 FROM activity WHERE student_id=? AND day=?", (student_id, d)).fetchone():
        return True
    row = db.execute("SELECT lessons, words FROM daily_goal WHERE student_id=? AND day=?", (student_id, d)).fetchone()
    return bool(row and (row["lessons"] or row["words"]))


def _coins_taken(db, student_id, day, kind, ref=""):
    return db.execute("SELECT 1 FROM castle_coins WHERE student_id=? AND day=? AND kind=? AND ref=?",
                      (student_id, day, kind, ref)).fetchone() is not None


def _give(db, student_id, day, kind, ref, amount):
    """Записать и начислить монетки один раз. True — если начислили."""
    cur = db.execute("INSERT OR IGNORE INTO castle_coins (student_id, day, kind, ref, amount, at) VALUES (?, ?, ?, ?, ?, ?)",
                     (student_id, day, kind, ref, amount, _now()))
    if cur.rowcount:
        from garden import get_garden
        get_garden(db, student_id)
        db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?", (amount, student_id))
    db.commit()
    return cur.rowcount > 0


def income(db, student_id, day=None):
    """Доход замка за день: {"amount", "rooms": [(комната, монетки)], "studied", "taken"}."""
    lv = levels(db, student_id)
    rooms = [(k, INCOME[lv[k]]) for k in ROOMS if lv.get(k) and ROOMS[k]["who"]]
    d = _day(day)
    return {"amount": sum(n for _k, n in rooms), "rooms": rooms, "studied": studied(db, student_id, day),
            "taken": _coins_taken(db, student_id, d, "income")}


def collect_income(db, student_id, day=None):
    """Собрать доход за сегодня. Возвращает (ok, сообщение)."""
    inc = income(db, student_id, day)
    if not inc["amount"]:
        return False, "Пока в замке нет соседей — построй комнату, и сосед переедет."
    if not inc["studied"]:
        return False, "Сначала позанимайся сегодня — тогда соседи принесут монетки."
    if not _give(db, student_id, _day(day), "income", "", inc["amount"]):
        return False, "Сегодня доход уже собран. Приходи завтра!"
    return True, f"Соседи принесли {inc['amount']} монеток!"


def _task_done(db, student_id, room, kind, d):
    if kind == "find":
        return db.execute("SELECT 1 FROM castle_bricks WHERE student_id=? AND reason='find' AND ref=?", (student_id, f"{room}:{d}")).fetchone() is not None
    if kind == "words":
        row = db.execute("SELECT words FROM daily_goal WHERE student_id=? AND day=?", (student_id, d)).fetchone()
        return bool(row and row["words"] >= WORDS_TASK)
    return db.execute("SELECT 1 FROM activity WHERE student_id=? AND day=? AND kind=?", (student_id, d, kind)).fetchone() is not None


def tasks(db, student_id, day=None):
    """Поручения соседей на день: до TASKS_PER_DAY соседей по очереди, вид меняется день ото дня."""
    d = date.fromisoformat(_day(day))
    lv = levels(db, student_id)
    who_rooms = [k for k in ROOMS if lv.get(k) and ROOMS[k]["who"]]
    if not who_rooms:
        return []
    n = d.toordinal()
    start = n % len(who_rooms)
    picked = (who_rooms[start:] + who_rooms[:start])[:TASKS_PER_DAY]
    out, used = [], set()
    for i, room in enumerate(picked):
        j = n + i * 3 + list(ROOMS).index(room)
        while TASK_ORDER[j % len(TASK_ORDER)] in used:     # у соседей в один день — разные поручения
            j += 1
        kind = TASK_ORDER[j % len(TASK_ORDER)]
        used.add(kind)
        en, ru, endpoint = TASKS[kind]
        who = ROOMS[room]["who"]
        out.append({"room": room, "room_name": ROOMS[room]["name"], "who": who, "who_ru": RESIDENT_RU[who], "kind": kind,
                    "en": en, "ru": ru, "endpoint": endpoint, "coins": TASK_COINS,
                    "done": _task_done(db, student_id, room, kind, d.isoformat()),
                    "taken": _coins_taken(db, student_id, d.isoformat(), "task", room)})
    return out


def claim_task(db, student_id, room, day=None):
    """Забрать награду за поручение соседа. (ok, сообщение)."""
    t = next((t for t in tasks(db, student_id, day) if t["room"] == room), None)
    if not t:
        return False, "У этого соседа сегодня нет поручения."
    if not t["done"]:
        return False, "Поручение ещё не выполнено: " + t["ru"][0].lower() + t["ru"][1:] + "."
    if not _give(db, student_id, _day(day), "task", room, TASK_COINS):
        return False, "Награда за это поручение уже получена."
    return True, f"{t['who_ru'][0].upper() + t['who_ru'][1:]} говорит: «Thank you!» +{TASK_COINS} монетки."


def forget_student(db, student_id):
    for t in ("castle", "castle_rooms", "castle_bricks", "castle_coins"):
        db.execute(f"DELETE FROM {t} WHERE student_id=?", (student_id,))
