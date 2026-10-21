# -*- coding: utf-8 -*-
"""Служебные страницы: проверка работоспособности, robots.txt, понятные страницы ошибок."""

from flask import Blueprint, Response, render_template

from database import get_db

bp = Blueprint("system", __name__)

ERROR_TEXTS = {
    400: ("Форма устарела", "Обнови страницу и попробуй ещё раз."),
    404: ("Тут ничего нет", "Такой страницы не существует. Вернись на главную."),
    413: ("Слишком большой запрос", "Попробуй отправить ещё раз."),
    429: ("Подожди немного", "Слишком много попыток. Попробуй чуть позже."),
    500: ("Что-то сломалось", "Мы уже знаем об этом. Попробуй обновить страницу."),
}


@bp.route("/healthz")
def healthz():
    """Для мониторинга: отвечает «ok», если приложение и база работают."""
    get_db().execute("SELECT 1").fetchone()
    return Response("ok", mimetype="text/plain", headers={"Cache-Control": "no-store"})


@bp.route("/robots.txt")
def robots():
    return Response("User-agent: *\nDisallow: /\n", mimetype="text/plain")


@bp.app_errorhandler(400)
@bp.app_errorhandler(404)
@bp.app_errorhandler(413)
@bp.app_errorhandler(429)
@bp.app_errorhandler(500)
def friendly_error(err):
    code = getattr(err, "code", 500) or 500
    title, text = ERROR_TEXTS.get(code, ERROR_TEXTS[500])
    if code == 400 and getattr(err, "description", None) and "Форма" in str(err.description):
        text = str(err.description)
    return render_template("error.html", code=code, title=title, text=text), code
