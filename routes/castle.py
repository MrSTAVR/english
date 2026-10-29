# -*- coding: utf-8 -*-
"""Замок Чик-чика закрыт: его заменила ферма бабушки Тома (farm.py, шаг 3 переезда — farm.move_from_castle).
Старые адреса ведут на ферму, действия замка (доход, поручения, постройка, «Find the…!») больше ничего не дают.
Данные замка в базе не стираются (откат кода не ломает базу)."""

from flask import Blueprint, jsonify, redirect, url_for

bp = Blueprint("castle", __name__)


@bp.route("/student/castle")
@bp.route("/student/castle/<room>")
def castle_page(room=None):
    return redirect(url_for("farm.farm_page"))


@bp.route("/student/castle/income", methods=["POST"])
@bp.route("/student/castle/task/<room>", methods=["POST"])
@bp.route("/student/castle/<room>/build", methods=["POST"])
def closed(room=None):
    return redirect(url_for("farm.farm_page"))


@bp.route("/api/castle/<room>/find", methods=["POST"])
def find_done(room):
    return jsonify(ok=False, closed=True), 410
