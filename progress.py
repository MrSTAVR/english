# -*- coding: utf-8 -*-
"""Зачёт уроков родителем: перенос прогресса (например, из локальной версии) без повторного прохождения."""

from datetime import datetime

from curriculum import LESSONS_BY_ID, MAIN_COUNT
from stats import compute_stats


def lesson_ids_upto(n):
    """Основные уроки с 1 по n (n ограничено размером курса)."""
    return set(range(1, max(0, min(int(n), MAIN_COUNT)) + 1))


def credit_lessons(db, student_id, lesson_ids, now=None):
    """Засчитывает уроки как пройденные. Уже пройденные не трогает. Возвращает список зачтённых id."""
    now = (now or datetime.now()).isoformat(timespec="seconds")
    done = compute_stats(db, student_id)["completed_ids"]
    added = []
    for lid in sorted(set(lesson_ids) & set(LESSONS_BY_ID)):
        if lid in done:
            continue
        db.execute(
            "INSERT INTO attempts (student_id, lesson_id, started_at, finished_at, seconds_spent, "
            "score_percent, passed, total_q, correct_q, mistakes_json, details_json, manual) "
            "VALUES (?, ?, ?, ?, 0, 100, 1, 0, 0, '[]', '{}', 1)",
            (student_id, lid, now, now))
        added.append(lid)
    db.commit()
    return added


def uncredit_lessons(db, student_id, lesson_ids):
    """Снимает зачёт (только зачёт родителя; настоящие попытки не удаляются)."""
    removed = []
    for lid in sorted(set(lesson_ids)):
        cur = db.execute("DELETE FROM attempts WHERE student_id=? AND lesson_id=? AND manual=1",
                         (student_id, lid))
        if cur.rowcount:
            removed.append(lid)
    db.commit()
    return removed
