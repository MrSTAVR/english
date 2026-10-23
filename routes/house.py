# -*- coding: utf-8 -*-
"""Альбом наклеек; старый адрес домика ведёт в замок Чик-чика."""

from database import get_db
from flask import Blueprint, redirect, render_template, session, url_for
from mascot import build_mascot_ctx
from stats import compute_stats
from stickers import collection

from routes.common import get_student_or_none, require_role

bp = Blueprint("house", __name__)


@bp.route("/student/house")
def house_page():
    """Домик переехал: теперь это замок."""
    return redirect(url_for("castle.castle_page"))


@bp.route("/student/stickers")
def stickers_page():
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    items = collection(compute_stats(db, student["id"]))
    mascot = build_mascot_ctx()
    mascot["page"] = "stickers"
    return render_template("stickers.html", mascot=mascot, items=items,
                           got=sum(1 for i in items if i["got"]), gold=sum(1 for i in items if i["gold"]))
