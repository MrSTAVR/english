# -*- coding: utf-8 -*-
"""Цель дня: по умолчанию 1 урок + 10 слов повторения (родитель может изменить).
За выполненную цель — монетки в сад."""

from datetime import date

from curriculum import MAIN_COUNT

GOAL_LESSONS = 1
GOAL_WORDS = 10
GOAL_COINS = 3
MAX_LESSONS = 3      # пределы настройки родителя
MAX_WORDS = 50


def target(db, student_id):
    """Цель ученика (уроков, слов): своя от родителя или стандартная."""
    r = db.execute("SELECT lessons, words FROM goal_settings WHERE student_id=?", (student_id,)).fetchone()
    return (r["lessons"], r["words"]) if r else (GOAL_LESSONS, GOAL_WORDS)


def set_target(db, student_id, lessons, words):
    """Сохраняет цель родителя. Нулевая цель запрещена (иначе нечего выполнять). Возвращает успех."""
    if not (0 <= lessons <= MAX_LESSONS and 0 <= words <= MAX_WORDS) or not (lessons or words):
        return False
    if (lessons, words) == (GOAL_LESSONS, GOAL_WORDS):
        db.execute("DELETE FROM goal_settings WHERE student_id=?", (student_id,))
    else:
        db.execute("INSERT INTO goal_settings (student_id, lessons, words) VALUES (?, ?, ?) "
                   "ON CONFLICT(student_id) DO UPDATE SET lessons=excluded.lessons, words=excluded.words",
                   (student_id, lessons, words))
    db.commit()
    return True


def needs(stats, pool_size, goal=None):
    """Что требуется сегодня: (уроков, слов). Нет уроков/слов для повторения — часть цели отпадает."""
    gl, gw = goal or (GOAL_LESSONS, GOAL_WORDS)
    left = MAIN_COUNT - stats["lessons_completed"]
    nl = min(gl, left) if left > 0 else 0
    nw = gw if pool_size >= 4 else 0
    return nl, nw


def today_row(db, student_id, today=None):
    day = (today or date.today()).isoformat()
    r = db.execute("SELECT * FROM daily_goal WHERE student_id=? AND day=?", (student_id, day)).fetchone()
    return {"lessons": r["lessons"], "words": r["words"], "done": bool(r["done"])} if r else \
        {"lessons": 0, "words": 0, "done": False}


def add(db, student_id, stats, pool_size, lessons=0, words=0, today=None):
    """Засчитывает действие в цель дня. Возвращает (строка дня, монет получено, только_что_выполнена)."""
    day = (today or date.today()).isoformat()
    row = today_row(db, student_id, today)
    row["lessons"] += lessons
    row["words"] += words
    nl, nw = needs(stats, pool_size, target(db, student_id))
    done = (nl or nw) and row["lessons"] >= nl and row["words"] >= nw
    just = bool(done) and not row["done"]
    db.execute("INSERT INTO daily_goal (student_id, day, lessons, words, done) VALUES (?, ?, ?, ?, ?) "
               "ON CONFLICT(student_id, day) DO UPDATE SET lessons=excluded.lessons, words=excluded.words, "
               "done=MAX(done, excluded.done)", (student_id, day, row["lessons"], row["words"], int(bool(done))))
    coins = 0
    if just:
        from garden import get_garden
        get_garden(db, student_id)
        db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?", (GOAL_COINS, student_id))
        coins = GOAL_COINS
        import farm
        farm.on_goal_done(db, student_id, today)
    db.commit()
    row["done"] = row["done"] or bool(done)
    return row, coins, just


def goal_days(db, student_id=None):
    if student_id is None:
        return db.execute("SELECT COUNT(*) FROM daily_goal WHERE done=1").fetchone()[0]
    return db.execute("SELECT COUNT(*) FROM daily_goal WHERE student_id=? AND done=1", (student_id,)).fetchone()[0]


def view(db, student_id, stats, pool_size):
    """Данные для карточки на главной."""
    nl, nw = needs(stats, pool_size, target(db, student_id))
    row = today_row(db, student_id)
    if not (nl or nw):
        return None
    return {"need_lessons": nl, "need_words": nw, "lessons": min(row["lessons"], nl) if nl else 0,
            "words": min(row["words"], nw) if nw else 0, "done": row["done"], "coins": GOAL_COINS}
