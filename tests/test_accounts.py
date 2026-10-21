# -*- coding: utf-8 -*-
"""Бывший smoke_test_v2.py: аккаунты учеников и изоляция прогресса."""
import re

import pytest

from curriculum import LESSONS_BY_ID, MAIN_COUNT
from tests.helpers import (build_form, db_all, db_scalar, open_lesson,
                           submit_lesson)


def add(parent, **kw):
    data = {"display_name": "Х", "username": "kid", "password": "abcd", "emoji": "🐰"}
    data.update(kw)
    return parent.post("/parent/students/add", data=data,
                       follow_redirects=True).get_data(as_text=True)


def test_create_and_validation(parent):
    assert "Аккаунт для Маша создан" in add(parent, display_name="Маша",
                                             username="masha", password="secret1")
    assert "уже занят" in add(parent, username="MASHA")          # без учёта регистра
    assert "только английские буквы" in add(parent, username="машина")
    assert "не короче 4" in add(parent, password="12")


def test_student_login_errors(anon, make_student):
    make_student()
    r = anon.post("/login/student", data={"username": "ghost", "password": "1234"},
                  follow_redirects=True)
    assert "Такого аккаунта нет" in r.get_data(as_text=True)
    r = anon.post("/login/student", data={"username": "masha", "password": "wrong"},
                  follow_redirects=True)
    assert "Такого аккаунта нет или пароль неверный" in r.get_data(as_text=True)


def test_progress_is_isolated(make_student):
    masha = make_student("masha", "Маша", "secret1", "🦄")
    petya = make_student("petya", "Петя", "secret2", "🐱")

    assert "Идеально! 100%" in submit_lesson(masha, 1)
    assert f"1/{MAIN_COUNT}" in masha.get("/student").get_data(as_text=True)

    body = petya.get("/student").get_data(as_text=True)
    assert f"0/{MAIN_COUNT}" in body and "Закрой предыдущий урок" in body
    r = petya.get("/lesson/2", follow_redirects=True)
    assert "Сначала пройди предыдущий урок" in r.get_data(as_text=True)


def test_foreign_attempt_rejected(make_student):
    masha = make_student("masha", "Маша", "secret1")
    petya = make_student("petya", "Петя", "secret2", "🐱")
    submit_lesson(masha, 1)
    masha_attempt = open_lesson(masha, 2)
    r = petya.post("/lesson/2/submit",
                   data=build_form(LESSONS_BY_ID[2], masha_attempt))
    assert r.status_code == 400


def test_parent_sees_all_students(parent, make_student):
    masha = make_student("masha", "Маша", "secret1", "🦄")
    petya = make_student("petya", "Петя", "secret2", "🐱")
    submit_lesson(masha, 1)
    submit_lesson(petya, 1)

    body = parent.get("/parent").get_data(as_text=True)
    assert "Маша" in body and "Петя" in body and "🦄" in body
    assert db_scalar("SELECT COUNT(*) FROM attempts WHERE passed=1") == 2
    m = re.search(rf'<span class="stat-num">(\d+)/{MAIN_COUNT}</span>', body)
    assert m and m.group(1) == "1"        # общий прогресс — по лучшим, не сумма

    assert parent.get("/api/mistakes").get_json() == []

    submit_lesson(petya, 2, wrong=True)
    mistakes = parent.get("/api/mistakes").get_json()
    assert mistakes and all(x["student"] == "Петя" for x in mistakes)


def test_reset_password(anon, parent, make_student):
    make_student("petya", "Петя", "secret2", "🐱")
    sid = db_scalar("SELECT id FROM students WHERE username='petya'")
    parent.post(f"/parent/students/{sid}/reset_password",
                data={"password": "newpass9"}, follow_redirects=True)
    r = anon.post("/login/student", data={"username": "petya", "password": "secret2"},
                  follow_redirects=True)
    assert "Такого аккаунта нет" in r.get_data(as_text=True)
    r = anon.post("/login/student", data={"username": "petya", "password": "newpass9"},
                  follow_redirects=True)
    assert "Привет, Петя" in r.get_data(as_text=True)


def test_delete_requires_parent(make_student):
    masha = make_student()
    sid = db_scalar("SELECT id FROM students WHERE username='masha'")
    r = masha.post(f"/parent/students/{sid}/delete")
    assert r.status_code == 302
    assert db_scalar("SELECT COUNT(*) FROM students WHERE id=?", (sid,)) == 1


def test_delete_removes_account_and_progress(parent, make_student, anon):
    masha = make_student()
    submit_lesson(masha, 1)
    sid = db_scalar("SELECT id FROM students WHERE username='masha'")
    r = parent.post(f"/parent/students/{sid}/delete", follow_redirects=True)
    assert "удалён" in r.get_data(as_text=True)
    assert db_scalar("SELECT COUNT(*) FROM students") == 0
    assert db_scalar("SELECT COUNT(*) FROM attempts WHERE student_id=?", (sid,)) == 0
    assert db_scalar("SELECT COUNT(*) FROM achievements WHERE student_id=?", (sid,)) == 0
    r = anon.post("/login/student", data={"username": "masha", "password": "secret1"},
                  follow_redirects=True)
    assert "Такого аккаунта нет" in r.get_data(as_text=True)


@pytest.mark.xfail(strict=True, reason="BUG #2: при удалении ученика остаются garden/decorations")
def test_delete_removes_garden(parent, make_student):
    masha = make_student()
    masha.get("/student")                       # создаёт строку сада
    sid = db_scalar("SELECT id FROM students WHERE username='masha'")
    parent.post(f"/parent/students/{sid}/delete")
    assert db_scalar("SELECT COUNT(*) FROM garden WHERE student_id=?", (sid,)) == 0
