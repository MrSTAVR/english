# -*- coding: utf-8 -*-
"""Пиццерия: страница /student/pizza и завершение рецепта /api/pizza/finish."""

import pizza
from database import get_db
from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from mascot import build_mascot_ctx

from routes.common import get_student_or_none, require_role

bp = Blueprint("pizza", __name__)


@bp.route("/student/pizza")
def pizza_page():
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    return render_template("pizza.html", data=pizza.state(db, student["id"]), mascot=build_mascot_ctx())


def _api_student():
    if session.get("role") != "student":
        abort(403)
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        abort(403)
    return db, student


@bp.route("/api/pizza/finish", methods=["POST"])
def api_finish():
    db, student = _api_student()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400)
    recipe = str(data.get("recipe", ""))
    if recipe not in pizza.RECIPES:
        abort(400)
    ok, gained, already, coins = pizza.finish(db, student["id"], recipe)
    if not ok:
        abort(400)
    return jsonify(ok=True, gained=gained, already=already, coins=coins)
