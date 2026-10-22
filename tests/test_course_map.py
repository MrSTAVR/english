# -*- coding: utf-8 -*-
"""Карта курса: все основные уроки по порядку, пройденные со звёздами, текущий, закрытые."""
from curriculum import LESSONS
from tests.helpers import N, db_scalar, submit_lesson


def test_map_shows_progress(make_student, parent):
    c = make_student()
    html = c.get("/student/map").get_data(as_text=True)
    assert html.count('class="map-row"') == len(LESSONS)
    assert 'id="map-current"' in html and "ты здесь!" in html and "Пройдено 0 из" in html
    assert html.count("map-locked") >= len(LESSONS) - 2
    submit_lesson(c, N(1))
    sid = db_scalar("SELECT id FROM students")
    parent.post(f"/parent/students/{sid}/credit", data={"lessons": str(N(2)), "action": "add"})
    html = c.get("/student/map").get_data(as_text=True)
    assert "⭐⭐⭐" in html and "✔️ зачтено" in html and "Пройдено 2 из" in html
    assert LESSONS[2]["title"] in html.split('id="map-current"')[1][:600]


def test_map_link_on_home_and_access(make_student, anon):
    c = make_student()
    assert "/student/map" in c.get("/student").get_data(as_text=True)
    assert anon.get("/student/map").status_code == 302
