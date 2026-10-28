# -*- coding: utf-8 -*-
"""Словарь ученика: слова из пройденных уроков."""
from curriculum import LESSONS_BY_ID
from tests.helpers import db_scalar, submit_lesson
from tests.helpers import N
from template_filters import noemoji


def words_html(client):
    r = client.get("/student/words")
    assert r.status_code == 200
    return r.get_data(as_text=True)


def test_empty_dictionary_for_new_student(make_student):
    html = words_html(make_student())
    assert "Словарь пока пуст" in html


def test_dictionary_shows_only_passed_lessons(make_student):
    student = make_student()
    submit_lesson(student, N(1))
    html = words_html(student)
    w1 = LESSONS_BY_ID[N(1)]["material"]
    from markupsafe import escape
    assert all(f'data-tts="{escape(w["en"])}"' in html for w in w1)       # What&#39;s your name?
    assert noemoji(LESSONS_BY_ID[N(1)]["title"]) in html
    assert LESSONS_BY_ID[2]["title"] not in html            # урок 2 ещё не пройден
    assert f"Все слова из пройденных уроков: <b>{len(w1)}</b>" in html


def test_credited_lessons_appear_in_dictionary(parent, make_student):
    student = make_student()
    sid = db_scalar("SELECT id FROM students WHERE username='masha'")
    parent.post(f"/parent/students/{sid}/credit", data={"upto": "2", "action": "add"})
    html = words_html(student)
    assert noemoji(LESSONS_BY_ID[N(1)]["title"]) in html and noemoji(LESSONS_BY_ID[N(2)]["title"]) in html
    assert LESSONS_BY_ID[N(3)]["title"] not in html


def test_dictionary_has_search_translation_toggle_and_audio(parent, make_student):
    student = make_student()
    submit_lesson(student, N(1))
    html = words_html(student)
    assert 'id="dict-search"' in html and 'id="dict-hide"' in html and "data-play" in html
    assert "tts.js" in html                                   # кнопки 🔊 рисует общий скрипт


def test_student_home_links_to_dictionary(make_student):
    student = make_student()
    home = student.get("/student").get_data(as_text=True)
    assert 'href="/student/words"' in home and "Открыть словарь" in home


def test_dictionary_requires_student_login(anon, parent):
    assert anon.get("/student/words").status_code == 302
    assert parent.get("/student/words").status_code == 302     # родитель — не ученик
