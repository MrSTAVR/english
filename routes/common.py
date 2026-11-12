# -*- coding: utf-8 -*-
"""Общие помощники для маршрутов: проверка роли и текущий ученик."""

import time

from flask import abort, flash, redirect, session, url_for

from database import get_db


def get_student_or_none(db):
    """Текущий ученик из сессии (или None)."""
    sid = session.get("student_id")
    if not sid:
        return None
    return db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()


def api_student(enabled=None):
    """(db, student) для JSON-маршрутов ученика: 403, если роль не та или раздел выключен.

    enabled — имя флага в students (например, "pizza_enabled"): маршрут закрытого раздела
    не должен работать, даже если страница уже недоступна.
    """
    if session.get("role") != "student":
        abort(403, description="Нет доступа.")
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        abort(403, description="Нужно войти учеником.")
    if enabled is not None and not student[enabled]:
        abort(403, description="Этот раздел выключен.")
    return db, student


def require_role(role):
    """None, если роль подходит; иначе редирект на главную.

    Вход администратора (роль "parent") действует ограниченное время (config.PARENT_SESSION_HOURS):
    ребёнок не должен получать кабинет администратора на «забытом» телефоне.
    """
    if session.get("role") != role:
        return redirect(url_for("auth.index"))
    if role == "parent" and time.time() > session.get("parent_until", 0):
        session.clear()
        flash("Вход администратора закончился. Войди снова 🔐", "error")
        return redirect(url_for("auth.admin_login"))
    return None
