# -*- coding: utf-8 -*-
"""Бывший smoke_test.py: полный путь одной ученицы (на временной БД)."""
import json
import re

import pytest

from achievements import ACHIEVEMENTS
from curriculum import LESSONS, LESSONS_BY_ID, MAIN_COUNT
from data.extra_lessons import EXTRA_LESSONS
from tests.helpers import (build_form, db_all, db_scalar, open_lesson,
                           submit_lesson)


def earned_keys():
    return {r[0] for r in db_all("SELECT key FROM achievements")}


def test_index_and_mascot(anon):
    r = anon.get("/")
    body = r.get_data(as_text=True)
    assert r.status_code == 200 and "Я ученик" in body
    assert "MASCOT_SETTINGS" in body and '"page": "anon"' in body
    assert "mascot.js" in body


def test_student_home_locks_and_extras(make_student):
    c = make_student()
    body = c.get("/student").get_data(as_text=True)
    assert "Закрой предыдущий урок" in body
    assert "Дополнительные уроки" in body
    assert '"page": "home"' in body


def test_locked_lesson_redirects(make_student):
    c = make_student()
    r = c.get("/lesson/2", follow_redirects=True)
    assert "Сначала пройди предыдущий урок" in r.get_data(as_text=True)


def test_lesson_page_has_mascot_context(make_student):
    c = make_student()
    body = c.get("/lesson/1").get_data(as_text=True)
    assert '"page": "lesson"' in body and '"lessonTitle"' in body


def test_failed_then_perfect_attempt(make_student):
    c = make_student()
    lesson = LESSONS_BY_ID[1]

    body = submit_lesson(c, 1, wrong=True)
    assert "fix=" in body and "Исправь ошибки" in body
    assert "Твой ответ" in body

    body = submit_lesson(c, 1)
    assert "Идеально! 100%" in body
    assert '"page": "result"' in body and '"percent": 100' in body

    home = c.get("/student").get_data(as_text=True)
    assert "Новые награды" in home                       # плашка показывается один раз
    assert "first_lesson" in earned_keys()
    assert f"1/{MAIN_COUNT}" in home
    assert "Начать урок" in home                         # урок 2 открыт


def test_all_main_lessons_give_champion(make_student):
    c = make_student()
    for l in LESSONS:
        assert "Идеально" in submit_lesson(c, l["id"], seconds=700), l["id"]
    keys = earned_keys()
    assert {"first_lesson", "three_lessons", "five_lessons", "half_way",
            "all_lessons", "perfect_test", "time60", "diamond"} <= keys


def test_parent_sees_mistakes(parent, make_student):
    c = make_student()
    submit_lesson(c, 1, wrong=True)
    expected = len(LESSONS_BY_ID[1]["test"])

    sid = db_scalar("SELECT id FROM students")
    body = parent.get(f"/parent/students/{sid}").get_data(as_text=True)
    m = re.search(r'<span><b>(\d+)</b><small>ошибок всего', body)
    assert m and int(m.group(1)) == expected

    mistakes = parent.get("/api/mistakes").get_json()
    assert len(mistakes) == expected
    assert all(k in mistakes[0] for k in
               ("question", "given", "correct", "date", "lesson_title", "student"))


def test_parent_wrong_password(anon):
    r = anon.post("/login/parent", data={"password": "0000"}, follow_redirects=True)
    assert "Неверный пароль" in r.get_data(as_text=True)


def test_api_mistakes_hidden_from_student(make_student):
    c = make_student()
    assert c.get("/api/mistakes").get_json() == []


def test_achievement_catalog():
    keys = {a["key"] for a in ACHIEVEMENTS}
    for k in ("five_lessons", "half_way", "streak10", "words100", "attempts5",
              "time180", "diamond", "first_try_perfect"):
        assert k in keys
    assert len(ACHIEVEMENTS) >= 16


@pytest.mark.parametrize("lesson", EXTRA_LESSONS, ids=lambda l: str(l["id"]))
def test_extra_lessons_always_open_and_passable(make_student, lesson):
    c = make_student()
    assert "Идеально" in submit_lesson(c, lesson["id"])


def test_garden_page_opens(make_student):
    c = make_student()
    r = c.get("/student/garden")
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "OperationalError" not in body and "garden-stage" in body


def test_extra_lessons_do_not_count_as_main_progress(make_student):
    c = make_student()
    submit_lesson(c, EXTRA_LESSONS[0]["id"])
    home = c.get("/student").get_data(as_text=True)
    assert f"0/{MAIN_COUNT}" in home
