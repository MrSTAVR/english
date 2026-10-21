# -*- coding: utf-8 -*-
"""Письмо: «Собери предложение» и «Мини-диктант»."""

import random

import activity
from achievements import public, update_achievements
from database import get_db
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from mascot import build_mascot_ctx
from review import learned_pool, record
from stats import compute_stats
from writing import BUILD_ROUND, DICT_ROUND, MIN_SENTENCES, sentences_for

from routes.common import get_student_or_none, require_role

bp = Blueprint("writing", __name__)

MODES = {
    "build": {"title": "Собери предложение", "emoji": "🧩",
              "desc": "Смотри на русскую фразу и собери её по-английски из слов-кубиков."},
    "dictation": {"title": "Мини-диктант", "emoji": "✍️",
                  "desc": "Слушай предложение и напиши его по-английски. Кнопка 🔊 — послушать ещё раз."},
}


def _student():
    err = require_role("student")
    if err:
        return None, None, err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return None, None, redirect(url_for("auth.index"))
    return db, student, None


@bp.route("/student/writing")
def writing_hub():
    db, student, err = _student()
    if err:
        return err
    stats = compute_stats(db, student["id"])
    count = len(sentences_for(stats["completed_ids"]))
    best = {r["game"]: r["best"] for r in db.execute("SELECT game, best FROM game_scores WHERE student_id=?", (student["id"],)).fetchall()}
    mascot = build_mascot_ctx()
    mascot["page"] = "writing"
    mascot["empty"] = count < MIN_SENTENCES
    return render_template("writing.html", mascot=mascot, modes=MODES, best=best, count=count,
                           enough=count >= MIN_SENTENCES, need=MIN_SENTENCES)


@bp.route("/student/writing/<mode>")
def writing_play(mode):
    if mode not in MODES:
        abort(404)
    db, student, err = _student()
    if err:
        return err
    stats = compute_stats(db, student["id"])
    pool = sentences_for(stats["completed_ids"])
    if len(pool) < MIN_SENTENCES:
        flash("Для письма нужно пройти ещё пару уроков — фраз пока мало 🌱", "error")
        return redirect(url_for("writing.writing_hub"))
    rng = random.Random()
    if mode == "dictation":
        pool = [s for s in pool if len(s["en"].split()) <= 7] or pool
    rng.shuffle(pool)
    items = pool[:BUILD_ROUND if mode == "build" else DICT_ROUND]
    mascot = build_mascot_ctx()
    mascot["page"] = "writing"
    return render_template("write_play.html", mascot=mascot, mode=mode, info=MODES[mode], items=items)


@bp.route("/api/writing", methods=["POST"])
def api_writing():
    if session.get("role") != "student":
        abort(403)
    data = request.get_json(silent=True) or {}
    mode = data.get("mode")
    try:
        stars = int(data.get("stars"))
    except (TypeError, ValueError):
        abort(400)
    if mode not in MODES or not 0 <= stars <= 3:
        abort(400)
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        abort(403)
    sid = student["id"]
    db.execute("INSERT INTO game_scores (student_id, game, best, plays) VALUES (?, ?, ?, 1) "
               "ON CONFLICT(student_id, game) DO UPDATE SET plays=plays+1, best=MAX(best, excluded.best)", (sid, mode, stars))
    db.commit()
    activity.log(db, sid, "write")
    stats = compute_stats(db, sid)
    # слова, в которых ошиблись, попадают в «работу над ошибками» (только уже изученные слова)
    known = {w["key"] for w in learned_pool(stats)}
    for w in {str(x).strip().lower() for x in (data.get("wrong") or [])[:30]}:
        if w in known:
            record(db, sid, w, False)
    new = update_achievements(db, compute_stats(db, sid), sid)
    if new:
        session["new_achievements"] = (session.get("new_achievements") or []) + [a["key"] for a in new]
    return jsonify(ok=True, newAchievements=[public(a) for a in new])
