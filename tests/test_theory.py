# -*- coding: utf-8 -*-
"""Страница теории ученика: правила из пройденных уроков."""
from curriculum import LESSONS_BY_ID
from tests.helpers import db_scalar, submit_lesson
from tests.helpers import N


def theory_html(client):
    r = client.get("/student/theory")
    assert r.status_code == 200
    return r.get_data(as_text=True)


def test_empty_theory_for_new_student(make_student):
    assert "Теории пока нет" in theory_html(make_student())


def test_theory_only_for_passed_lessons(make_student):
    student = make_student()
    submit_lesson(student, 1)
    html = theory_html(student)
    t1 = LESSONS_BY_ID[1]["theory"]
    assert t1["intro"] in html and t1["blocks"][0]["title"] in html and t1["tip"] in html
    assert LESSONS_BY_ID[2]["theory"]["intro"] not in html
    assert "Правила из всех пройденных уроков: <b>1</b>" in html


def test_credited_lessons_have_theory(parent, make_student):
    student = make_student()
    sid = db_scalar("SELECT id FROM students WHERE username='masha'")
    parent.post(f"/parent/students/{sid}/credit", data={"upto": "3", "action": "add"})
    html = theory_html(student)
    for i in (1, 2, 3):
        assert LESSONS_BY_ID[N(i)]["theory"]["intro"] in html
    assert LESSONS_BY_ID[N(4)]["theory"]["intro"] not in html
    assert 'id="th-search"' in html and f'href="/lesson/{N(3)}"' in html


def test_student_home_links_to_theory(make_student):
    home = make_student().get("/student").get_data(as_text=True)
    assert 'href="/student/theory"' in home and "Открыть теорию" in home


def test_theory_requires_student_login(anon, parent):
    assert anon.get("/student/theory").status_code == 302
    assert parent.get("/student/theory").status_code == 302
