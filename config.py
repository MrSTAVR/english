# -*- coding: utf-8 -*-
"""Конфигурация: пути, константы и настройки из переменных окружения.

Все настройки боевого сервера задаются переменными окружения (см. .env.example),
в коде и в репозитории паролей и ключей нет.
"""

import os


def _env_flag(name, default=False):
    """Булева переменная окружения: 1/true/yes/on -> True."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Путь к БД можно переопределить (так тесты не трогают настоящую базу)
DB_PATH = os.environ.get("ENGLISH_APP_DB") or os.path.join(BASE_DIR, "english_app.db")


SPEAKING = _env_flag("ENGLISH_SPEAKING", True)   # тренировка произношения с микрофоном
PASS_MARK_SOFT = 60     # для фонетики и алфавита (самые сухие уроки)
PASS_MARK = 70          # минимальный процент, чтобы тест считаться сданным
PASS_MARK_SCENE = 60    # сцена-история: верно с первой попытки — балл, со второй — полбалла

# --- Режим работы ----------------------------------------------------------
# development (по умолчанию): удобно дома и в тестах.
# production: включает строгие проверки и защищённые cookie.
ENV = os.environ.get("ENGLISH_ENV", "development").strip().lower()
IS_PRODUCTION = ENV == "production"

# --- Пароль родителя -------------------------------------------------------
DEFAULT_PARENT_PASSWORD = "1234"
PARENT_PASSWORD = os.environ.get("ENGLISH_PARENT_PASSWORD", DEFAULT_PARENT_PASSWORD)
WEAK_PASSWORDS = {DEFAULT_PARENT_PASSWORD, "12345678", "123456789", "1234567890",
                  "password", "qwerty123", "11111111", "00000000", "parent123"}
MIN_PARENT_PASSWORD_LEN = 8

# --- Сессии и cookie -------------------------------------------------------
TIMEZONE = os.environ.get("ENGLISH_TZ", "Europe/Moscow")   # часовой пояс расписания логопеда
SESSION_DAYS = int(os.environ.get("ENGLISH_SESSION_DAYS", "30"))   # ученик не вводит пароль каждый раз
PARENT_SESSION_HOURS = int(os.environ.get("ENGLISH_PARENT_SESSION_HOURS", "12"))
ADMIN_BACK_MINUTES = 15   # из учётки ученика «В админку» без пароля — только недолго (планшет могут отдать ребёнку)
# Secure-cookie уходят только по HTTPS. В боевом режиме включены автоматически.
COOKIE_SECURE = _env_flag("ENGLISH_COOKIE_SECURE", IS_PRODUCTION)

# --- За обратным прокси (Caddy/nginx) ---------------------------------------
# Включайте, только если перед приложением стоит свой прокси: тогда настоящий IP
# посетителя и схема (https) берутся из его заголовков X-Forwarded-*.
BEHIND_PROXY = _env_flag("ENGLISH_BEHIND_PROXY", False)

# --- Ограничение попыток входа ----------------------------------------------
LOGIN_WINDOW_SEC = 600                                   # окно подсчёта неудач: 10 минут
LOGIN_LIMITS = {"ip": 10, "student": 8, "parent": 20, "logoped": 10, "family": 8}   # допустимо неудач за окно


def production_problems():
    """Список проблем конфигурации, из-за которых нельзя запускаться в интернете."""
    problems = []
    if "ENGLISH_PARENT_PASSWORD" not in os.environ:
        problems.append("не задан ENGLISH_PARENT_PASSWORD (пароль родителя)")
    elif PARENT_PASSWORD.lower() in WEAK_PASSWORDS:
        problems.append("пароль родителя слишком простой — выберите другой")
    elif len(PARENT_PASSWORD) < MIN_PARENT_PASSWORD_LEN:
        problems.append(f"пароль родителя короче {MIN_PARENT_PASSWORD_LEN} символов")
    if not COOKIE_SECURE:
        problems.append("ENGLISH_COOKIE_SECURE выключен — cookie уйдут без шифрования")
    return problems
