# -*- coding: utf-8 -*-
"""Истории: чтение с кликабельными словами и аудирование с вопросами."""

from datetime import datetime

import activity
from achievements import public, update_achievements
from curriculum import LESSONS_BY_ID
from data.stories import COMMON, STORIES, STORIES_BY_KEY, story_words
from database import get_db
from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from garden import get_garden
from mascot import build_mascot_ctx
from review import all_words
from stats import compute_stats

from routes.common import get_student_or_none, require_role

bp = Blueprint("stories", __name__)
STORY_COINS = 2          # монетки за первое прохождение истории в каждом режиме
MODES = ("read", "listen")
_DICT = None


def _course_dict():
    global _DICT
    if _DICT is None:
        _DICT = {w["en"].lower(): w["ru"] for w in all_words() if " " not in w["en"].strip()}
    return _DICT


def gloss_for(story):
    """{слово: перевод} для каждого слова истории: свой глоссарий > слова курса > служебные слова."""
    own, course = story.get("gloss", {}), _course_dict()
    return {w: own.get(w) or course.get(w) or COMMON.get(w, "") for w in story_words(story)}


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


def _done_map(db, sid):
    rows = db.execute("SELECT key, mode, best FROM story_done WHERE student_id=?", (sid,)).fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["key"], {})[r["mode"]] = r["best"]
    return out


@bp.route("/student/stories")
def stories_page():
    db, student, err = _student()
    if err:
        return err
    stats = compute_stats(db, student["id"])
    done = _done_map(db, student["id"])
    items = []
    for s in STORIES:
        lesson = LESSONS_BY_ID[s["lesson"]]
        items.append({"key": s["key"], "title": s["title"], "emoji": s["emoji"], "open": s["lesson"] in stats["completed_ids"],
                      "lesson_num": lesson.get("num"), "lesson_title": lesson["title"], "done": done.get(s["key"], {})})
    mascot = build_mascot_ctx()
    mascot["page"] = "stories"
    mascot["empty"] = not any(i["open"] for i in items)
    return render_template("stories.html", mascot=mascot, items=items, total=len(STORIES),
                           opened=sum(1 for i in items if i["open"]))


@bp.route("/student/stories/<key>")
def story_page(key):
    story = STORIES_BY_KEY.get(key) or abort(404)
    db, student, err = _student()
    if err:
        return err
    stats = compute_stats(db, student["id"])
    if story["lesson"] not in stats["completed_ids"]:
        abort(403)
    mode = request.args.get("mode", "read")
    if mode not in MODES:
        mode = "read"
    mascot = build_mascot_ctx()
    mascot["page"] = "stories"
    data = {"key": story["key"], "title": story["title"], "emoji": story["emoji"], "mode": mode,
            "sentences": story["sentences"], "gloss": gloss_for(story), "questions": story["questions"]}
    return render_template("story.html", mascot=mascot, story=data, done=_done_map(db, student["id"]).get(key, {}))


@bp.route("/api/story", methods=["POST"])
def api_story():
    if session.get("role") != "student":
        abort(403)
    data = request.get_json(silent=True) or {}
    story = STORIES_BY_KEY.get(str(data.get("key", ""))) or abort(400)
    mode = data.get("mode")
    try:
        correct = int(data.get("correct"))
    except (TypeError, ValueError):
        abort(400)
    if mode not in MODES or not 0 <= correct <= len(story["questions"]):
        abort(400)
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        abort(403)
    stats = compute_stats(db, student["id"])
    if story["lesson"] not in stats["completed_ids"]:
        abort(403)
    sid = student["id"]
    first = db.execute("SELECT 1 FROM story_done WHERE student_id=? AND key=? AND mode=?", (sid, story["key"], mode)).fetchone() is None
    db.execute("INSERT INTO story_done (student_id, key, mode, best, done_at) VALUES (?, ?, ?, ?, ?) "
               "ON CONFLICT(student_id, key, mode) DO UPDATE SET best=MAX(best, excluded.best), done_at=excluded.done_at",
               (sid, story["key"], mode, correct, datetime.now().isoformat(timespec="seconds")))
    coins = 0
    if first:
        get_garden(db, sid)
        db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?", (STORY_COINS, sid))
        coins = STORY_COINS
    db.commit()
    activity.log(db, sid, "story")
    new = update_achievements(db, compute_stats(db, sid), sid)
    if new:
        session["new_achievements"] = (session.get("new_achievements") or []) + [a["key"] for a in new]
    return jsonify(ok=True, coins=coins, newAchievements=[public(a) for a in new])
