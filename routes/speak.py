# -*- coding: utf-8 -*-
"""Тренировка произношения: страница «Говорим» и сохранение оценок."""

import random
from datetime import datetime

import config
from achievements import public, update_achievements
from curriculum import ALL_LESSONS, LESSONS_BY_ID
from database import get_db
from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from mascot import build_mascot_ctx
from stats import compute_stats

from routes.common import get_student_or_none, require_role

bp = Blueprint("speak", __name__)

ROUND_SIZE = 10


def _pool(stats):
    """Фразы из пройденных уроков (без повторов); если ничего нет — из урока 1."""
    seen, pool = set(), []
    lessons = [l for l in ALL_LESSONS if l["id"] in stats["completed_ids"]] or [LESSONS_BY_ID[1]]
    for l in lessons:
        for it in l.get("speak", []):
            key = it["en"].lower()
            if key in seen:
                continue
            seen.add(key)
            pool.append({**it, "lesson": l["id"]})
    return pool, not stats["completed_ids"]


@bp.route("/student/speak")
def speak_page():
    if not config.SPEAKING:
        abort(404)
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    stats = compute_stats(db, student["id"])
    pool, fallback = _pool(stats)
    # слабые места вперёд: слова с низкой лучшей оценкой
    best = {r["target"].lower(): r["best"] for r in db.execute(
        "SELECT target, MAX(score) AS best FROM speaking WHERE student_id=? GROUP BY target",
        (student["id"],)).fetchall()}
    rng = random.Random()
    rng.shuffle(pool)
    pool.sort(key=lambda it: best.get(it["en"].lower(), -1) >= 3)   # неидеальные — первыми
    items = pool[:ROUND_SIZE]
    rng.shuffle(items)
    mascot = build_mascot_ctx()
    mascot["page"] = "speak"
    return render_template("speak.html", mascot=mascot, items=items, fallback=fallback,
                           pool_size=len(pool), stats=stats, name=student["display_name"])


@bp.route("/api/speak", methods=["POST"])
def api_speak():
    """Запоминает оценку за произнесённое слово. Звук на сервер не отправляется."""
    if not config.SPEAKING:
        abort(404)
    if session.get("role") != "student":
        abort(403)
    data = request.get_json(silent=True) or {}
    target = str(data.get("target", "")).strip()
    try:
        score = int(data.get("score"))
        lesson_id = int(data.get("lesson") or 0)
    except (TypeError, ValueError):
        abort(400)
    if not 1 <= len(target) <= 80 or not 0 <= score <= 3:
        abort(400)
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        abort(403)
    db.execute("INSERT INTO speaking (student_id, lesson_id, target, score, created_at) "
               "VALUES (?, ?, ?, ?, ?)",
               (student["id"], lesson_id if lesson_id in LESSONS_BY_ID else 0, target, score,
                datetime.now().isoformat(timespec="seconds")))
    db.commit()
    stats = compute_stats(db, student["id"])
    new = update_achievements(db, stats, student["id"])
    if new:
        keys = session.get("new_achievements") or []
        session["new_achievements"] = keys + [a["key"] for a in new]
    return jsonify(ok=True, words=stats["speak_words"], perfect=stats["speak_perfect"],
                   newAchievements=[public(a) for a in new])
