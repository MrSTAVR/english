# -*- coding: utf-8 -*-
"""app.py — веб-приложение «Английский для дочки» на Flask + SQLite.

Что внутри:
  * Режим ученика: уроки (материал -> упражнения -> итоговый тест),
    трекер успеваемости и ачивки за прохождения.
  * Режим родителя: время, потраченное на каждый урок/тест, все ошибки
    с правильными ответами, прогресс и достижения.
"""

from csrf import init_csrf
import logging
import os
import sys

from flask import Flask, g, request, session

import config
from database import init_db
from hardening import init_hardening
from badges import medal
from mascot import build_mascot_ctx
from version import info as app_version
from routes import register_blueprints
from security import load_secret_key
from template_filters import human_time, noemoji, is_russian_answer, match_answer_json, match_cols, match_expected_json, mistakes_count, \
    shuffle_match, shuffle_sort, shuffle_words, tree_mini

app = Flask(__name__)
if not logging.getLogger().handlers:           # журнал приложения: под systemd — в journalctl -u english
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


# В боевом режиме отказываемся стартовать с небезопасными настройками
if config.IS_PRODUCTION:
    _problems = config.production_problems()
    if _problems:
        raise RuntimeError("Небезопасная настройка для боевого режима:\n  - " + "\n  - ".join(_problems)
                           + "\nСм. .env.example")

# Постоянный секретный ключ, чтобы сессии не сбрасывались после перезапуска
app.secret_key = load_secret_key()
init_hardening(app)


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


init_db()


app.jinja_env.filters["human_time"] = human_time
app.jinja_env.tests["russian_answer"] = is_russian_answer


app.jinja_env.filters["shuffle_words"] = shuffle_words


app.jinja_env.filters["match_cols"] = match_cols

app.jinja_env.filters["match_answer"] = match_answer_json

app.jinja_env.filters["shuffle_match"] = shuffle_match


app.jinja_env.filters["match_expected"] = match_expected_json

app.jinja_env.filters["shuffle_sort"] = shuffle_sort


app.jinja_env.filters["mistakes_count"] = mistakes_count


app.template_filter("tree_mini")(tree_mini)

app.jinja_env.filters["medal"] = medal
app.jinja_env.filters["noemoji"] = noemoji


@app.context_processor
def inject_mascot():
    """Добавляет переменную `mascot` во все шаблоны: кто на какой странице,
    чтобы JS-помощник знал, что говорить и когда."""
    return {"mascot": build_mascot_ctx(), "app_version": app_version(),
            "speech_area": request.blueprint == "speech"}


@app.context_processor
def inject_snow():
    """Снегопад на страницах ученика, пока идёт Новый год."""
    if session.get("role") != "student":
        return {"snow": False}
    from seasons import active_season
    return {"snow": active_season() == "newyear"}


init_csrf(app)
register_blueprints(app)


if __name__ == "__main__":
    # Порт можно менять: python3 app.py 8080  (или PORT=8080 python3 app.py)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 5000))
    print(f"==> Приложение запущено: http://localhost:{port}")
    print("    Ученики входят по логину и паролю (аккаунты создаёт родитель в кабинете).")
    app.run(host="0.0.0.0", port=port, debug=False)
