# -*- coding: utf-8 -*-
"""Гардероб Чик-чика: просмотр, покупка и ношение нарядов."""

from achievements import update_achievements
from database import get_db
from flask import Blueprint, redirect, render_template, request, session, url_for
from garden import get_garden
from mascot import build_mascot_ctx
from stats import compute_stats
from wardrobe import ITEMS, SLOTS, buy, outfit, owned_keys, wear

from routes.common import get_student_or_none, require_role

bp = Blueprint("wardrobe", __name__)


def _student():
    err = require_role("student")
    if err:
        return None, None, err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return None, None, redirect(url_for("auth.index"))
    return db, student, None


@bp.route("/student/wardrobe")
def wardrobe_page():
    db, student, err = _student()
    if err:
        return err
    mascot = build_mascot_ctx()
    mascot["page"] = "wardrobe"
    return render_template("wardrobe.html", mascot=mascot, slots=SLOTS, items=ITEMS,
                           coins=get_garden(db, student["id"])["coins"],
                           owned=sorted(owned_keys(db, student["id"])), worn=outfit(db, student["id"]),
                           flash_msg=session.pop("wardrobe_flash", None))


@bp.route("/student/wardrobe/buy", methods=["POST"])
def wardrobe_buy():
    db, student, err = _student()
    if err:
        return err
    ok, msg = buy(db, student["id"], request.form.get("key", ""))
    session["wardrobe_flash"] = msg
    if ok:
        new = update_achievements(db, compute_stats(db, student["id"]), student["id"])
        if new:
            session["new_achievements"] = (session.get("new_achievements") or []) + [a["key"] for a in new]
    return redirect(url_for("wardrobe.wardrobe_page"))


@bp.route("/student/wardrobe/wear", methods=["POST"])
def wardrobe_wear():
    db, student, err = _student()
    if err:
        return err
    ok, msg = wear(db, student["id"], request.form.get("key", ""))
    session["wardrobe_flash"] = msg
    return redirect(url_for("wardrobe.wardrobe_page"))
