# -*- coding: utf-8 -*-
"""Замок Чик-чика: этажи с комнатами, комната-словарь, постройка и улучшение."""

import castle
import castle_art
from achievements import update_achievements
from database import get_db
from flask import Blueprint, abort, flash, redirect, render_template, session, url_for
from garden import get_garden
from markupsafe import Markup
from mascot import build_mascot_ctx
from stats import compute_stats
from wardrobe import outfit

from routes.common import get_student_or_none, require_role

bp = Blueprint("castle", __name__)


def art_helpers():
    """Рисунки для шаблонов (SVG из castle_art)."""
    return {
        "room_svg": lambda key: Markup(castle_art.room_svg(key)),
        "animal": lambda name, h=44: Markup(castle_art.person(name, 0, 0, h)),
        "animal_ava": lambda name, size=44: Markup(castle_art.avatar(name, size)),
        "brick": lambda s=18: Markup(castle_art.brick(s)),
        "coin": lambda s=18: Markup(castle_art.coin(s)),
        "gate": lambda h=40: Markup(castle_art.gate(h)),
    }


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


def _state(db, student):
    stats = compute_stats(db, student["id"])
    castle.ensure(db, student["id"], stats["completed_ids"])
    return stats, get_garden(db, student["id"])


@bp.route("/student/castle")
def castle_page():
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    stats, g = _state(db, student)
    view = castle.view(db, student["id"], stats, g)
    moved = castle.take_move_note(db, student["id"])
    mascot = build_mascot_ctx()
    mascot["page"] = "castle"
    built = [r for fl in view["floors"] for r in fl if r["state"] == "built" and r["key"] != "bedroom"]
    selected = (built[0] if built else view["rooms"]["bedroom"])["key"]
    return render_template("castle.html", mascot=mascot, view=view, moved=moved, selected=selected,
                           outfit=outfit(db, student["id"]), cost=castle.COST, earn_rules=EARN_RULES, **art_helpers())


EARN_RULES = [("book", "Пройти урок (первый раз)", castle.BRICKS_LESSON),
              ("castle", "Урок замка — открывает комнату", castle.BRICKS_CASTLE_LESSON),
              ("target", "Выполнить цель дня", castle.BRICKS_GOAL)]


@bp.route("/student/castle/<room>")
def room_page(room):
    if room not in castle.ROOMS:
        abort(404)
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    stats, g = _state(db, student)
    level = castle.levels(db, student["id"]).get(room, 0)
    if not level:
        return redirect(url_for("castle.castle_page"))
    r = castle.ROOMS[room]
    nxt = castle.COST.get(level + 1)
    mascot = build_mascot_ctx()
    mascot["page"] = "castle"
    return render_template("castle_room.html", mascot=mascot, key=room, room=r, level=level, words=castle.room_words(room, level),
                           next_words=[w for w in castle.room_words(room, level + 1) if w not in castle.room_words(room, level)] if nxt else [],
                           next_cost=nxt, bricks=castle.bricks(db, student["id"]), coins=g["coins"], who_ru=castle.RESIDENT_RU.get(r["who"]),
                           outfit=outfit(db, student["id"]), **art_helpers())


@bp.route("/student/castle/<room>/build", methods=["POST"])
def build(room):
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    stats, g = _state(db, student)
    ok, msg = castle.build(db, student["id"], room, stats, g)
    flash(msg, "ok" if ok else "error")
    if ok:
        new = update_achievements(db, compute_stats(db, student["id"]), student["id"])
        if new:
            session["new_achievements"] = (session.get("new_achievements") or []) + [a["key"] for a in new]
        return redirect(url_for("castle.room_page", room=room))
    return redirect(url_for("castle.castle_page"))
