# -*- coding: utf-8 -*-
"""Журнал посещений ученика."""
from datetime import datetime, timedelta

import visits
from curriculum import LESSONS
from tests.helpers import db_scalar, submit_lesson
from tests.test_vacation import conn, sid_of


def test_student_pages_and_actions_logged(make_student):
    c = make_student(); sid = sid_of()
    c.get("/student"); c.get("/student/games"); c.get("/static/style.css"); c.get("/offline")
    submit_lesson(c, LESSONS[0]["id"])
    c.post(f"/api/lesson/{LESSONS[0]['id']}/progress", json={"step": "step-theory"})     # автосохранение — не пишем
    paths = [r[0] for r in conn().execute("SELECT path FROM visits WHERE student_id=? ORDER BY id", (sid,))]
    assert "/student" in paths and "/student/games" in paths and f"/lesson/{LESSONS[0]['id']}/submit" in paths
    assert not any(p.startswith(("/static", "/offline", "/api/lesson")) for p in paths)


def test_parent_not_logged(parent):
    parent.get("/parent"); parent.get("/parent/students")
    assert db_scalar("SELECT COUNT(*) FROM visits") == 0


def test_sessions_split_and_sections(make_student):
    make_student(); sid = sid_of(); cn = conn()
    import sqlite3
    cn.row_factory = sqlite3.Row
    cn.execute("DELETE FROM visits")                    # заход при входе ученика не нужен
    t0 = datetime(2026, 10, 26, 8, 0)
    for m, p in ((0, "/student"), (2, "/student/games"), (3, "/api/game"), (10, "/lesson/12"), (60, "/student/castle")):
        visits.add(cn, sid, p, "act" if p.startswith("/api") else "page", at=t0 + timedelta(minutes=m))
    s = visits.sessions(cn, sid, days=3, now=t0 + timedelta(hours=2))
    assert len(s) == 2 and s[1]["minutes"] == 10 and s[1]["acts"] == 1
    assert dict(s[1]["sections"]) == {"Игры": 2, "Уроки": 1} and s[0]["sections"] == [("Замок", 1)]


def test_admin_card_and_delete(parent, make_student):
    c = make_student(); sid = sid_of()
    c.get("/student/castle")
    html = parent.get(f"/parent/students/{sid}").get_data(as_text=True)
    assert "Заходы за 2 недели" in html and "Замок" in html
    parent.post(f"/parent/students/{sid}/delete")
    assert db_scalar("SELECT COUNT(*) FROM visits") == 0
