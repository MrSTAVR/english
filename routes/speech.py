# -*- coding: utf-8 -*-
"""Логопедическая часть: вход и кабинет логопеда, «Кабинет родителя» для семей учеников."""
import ratelimit
import speech
import speech_schedule as sched
from datetime import timedelta
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
                           today_sessions=sched.for_day(db, me["id"], sched.today()),
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
                           stages=speech.STAGES, history=speech.sound_history(db, cid),
                           upcoming=sched.client_sessions(db, cid, me["id"]),
                           past=sched.client_sessions(db, cid, me["id"], upcoming=False, limit=8),
                           series=sched.series_of(db, cid), default_minutes=sched.DEFAULT_MINUTES,
                           today=sched.today().isoformat())


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


# ---------------------------------------------------------------- расписание

@bp.route("/logoped/schedule")
def logoped_schedule():
    ctx, err = _current("logoped")
    if err:
        return err
    db, me = ctx
    shift = max(-104, min(104, request.args.get("week", 0, type=int)))
    monday = sched.today() - timedelta(days=sched.today().weekday()) + timedelta(weeks=shift)
    days = sched.week(db, me["id"], monday)
    return render_template("speech/schedule.html", me=me, days=days, shift=shift,
                           week_total=sum(len(d["sessions"]) for d in days),
                           monday=monday, sunday=monday + timedelta(days=6), clients=speech.clients(db, me["id"]),
                           days_off=sched.days_off(db, me["id"]), default_minutes=sched.DEFAULT_MINUTES,
                           today=sched.today().isoformat(), months=sched.MONTHS)


@bp.route("/logoped/sessions/add", methods=["POST"])
def logoped_session_add():
    ctx, err = _current("logoped")
    if err:
        return err
    db, me = ctx
    f = request.form
    cid = f.get("client_id", type=int)
    back = f.get("back") == "client" and cid
    target = url_for("speech.logoped_client", cid=cid) + "#schedule" if back else None
    client = speech.client_of(db, me["id"], cid)
    start = sched.parse_start(f.get("day"), f.get("time"))
    minutes = f.get("minutes", sched.DEFAULT_MINUTES, type=int)
    if not client or client["archived"]:
        error = "Выберите ученика."
    elif not start:
        error = "Укажите дату и время."
    elif f.get("repeat"):
        end_day = speech.parse_date(f.get("until")) if f.get("until") else None
        _id, error = sched.add_series(db, me["id"], cid, start, minutes, end_day)
    else:
        _id, error = sched.add_session(db, me["id"], cid, start, minutes)
    if error:
        flash(error, "error")
    else:
        flash(f"Занятие назначено: {client['child_name']}, {sched.day_text(start.date())} в {start:%H:%M}"
              + (", каждую неделю" if f.get("repeat") else "") + ".", "ok")
    if target:
        return redirect(target)
    monday = sched.today() - timedelta(days=sched.today().weekday())
    shift = ((start.date() - monday).days // 7) if start else 0
    return redirect(url_for("speech.logoped_schedule", week=shift or None))


@bp.route("/logoped/sessions/<int:sid>", methods=["GET", "POST"])
def logoped_session(sid):
    ctx, err = _current("logoped")
    if err:
        return err
    db, me = ctx
    s = sched.get_session(db, me["id"], sid) or abort(404)
    if request.method == "GET":
        return render_template("speech/session.html", me=me, s=sched.decorate(s), statuses=sched.STATUSES,
                               day=sched.day_text(sched.parse_start(s["start"][:10], s["start"][11:]).date()))
    action = request.form.get("action")
    if action in sched.STATUSES:
        sched.set_status(db, sid, action, request.form.get("note"))
        flash(f"Отмечено: {sched.STATUSES[action]}.", "ok")
    elif action == "note":
        sched.set_status(db, sid, s["status"], request.form.get("note") or "")
        flash("Заметка сохранена.", "ok")
    elif action == "move":
        start = sched.parse_start(request.form.get("day"), request.form.get("time"))
        error = sched.move_session(db, me["id"], sid, start, request.form.get("minutes", s["minutes"], type=int)) \
            if start else "Укажите дату и время."
        flash(error or "Занятие перенесено.", "error" if error else "ok")
    elif action == "delete":
        db.execute("DELETE FROM sp_sessions WHERE id=?", (sid,))
        db.commit()
        flash("Занятие удалено.", "ok")
        return redirect(url_for("speech.logoped_schedule"))
    else:
        abort(400)
    return redirect(url_for("speech.logoped_session", sid=sid))


@bp.route("/logoped/series/<int:series_id>/stop", methods=["POST"])
def logoped_series_stop(series_id):
    ctx, err = _current("logoped")
    if err:
        return err
    db, me = ctx
    row = db.execute("SELECT client_id FROM sp_series WHERE id=? AND logoped_id=?", (series_id, me["id"])).fetchone() \
        or abort(404)
    sched.stop_series(db, me["id"], series_id)
    flash("Повторяющееся занятие остановлено, будущие занятия из него удалены.", "ok")
    return redirect(url_for("speech.logoped_client", cid=row["client_id"]) + "#schedule")


@bp.route("/logoped/days-off", methods=["POST"])
def logoped_days_off():
    ctx, err = _current("logoped")
    if err:
        return err
    db, me = ctx
    if request.form.get("action") == "delete":
        db.execute("DELETE FROM sp_days_off WHERE id=? AND logoped_id=?", (request.form.get("id", type=int), me["id"]))
        db.commit()
        flash("Выходные удалены.", "ok")
    else:
        d1, d2 = speech.parse_date(request.form.get("start_day")), speech.parse_date(request.form.get("end_day"))
        if not d1:
            flash("Укажите дату.", "error")
        else:
            ok, msg = sched.add_days_off(db, me["id"], d1, d2 or d1, request.form.get("note"))
            flash(msg, "ok" if ok else "error")
    return redirect(url_for("speech.logoped_schedule") + "#days-off")


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
                           sounds=speech.sound_map(db, client["id"]),
                           upcoming=sched.client_sessions(db, client["id"], client["logoped_id"], limit=4),
                           past=sched.client_sessions(db, client["id"], client["logoped_id"], upcoming=False, limit=5))
