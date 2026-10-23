# -*- coding: utf-8 -*-
"""Уроки замка: на месте, открыты всегда, страницы рисуются и сдаются."""
from curriculum import LESSONS_BY_ID, unlocked_lesson_ids, validate_lessons
from data.castle_lessons import CASTLE_LESSONS
from tests.helpers import submit_lesson

ROOMS = {"bedroom", "kitchen", "music", "gym", "living", "workshop"}


def test_castle_lessons_catalog():
    assert not validate_lessons()
    assert {l["castle"] for l in CASTLE_LESSONS} == ROOMS
    for l in CASTLE_LESSONS:
        assert l["is_extra"] and l["id"] in LESSONS_BY_ID
        assert len(l["material"]) >= 12 and len(l["test"]) >= 10
        assert all(w["hint"] and w["ru"] for w in l["material"])
    assert {l["id"] for l in CASTLE_LESSONS} <= unlocked_lesson_ids({"completed_ids": set()})


def test_castle_lessons_render_and_pass(make_student):
    c = make_student()
    for l in CASTLE_LESSONS:
        html = c.get(f"/lesson/{l['id']}").get_data(as_text=True)
        assert "Дополнительный урок" in html and 'id="wd-data"' in html
        assert "Идеально" in submit_lesson(c, l["id"]), l["id"]
