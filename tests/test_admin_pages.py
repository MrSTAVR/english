# -*- coding: utf-8 -*-
"""Кабинет администратора разложен по вкладкам: каждая открывается, доступ только администратору."""
import pytest

from tests.helpers import db_scalar

PAGES = ["/parent", "/parent/students", "/parent/progress", "/parent/mistakes", "/parent/holidays",
         "/parent/logopeds", "/parent/updates"]


@pytest.mark.parametrize("url", PAGES)
def test_every_tab_opens_with_nav(parent, make_student, url):
    make_student()
    html = parent.get(url).get_data(as_text=True)
    assert 'class="admin-tabs"' in html and 'aria-current="page"' in html
    assert "ach-cards" not in html                     # огромной карточки ачивок больше нет


@pytest.mark.parametrize("url", PAGES + ["/parent/students/1"])
def test_tabs_need_admin(anon, make_student, url):
    make_student()
    assert anon.get(url).status_code == 302


def test_overview_and_student_page(parent, make_student):
    make_student()
    sid = db_scalar("SELECT id FROM students")
    html = parent.get("/parent").get_data(as_text=True)
    assert "Маша" in html and f"/parent/students/{sid}" in html and "занятий ещё не было" in html
    page = parent.get(f"/parent/students/{sid}").get_data(as_text=True)
    for part in ("Цель дня", "День рождения", "Каникулы", "Сад", "Зачесть пройденные уроки", "Удалить аккаунт"):
        assert part in page, part
    assert parent.get("/parent/students/999").status_code == 404


def test_actions_return_to_student_page_and_delete_to_list(parent, make_student):
    make_student()
    sid = db_scalar("SELECT id FROM students")
    r = parent.post(f"/parent/students/{sid}/goal", data={"lessons": "2", "words": "20"})
    assert r.headers["Location"].endswith(f"/parent/students/{sid}")
    r = parent.post(f"/parent/students/{sid}/delete")
    assert r.headers["Location"].endswith("/parent/students")
