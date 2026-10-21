# -*- coding: utf-8 -*-
"""Недельный челлендж и босс недели."""
import random
from datetime import datetime

import activity

WEEKLY_COINS = 15
BOSS_COINS = 10
BOSS_QUESTIONS = 10
BOSS_LIVES = 3
MIN_BOSS_WORDS = 8

TASKS = {
    "lesson": {"emoji": "📚", "text": "Пройди уроки", "need": 2},
    "game": {"emoji": "🎮", "text": "Сыграй в игры", "need": 4},
    "dialog": {"emoji": "💬", "text": "Пройди диалоги", "need": 3},
    "story": {"emoji": "📖", "text": "Прочитай или послушай истории", "need": 2},
    "write": {"emoji": "✍️", "text": "Выполни письменные задания", "need": 3},
}
BOSSES = [("🐉", "Дракон Грамматикон"), ("👹", "Тролль Спеллинг"), ("🦖", "Рекс-Словоед"), ("🧟", "Зомби Забывака")]

# Награды босса, которых нет в магазине: число побед -> наряд
BOSS_REWARDS = [(1, "hat-knight"), (3, "neck-cape")]


def pick_tasks(week):
    """Три задания недели: урок + игра + одно из (диалог/история/письмо) — по номеру недели."""
    rng = random.Random(week.isoformat())
    return ["lesson", "game", rng.choice(["dialog", "story", "write"])]


def boss_of(week):
    return BOSSES[(week.toordinal() // 7) % len(BOSSES)]


def status(db, student_id, today=None):
    week = activity.week_start(today)
    c = activity.counts(db, student_id, week)
    tasks = []
    for k in pick_tasks(week):
        t = TASKS[k]
        have = min(c.get(k, 0), t["need"])
        tasks.append({"kind": k, "emoji": t["emoji"], "text": t["text"], "need": t["need"],
                      "have": have, "done": have >= t["need"]})
    row = db.execute("SELECT boss_won FROM weekly_done WHERE student_id=? AND week=?",
                     (student_id, week.isoformat())).fetchone()
    done_all = all(t["done"] for t in tasks)
    emoji, name = boss_of(week)
    return {"week": week, "tasks": tasks, "complete": done_all, "claimed": row is not None,
            "boss_won": bool(row and row["boss_won"]), "boss_emoji": emoji, "boss_name": name,
            "days_left": 6 - ((today or datetime.now().date()) - week).days}


def claim(db, student_id, today=None):
    """Если все задания выполнены и награда ещё не выдана — выдаёт монетки. -> монетки (0 если нет)."""
    from garden import get_garden
    st = status(db, student_id, today)
    if not st["complete"] or st["claimed"]:
        return 0
    get_garden(db, student_id)
    db.execute("INSERT OR IGNORE INTO weekly_done (student_id, week) VALUES (?,?)", (student_id, st["week"].isoformat()))
    db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?", (WEEKLY_COINS, student_id))
    db.commit()
    return WEEKLY_COINS


def weeks_done(db, student_id):
    return db.execute("SELECT COUNT(*) FROM weekly_done WHERE student_id=?", (student_id,)).fetchone()[0]


def boss_wins(db, student_id):
    return db.execute("SELECT COUNT(*) FROM boss_wins WHERE student_id=?", (student_id,)).fetchone()[0]


def win_boss(db, student_id, today=None):
    """Победа над боссом. -> (coins, [ключи новых наград]). Один раз за неделю, только после челленджа."""
    from garden import get_garden
    from wardrobe import grant
    st = status(db, student_id, today)
    if not (st["complete"] and st["claimed"]) or st["boss_won"]:
        return 0, []
    get_garden(db, student_id)
    wk = st["week"].isoformat()
    db.execute("UPDATE weekly_done SET boss_won=1 WHERE student_id=? AND week=?", (student_id, wk))
    db.execute("INSERT OR IGNORE INTO boss_wins (student_id, week) VALUES (?,?)", (student_id, wk))
    db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?", (BOSS_COINS, student_id))
    db.commit()
    n = boss_wins(db, student_id)
    new = [key for need, key in BOSS_REWARDS if n >= need and grant(db, student_id, key)]
    return BOSS_COINS, new
