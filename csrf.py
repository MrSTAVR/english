# -*- coding: utf-8 -*-
"""CSRF-защита: токен в сессии + скрытое поле во всех POST-формах."""
import hmac
import secrets

from flask import abort, request, session

UNSAFE = ("POST", "PUT", "PATCH", "DELETE")


def csrf_token():
    """Токен текущей сессии (создаётся при первом обращении)."""
    if not session.get("csrf_token"):
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def init_csrf(app):
    """Подключает проверку токена ко всем небезопасным запросам."""
    app.config.setdefault("CSRF_ENABLED", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def _check_csrf():
        if not app.config.get("CSRF_ENABLED", True):
            return
        if request.method not in UNSAFE:
            return
        expected = session.get("csrf_token")
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
        if not expected or not hmac.compare_digest(str(sent), str(expected)):
            abort(400, description="Форма устарела или подделана. Обнови страницу и попробуй ещё раз.")
