# -*- coding: utf-8 -*-
"""Недельный отчёт родителю: что ребёнок делал с понедельника по воскресенье."""
import json
from collections import Counter
from datetime import datetime, timedelta

from activity import week_start
from curriculum import LESSONS_BY_ID
from garden import vacation_days

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
KINDS = [("lesson", "📚", "уроков сдано"), ("game", "🎮", "игр"), ("story", "📖", "историй"),
         ("dialog", "💬", "диалогов"), ("write", "✏️", "заданий на письмо")]
MAX_WEEKS_BACK = 52


def week_report(db, student_id, weeks_back=0, today=None):
    """Сводка за неделю: weeks_back=0 — текущая, 1 — прошлая и т.д."""
    today = today or datetime.now().date()
    monday = week_start(today) - timedelta(weeks=weeks_back)
    sunday = monday + timedelta(days=6)
    a, b = monday.isoformat(), sunday.isoformat()

    days = {(monday + timedelta(days=i)).isoformat(): {"label": WEEKDAYS[i], "date": monday + timedelta(days=i),
                                                     "acts": 0, "seconds": 0, "words": 0, "goal": False}
            for i in range(7)}
    kinds = Counter()
    for r in db.execute("SELECT day, kind FROM activity WHERE student_id=? AND day>=? AND day<=?",
                        (student_id, a, b)):
        kinds[r["kind"]] += 1
        if r["day"] in days:
            days[r["day"]]["acts"] += 1
    for r in db.execute("SELECT day, words, done FROM daily_goal WHERE student_id=? AND day>=? AND day<=?",
                        (student_id, a, b)):
        if r["day"] in days:
            days[r["day"]]["words"] = r["words"]
            days[r["day"]]["goal"] = bool(r["done"])

    attempts = db.execute(
        "SELECT * FROM attempts WHERE student_id=? AND finished_at IS NOT NULL AND COALESCE(manual, 0)=0 "
        "AND substr(finished_at, 1, 10)>=? AND substr(finished_at, 1, 10)<=? ORDER BY finished_at",
        (student_id, a, b)).fetchall()
    lessons, mistakes = [], Counter()
    for r in attempts:
        day = r["finished_at"][:10]
        days[day]["seconds"] += r["seconds_spent"] or 0
        lesson = LESSONS_BY_ID.get(r["lesson_id"], {})
        lessons.append({"title": lesson.get("title", f"Урок {r['lesson_id']}"),
                        "day": WEEKDAYS[(datetime.fromisoformat(day).date() - monday).days],
                        "score": round(r["score_percent"] or 0), "passed": bool(r["passed"])})
        try:
            results = json.loads(r["details_json"] or "{}").get("results", [])
        except ValueError:
            results = []
        for res in results:
            if not res.get("correct"):
                mistakes[(res.get("q", ""), res.get("correct_answer", ""))] += 1

    vac = vacation_days(db, student_id)
    for d in days.values():
        d["vacation"] = d["date"] in vac
        d["future"] = d["date"] > today
        d["active"] = bool(d["acts"] or d["seconds"] or d["words"])
        d["minutes"] = round(d["seconds"] / 60)

    hard = db.execute(
        "SELECT key, n_bad, box FROM word_review WHERE student_id=? AND n_bad>0 "
        "AND substr(last_at, 1, 10)>=? AND substr(last_at, 1, 10)<=? ORDER BY n_bad DESC, box ASC, key LIMIT 8",
        (student_id, a, b)).fetchall()
    total_seconds = sum(d["seconds"] for d in days.values())
    scores = [l["score"] for l in lessons]
    return {
        "weeks_back": weeks_back, "monday": monday, "sunday": sunday,
        "days": list(days.values()),
        "active_days": sum(1 for d in days.values() if d["active"]),
        "goal_days": sum(1 for d in days.values() if d["goal"]),
        "minutes": round(total_seconds / 60),
        "words": sum(d["words"] for d in days.values()),
        "kinds": [{"emoji": e, "label": t, "n": kinds.get(k, 0)} for k, e, t in KINDS],
        "lessons": lessons,
        "passed": sum(1 for l in lessons if l["passed"]),
        "avg_score": round(sum(scores) / len(scores)) if scores else None,
        "mistakes_total": sum(mistakes.values()),
        "top_mistakes": [{"q": q, "correct": c, "n": n} for (q, c), n in mistakes.most_common(5)],
        "hard_words": [dict(r) for r in hard],
    }


# ---------------------------------------------------------------- прогресс за несколько недель

def activity_heatmap(db, student_id, weeks=12, today=None):
    """Календарь «сколько занималась» по дням: недели (колонки) × дни (строки), уровень 0–4."""
    today = today or datetime.now().date()
    first = week_start(today) - timedelta(weeks=weeks - 1)
    a, b = first.isoformat(), today.isoformat()
    score = Counter()
    for r in db.execute("SELECT day, COUNT(*) n FROM activity WHERE student_id=? AND day>=? AND day<=? GROUP BY day",
                        (student_id, a, b)):
        score[r["day"]] += r["n"]
    for r in db.execute("SELECT day, words FROM daily_goal WHERE student_id=? AND day>=? AND day<=?", (student_id, a, b)):
        score[r["day"]] += (r["words"] or 0) // 5                  # каждые 5 слов повторения — как одно занятие
    for r in db.execute("SELECT substr(finished_at, 1, 10) d, COUNT(*) n FROM attempts WHERE student_id=? "
                        "AND finished_at IS NOT NULL AND COALESCE(manual, 0)=0 AND substr(finished_at, 1, 10)>=? "
                        "GROUP BY d", (student_id, a)):
        score[r["d"]] += r["n"]
    cols = []
    for w in range(weeks):
        col = []
        for i in range(7):
            d = first + timedelta(weeks=w, days=i)
            n = score.get(d.isoformat(), 0)
            col.append({"date": d, "n": n, "future": d > today,
                        "level": 0 if n == 0 else 1 if n == 1 else 2 if n <= 3 else 3 if n <= 6 else 4})
        cols.append(col)
    return {"weeks": cols, "active_days": sum(1 for c in cols for d in c if d["n"]),
            "first": first, "labels": WEEKDAYS}


def score_trend(db, student_id, weeks=12, today=None):
    """Средний балл тестов по неделям (только настоящие попытки): [{"label", "avg" или None, "n"}]."""
    today = today or datetime.now().date()
    first = week_start(today) - timedelta(weeks=weeks - 1)
    rows = db.execute("SELECT substr(finished_at, 1, 10) d, score_percent s FROM attempts WHERE student_id=? "
                      "AND finished_at IS NOT NULL AND COALESCE(manual, 0)=0 AND substr(finished_at, 1, 10)>=?",
                      (student_id, first.isoformat())).fetchall()
    buckets = [[] for _ in range(weeks)]
    for r in rows:
        idx = (datetime.fromisoformat(r["d"]).date() - first).days // 7
        if 0 <= idx < weeks:
            buckets[idx].append(r["s"] or 0)
    return [{"label": (first + timedelta(weeks=i)).strftime("%d.%m"), "n": len(v),
             "avg": round(sum(v) / len(v)) if v else None} for i, v in enumerate(buckets)]


def hard_words(db, student_id, limit=10):
    """Слова, в которых больше всего ошибок и которые ещё не выучены."""
    from review import MASTERED_BOX, all_words
    by_key = {w["key"]: w for w in all_words()}
    rows = db.execute("SELECT key, n_bad, n_ok, box FROM word_review WHERE student_id=? AND n_bad>0 AND box<? "
                      "ORDER BY n_bad DESC, box ASC, key LIMIT ?", (student_id, MASTERED_BOX, limit)).fetchall()
    return [{"key": r["key"], "en": by_key.get(r["key"], {}).get("en", r["key"]),
             "ru": by_key.get(r["key"], {}).get("ru", ""), "bad": r["n_bad"], "ok": r["n_ok"], "box": r["box"]}
            for r in rows]
