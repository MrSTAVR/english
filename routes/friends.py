# -*- coding: utf-8 -*-
"""Друзья: дуэли, рекорды, лента «Что нового», в гостях у друга (сад и замок)."""

import castle
import friends
from database import get_db
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from garden import garden_view, get_garden, refresh_garden
from mascot import build_mascot_ctx
from stats import compute_stats
from wardrobe import outfit

from routes.castle import art_helpers
from routes.common import get_student_or_none, require_role

bp = Blueprint("friends", __name__)


def _student():
    """(db, ученик) или (None, ответ): ученик должен участвовать в соревнованиях."""
    err = require_role("student")
    if err:
        return None, err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return None, redirect(url_for("auth.index"))
    if not friends.competing(student):
        flash("Раздел «Друзья» сейчас выключен.", "error")
        return None, redirect(url_for("student.student_home"))
    return (db, student), None


@bp.route("/student/friends")
def friends_page():
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    sid = student["id"]
    view = dict(friends=friends.friends(db, sid), duels=friends.duels_view(db, sid),
                records=friends.records_table(db, sid), feed=friends.feed_view(db, sid),
                duel_games={g: friends.GAME_TITLES[g] for g in friends.DUEL_GAMES},
                reactions=friends.REACTIONS, days=friends.DUEL_DAYS)
    friends.mark_seen(db, sid)
    mascot = build_mascot_ctx()
    mascot["page"] = "friends"
    return render_template("friends.html", mascot=mascot, **view)


@bp.route("/student/friends/duel", methods=["POST"])
def duel_new():
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    game = request.form.get("game", "")
    duel_id, msg = friends.create_duel(db, student["id"], request.form.get("friend", type=int), game)
    if not duel_id:
        flash(msg, "error")
        return redirect(url_for("friends.friends_page") + "#duels")
    return redirect(url_for("games.game_play", game=game, duel=duel_id))


@bp.route("/student/friends/react", methods=["POST"])
def react():
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    if not friends.react(db, student["id"], request.form.get("feed", type=int), request.form.get("kind", "")):
        abort(400)
    return redirect(url_for("friends.friends_page") + "#feed")


@bp.route("/student/friends/<int:fid>/castle/<room>")
def visit_room(fid, room):
    """Замок закрыт (его заменила ферма) — старые ссылки на комнаты друга ведут в его сад."""
    return redirect(url_for("friends.visit", fid=fid, what="garden"))


@bp.route("/student/friends/<int:fid>/<what>")
def visit(fid, what):
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    f = friends.friend(db, student["id"], fid)
    if not f or what not in friends.LIKE_WHAT:
        abort(404)
    if what == "house":                                  # замок закрыт (ферма) — в гостях показываем сад
        return redirect(url_for("friends.visit", fid=fid, what="garden"))
    likes = friends.likes_of(db, fid, what)
    ctx = dict(friend=f, what=what, likes=likes, liked=student["display_name"] in likes)
    if what == "garden":
        refresh_garden(db, fid)
        g = garden_view(db, fid)
        ctx.update(scene=g["scene"], streak=g["garden"]["streak_days"], trees=g["tree_count"])
    else:
        stats = compute_stats(db, fid)
        castle.ensure(db, fid, stats["completed_ids"])
        ctx.update(view=castle.view(db, fid, stats, get_garden(db, fid)), outfit=outfit(db, fid), visit_fid=fid, **art_helpers())
    mascot = build_mascot_ctx()
    mascot["page"] = "friends"
    return render_template("friend_visit.html", mascot=mascot, **ctx)


@bp.route("/student/friends/<int:fid>/<what>/like", methods=["POST"])
def like(fid, what):
    ctx, err = _student()
    if err:
        return err
    db, student = ctx
    if not friends.toggle_like(db, student["id"], fid, what):
        abort(404)
    return redirect(url_for("friends.visit", fid=fid, what=what))
