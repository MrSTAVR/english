# -*- coding: utf-8 -*-
"""CSRF: токен вычисляется из зерна входа — одинаковый на всех страницах, старые токены сессий работают."""
import re

import config


def _meta(html):
    return re.search(r'<meta name="csrf-token" content="([^"]+)"', html).group(1)


def test_token_stable_and_checked(flask_app, parent):
    flask_app.config["CSRF_ENABLED"] = True
    try:
        c = flask_app.test_client()
        t0 = _meta(c.get("/admin").get_data(as_text=True))
        r = c.post("/login/parent", data={"password": config.PARENT_PASSWORD, "csrf_token": t0})
        assert r.status_code == 302
        a = _meta(c.get("/parent").get_data(as_text=True))
        b = _meta(c.get("/parent/students").get_data(as_text=True))
        assert a == b and a != t0                   # новое зерно при входе, дальше токен не меняется
        with c.session_transaction() as s:
            assert "csrf_token" not in s            # токен не хранится — нечего перетирать
        assert c.post("/parent/students/add", data={"display_name": "Аня"}).status_code == 400
        r = c.post("/parent/students/add", data={"display_name": "Аня", "username": "anya", "password": "secret1",
                                                 "emoji": "🐼", "csrf_token": a})
        assert r.status_code == 302
        # сессия «до зерна»: сохранённый токен продолжает работать
        with c.session_transaction() as s:
            s["csrf_token"] = "legacy123"
        assert _meta(c.get("/parent").get_data(as_text=True)) == "legacy123"
        assert c.post("/parent/students/add", data={"display_name": "Катя", "username": "kate", "password": "secret1",
                                                    "emoji": "🐼", "csrf_token": "legacy123"}).status_code == 302
    finally:
        flask_app.config["CSRF_ENABLED"] = False
