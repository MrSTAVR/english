# -*- coding: utf-8 -*-
"""CSRF-защита: токен в сессии + скрытое поле во всех POST-формах.

Токен не хранится, а вычисляется из «зерна» сессии (HMAC секретом приложения). Зерно задаётся
один раз при входе (`new_seed`), поэтому параллельные запросы (страница + service worker) не
придумывают каждый свой токен и не перетирают его друг у друга в cookie сессии.
"""
import hashlib
import hmac
import secrets

from flask import abort, current_app, request, session

UNSAFE = ("POST", "PUT", "PATCH", "DELETE")


def new_seed():
    """Новое зерно токена — вызывать сразу после session.clear() при входе."""
    session["csrf_seed"] = secrets.token_hex(16)


def _derived(seed):
    key = str(current_app.secret_key or "").encode()
    return hmac.new(key, seed.encode(), hashlib.sha256).hexdigest()[:32]


def csrf_token():
    """Токен текущей сессии. Старые сессии (до зерна) продолжают жить со своим сохранённым токеном."""
    if session.get("csrf_token"):
        return session["csrf_token"]
    if not session.get("csrf_seed"):
        new_seed()                           # гость без входа — зерно появляется при первой странице
    return _derived(session["csrf_seed"])


def _valid(sent):
    if not sent:
        return False
    ok = False
    if session.get("csrf_seed"):
        ok = hmac.compare_digest(str(sent), _derived(session["csrf_seed"]))
    if session.get("csrf_token"):
        ok = hmac.compare_digest(str(sent), str(session["csrf_token"])) or ok
    return ok


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
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
        if not _valid(sent):
            abort(400, description="Форма устарела или подделана. Обнови страницу и попробуй ещё раз.")
