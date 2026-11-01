# -*- coding: utf-8 -*-
"""Ферма бабушки Тома: страница /student/farm и действия /api/farm/<action> (логика — farm.py)."""

import farm
import pizza_farm
from database import get_db
from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from mascot import build_mascot_ctx
from stats import compute_stats

from routes.common import get_student_or_none, require_role

bp = Blueprint("farm", __name__)


@bp.route("/student/farm")
def farm_page():
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    if not student["farm_enabled"]:
        return redirect(url_for("student.student_home"))
    farm.move_from_castle(db, student["id"])
    moved = farm.take_move_note(db, student["id"])
    stats = compute_stats(db, student["id"])
    return render_template("farm.html", data=farm.state(db, student["id"], stats), moved=moved, mascot=build_mascot_ctx())


def _api_student():
    if session.get("role") != "student":
        abort(403)
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        abort(403)
    return db, student


@bp.route("/api/farm")
def api_state():
    db, student = _api_student()
    return jsonify(farm.state(db, student["id"], compute_stats(db, student["id"])))


def _int(data, key):
    try:
        return int(data.get(key))
    except (TypeError, ValueError):
        abort(400)


@bp.route("/api/farm/<action>", methods=["POST"])
def api_action(action):
    db, student = _api_student()
    sid = student["id"]
    data = request.get_json(silent=True) or {}
    stats = compute_stats(db, sid)
    extra = {}
    if action == "plant":
        ok, msg = farm.plant(db, sid, _int(data, "slot"), str(data.get("crop", "")), stats)
    elif action == "water":
        ok, msg = farm.water(db, sid, _int(data, "slot"))
    elif action == "harvest" and data.get("slot") == "all":
        got = farm.harvest_all(db, sid)
        ok, msg, extra = bool(got), ("" if got else "Ещё не поспело."), {"got": sum(got.values())}
    elif action == "harvest":
        ok, n = farm.harvest(db, sid, _int(data, "slot"))
        msg, extra = ("" if ok else "Ещё не поспело."), {"got": n}
    elif action == "feed":
        ok, msg = farm.feed(db, sid, str(data.get("kind", "")))
    elif action == "collect":
        ok, n = farm.collect(db, sid, str(data.get("kind", "")))
        msg, extra = ("" if ok else "Пока нечего собирать."), {"got": n}
    elif action == "plot":
        ok, msg = farm.buy_plot(db, sid)
    elif action == "cow":
        ok, msg = farm.buy_cow(db, sid, stats)
    elif action == "well":
        ok, n = farm.well(db, sid)
        msg, extra = ("" if ok else "Сегодня вода уже набрана."), {"got": n}
    elif action == "process":
        ok, msg = pizza_farm.process(db, sid, str(data.get("key", "")))
    elif action == "order":
        given = data.get("items")
        if not isinstance(given, dict):
            abort(400)
        try:
            res = farm.fulfil(db, sid, _int(data, "id"), {str(k): int(v) for k, v in given.items()})
        except (TypeError, ValueError):
            abort(400)
        ok, msg, extra = res["ok"], "", {k: v for k, v in res.items() if k != "ok"}
    else:
        abort(404)
    return jsonify(ok=ok, msg=msg, state=farm.state(db, sid, compute_stats(db, sid)), **extra)
