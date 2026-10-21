# -*- coding: utf-8 -*-
"""Помощник Чик-чик: контекст страниц и статические файлы."""
import json
import re
from pathlib import Path

from tests.helpers import submit_lesson

ROOT = Path(__file__).resolve().parent.parent


def settings(html):
    m = re.search(r"window\.MASCOT_SETTINGS = (\{.*?\});</script>", html, re.S)
    assert m, "MASCOT_SETTINGS не найден"
    return json.loads(m.group(1))


def test_assets_linked_and_served(anon):
    body = anon.get("/").get_data(as_text=True)
    assert "mascot.css" in body and "mascot.js" in body
    for name in ("mascot.css", "mascot.js"):
        assert anon.get("/static/" + name).status_code == 200


def test_student_pages_have_names_and_page_keys(make_student):
    c = make_student()
    home = settings(c.get("/student").get_data(as_text=True))
    assert home["page"] == "home" and home["student"] == "Маша" and home["enabled"] is True
    w = settings(c.get("/student/words").get_data(as_text=True))
    assert w["page"] == "words" and w["empty"] is True
    t = settings(c.get("/student/theory").get_data(as_text=True))
    assert t["page"] == "theory" and t["empty"] is True
    submit_lesson(c, 1)
    assert settings(c.get("/student/words").get_data(as_text=True))["empty"] is False
    assert settings(c.get("/student/theory").get_data(as_text=True))["empty"] is False


def test_mascot_disabled_for_parent(parent):
    html = parent.get("/parent").get_data(as_text=True)
    assert settings(html)["enabled"] is False


def test_old_mascot_code_is_gone():
    css = (ROOT / "static" / "style.css").read_text(encoding="utf-8")
    for old in (".mascot-body", ".mascot-balloon", "m-breathe", "m-jump"):
        assert old not in css
    js = (ROOT / "static" / "mascot.js").read_text(encoding="utf-8")
    assert "explode" in js and "feather" in js
    assert "dragstart" not in js
