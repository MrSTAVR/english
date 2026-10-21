# -*- coding: utf-8 -*-
"""Режим ученика: список уроков, урок, сдача теста."""

import json
from badges import TIERS
from achievements import (ACHIEVEMENTS, BY_KEY, CATEGORIES, public, tier_counts,
                          update_achievements, views as achievement_views)
import config
from config import PASS_MARK
from curriculum import ALL_LESSONS, LESSONS, LESSONS_BY_ID, unlocked_lesson_ids
from data.extra_lessons import EXTRA_LESSONS
from database import get_db
from datetime import datetime
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from garden import award_coins, get_garden, refresh_garden, touch_streak, tree_count_for, tree_stage
from grading import grade_question
from mascot import build_mascot_ctx
from stats import compute_stats

from routes.common import get_student_or_none, require_role

bp = Blueprint("student", __name__)


@bp.route("/student/theory")
def theory_page():
    """Теория из всех пройденных (и зачтённых) уроков."""
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    stats = compute_stats(db, student["id"])
    lessons = [l for l in ALL_LESSONS if l["id"] in stats["completed_ids"] and l.get("theory")]
    mascot = build_mascot_ctx()
    mascot["empty"] = not lessons
    return render_template("theory.html", mascot=mascot, lessons=lessons)


@bp.route("/student/words")
def words_page():
    """Словарь ученика: все слова из пройденных (и зачтённых) уроков."""
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    stats = compute_stats(db, student["id"])
    groups = [{"lesson": l, "words": l["material"]}
              for l in ALL_LESSONS if l["id"] in stats["completed_ids"]]
    mascot = build_mascot_ctx()
    mascot["empty"] = not groups
    return render_template("words.html", mascot=mascot, groups=groups,
                           total_words=sum(len(g["words"]) for g in groups),
                           name=student["display_name"], emoji=student["emoji"])


@bp.route("/student")
def student_home():
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        flash("Аккаунт был удалён родителем. Войди заново 🙂", "error")
        return redirect(url_for("auth.index"))
    stats = compute_stats(db, student["id"])
    garden = refresh_garden(db, student["id"])
    unlocked = unlocked_lesson_ids(stats)

    def lesson_info(l):
        best = stats["best_by_lesson"].get(l["id"])
        credited = l["id"] in stats["credited_ids"]
        return {
            "lesson": l,
            "locked": l["id"] not in unlocked,
            "done": l["id"] in stats["completed_ids"],
            "credited": credited,
            "best_score": best["score_percent"] if best and not credited else None,
        }

    lessons_info = [lesson_info(l) for l in LESSONS]
    extra_info = [lesson_info(l) for l in EXTRA_LESSONS]
    extras_done = sum(1 for i in extra_info if i["done"])
    achievements = achievement_views(db, stats, student["id"])
    new_keys = session.pop("new_achievements", None) or []
    new_badge = [a for a in achievements if a["key"] in new_keys]
    ach_recent = sorted((a for a in achievements if a["earned"]),
                        key=lambda a: a["earned_at"] or "", reverse=True)[:8]
    ach_next = sorted((a for a in achievements if not a["earned"] and a["progress"]),
                      key=lambda a: -a["progress"][2])[:3]
    mascot = build_mascot_ctx()
    mascot["alreadyStarted"] = bool(stats["attempts"] or stats["completed_ids"])
    mascot["allDone"] = stats["lessons_completed"] >= len(LESSONS)
    # Следующий непройденный доступный урок (для крупной кнопки «Продолжить»)
    next_lesson = None
    for l in LESSONS:
        if l["id"] in unlocked and l["id"] not in stats["completed_ids"]:
            next_lesson = l
            break
    # Компактный вид блока «Мои уроки»: последний пройденный, следующий
    # доступный и первый закрытый. Остальные — за кнопкой «показать все».
    last_done_id = None
    for info in reversed(lessons_info):
        if info["done"]:
            last_done_id = info["lesson"]["id"]
            break
    next_id = next_lesson["id"] if next_lesson else None
    first_locked_id = None
    for info in lessons_info:
        if info["locked"]:
            first_locked_id = info["lesson"]["id"]
            break
    highlight_ids = {i for i in (last_done_id, next_id, first_locked_id) if i}
    for info in lessons_info:
        info["highlight"] = info["lesson"]["id"] in highlight_ids
    hidden_count = sum(1 for info in lessons_info if not info["highlight"])
    earned_count = sum(1 for a in achievements if a["earned"])
    return render_template("student_home.html", mascot=mascot, speaking=config.SPEAKING,
                           name=student["display_name"],
                           emoji=student["emoji"],
                           lessons=lessons_info,
                           hidden_lessons_count=hidden_count,
                           extra_lessons=extra_info,
                           extras_done=extras_done,
                           total_extras=len(EXTRA_LESSONS),
                           stats=stats,
                           achievements=achievements, ach_recent=ach_recent, ach_next=ach_next,
                           total_lessons=len(LESSONS),
                           new_badge=new_badge,
                           next_lesson=next_lesson,
                           earned_count=earned_count,
                           garden=garden,
                           tree_stage=tree_stage(garden["streak_days"]),
                           tree_count=tree_count_for(garden["streak_days"]))


@bp.route("/lesson/<int:lesson_id>")
def lesson_page(lesson_id):
    err = require_role("student")
    if err:
        return err
    lesson = LESSONS_BY_ID.get(lesson_id) or abort(404)
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    stats = compute_stats(db, student["id"])
    if lesson_id not in unlocked_lesson_ids(stats):
        flash("Сначала пройди предыдущий урок! 😉", "error")
        return redirect(url_for("student.student_home"))
    touch_streak(db, student["id"])   # занялись сегодня — серия дня продлевается
    # Создаём новую попытку (начало занятия)
    started = datetime.now()
    cur = db.execute(
        "INSERT INTO attempts (student_id, lesson_id, started_at) VALUES (?, ?, ?)",
        (student["id"], lesson_id, started.isoformat(timespec="seconds")))
    db.commit()
    mascot = build_mascot_ctx()
    mascot["lessonId"] = lesson_id
    mascot["lessonTitle"] = lesson["title"]
    return render_template("lesson.html", lesson=lesson, speaking=config.SPEAKING,
                           attempt_id=cur.lastrowid,
                           started_ts=started.timestamp(),
                           mascot=mascot)


@bp.route("/lesson/<int:lesson_id>/submit", methods=["POST"])
def submit_test(lesson_id):
    err = require_role("student")
    if err:
        return err
    lesson = LESSONS_BY_ID.get(lesson_id) or abort(404)
    attempt_id = request.form.get("attempt_id", type=int)
    seconds = request.form.get("seconds", type=int) or 0
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    attempt = db.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
    if not attempt or attempt["finished_at"] or attempt["student_id"] != student["id"]:
        abort(400)

    test = lesson["test"]
    results, mistakes = [], []
    correct = 0
    for i, q in enumerate(test):
        if q["type"] == "choice":
            raw = request.form.get(f"q{i}")
            given = int(raw) if raw is not None and raw.isdigit() else -1
        elif q["type"] == "order":
            raw = request.form.get(f"q{i}_order", "")
            given = raw
        elif q["type"] in ("match", "sort"):
            # скрытые поля заполняет drag&drop-скрипт перед отправкой
            given = request.form.get(f"q{i}_{q['type']}", "")
        else:
            given = request.form.get(f"q{i}", "")
        ok, correct_disp = grade_question(q, given)
        if ok:
            correct += 1
        else:
            mistakes.append({"question": q["q"],
                             "given": str(given if given != -1 else "(пусто)"),
                             "correct": str(correct_disp)})
        results.append({"q": q["q"], "type": q["type"],
                        "given": str(given if given != -1 else ""),
                        "correct_answer": str(correct_disp),
                        "explain": q.get("explain", ""),
                        "correct": bool(ok)})

    total = len(test)
    percent = round(100 * correct / total) if total else 0
    passed = percent >= PASS_MARK
    finished = datetime.now()
    db.execute(
        """UPDATE attempts SET finished_at=?, seconds_spent=?, score_percent=?,
           passed=?, total_q=?, correct_q=?, mistakes_json=?, details_json=? WHERE id=?""",
        (finished.isoformat(timespec="seconds"), seconds, percent, int(passed),
         total, correct, json.dumps(mistakes, ensure_ascii=False),
         json.dumps({"results": results}, ensure_ascii=False), attempt_id))
    db.commit()

    stats = compute_stats(db, student["id"])
    new_achievements = update_achievements(db, stats, student["id"])
    if new_achievements:
        session["new_achievements"] = [a["key"] for a in new_achievements]

    coins_earned = award_coins(db, student["id"], percent, passed)
    garden = get_garden(db, student["id"])

    mascot = build_mascot_ctx()
    mascot["percent"] = percent
    mascot["passed"] = passed
    mascot["coinsEarned"] = coins_earned
    mascot["newAchievements"] = [public(a) for a in new_achievements]
    return render_template("result.html", mascot=mascot,
                           lesson=lesson, percent=percent, passed=passed,
                           correct=correct, total=total,
                           seconds=seconds, results=results,
                           coins_earned=coins_earned,
                           coins_total=garden["coins"],
                           streak_days=garden["streak_days"],
                           tier_names={k: v["name"] for k, v in TIERS.items()},
                           new_achievements=[a for a in ACHIEVEMENTS
                                             if a["key"] in [n["key"] for n in new_achievements]])


@bp.route("/student/achievements")
def achievements_page():
    """Коллекция наград: медали по категориям, шкалы прогресса, счётчики по уровням."""
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    items = achievement_views(db, compute_stats(db, student["id"]), student["id"])
    groups = [{"key": k, "name": n, "emoji": e, "items": [i for i in items if i["cat"] == k]}
              for k, n, e in CATEGORIES]
    mascot = build_mascot_ctx()
    mascot["earned"] = sum(1 for i in items if i["earned"])
    mascot["total"] = len(items)
    return render_template("achievements.html", mascot=mascot, groups=groups,
                           earned=mascot["earned"], total=len(items),
                           tiers=tier_counts(items))
