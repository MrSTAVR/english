# -*- coding: utf-8 -*-
"""Недельный челлендж, босс недели и сезон Хэллоуин."""

import random
from datetime import datetime

import weekly
from achievements import public, update_achievements
from data.halloween import DAILY_COINS, PASS_MARK, PHRASE, QUIZ_LEN, WORDS
from database import get_db
from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from garden import get_garden
from mascot import build_mascot_ctx
from review import all_words, learned_pool
from seasons import active_season
from stats import compute_stats
from wardrobe import ITEMS_BY_KEY

from routes.common import get_student_or_none, require_role

bp = Blueprint("season", __name__)


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


def _push_achievements(db, sid):
    new = update_achievements(db, compute_stats(db, sid), sid)
    if new:
        session["new_achievements"] = (session.get("new_achievements") or []) + [a["key"] for a in new]
    return [public(a) for a in new]


@bp.route("/student/weekly")
def weekly_page():
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    got = weekly.claim(db, student["id"])
    if got:
        _push_achievements(db, student["id"])
    st = weekly.status(db, student["id"])
    stats = compute_stats(db, student["id"])
    mascot = build_mascot_ctx()
    mascot["page"] = "weekly"
    return render_template("weekly.html", mascot=mascot, st=st, got=got, coins=weekly.WEEKLY_COINS,
                           boss_coins=weekly.BOSS_COINS, wins=weekly.boss_wins(db, student["id"]),
                           weeks=weekly.weeks_done(db, student["id"]), rewards=weekly.BOSS_REWARDS,
                           items=ITEMS_BY_KEY, enough=len(learned_pool(stats)) >= weekly.MIN_BOSS_WORDS,
                           min_words=weekly.MIN_BOSS_WORDS)


@bp.route("/student/boss")
def boss_page():
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    st = weekly.status(db, student["id"])
    if not (st["complete"] and st["claimed"]):
        return redirect(url_for("season.weekly_page"))
    pool = learned_pool(compute_stats(db, student["id"]))
    if len(pool) < weekly.MIN_BOSS_WORDS:
        return redirect(url_for("season.weekly_page"))
    rng = random.Random()
    words = pool[:]
    rng.shuffle(words)
    others = [w for w in all_words() if w["key"] not in {x["key"] for x in words}]
    rng.shuffle(others)
    keep = ("key", "en", "ru", "pic")
    mascot = build_mascot_ctx()
    mascot["page"] = "boss"
    return render_template("boss.html", mascot=mascot, st=st, lives=weekly.BOSS_LIVES,
                           words=[{k: w.get(k, "") for k in keep} for w in words[:weekly.BOSS_QUESTIONS]],
                           distract=[{k: w.get(k, "") for k in keep} for w in (others + pool)[:40]],
                           rewarded=st["boss_won"])


@bp.route("/api/boss", methods=["POST"])
def api_boss():
    if session.get("role") != "student":
        abort(403)
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        abort(403)
    if not (request.get_json(silent=True) or {}).get("win"):
        return jsonify(ok=True, coins=0, items=[])
    coins, new = weekly.win_boss(db, student["id"])
    ach = _push_achievements(db, student["id"])
    return jsonify(ok=True, coins=coins, items=[ITEMS_BY_KEY[k]["name"] for k in new], newAchievements=ach)


@bp.route("/student/halloween")
def halloween_page():
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    if active_season() != "halloween":
        return redirect(url_for("student.student_home"))
    today = datetime.now().date().isoformat()
    row = db.execute("SELECT correct FROM season_log WHERE student_id=? AND season='halloween' AND day=?",
                     (student["id"], today)).fetchone()
    mascot = build_mascot_ctx()
    mascot["page"] = "halloween"
    return render_template("halloween.html", mascot=mascot, words=WORDS, phrase=PHRASE, quiz_len=QUIZ_LEN,
                           pass_mark=PASS_MARK, coins=DAILY_COINS, done_today=bool(row and row["correct"] >= PASS_MARK))


@bp.route("/api/halloween", methods=["POST"])
def api_halloween():
    if session.get("role") != "student":
        abort(403)
    if active_season() != "halloween":
        abort(403)
    try:
        correct = int((request.get_json(silent=True) or {}).get("correct"))
    except (TypeError, ValueError):
        abort(400)
    if not 0 <= correct <= QUIZ_LEN:
        abort(400)
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        abort(403)
    sid, today = student["id"], datetime.now().date().isoformat()
    prev = db.execute("SELECT correct FROM season_log WHERE student_id=? AND season='halloween' AND day=?",
                      (sid, today)).fetchone()
    coins = 0
    if correct >= PASS_MARK and not (prev and prev["correct"] >= PASS_MARK):
        get_garden(db, sid)
        db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?", (DAILY_COINS, sid))
        coins = DAILY_COINS
    db.execute("INSERT INTO season_log (student_id, season, day, correct) VALUES (?, 'halloween', ?, ?) "
               "ON CONFLICT(student_id, season, day) DO UPDATE SET correct=MAX(correct, excluded.correct)",
               (sid, today, correct))
    db.commit()
    return jsonify(ok=True, coins=coins, newAchievements=_push_achievements(db, sid))
