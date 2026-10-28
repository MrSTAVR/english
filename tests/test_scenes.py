# -*- coding: utf-8 -*-
"""Сцена истории вместо теста урока (data/story.py, scenes.py, static/scene.js)."""
import json
import re

import scenes
from curriculum import LESSONS, LESSONS_BY_ID, validate_scenes
from data.story import SCENES
from tests.helpers import N, attempt_id_from, db_scalar, submit_lesson


def _scene_data(html):
    return json.loads(re.search(r'<script type="application/json" id="scene-data">(.*?)</script>', html, re.S).group(1))


def test_scenes_are_valid():
    assert validate_scenes() == []


def test_first_island_is_story():
    assert all(l["id"] in SCENES for l in LESSONS[:9])


def test_scene_questions_are_the_test():
    for lid, sc in SCENES.items():
        l = LESSONS_BY_ID[lid]
        asks = [ln["ask"] for ln in sc["lines"] if "ask" in ln]
        assert l["test"][:len(asks)] == asks
        assert len(l["test"]) <= 10
        steps = scenes.steps(l)
        assert [s["i"] for s in steps if s["t"] == "q"] == list(range(len(l["test"])))


def test_review_question_comes_after_scene():
    l = LESSONS[1]                                       # второй урок курса: есть «Повторение»
    steps = scenes.steps(l)
    assert steps[-1]["t"] == "q" and "Повторение" in steps[-1]["q"]
    assert any(s["t"] == "note" and "повторение" in s["text"] for s in steps)


def test_lesson_page_shows_scene(make_student):
    c = make_student()
    html = c.get(f"/lesson/{N(1)}").get_data(as_text=True)
    assert 'id="scene-data"' in html and "scene.js" in html and "Итоговый тест" not in html
    assert LESSONS_BY_ID[N(1)]["scene"]["title"] in html and 'id="test-form"' in html
    steps = _scene_data(html)
    assert any(s["t"] == "say" for s in steps) and any(s["t"] == "q" for s in steps)


def test_scene_passes_like_test(make_student):
    c = make_student()
    submit_lesson(c, N(1))
    assert db_scalar("SELECT passed FROM attempts WHERE finished_at IS NOT NULL") == 1


def test_fix_mode_marks_done_questions(make_student):
    c = make_student()
    html = submit_lesson(c, N(1), wrong=True)
    aid = db_scalar("SELECT id FROM attempts WHERE finished_at IS NOT NULL")
    page = c.get(f"/lesson/{N(1)}?step=test&fix={aid}").get_data(as_text=True)
    assert "Исправь ошибки" in page and attempt_id_from(page)
    assert all(not s["done"] for s in _scene_data(page) if s["t"] == "q")   # всё было неверно — ничего не засчитано
    assert html


def test_type_in_keeps_synonyms():
    l = LESSONS_BY_ID[1]
    dog = next(q for q in l["test"] if q.get("answer") == "собака")
    assert "пёс" in dog["accept"]
