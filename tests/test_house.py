# -*- coding: utf-8 -*-
"""Наклейки (домик заменён замком — см. test_castle.py)."""
from curriculum import LESSONS
from tests.helpers import submit_lesson


def test_house_redirects_to_castle(make_student):
    c = make_student()
    r = c.get("/student/house")
    assert r.status_code == 302 and r.headers["Location"].endswith("/student/castle")


def test_stickers_page(make_student):
    c = make_student()
    body = c.get("/student/stickers").get_data(as_text=True)
    assert "Мои наклейки" in body and "Собрано: 0 из" in body
    submit_lesson(c, LESSONS[0]["id"])
    body = c.get("/student/stickers").get_data(as_text=True)
    assert "Собрано: 1 из" in body and "sk-gold" in body
