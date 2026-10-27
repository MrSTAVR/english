# -*- coding: utf-8 -*-
"""Отправка теста: повторная отправка, старая попытка из офлайн-кэша, чужая попытка, испорченные записи."""
import sqlite3

import database
from curriculum import LESSONS
from tests.helpers import build_form, db_scalar, open_lesson


def _exec(sql, args=()):
    conn = sqlite3.connect(database.DB_PATH)
    try:
        conn.execute(sql, args)
        conn.commit()
    finally:
        conn.close()


def test_double_submit_is_not_an_error(make_student):
    """Двойное нажатие «Проверить» или «Назад» + отправка — не голая 400, а главная с сообщением."""
    c = make_student()
    l = LESSONS[0]
    aid = open_lesson(c, l["id"])
    form = build_form(l, aid)
    assert c.post(f"/lesson/{l['id']}/submit", data=form).status_code == 200
    r = c.post(f"/lesson/{l['id']}/submit", data=form)
    assert r.status_code == 302 and r.headers["Location"].endswith("/student")
    assert db_scalar("SELECT COUNT(*) FROM attempts WHERE finished_at IS NOT NULL") == 1


def test_old_cached_attempt_gets_new_attempt(make_student):
    """Страница урока из офлайн-кэша несёт уже закрытую попытку — ответы не теряем."""
    c = make_student()
    l = LESSONS[0]
    aid = open_lesson(c, l["id"])
    form = build_form(l, aid)
    c.post(f"/lesson/{l['id']}/submit", data=form)
    _exec("UPDATE attempts SET finished_at='2026-01-01T10:00:00' WHERE id=?", (aid,))
    r = c.post(f"/lesson/{l['id']}/submit", data=form)
    body = r.get_data(as_text=True)
    assert r.status_code == 200 and ("Урок пройден" in body or "Идеально" in body)
    assert db_scalar("SELECT COUNT(*) FROM attempts WHERE finished_at IS NOT NULL") == 2


def test_attempt_of_other_lesson_is_rejected(make_student):
    """Попытку одного урока нельзя отправить ответами другого (и засчитать закрытый урок)."""
    c = make_student()
    first, second = LESSONS[0], LESSONS[1]
    aid = open_lesson(c, first["id"])
    r = c.post(f"/lesson/{second['id']}/submit", data=build_form(second, aid))
    assert r.status_code == 400
    assert db_scalar("SELECT COUNT(*) FROM attempts WHERE passed=1") == 0


def test_broken_mistakes_json_does_not_break_pages(make_student):
    """Одна испорченная запись попытки не роняет страницы ученицы."""
    c = make_student()
    l = LESSONS[0]
    aid = open_lesson(c, l["id"])
    c.post(f"/lesson/{l['id']}/submit", data=build_form(l, aid))
    _exec("UPDATE attempts SET mistakes_json='{bad', details_json='[1]' WHERE id=?", (aid,))
    for url in ("/student", f"/lesson/{l['id']}", "/student/achievements"):
        assert c.get(url).status_code == 200, url
