# -*- coding: utf-8 -*-
"""Логопедическая часть: аккаунты логопедов, ученики (семейные аккаунты), входы и доступ."""
from datetime import date

import pytest

import config
import speech
from tests.helpers import db_all, db_scalar
from tests.test_vacation import conn


@pytest.fixture
def logoped(flask_app, parent):
    """Логопед, созданный администратором, уже вошедший в свой кабинет."""
    r = parent.post("/parent/logopeds", data={"action": "add", "name": "Елена Петровна", "username": "elena",
                                              "password": "secret12"}, follow_redirects=True)
    assert "Аккаунт логопеда создан" in r.get_data(as_text=True)
    c = flask_app.test_client()
    r = c.post("/logoped", data={"username": "elena", "password": "secret12"}, follow_redirects=True)
    assert "Здравствуйте, Елена Петровна" in r.get_data(as_text=True)
    return c


CHILD = {"child_name": "Петя", "birth_date": "2020-05-10", "parent_name": "Анна", "phone": "+7 900 1",
         "username": "petya", "password": "pass123"}


def add_child(c, **over):
    return c.post("/logoped/clients/add", data={**CHILD, **over}, follow_redirects=True)


def test_age_text():
    assert speech.age_text("2020-05-10", date(2025, 10, 22)) == "5 лет 5 мес."
    assert speech.age_text("2021-10-22", date(2025, 10, 22)) == "4 года"
    assert speech.age_text("2024-10-22", date(2025, 10, 22)) == "1 год"
    assert speech.age_text("", date(2025, 1, 1)) == "" and speech.age_text("bad") == ""


def test_admin_creates_logoped_with_validation(parent):
    for data, msg in (({"name": "", "username": "elena", "password": "secret12"}, "Укажите имя"),
                      ({"name": "Е", "username": "е", "password": "secret12"}, "Логин"),
                      ({"name": "Е", "username": "elena", "password": "123"}, "не короче")):
        r = parent.post("/parent/logopeds", data={"action": "add", **data}, follow_redirects=True)
        assert msg in r.get_data(as_text=True)
    assert db_scalar("SELECT COUNT(*) FROM sp_logopeds") == 0
    parent.post("/parent/logopeds", data={"action": "add", "name": "Е", "username": "elena", "password": "secret12"})
    r = parent.post("/parent/logopeds", data={"action": "add", "name": "Е2", "username": "ELENA", "password": "secret12"},
                    follow_redirects=True)
    assert "уже занят" in r.get_data(as_text=True)
    html = parent.get("/parent/logopeds").get_data(as_text=True)
    assert 'id="logopeds"' in html and "<code>elena</code>" in html


def test_logoped_login_and_password_reset(parent, anon):
    parent.post("/parent/logopeds", data={"action": "add", "name": "Е", "username": "elena", "password": "secret12"})
    r = anon.post("/logoped", data={"username": "elena", "password": "wrong"}, follow_redirects=True)
    assert "Неверный логин или пароль" in r.get_data(as_text=True)
    lid = db_scalar("SELECT id FROM sp_logopeds")
    parent.post("/parent/logopeds", data={"action": "password", "id": lid, "password": "newpass1"})
    assert anon.post("/logoped", data={"username": "elena", "password": "newpass1"}).headers["Location"].endswith("/logoped/home")


def test_logoped_login_rate_limited(parent, anon, monkeypatch):
    monkeypatch.setitem(config.LOGIN_LIMITS, "ip", 1000)
    parent.post("/parent/logopeds", data={"action": "add", "name": "Е", "username": "elena", "password": "secret12"})
    for _ in range(config.LOGIN_LIMITS["logoped"]):
        anon.post("/logoped", data={"username": "elena", "password": "wrong"})
    r = anon.post("/logoped", data={"username": "elena", "password": "secret12"}, follow_redirects=True)
    assert "Слишком много неудачных попыток" in r.get_data(as_text=True)


def test_add_client_validation(logoped):
    for over, msg in (({"child_name": ""}, "Укажите имя ребёнка"), ({"username": "п"}, "Логин"),
                      ({"password": "1"}, "не короче"), ({"birth_date": "2999-01-01"}, "Дата рождения")):
        assert msg in add_child(logoped, **over).get_data(as_text=True)
    assert db_scalar("SELECT COUNT(*) FROM sp_clients") == 0
    html = add_child(logoped).get_data(as_text=True)
    assert "Ученик добавлен" in html and "Петя" in html and "<code>petya</code>" in html
    assert "уже занят" in add_child(logoped, child_name="Другой").get_data(as_text=True)
    assert "Петя" in logoped.get("/logoped/home").get_data(as_text=True)


def test_edit_archive_and_family_access(logoped, flask_app):
    add_child(logoped)
    cid = db_scalar("SELECT id FROM sp_clients")
    logoped.post(f"/logoped/clients/{cid}/edit", data={"action": "contacts", "child_name": "Пётр", "birth_date": "",
                                                       "parent_name": "Анна", "phone": "+7"})
    assert db_all("SELECT child_name, birth_date FROM sp_clients") == [("Пётр", None)]

    fam = flask_app.test_client()
    r = fam.post("/family", data={"username": "petya", "password": "pass123"}, follow_redirects=True)
    html = r.get_data(as_text=True)
    assert "Кабинет родителя" in html and "Пётр" in html and "Елена Петровна" in html

    logoped.post(f"/logoped/clients/{cid}/edit", data={"action": "password", "password": "newpass"})
    logoped.post(f"/logoped/clients/{cid}/edit", data={"action": "archive"})
    assert fam.get("/family/home").status_code == 302                   # архив — сессия семьи закрыта
    r = fam.post("/family", data={"username": "petya", "password": "newpass"}, follow_redirects=True)
    assert "Неверный логин или пароль" in r.get_data(as_text=True)
    assert "Архив (1)" in logoped.get("/logoped/home").get_data(as_text=True)
    logoped.post(f"/logoped/clients/{cid}/edit", data={"action": "restore"})
    assert fam.post("/family", data={"username": "petya", "password": "newpass"}).headers["Location"].endswith("/family/home")
    assert logoped.post(f"/logoped/clients/{cid}/edit", data={"action": "drop"}).status_code == 400


def test_logoped_sees_only_own_clients(logoped, parent, flask_app):
    add_child(logoped)
    cid = db_scalar("SELECT id FROM sp_clients")
    parent.post("/parent/logopeds", data={"action": "add", "name": "Другой", "username": "other", "password": "secret12"})
    other = flask_app.test_client()
    other.post("/logoped", data={"username": "other", "password": "secret12"})
    assert other.get(f"/logoped/clients/{cid}").status_code == 404
    assert other.post(f"/logoped/clients/{cid}/edit", data={"action": "archive"}).status_code == 404
    assert f"/logoped/clients/{cid}" not in other.get("/logoped/home").get_data(as_text=True)


def test_roles_are_separated(logoped, make_student, flask_app, anon):
    add_child(logoped)
    student = make_student()
    assert student.get("/logoped/home").headers["Location"].endswith("/logoped")
    assert student.get("/family/home").headers["Location"].endswith("/family")
    assert logoped.get("/parent").status_code == 302
    assert logoped.get("/family/home").status_code == 302
    fam = flask_app.test_client()
    fam.post("/family", data={"username": "petya", "password": "pass123"})
    assert fam.get("/logoped/home").status_code == 302 and fam.get("/student").status_code == 302
    assert anon.get("/logoped/home").status_code == 302


def test_speech_pages_look_separate_and_logout(logoped):
    html = logoped.get("/logoped/home").get_data(as_text=True)
    assert "logo-badge" in html and "Логопед" in html and "MASCOT_SETTINGS" not in html and "English Fun" not in html
    assert logoped.get("/logout").headers["Location"].endswith("/logoped")


# ---------------------------------------------------------------- шаг 2: карточка и звуковая карта

def _family(flask_app):
    fam = flask_app.test_client()
    fam.post("/family", data={"username": "petya", "password": "pass123"})
    return fam


def test_diagnosis_is_private(logoped, flask_app):
    add_child(logoped)
    cid = db_scalar("SELECT id FROM sp_clients")
    logoped.post(f"/logoped/clients/{cid}/card", data={"diagnosis": "ФФНР секретно", "program": "1. Р постановка"})
    html = logoped.get(f"/logoped/clients/{cid}").get_data(as_text=True)
    assert "ФФНР секретно" in html and "1. Р постановка" in html
    fam_html = _family(flask_app).get("/family/home").get_data(as_text=True)
    assert "ФФНР" not in fam_html and "постановка" not in fam_html


def test_sound_map_stages_history_and_family_view(logoped, flask_app):
    add_child(logoped)
    cid = db_scalar("SELECT id FROM sp_clients")
    logoped.post(f"/logoped/clients/{cid}/sound", data={"sound": "Р", "stage": "1", "action": "set"})
    logoped.post(f"/logoped/clients/{cid}/sound", data={"sound": "Ш", "stage": str(speech.DONE_STAGE), "action": "set"})
    logoped.post(f"/logoped/clients/{cid}/sound", data={"sound": "Р", "stage": "3", "note": "лучше в начале слова",
                                                        "action": "set"})
    logoped.post(f"/logoped/clients/{cid}/sound", data={"sound": "Р", "stage": "3", "note": "ещё заметка",
                                                        "action": "set"})       # стадия та же — в историю не пишем
    assert db_all("SELECT sound, stage FROM sp_sound_log ORDER BY id") == [("Р", 1), ("Ш", speech.DONE_STAGE), ("Р", 3)]
    m = {s["sound"]: s for s in speech.sound_map(conn(), cid)}
    assert list(m) == ["Ш", "Р"] and m["Ш"]["percent"] == 100 and m["Р"]["note"] == "ещё заметка"
    html = logoped.get(f"/logoped/clients/{cid}").get_data(as_text=True)
    assert "автоматизация: слова" in html and "История (3)" in html
    fam = _family(flask_app).get("/family/home").get_data(as_text=True)
    assert "Наши звуки" in fam and "тренируем в словах" in fam and "говорим правильно" in fam
    assert "ещё заметка" not in fam                                   # заметки логопеда семье не видны
    logoped.post(f"/logoped/clients/{cid}/sound", data={"sound": "Ш", "action": "remove"})
    assert db_all("SELECT sound FROM sp_sounds") == [("Р",)]
    assert logoped.post(f"/logoped/clients/{cid}/sound", data={"sound": "Q", "stage": "1", "action": "set"}).status_code == 400
    assert logoped.post(f"/logoped/clients/{cid}/sound", data={"sound": "Р", "stage": "99", "action": "set"}).status_code == 400


def test_card_and_sounds_only_for_own_clients(logoped, parent, flask_app):
    add_child(logoped)
    cid = db_scalar("SELECT id FROM sp_clients")
    parent.post("/parent/logopeds", data={"action": "add", "name": "Другой", "username": "other", "password": "secret12"})
    other = flask_app.test_client()
    other.post("/logoped", data={"username": "other", "password": "secret12"})
    assert other.post(f"/logoped/clients/{cid}/card", data={"diagnosis": "x"}).status_code == 404
    assert other.post(f"/logoped/clients/{cid}/sound", data={"sound": "Р", "stage": "1"}).status_code == 404
    assert db_scalar("SELECT COUNT(*) FROM sp_card") == 0 and db_scalar("SELECT COUNT(*) FROM sp_sounds") == 0
