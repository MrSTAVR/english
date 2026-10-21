# -*- coding: utf-8 -*-
"""Статистика успеваемости по попыткам."""

import json

from curriculum import LESSONS_BY_ID


def speaking_stats(db, student_id=None):
    """Итоги тренировки произношения: слов (≥2⭐), идеальных (3⭐), средняя оценка."""
    if student_id is None:
        rows = db.execute("SELECT student_id, target, MAX(score) AS best, COUNT(*) AS n, "
                          "SUM(score) AS total FROM speaking GROUP BY student_id, target").fetchall()
    else:
        rows = db.execute("SELECT student_id, target, MAX(score) AS best, COUNT(*) AS n, "
                          "SUM(score) AS total FROM speaking WHERE student_id=? GROUP BY target",
                          (student_id,)).fetchall()
    tries = sum(r["n"] for r in rows)
    return {
        "speak_words": sum(1 for r in rows if r["best"] >= 2),
        "speak_perfect": sum(1 for r in rows if r["best"] >= 3),
        "speak_tries": tries,
        "speak_avg": round(sum(r["total"] for r in rows) / tries, 1) if tries else 0,
    }


def compute_stats(db, student_id=None):
    """Статистика по попыткам — используется для ачивок и трекера.

    student_id=None — общая статистика (кабинет родителя),
    student_id=<id> — статистика конкретного ученика.
    """
    if student_id is None:
        rows = db.execute(
            "SELECT * FROM attempts WHERE finished_at IS NOT NULL "
            "ORDER BY finished_at ASC, id ASC").fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM attempts WHERE finished_at IS NOT NULL AND student_id=? "
            "ORDER BY finished_at ASC, id ASC", (student_id,)).fetchall()

    # Уроки, зачтённые родителем, — не настоящие попытки: они открывают следующие уроки
    # и считаются пройденными, но не влияют на «идеальные тесты», время и средний балл.
    credited = {}
    real_rows = []
    for r in rows:
        if r["manual"]:
            credited.setdefault(r["lesson_id"], r)
        else:
            real_rows.append(r)
    rows = real_rows

    best_by_lesson = {}   # лучший результат по каждому уроку
    max_streak = 0
    clean_run = 0        # текущая серия идеальных тестов подряд
    best_clean_run = 0   # лучшая серия
    has_perfect = False
    perfect_count = 0
    first_try_perfect = False
    total_seconds = 0
    total_mistakes = 0
    attempts_by_lesson = {}
    failed_lessons = set()
    comeback = early_bird = evening = False

    for r in rows:
        total_seconds += r["seconds_spent"] or 0
        try:
            details = json.loads(r["details_json"] or "{}")
        except Exception:
            details = {}
        results = details.get("results", [])
        streak = cur = 0
        for item in results:
            if item.get("correct"):
                cur += 1
                streak = max(streak, cur)
            else:
                cur = 0
        max_streak = max(max_streak, streak)

        lid = r["lesson_id"]
        attempts_by_lesson[lid] = attempts_by_lesson.get(lid, 0) + 1
        hour = None
        try:
            hour = int((r["finished_at"] or "")[11:13])
        except ValueError:
            pass
        if r["passed"]:
            if lid in failed_lessons:
                comeback = True
            if hour is not None:
                early_bird = early_bird or hour < 9
                evening = evening or hour >= 20
        else:
            failed_lessons.add(lid)
        if r["passed"]:
            if lid not in best_by_lesson or r["score_percent"] > best_by_lesson[lid]["score_percent"]:
                best_by_lesson[lid] = r
            if r["mistakes_json"] and len(json.loads(r["mistakes_json"])) == 0:
                has_perfect = True
                perfect_count += 1
                if attempts_by_lesson[lid] == 1:
                    first_try_perfect = True
                clean_run += 1
                best_clean_run = max(best_clean_run, clean_run)
            else:
                clean_run = 0
        else:
            clean_run = 0

        try:
            total_mistakes += len(json.loads(r["mistakes_json"] or "[]"))
        except Exception:
            pass

    for lid, r in credited.items():
        best_by_lesson.setdefault(lid, r)           # настоящая попытка важнее зачёта

    completed_ids = sorted(best_by_lesson.keys())
    real_best = [r for r in best_by_lesson.values() if not r["manual"]]
    main_ids = [i for i in completed_ids if not LESSONS_BY_ID[i].get("is_extra")]
    # уникальные слова: «Orange» в уроках про цвета и про фрукты — одно слово
    words_learned = len({w["en"].strip().lower()
                         for i in completed_ids for w in LESSONS_BY_ID[i]["material"]})
    speak = speaking_stats(db, student_id)

    return {
        "attempts": rows,
        "best_by_lesson": best_by_lesson,
        "lessons_completed": len(main_ids),          # только основной курс
        "extras_completed": len(completed_ids) - len(main_ids),
        "completed_ids": set(completed_ids),
        "credited_ids": {lid for lid, r in best_by_lesson.items() if r["manual"]},
        "avg_score": (sum(r["score_percent"] for r in real_best) / len(real_best))
                     if real_best else 0.0,
        "total_seconds": total_seconds,
        "total_minutes": round(total_seconds / 60),
        "max_streak": max_streak,
        "best_clean_run": best_clean_run,
        "has_perfect": has_perfect,
        "perfect_count": perfect_count,
        "first_try_perfect": first_try_perfect,
        "words_learned": words_learned,
        **speak,
        "total_mistakes": total_mistakes,
        "comeback": comeback,
        "early_bird": early_bird,
        "evening": evening,
    }
