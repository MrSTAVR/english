# -*- coding: utf-8 -*-
"""Незаконченный урок: место сохраняется и восстанавливается, после теста стирается."""
import json
import re

from tests.helpers import N, db_scalar, submit_lesson


def _state_on_page(html):
    m = re.search(r'<script type="application/json" id="ls-state" data-lesson="\d+">(.*?)</script>', html, re.S)
    return json.loads(m.group(1))


def test_progress_saved_restored_and_cleared(make_student):
    c = make_student()
    lid = N(1)
    html = c.get(f"/lesson/{lid}").get_data(as_text=True)
    assert _state_on_page(html) is None
    state = {"step": "step-test", "words": {"i": 3, "seen": [0, 1, 2]}, "ex": {"radio": {"ex0": "1"}, "text": []},
             "test": {"radio": {"q0": "2"}, "text": ["hello"]}, "secs": 120}
    assert c.post(f"/api/lesson/{lid}/progress", json={"state": state}).status_code == 200
    html = c.get(f"/lesson/{lid}").get_data(as_text=True)
    assert _state_on_page(html)["test"]["radio"] == {"q0": "2"}
    assert 'id="ls-resume"' in html
    # время урока копится: старт сдвинут на сохранённые секунды
    ts = float(re.search(r"var START_TS = ([\d.]+);", html).group(1))
    assert db_scalar("SELECT COUNT(*) FROM lesson_progress") == 1 and ts > 0
    submit_lesson(c, lid)
    assert db_scalar("SELECT COUNT(*) FROM lesson_progress") == 0


def test_progress_reset_and_validation(make_student, anon):
    c = make_student()
    lid = N(1)
    assert c.post(f"/api/lesson/{lid}/progress", json={"state": {"step": "nope"}}).status_code == 400
    assert c.post(f"/api/lesson/{lid}/progress", json={"state": {"step": "step-material", "pad": "x" * 30000}}).status_code == 400
    assert c.post("/api/lesson/99999/progress", json={"state": {"step": "step-material"}}).status_code == 404
    assert anon.post(f"/api/lesson/{lid}/progress", json={"state": {"step": "step-material"}}).status_code == 403
    c.post(f"/api/lesson/{lid}/progress", json={"state": {"step": "step-material"}})
    assert db_scalar("SELECT COUNT(*) FROM lesson_progress") == 1
    c.post(f"/api/lesson/{lid}/progress", json={"reset": True})
    assert db_scalar("SELECT COUNT(*) FROM lesson_progress") == 0
