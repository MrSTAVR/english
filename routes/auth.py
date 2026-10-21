# -*- coding: utf-8 -*-
"""Вход, выход и главная страница."""

from config import PARENT_PASSWORD
from database import get_db
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from security import verify_password

bp = Blueprint("auth", __name__)


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
    student = db.execute("SELECT * FROM students WHERE username=?",
                         (username,)).fetchone()
    if not student or not verify_password(student["password_hash"], password):
        flash("Такого аккаунта нет или пароль неверный. Попроси родителей проверить в кабинете 👀", "error")
        return redirect(url_for("auth.index"))
    session["role"] = "student"
    session["student_id"] = student["id"]
    session["student_name"] = student["display_name"]
    return redirect(url_for("student.student_home"))


@bp.route("/login/parent", methods=["POST"])
def login_parent():
    pwd = request.form.get("password") or ""
    if pwd != PARENT_PASSWORD:
        flash("Неверный пароль. Подсказка: спроси у родителей 😉", "error")
        return redirect(url_for("auth.index"))
    session["role"] = "parent"
    return redirect(url_for("parent.parent_dashboard"))


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.index"))
