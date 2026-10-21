# -*- coding: utf-8 -*-
"""Настройки анимированного помощника для base.html."""

from flask import request, session


MASCOT_NAME = "Чик-чик"        # имя помощника (можно поменять)
MASCOT_ENABLED = True          # False — полностью отключить помощника


def build_mascot_ctx():
    """Собирает базовые настройки помощника для текущей страницы."""
    role = session.get("role")
    page = "anon" if not role else ("parent" if role == "parent" else "student")
    endpoint = request.endpoint or ""
    mascot = {"enabled": MASCOT_ENABLED, "name": MASCOT_NAME, "page": page}
    if page != "student":
        return mascot
    if endpoint == "auth.index":
        mascot["page"] = "index"
    elif endpoint == "student.student_home":
        mascot["page"] = "home"
    elif endpoint == "student.lesson_page":
        mascot["page"] = "lesson"
    elif endpoint == "student.submit_test":
        mascot["page"] = "result"
    elif endpoint == "garden.garden_page":
        mascot["page"] = "garden"
    return mascot
