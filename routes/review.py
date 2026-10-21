# -*- coding: utf-8 -*-
"""Повторение слов (интервальное): страница раунда и запись ответов."""

from achievements import public, update_achievements
from database import get_db
from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from mascot import build_mascot_ctx
import goals
from review import MASTERED_BOX, build_round, counts, learned_pool, record, state
from stats import compute_stats

from routes.common import get_student_or_none, require_role

bp = Blueprint("review", __name__)


@bp.route("/student/review")
def review_page():
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    stats = compute_stats(db, student["id"])
    pool = learned_pool(stats)
    st = state(db, student["id"])
    due, new, mastered = counts(pool, st)
    extra = request.args.get("extra") == "1"
    questions = build_round(pool, st, extra=extra) if len(pool) >= 4 else []
    mascot = build_mascot_ctx()
    mascot["page"] = "review"
    mascot["empty"] = not pool
    return render_template("review.html", mascot=mascot, questions=questions, pool_size=len(pool),
                           due=due, new=new, mastered=mastered, extra=extra,
                           all_done=(not questions and len(pool) >= 4))


@bp.route("/api/review", methods=["POST"])
def api_review():
    if session.get("role") != "student":
        abort(403)
    data = request.get_json(silent=True) or {}
    key = str(data.get("key", "")).strip().lower()
    ok = bool(data.get("ok"))
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        abort(403)
    stats = compute_stats(db, student["id"])
    if key not in {w["key"] for w in learned_pool(stats)}:
        abort(400)                       # слово ещё не изучено — не записываем
    box = record(db, student["id"], key, ok)
    stats = compute_stats(db, student["id"])
    _row, goal_coins, goal_done = goals.add(db, student["id"], stats, len(learned_pool(stats)), words=1)
    stats = compute_stats(db, student["id"])             # цель дня могла дать ачивку
    new = update_achievements(db, stats, student["id"])
    if new:
        session["new_achievements"] = (session.get("new_achievements") or []) + [a["key"] for a in new]
    return jsonify(ok=True, box=box, mastered=stats["review_mastered"], correct=stats["review_correct"],
                   learned=box >= MASTERED_BOX, goalDone=goal_done, goalCoins=goal_coins,
                   newAchievements=[public(a) for a in new])
