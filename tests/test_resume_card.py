# -*- coding: utf-8 -*-
"""Карточка «Продолжи урок» на главной ученика."""
from curriculum import LESSONS
from tests.helpers import submit_lesson


def test_resume_card_shows_unfinished_lesson(make_student):
    c = make_student()
    l = LESSONS[0]
    assert "Продолжи урок" not in c.get("/student").get_data(as_text=True)
    c.get(f"/lesson/{l['id']}")
    c.post(f"/api/lesson/{l['id']}/progress", json={"state": {"step": "step-test", "test": {"radio": {"q0": "1", "q1": "0"}, "text": ["", ""]}}})
    html = c.get("/student").get_data(as_text=True)
    assert "Продолжи урок" in html and f"ответов 2 из {len(l['test'])}" in html and f'href="/lesson/{l["id"]}"' in html


def test_resume_card_steps_and_gone_after_pass(make_student):
    c = make_student()
    l = LESSONS[0]
    c.get(f"/lesson/{l['id']}")
    c.post(f"/api/lesson/{l['id']}/progress", json={"state": {"step": "step-material", "words": {"i": 2, "seen": [0, 1, 2]}}})
    assert f"слов 3 из {len(l['material'])}" in c.get("/student").get_data(as_text=True)
    submit_lesson(c, l["id"])
    assert "Продолжи урок" not in c.get("/student").get_data(as_text=True)
