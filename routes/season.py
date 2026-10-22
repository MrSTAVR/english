# -*- coding: utf-8 -*-
"""Недельный челлендж, босс недели, праздничные сезоны и адвент-календарь."""

import random
from datetime import datetime

import seasons
import weekly
from achievements import public, update_achievements
from data.newyear import ADVENT, ADVENT_COINS
from database import get_db
from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from garden import get_garden
from mascot import build_mascot_ctx
from review import all_words, learned_pool
from seasons import SEASONS, active_season, advent_open, content
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


_KEYS = ",".join(list(SEASONS) + ["birthday"])


def _open(key, student):
    """Открыт ли праздник key для ученика: общий сезон или его день рождения."""
    if key == "birthday":
        return seasons.birthday_active(student["birthday"])
    return active_season() == key


def _birthday_gift(db, student):
    """Подарок на день рождения: BIRTHDAY_GIFT монет, раз в год. Возвращает число монет (0 — уже дарили)."""
    year = seasons.today().year
    if db.execute("SELECT 1 FROM birthday_gifts WHERE student_id=? AND year=?", (student["id"], year)).fetchone():
        return 0
    db.execute("INSERT INTO birthday_gifts (student_id, year) VALUES (?, ?)", (student["id"], year))
    get_garden(db, student["id"])
    db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?", (seasons.BIRTHDAY_GIFT, student["id"]))
    db.commit()
    return seasons.BIRTHDAY_GIFT


@bp.route(f"/student/<any({_KEYS}):key>")
def season_page(key):
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    if not _open(key, student):
        return redirect(url_for("student.student_home"))
    data = content(key)
    gift = _birthday_gift(db, student) if key == "birthday" else 0
    today = datetime.now().date().isoformat()
    row = db.execute("SELECT correct FROM season_log WHERE student_id=? AND season=? AND day=?",
                     (student["id"], key, today)).fetchone()
    mascot = build_mascot_ctx()
    mascot["page"] = key
    season = SEASONS.get(key) or {"title": f"С днём рождения, {student['display_name']}!", "emoji": "🎂"}
    return render_template("season.html", mascot=mascot, key=key, season=season, data=data, gift=gift,
                           intro=data.INTRO.format(pass_mark=data.PASS_MARK, quiz_len=data.QUIZ_LEN,
                                                   coins=data.DAILY_COINS, gift=seasons.BIRTHDAY_GIFT),
                           done_today=bool(row and row["correct"] >= data.PASS_MARK),
                           advent=key == "newyear" and advent_open())


@bp.route(f"/api/<any({_KEYS}):key>", methods=["POST"])
def api_season(key):
    if session.get("role") != "student":
        abort(403)
    db = get_db()
    student = get_student_or_none(db)
    if not student or not _open(key, student):
        abort(403)
    data = content(key)
    try:
        correct = int((request.get_json(silent=True) or {}).get("correct"))
    except (TypeError, ValueError):
        abort(400)
    if not 0 <= correct <= data.QUIZ_LEN:
        abort(400)
    sid, today = student["id"], datetime.now().date().isoformat()
    prev = db.execute("SELECT correct FROM season_log WHERE student_id=? AND season=? AND day=?",
                      (sid, key, today)).fetchone()
    coins = 0
    if correct >= data.PASS_MARK and not (prev and prev["correct"] >= data.PASS_MARK):
        get_garden(db, sid)
        db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?", (data.DAILY_COINS, sid))
        coins = data.DAILY_COINS
    db.execute("INSERT INTO season_log (student_id, season, day, correct) VALUES (?, ?, ?, ?) "
               "ON CONFLICT(student_id, season, day) DO UPDATE SET correct=MAX(correct, excluded.correct)",
               (sid, key, today, correct))
    db.commit()
    return jsonify(ok=True, coins=coins, newAchievements=_push_achievements(db, sid))


def _advent_state(db, sid, today):
    opened = {r["day"]: r["coins"] for r in db.execute(
        "SELECT day, coins FROM advent WHERE student_id=? AND year=?", (sid, today.year))}
    return [{"day": i + 1, **w, "open": (i + 1) in opened, "can": i + 1 <= today.day, "today": i + 1 == today.day}
            for i, w in enumerate(ADVENT)]


@bp.route("/student/advent")
def advent_page():
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    if not advent_open():
        return redirect(url_for("student.student_home"))
    today = seasons.today()
    mascot = build_mascot_ctx()
    mascot["page"] = "advent"
    return render_template("advent.html", mascot=mascot, days=_advent_state(db, student["id"], today),
                           coins=ADVENT_COINS, today=today)


@bp.route("/api/advent", methods=["POST"])
def api_advent():
    if session.get("role") != "student" or not advent_open():
        abort(403)
    try:
        day = int((request.get_json(silent=True) or {}).get("day"))
    except (TypeError, ValueError):
        abort(400)
    today = seasons.today()
    if not 1 <= day <= today.day:
        abort(400)                                   # будущие окошки ещё закрыты
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        abort(403)
    sid = student["id"]
    if db.execute("SELECT 1 FROM advent WHERE student_id=? AND year=? AND day=?", (sid, today.year, day)).fetchone():
        return jsonify(ok=True, coins=0, word=ADVENT[day - 1], newAchievements=[])
    coins = ADVENT_COINS if day == today.day else 0  # пропущенные окошки открываются, но без монетки
    db.execute("INSERT INTO advent (student_id, year, day, coins, opened_at) VALUES (?, ?, ?, ?, ?)",
               (sid, today.year, day, coins, datetime.now().isoformat(timespec="seconds")))
    if coins:
        get_garden(db, sid)
        db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?", (coins, sid))
    db.commit()
    return jsonify(ok=True, coins=coins, word=ADVENT[day - 1], newAchievements=_push_achievements(db, sid))
