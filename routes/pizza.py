# -*- coding: utf-8 -*-
"""Пиццерия: страница /student/pizza и завершение рецепта /api/pizza/finish."""

import pizza
from database import get_db
from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from mascot import build_mascot_ctx

from routes.common import api_student, get_student_or_none, require_role

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
    if not student["pizza_enabled"]:
        return redirect(url_for("student.student_home"))
    return render_template("pizza.html", data=pizza.state(db, student["id"]), mascot=build_mascot_ctx())


@bp.route("/api/pizza/finish", methods=["POST"])
def api_finish():
    # 403, если ученик не вошёл или пиццерия выключена в админке.
    db, student = api_student("pizza_enabled")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(ok=False, error="bad_request", message="Нужен JSON с рецептом."), 400
    recipe = str(data.get("recipe") or "")
    # pieces не обязателен: сколько кусков рисовать, решает фронтенд (1..20 проверит pizza.finish).
    res = pizza.finish(db, student["id"], recipe, pieces=data.get("pieces"))
    return jsonify(res), 200 if res["ok"] else 400
