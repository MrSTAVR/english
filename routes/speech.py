# -*- coding: utf-8 -*-
"""Логопедическая часть: вход и кабинет логопеда, «Кабинет родителя» для семей учеников."""
import ratelimit
import speech
from database import get_db
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from security import hash_password, verify_password

bp = Blueprint("speech", __name__)

LOGINS = {   # роль: (таблица, ключ сессии, страница входа, кабинет)
    "logoped": ("sp_logopeds", "logoped_id", "speech.logoped_login", "speech.logoped_home"),
    "family": ("sp_clients", "client_id", "speech.family_login", "speech.family_home"),
}


def _login(role):
    table, key, page, home = LOGINS[role]
    username = (request.form.get("username") or "").strip().lower()
    password = request.form.get("password") or ""
    db = get_db()
    keys = [("ip", request.remote_addr), (role, username)]
    wait = ratelimit.blocked_for(db, keys)
    if wait:
        flash(f"Слишком много неудачных попыток. Подождите {ratelimit.wait_text(wait)} и попробуйте снова.", "error")
        return redirect(url_for(page))
    row = db.execute(f"SELECT * FROM {table} WHERE username=?", (username,)).fetchone()
    if not row or not verify_password(row["password_hash"], password) or (role == "family" and row["archived"]):
        ratelimit.record_failure(db, keys)
        flash("Неверный логин или пароль.", "error")
        return redirect(url_for(page))
    ratelimit.clear(db, [(role, username)])
    session.clear()
    session.permanent = True
    session["role"] = role
    session[key] = row["id"]
    return redirect(url_for(home))


def _current(role):
    """(db, строка аккаунта) или (None, редирект на вход)."""
    table, key, page, _home = LOGINS[role]
    if session.get("role") != role:
        return None, redirect(url_for(page))
    db = get_db()
    row = db.execute(f"SELECT * FROM {table} WHERE id=?", (session.get(key),)).fetchone()
    if not row or (role == "family" and row["archived"]):
        session.clear()
        return None, redirect(url_for(page))
    return (db, row), None


# ---------------------------------------------------------------- логопед

@bp.route("/logoped", methods=["GET", "POST"])
def logoped_login():
    if request.method == "POST":
        return _login("logoped")
    if session.get("role") == "logoped":
        return redirect(url_for("speech.logoped_home"))
    return render_template("speech/login.html", who="logoped")


@bp.route("/logoped/home")
def logoped_home():
    ctx, err = _current("logoped")
    if err:
        return err
    db, me = ctx
    return render_template("speech/logoped_home.html", me=me, clients=speech.clients(db, me["id"]),
                           archived=speech.clients(db, me["id"], archived=True), age=speech.age_text,
                           min_password=speech.MIN_PASSWORD, username_re=speech.USERNAME_RE)


@bp.route("/logoped/clients/add", methods=["POST"])
def logoped_client_add():
    ctx, err = _current("logoped")
    if err:
        return err
    db, me = ctx
    cid, error = speech.create_client(db, me["id"], request.form)
    if error:
        flash(error, "error")
        return redirect(url_for("speech.logoped_home") + "#add")
    flash(f"Ученик добавлен. Логин для родителей: {request.form.get('username', '').strip().lower()}", "ok")
    return redirect(url_for("speech.logoped_client", cid=cid))


@bp.route("/logoped/clients/<int:cid>")
def logoped_client(cid):
    ctx, err = _current("logoped")
    if err:
        return err
    db, me = ctx
    client = speech.client_of(db, me["id"], cid) or abort(404)
    sounds = speech.sound_map(db, cid)
    in_work = {s["sound"] for s in sounds}
    return render_template("speech/logoped_client.html", me=me, c=client, age=speech.age_text,
                           min_password=speech.MIN_PASSWORD, card=speech.get_card(db, cid), sounds=sounds,
                           free_groups=[(g, [x for x in group if x not in in_work]) for g, group in speech.SOUND_GROUPS],
                           stages=speech.STAGES, history=speech.sound_history(db, cid))


@bp.route("/logoped/clients/<int:cid>/card", methods=["POST"])
def logoped_client_card(cid):
    ctx, err = _current("logoped")
    if err:
        return err
    db, me = ctx
    speech.client_of(db, me["id"], cid) or abort(404)
    speech.save_card(db, cid, request.form.get("diagnosis"), request.form.get("program"))
    flash("Диагноз и программа сохранены.", "ok")
    return redirect(url_for("speech.logoped_client", cid=cid) + "#card")


@bp.route("/logoped/clients/<int:cid>/sound", methods=["POST"])
def logoped_client_sound(cid):
    ctx, err = _current("logoped")
    if err:
        return err
    db, me = ctx
    speech.client_of(db, me["id"], cid) or abort(404)
    sound = request.form.get("sound", "")
    if request.form.get("action") == "remove":
        speech.remove_sound(db, cid, sound)
    elif not speech.set_sound(db, cid, sound, request.form.get("stage", -1, type=int), request.form.get("note", "")):
        abort(400)
    return redirect(url_for("speech.logoped_client", cid=cid) + "#sounds")


@bp.route("/logoped/clients/<int:cid>/edit", methods=["POST"])
def logoped_client_edit(cid):
    ctx, err = _current("logoped")
    if err:
        return err
    db, me = ctx
    speech.client_of(db, me["id"], cid) or abort(404)
    back = redirect(url_for("speech.logoped_client", cid=cid))
    action = request.form.get("action")
    if action == "contacts":
        fields, error = speech.clean_client_fields(request.form)
        if error:
            flash(error, "error")
            return back
        db.execute("UPDATE sp_clients SET child_name=?, birth_date=?, parent_name=?, phone=? WHERE id=?",
                   (fields["child_name"], fields["birth_date"], fields["parent_name"], fields["phone"], cid))
        flash("Данные сохранены.", "ok")
    elif action == "password":
        password = request.form.get("password") or ""
        if len(password) < speech.MIN_PASSWORD:
            flash(f"Пароль должен быть не короче {speech.MIN_PASSWORD} символов.", "error")
            return back
        db.execute("UPDATE sp_clients SET password_hash=? WHERE id=?", (hash_password(password), cid))
        flash("Новый пароль для родителей сохранён 🔑", "ok")
    elif action in ("archive", "restore"):
        db.execute("UPDATE sp_clients SET archived=? WHERE id=?", (int(action == "archive"), cid))
        flash("Ученик перенесён в архив: вход для родителей закрыт." if action == "archive" else
              "Ученик снова в списке, вход для родителей открыт.", "ok")
    else:
        abort(400)
    db.commit()
    return back


# ---------------------------------------------------------------- кабинет родителя

@bp.route("/family", methods=["GET", "POST"])
def family_login():
    if request.method == "POST":
        return _login("family")
    if session.get("role") == "family":
        return redirect(url_for("speech.family_home"))
    return render_template("speech/login.html", who="family")


@bp.route("/family/home")
def family_home():
    ctx, err = _current("family")
    if err:
        return err
    db, client = ctx
    logoped = db.execute("SELECT name FROM sp_logopeds WHERE id=?", (client["logoped_id"],)).fetchone()
    return render_template("speech/family_home.html", c=client, logoped=logoped,
                           sounds=speech.sound_map(db, client["id"]))
