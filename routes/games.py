# -*- coding: utf-8 -*-
"""Игры со словами и мини-диалоги."""

import random
from datetime import datetime

from achievements import public, update_achievements
from curriculum import ALL_LESSONS, LESSONS_BY_ID, unlocked_lesson_ids
from data.dialogs import DIALOGS, DIALOGS_BY_KEY, character
from database import get_db
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from mascot import build_mascot_ctx
from practice import pool_from
from review import all_words, learned_pool
from stats import compute_stats

from routes.common import get_student_or_none, require_role

bp = Blueprint("games", __name__)

GAMES = {
    "pairs": {"title": "Найди пару", "emoji": "⚡", "desc": "Соедини английское слово с переводом — как можно быстрее."},
    "memory": {"title": "Мемори", "emoji": "🃏", "desc": "Переворачивай карточки и находи одинаковые пары."},
    "blitz": {"title": "Блиц 60 секунд", "emoji": "⏱️", "desc": "Сколько слов успеешь перевести за минуту?"},
}
MIN_WORDS = 4


def _student():
    err = require_role("student")
    if err:
        return None, err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return None, redirect(url_for("auth.index"))
    return (db, student), None


def _pool(db, student, lesson_id):
    """Слова для игры: из одного урока (если открыт) или все выученные."""
    stats = compute_stats(db, student["id"])
    if lesson_id:
        lesson = LESSONS_BY_ID.get(lesson_id) or abort(404)
        if lesson_id not in unlocked_lesson_ids(stats):
            abort(403)
        return pool_from([lesson]), lesson, stats
    return learned_pool(stats), None, stats


@bp.route("/student/games")
def games_hub():
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    lesson_id = request.args.get("lesson", type=int)
    pool, lesson, stats = _pool(db, student, lesson_id)
    best = {r["game"]: r for r in db.execute(
        "SELECT game, best, plays FROM game_scores WHERE student_id=?", (student["id"],)).fetchall()}
    mascot = build_mascot_ctx()
    mascot["page"] = "games"
    mascot["empty"] = len(pool) < MIN_WORDS
    return render_template("games.html", mascot=mascot, games=GAMES, best=best, lesson=lesson,
                           pool_size=len(pool), enough=len(pool) >= MIN_WORDS)


@bp.route("/student/games/play/<game>")
def game_play(game):
    if game not in GAMES:
        abort(404)
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    lesson_id = request.args.get("lesson", type=int)
    pool, lesson, stats = _pool(db, student, lesson_id)
    if len(pool) < MIN_WORDS:
        flash("Для игры нужно хотя бы 4 слова — пройди ещё урок! 🌱", "error")
        return redirect(url_for("games.games_hub", lesson=lesson_id) if lesson_id else url_for("games.games_hub"))
    rng = random.Random()
    words = pool[:]
    rng.shuffle(words)
    others = [w for w in all_words() if w["key"] not in {x["key"] for x in words}]
    rng.shuffle(others)
    keep = ("key", "en", "ru", "hint", "pic")
    mascot = build_mascot_ctx()
    mascot["page"] = "games"
    return render_template("game.html", mascot=mascot, game=game, info=GAMES[game], lesson=lesson,
                           words=[{k: w[k] for k in keep} for w in words[:40]],
                           distract=[{k: w[k] for k in keep} for w in others[:30]])


@bp.route("/api/game", methods=["POST"])
def api_game():
    if session.get("role") != "student":
        abort(403)
    data = request.get_json(silent=True) or {}
    game = data.get("game")
    try:
        stars = int(data.get("stars"))
    except (TypeError, ValueError):
        abort(400)
    if game not in GAMES or not 0 <= stars <= 3:
        abort(400)
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        abort(403)
    db.execute("INSERT INTO game_scores (student_id, game, best, plays) VALUES (?, ?, ?, 1) "
               "ON CONFLICT(student_id, game) DO UPDATE SET plays=plays+1, best=MAX(best, excluded.best)",
               (student["id"], game, stars))
    db.commit()
    stats = compute_stats(db, student["id"])
    new = update_achievements(db, stats, student["id"])
    if new:
        session["new_achievements"] = (session.get("new_achievements") or []) + [a["key"] for a in new]
    return jsonify(ok=True, plays=stats["games_played"], newAchievements=[public(a) for a in new])


def _dialog_payload(d, done):
    return {"key": d["key"], "title": d["title"], "partner": d["partner"], "lines": d["lines"],
            "done": d["key"] in done, "lesson": d["lesson"], "who": character(d["partner"])}


def dialogs_for(db, student_id, lesson_ids):
    done = {r["key"] for r in db.execute("SELECT key FROM dialog_done WHERE student_id=?", (student_id,)).fetchall()}
    return [_dialog_payload(d, done) for d in DIALOGS if d["lesson"] in lesson_ids]


@bp.route("/student/dialogs")
def dialogs_page():
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    stats = compute_stats(db, student["id"])
    lesson_id = request.args.get("lesson", type=int)
    if lesson_id:
        if lesson_id not in unlocked_lesson_ids(stats):
            abort(403)
        ids = {lesson_id}
    else:
        ids = set(stats["completed_ids"])
    dialogs = dialogs_for(db, student["id"], ids)
    mascot = build_mascot_ctx()
    mascot["page"] = "dialogs"
    mascot["empty"] = not dialogs
    return render_template("dialogs.html", mascot=mascot, dialogs=dialogs, total=len(DIALOGS),
                           lesson=LESSONS_BY_ID.get(lesson_id) if lesson_id else None,
                           me_emoji=student["emoji"] or "🎒", me_name=student["display_name"])


@bp.route("/api/dialog", methods=["POST"])
def api_dialog():
    if session.get("role") != "student":
        abort(403)
    key = str((request.get_json(silent=True) or {}).get("key", ""))
    if key not in DIALOGS_BY_KEY:
        abort(400)
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        abort(403)
    db.execute("INSERT OR IGNORE INTO dialog_done (student_id, key, done_at) VALUES (?, ?, ?)",
               (student["id"], key, datetime.now().isoformat(timespec="seconds")))
    db.commit()
    stats = compute_stats(db, student["id"])
    new = update_achievements(db, stats, student["id"])
    if new:
        session["new_achievements"] = (session.get("new_achievements") or []) + [a["key"] for a in new]
    return jsonify(ok=True, done=stats["dialogs_done"], newAchievements=[public(a) for a in new])
