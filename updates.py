# -*- coding: utf-8 -*-
"""Обновления сайта из кабинета администратора.

Сайт работает под ограниченным пользователем и сам ничего не устанавливает: он только кладёт
«записки» в папку control (рядом с базой), а серверная служба deploy/autoupdate.sh (root)
их выполняет и пишет туда же журнал и статус. Подробности — в deploy/OPERATIONS.md."""
import os

import database

RESULTS = {
    "updated": "обновлено", "up-to-date": "установлена последняя версия", "available": "есть новая версия",
    "bad": "новая версия сломала сайт — ждём исправление", "rolled-back": "обновление не удалось, выполнен откат",
    "down": "после отката сайт не отвечает!", "no-network": "нет связи с GitHub", "not-main": "код не на ветке main",
}


def control_dir():
    return os.environ.get("ENGLISH_CONTROL_DIR") or os.path.join(os.path.dirname(os.path.abspath(database.DB_PATH)), "control")


def _path(name):
    return os.path.join(control_dir(), name)


def _touch(name):
    os.makedirs(control_dir(), exist_ok=True)
    with open(_path(name), "w", encoding="utf-8") as f:
        f.write("1\n")


def status():
    """Последний снимок от сервера (dict) или None, если автообновление на сервере ещё не работало."""
    try:
        with open(_path("status"), encoding="utf-8") as f:
            st = dict(line.rstrip("\n").split("=", 1) for line in f if "=" in line)
    except OSError:
        return None
    st["result_text"] = RESULTS.get(st.get("result", ""), st.get("result", ""))
    return st


def log_lines(n=150):
    """Последние строки журнала обновлений, свежие сверху."""
    try:
        with open(_path("update.log"), encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    return list(reversed(lines[-n:]))


def auto_enabled():
    return not os.path.exists(_path("autoupdate-off"))


def set_auto(enabled):
    if enabled:
        try:
            os.remove(_path("autoupdate-off"))
        except FileNotFoundError:
            pass
    else:
        _touch("autoupdate-off")


def request_update():
    _touch("update-now")


def update_pending():
    return os.path.exists(_path("update-now"))


def view(current_commit):
    """Всё для блока «Обновления сайта» в кабинете."""
    st = status()
    remote = (st or {}).get("remote", "")
    return {"status": st, "auto": auto_enabled(), "pending": update_pending(), "log": log_lines(),
            "remote_short": remote[:7],
            "available": bool(remote and current_commit and not remote.startswith(current_commit))}
