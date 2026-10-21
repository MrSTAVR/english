# -*- coding: utf-8 -*-
"""Сад ученика: просмотр, покупка и снятие украшений."""

from database import get_db
from flask import Blueprint, abort, redirect, render_template, request, session, url_for
from garden import DECORATIONS, DECOS_BY_KEY, MAX_SLOTS, garden_view, get_garden, refresh_garden
from mascot import build_mascot_ctx

from routes.common import get_student_or_none, require_role

bp = Blueprint("garden", __name__)


@bp.route("/student/garden")
def garden_page():
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    refresh_garden(db, student["id"])
    view = garden_view(db, student["id"])
    mascot = build_mascot_ctx()
    mascot["page"] = "garden"
    mascot["streak"] = view["garden"]["streak_days"]
    flash_msg = session.pop("garden_flash", None)
    return render_template("garden.html", mascot=mascot, name=student["display_name"],
                           deco_by_key=DECOS_BY_KEY,
                           deco_emojis={k: d["emoji"] for k, d in DECOS_BY_KEY.items()},
                           flash_msg=flash_msg, **view)


@bp.route("/student/garden/buy", methods=["POST"])
def garden_buy():
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    key = request.form.get("deco_key")
    deco = DECOS_BY_KEY.get(key) or abort(400)
    g = get_garden(db, student["id"])
    used = {r["slot"] for r in db.execute(
        "SELECT slot FROM decorations WHERE student_id=?", (student["id"],)).fetchall()}
    free_slots = [s for s in range(MAX_SLOTS) if s not in used]
    if bool(g["broken"]) or g["streak_days"] <= 0:
        session["garden_flash"] = "Серия прервана — сначала позанимайся сегодня, чтобы сад ожил! 🍂"
    elif not free_slots:
        session["garden_flash"] = f"В саду уже максимум украшений ({MAX_SLOTS}). Сними одно 😉"
    elif g["coins"] < deco["cost"]:
        session["garden_flash"] = (f"Не хватает монеток: нужно {deco['cost']}, "
                                   f"а у тебя {g['coins']}. Пройди ещё пару тестов!")
    elif deco["category"] == "theme":
        # фон может быть только ОДИН: старый снимается, деньги возвращаются
        theme_keys = {d["key"] for d in DECORATIONS if d["category"] == "theme"}
        old_theme = [r for r in db.execute(
            "SELECT id, slot, deco_key FROM decorations WHERE student_id=?",
            (student["id"],)).fetchall() if r["deco_key"] in theme_keys]
        refund = sum(DECOS_BY_KEY.get(r["deco_key"], {"cost": 0})["cost"] // 2
                     for r in old_theme)
        for r in old_theme:
            db.execute("DELETE FROM decorations WHERE id=?", (r["id"],))
        used2 = {r["slot"] for r in db.execute(
            "SELECT slot FROM decorations WHERE student_id=?", (student["id"],)).fetchall()}
        free2 = [s for s in range(MAX_SLOTS) if s not in used2]
        if not free2:
            # все слоты заняты не-фонами — снимаем самый первый слот под фон
            db.execute("DELETE FROM decorations WHERE student_id=? AND slot=0",
                       (student["id"],))
            free2 = [0]
        db.execute("UPDATE garden SET coins=coins-?+? WHERE student_id=?",
                   (deco["cost"], refund, student["id"]))
        db.execute("INSERT INTO decorations (student_id, deco_key, slot) VALUES (?, ?, ?)",
                   (student["id"], key, free2[0]))
        db.commit()
        note = f" (старый фон снят, вернулось {refund} монеток)" if refund else ""
        session["garden_flash"] = f"{deco['emoji']} Новый фон сада «{deco['name']}»!{note}"
    else:
        db.execute("UPDATE garden SET coins=coins-? WHERE student_id=?",
                   (deco["cost"], student["id"]))
        db.execute("INSERT INTO decorations (student_id, deco_key, slot) VALUES (?, ?, ?)",
                   (student["id"], key, free_slots[0]))
        db.commit()
        session["garden_flash"] = f"{deco['emoji']} «{deco['name']}» украсило весь сад!"
    return redirect(url_for("garden.garden_page"))


@bp.route("/student/garden/remove/<int:slot>", methods=["POST"])
def garden_remove(slot):
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    row = db.execute("SELECT * FROM decorations WHERE student_id=? AND slot=?",
                     (student["id"], slot)).fetchone()
    if row:
        db.execute("DELETE FROM decorations WHERE id=?", (row["id"],))
        # возвращаем половину стоимости — сняли украшение с дерева
        deco = DECOS_BY_KEY.get(row["deco_key"], {"cost": 0, "name": "", "emoji": ""})
        refund = deco["cost"] // 2
        db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?",
                   (refund, student["id"]))
        db.commit()
        session["garden_flash"] = (f"{deco['emoji']} «{deco['name']}» снято из сада, "
                                   f"вернулось {refund} монеток")
    return redirect(url_for("garden.garden_page"))
