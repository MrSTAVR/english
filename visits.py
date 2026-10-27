# -*- coding: utf-8 -*-
"""Журнал посещений ученика: какие страницы открывал и что делал, — чтобы видеть, как ребёнок занимается.

Пишем только для вошедшего ученика: открытые страницы (GET, HTML, 200) и действия (POST),
кроме частого автосохранения урока. Храним KEEP_DAYS дней. Сессия — заходы без перерыва дольше GAP_MIN минут.
"""

import logging
import re
import sqlite3
from datetime import datetime, timedelta

from flask import request, session

log = logging.getLogger(__name__)

KEEP_DAYS = 60
GAP_MIN = 15
_SKIP = re.compile(r"^/(offline|healthz|static/|api/lesson/\d+/progress|parent/|admin)")

# раздел по адресу (первое совпадение)
SECTIONS = [
    (r"^/lesson/|^/student/theory", "Уроки"), (r"^/student/games|^/api/game", "Игры"), (r"^/student/dialogs|^/api/dialog", "Диалоги"),
    (r"^/student/stories|^/api/story", "Истории"), (r"^/student/review|^/api/review", "Повторение"), (r"^/student/speak|^/api/speak", "Скажи вслух"),
    (r"^/student/writing|^/api/writing", "Письмо"), (r"^/student/castle|^/api/castle|^/student/house", "Замок"),
    (r"^/student/garden", "Сад"), (r"^/student/wardrobe", "Гардероб"), (r"^/student/friends", "Друзья"),
    (r"^/student/(weekly|boss)|^/api/boss", "Неделя и босс"), (r"^/student/achievements|^/student/stickers", "Награды"),
    (r"^/student/map", "Карта"), (r"^/student/words", "Словарь"), (r"^/student/?$", "Главная"),
]
_SECTIONS = [(re.compile(p), name) for p, name in SECTIONS]


def section(path):
    for rx, name in _SECTIONS:
        if rx.search(path):
            return name
    return "Другое"


def init_app(app):
    from database import get_db

    @app.after_request
    def _log_visit(resp):
        sid = session.get("student_id")
        if session.get("role") != "student" or not sid or _SKIP.search(request.path):
            return resp
        if request.method == "GET":
            if resp.status_code != 200 or resp.mimetype != "text/html":
                return resp
            kind = "page"
        elif request.method == "POST" and not request.path.startswith("/login"):
            kind = "act"
        else:
            return resp
        try:
            add(get_db(), sid, request.path, kind)
        except sqlite3.Error as e:                      # журнал — не повод ломать страницу
            log.warning("visit log: %s", e)
        return resp


def add(db, student_id, path, kind="page", at=None):
    at = at or datetime.now()
    cur = db.execute("INSERT INTO visits (student_id, at, path, kind) VALUES (?, ?, ?, ?)",
                     (student_id, at.isoformat(timespec="seconds"), path[:200], kind))
    if cur.lastrowid % 500 == 0:                       # изредка подчищаем старое
        db.execute("DELETE FROM visits WHERE at < ?", ((at - timedelta(days=KEEP_DAYS)).isoformat(timespec="seconds"),))
    db.commit()


def sessions(db, student_id, days=14, now=None):
    """Занятия за последние days дней: [{start, end, minutes, pages, sections: [(раздел, сколько)]}], новые сверху."""
    since = ((now or datetime.now()) - timedelta(days=days)).isoformat(timespec="seconds")
    rows = db.execute("SELECT at, path, kind FROM visits WHERE student_id=? AND at>=? ORDER BY at", (student_id, since)).fetchall()
    out, cur = [], None
    for r in rows:
        t = datetime.fromisoformat(r["at"])
        if not cur or (t - cur["end"]).total_seconds() > GAP_MIN * 60:
            cur = {"start": t, "end": t, "pages": 0, "acts": 0, "sec": {}}
            out.append(cur)
        cur["end"] = t
        cur["pages" if r["kind"] == "page" else "acts"] += 1
        name = section(r["path"])
        if name != "Главная":
            cur["sec"][name] = cur["sec"].get(name, 0) + 1
    for s in out:
        s["minutes"] = max(1, round((s["end"] - s["start"]).total_seconds() / 60))
        s["sections"] = sorted(s.pop("sec").items(), key=lambda kv: -kv[1])
    return out[::-1]


def forget_student(db, student_id):
    db.execute("DELETE FROM visits WHERE student_id=?", (student_id,))
