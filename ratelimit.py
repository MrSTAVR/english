# -*- coding: utf-8 -*-
"""Ограничение числа неудачных попыток входа (защита от подбора пароля).

Счётчики хранятся в SQLite (таблица login_failures), поэтому работают одинаково
при нескольких процессах сервера и переживают перезапуск.

Ключи — пары (область, идентификатор):
  ("ip", "203.0.113.5")      — все неудачи с одного адреса
  ("student", "masha")       — неудачи входа в один аккаунт
  ("parent", "*")            — неудачи входа в кабинет родителя
"""
import time

import config

KEEP_SECONDS = 24 * 3600   # старые записи удаляются


def _norm(scope, ident):
    return scope, str(ident or "")[:64]


def blocked_for(db, keys, now=None):
    """Сколько секунд ждать до следующей попытки (0 — можно пробовать)."""
    now = time.time() if now is None else now
    window = config.LOGIN_WINDOW_SEC
    wait = 0
    for scope, ident in (_norm(*k) for k in keys):
        limit = config.LOGIN_LIMITS[scope]
        rows = db.execute(
            "SELECT ts FROM login_failures WHERE scope=? AND ident=? AND ts>? ORDER BY ts",
            (scope, ident, now - window)).fetchall()
        if len(rows) >= limit:
            # блокировка снимется, когда старейшая из последних `limit` неудач выйдет из окна
            wait = max(wait, int(rows[-limit]["ts"] + window - now) + 1)
    return wait


def record_failure(db, keys, now=None):
    """Запоминает неудачную попытку по всем ключам."""
    now = time.time() if now is None else now
    for scope, ident in (_norm(*k) for k in keys):
        db.execute("INSERT INTO login_failures (scope, ident, ts) VALUES (?, ?, ?)",
                   (scope, ident, now))
    db.execute("DELETE FROM login_failures WHERE ts<?", (now - KEEP_SECONDS,))
    db.commit()


def clear(db, keys):
    """Сбрасывает счётчик (после успешного входа)."""
    for scope, ident in (_norm(*k) for k in keys):
        db.execute("DELETE FROM login_failures WHERE scope=? AND ident=?", (scope, ident))
    db.commit()


def wait_text(seconds):
    """Человеческое «подожди N мин»."""
    minutes = max(1, -(-int(seconds) // 60))
    return f"{minutes} мин"
