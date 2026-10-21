# -*- coding: utf-8 -*-
"""Истории: данные, доступ, прохождение, монетки и награды."""
import re

from data.stories import STORIES, STORIES_BY_KEY, story_words
from routes.stories import gloss_for
from curriculum import LESSONS_BY_ID
from tests.helpers import N, db_all, db_scalar, submit_lesson


def _credit(parent, n=12):
    sid = db_scalar("SELECT id FROM students WHERE username='masha'")
    parent.post(f"/parent/students/{sid}/credit", data={"upto": str(n), "action": "add"})


def test_stories_are_valid():
    keys = [s["key"] for s in STORIES]
    assert len(keys) == len(set(keys)) and len(STORIES) >= 15
    for s in STORIES:
        assert s["lesson"] in LESSONS_BY_ID, s["key"]
        assert 4 <= len(s["sentences"]) <= 8 and len(s["questions"]) == 3, s["key"]
        for q in s["questions"]:
            assert 2 <= len(q["options"]) <= 4 and 0 <= q["answer"] < len(q["options"]), s["key"]
            assert len(set(q["options"])) == len(q["options"]), s["key"]
        for sen in s["sentences"]:
            assert sen["en"] and sen["ru"]


def test_every_word_has_translation():
    for s in STORIES:
        g = gloss_for(s)
        assert set(g) == set(story_words(s))
        missing = [w for w, ru in g.items() if not ru]
        assert not missing, (s["key"], missing)


def test_stories_page_locked_then_open(parent, make_student):
    c = make_student()
    html = c.get("/student/stories").get_data(as_text=True)
    assert "Откроется после урока" in html
    assert c.get("/student/stories/meet-tom").status_code == 403
    _credit(parent, 3)
    assert c.get("/student/stories/meet-tom").status_code == 200


def test_story_page_contents(parent, make_student):
    c = make_student()
    _credit(parent, 3)
    html = c.get("/student/stories/meet-tom?mode=listen").get_data(as_text=True)
    assert 'id="story"' in html and "stories.js" in html and "Hello! My name is Tom." in html
    assert c.get("/student/stories/nope").status_code == 404


def test_story_progress_coins_and_achievement(parent, make_student):
    c = make_student()
    _credit(parent, 3)
    c.get("/student/garden")
    r = c.post("/api/story", json={"key": "meet-tom", "mode": "read", "correct": 3}).get_json()
    assert r["coins"] == 2 and any(a["key"] == "story_1" for a in r["newAchievements"])
    coins = db_scalar("SELECT coins FROM garden")
    r = c.post("/api/story", json={"key": "meet-tom", "mode": "read", "correct": 1}).get_json()
    assert r["coins"] == 0 and db_scalar("SELECT coins FROM garden") == coins          # повтор без монеток
    assert db_scalar("SELECT best FROM story_done WHERE mode='read'") == 3             # лучший результат сохраняется
    c.post("/api/story", json={"key": "meet-tom", "mode": "listen", "correct": 2})
    assert db_scalar("SELECT COUNT(*) FROM story_done") == 2


def test_story_api_validation(parent, make_student, anon):
    c = make_student()
    assert c.post("/api/story", json={"key": "nope", "mode": "read", "correct": 1}).status_code == 400
    assert c.post("/api/story", json={"key": "meet-tom", "mode": "zzz", "correct": 1}).status_code == 400
    assert c.post("/api/story", json={"key": "meet-tom", "mode": "read", "correct": 9}).status_code == 400
    assert c.post("/api/story", json={"key": "meet-tom", "mode": "read", "correct": 1}).status_code == 403   # урок не пройден
    assert anon.post("/api/story", json={"key": "meet-tom", "mode": "read", "correct": 1}).status_code == 403
