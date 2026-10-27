# -*- coding: utf-8 -*-
"""Быстрый переход админка ↔ учётка ученика без пароля."""
import time

from tests.test_vacation import sid_of


def test_switch_there_and_back(parent, make_student):
    make_student(); sid = sid_of()
    html = parent.get(f"/parent/students/{sid}").get_data(as_text=True)
    assert f"/parent/students/{sid}/switch" in html
    r = parent.post(f"/parent/students/{sid}/switch")
    assert r.headers["Location"].endswith("/student")
    home = parent.get("/student").get_data(as_text=True)
    assert "В админку" in home and "/admin/back" in home
    assert parent.get("/parent").status_code == 302                        # в роли ученика админка закрыта
    r = parent.post("/admin/back")
    assert r.headers["Location"].endswith(f"/parent/students/{sid}")
    page = parent.get("/parent").get_data(as_text=True)
    assert "В учётку" in page and f"/parent/students/{sid}/switch" in page


def test_back_needs_admin_session(make_student):
    c = make_student()                                                      # обычный вход ученика (как у Маши)
    assert "/admin/back" not in c.get("/student").get_data(as_text=True)
    r = c.post("/admin/back")
    assert r.headers["Location"].endswith("/admin")
    assert c.get("/parent").status_code == 302


def test_back_expires_with_admin_login(parent, make_student):
    make_student(); sid = sid_of()
    parent.post(f"/parent/students/{sid}/switch")
    with parent.session_transaction() as s:
        s["parent_until"] = time.time() - 1
    assert "/admin/back" not in parent.get("/student").get_data(as_text=True)
    assert parent.post("/admin/back").headers["Location"].endswith("/admin")


def test_switch_requires_admin(make_student):
    c = make_student(); sid = sid_of()
    assert c.post(f"/parent/students/{sid}/switch").headers["Location"].endswith("/")
