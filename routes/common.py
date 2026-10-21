# -*- coding: utf-8 -*-
"""Общие помощники для маршрутов: проверка роли и текущий ученик."""

from flask import redirect, session, url_for


def get_student_or_none(db):
    """Текущий ученик из сессии (или None)."""
    sid = session.get("student_id")
    if not sid:
        return None
    return db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()


def require_role(role):
    if session.get("role") != role:
        return redirect(url_for("auth.index"))
    return None
