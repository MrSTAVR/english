# -*- coding: utf-8 -*-
"""Вход, выход и главная страница."""

import time

import config
import ratelimit
from database import get_db
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from security import check_parent_password, verify_password

bp = Blueprint("auth", __name__)


def _too_many(seconds, back="auth.index"):
    flash(f"Слишком много неудачных попыток. Подожди {ratelimit.wait_text(seconds)} и попробуй снова 🕐", "error")
    return redirect(url_for(back))


@bp.route("/")
def index():
    if session.get("role") == "student":
        return redirect(url_for("student.student_home"))
    return render_template("index.html")


@bp.route("/login/student", methods=["POST"])
def login_student():
    """Вход ученика по логину и паролю (аккаунты создаёт родитель)."""
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    db = get_db()
    keys = [("ip", request.remote_addr), ("student", username.lower())]
    wait = ratelimit.blocked_for(db, keys)
    if wait:
        return _too_many(wait)
    student = db.execute("SELECT * FROM students WHERE username=?",
                         (username,)).fetchone()
    if not student or not verify_password(student["password_hash"], password):
        ratelimit.record_failure(db, keys)
        flash("Такого аккаунта нет или пароль неверный. Попроси родителей проверить в кабинете 👀", "error")
        return redirect(url_for("auth.index"))
    ratelimit.clear(db, [("student", username.lower())])
    session.clear()                      # новая сессия при входе
    session.permanent = True             # ребёнок не вводит пароль при каждом запуске
    session["role"] = "student"
    session["student_id"] = student["id"]
    session["student_name"] = student["display_name"]
    return redirect(url_for("student.student_home"))


@bp.route("/admin")
def admin_login():
    """Вход в кабинет администратора (ссылка — неприметная кнопка ⚙ в углу главной)."""
    if session.get("role") == "parent":
        return redirect(url_for("parent.parent_dashboard"))
    return render_template("admin_login.html")


@bp.route("/login/parent", methods=["POST"])
def login_parent():
    pwd = request.form.get("password") or ""
    db = get_db()
    keys = [("ip", request.remote_addr), ("parent", "*")]
    wait = ratelimit.blocked_for(db, keys)
    if wait:
        return _too_many(wait, "auth.admin_login")
    if not check_parent_password(pwd):
        ratelimit.record_failure(db, keys)
        flash("Неверный пароль администратора.", "error")
        return redirect(url_for("auth.admin_login"))
    ratelimit.clear(db, [("parent", "*")])
    session.clear()
    session.permanent = True
    session["role"] = "parent"
    session["parent_until"] = time.time() + config.PARENT_SESSION_HOURS * 3600
    return redirect(url_for("parent.parent_dashboard"))


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.index"))
