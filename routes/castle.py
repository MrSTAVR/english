# -*- coding: utf-8 -*-
"""Замок Чик-чика закрыт: его заменила ферма бабушки Тома (farm.py, шаг 3 переезда — farm.move_from_castle).
Старые адреса ведут на ферму, действия замка (доход, поручения, постройка, «Find the…!») больше ничего не дают.
Данные замка в базе не стираются (откат кода не ломает базу); рисунки остаются для архивных страниц."""

import castle
import castle_art
from flask import Blueprint, jsonify, redirect, url_for
from markupsafe import Markup

bp = Blueprint("castle", __name__)


def art_helpers():
    """Рисунки для шаблонов (SVG из castle_art)."""
    return {
        "room_svg": lambda key, level=1: Markup(castle.scene(key, level)[0]),
        "animal": lambda name, h=44: Markup(castle_art.person(name, 0, 0, h)),
        "animal_ava": lambda name, size=44: Markup(castle_art.avatar(name, size)),
        "brick": lambda s=18: Markup(castle_art.brick(s)),
        "coin": lambda s=18: Markup(castle_art.coin(s)),
        "gate": lambda h=40: Markup(castle_art.gate(h)),
    }


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
