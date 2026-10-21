# -*- coding: utf-8 -*-
"""Домик Чик-чика и альбом наклеек."""

from achievements import update_achievements
from database import get_db
from flask import Blueprint, redirect, render_template, request, session, url_for
from garden import get_garden
from house import ITEMS, SLOTS, buy, owned_keys, place, placed
from mascot import build_mascot_ctx
from stats import compute_stats
from stickers import collection
from wardrobe import outfit

from routes.common import get_student_or_none, require_role

bp = Blueprint("house", __name__)


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


@bp.route("/student/house")
def house_page():
    db, student, err = _student()
    if err:
        return err
    sid = student["id"]
    mascot = build_mascot_ctx()
    mascot["page"] = "house"
    return render_template("house.html", mascot=mascot, slots=SLOTS, items=ITEMS,
                           coins=get_garden(db, sid)["coins"], owned=sorted(owned_keys(db, sid)),
                           placed=placed(db, sid), outfit=outfit(db, sid),
                           flash_msg=session.pop("house_flash", None))


@bp.route("/student/house/buy", methods=["POST"])
def house_buy():
    db, student, err = _student()
    if err:
        return err
    ok, msg = buy(db, student["id"], request.form.get("key", ""))
    session["house_flash"] = msg
    if ok:
        new = update_achievements(db, compute_stats(db, student["id"]), student["id"])
        if new:
            session["new_achievements"] = (session.get("new_achievements") or []) + [a["key"] for a in new]
    return redirect(url_for("house.house_page"))


@bp.route("/student/house/place", methods=["POST"])
def house_place():
    db, student, err = _student()
    if err:
        return err
    ok, msg = place(db, student["id"], request.form.get("key", ""))
    session["house_flash"] = msg
    return redirect(url_for("house.house_page"))


@bp.route("/student/stickers")
def stickers_page():
    db, student, err = _student()
    if err:
        return err
    items = collection(compute_stats(db, student["id"]))
    mascot = build_mascot_ctx()
    mascot["page"] = "stickers"
    return render_template("stickers.html", mascot=mascot, items=items,
                           got=sum(1 for i in items if i["got"]), gold=sum(1 for i in items if i["gold"]))
