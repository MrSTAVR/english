# -*- coding: utf-8 -*-
"""Регрессионные тесты на баги, исправленные на шаге 4."""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import config
import security
from curriculum import MAIN_COUNT
from data.extra_lessons import EXTRA_LESSONS
from tests.helpers import N, db_all, submit_lesson

ROOT = Path(__file__).resolve().parent.parent


def earned_keys():
    return {r[0] for r in db_all("SELECT key FROM achievements")}


# ---------- #1 доп. уроки не считаются прогрессом основного курса ----------

def test_extra_plus_main_counts_only_main(make_student):
    c = make_student()
    submit_lesson(c, EXTRA_LESSONS[0]["id"])
    submit_lesson(c, N(1))
    home = c.get("/student").get_data(as_text=True)
    assert f"1/{MAIN_COUNT}" in home
    assert "all_lessons" not in earned_keys()


# ---------- #3 стабильное перемешивание ----------

def test_shuffle_words_is_stable_across_processes():
    code = ("from template_filters import shuffle_words; "
            "print(shuffle_words(['I', 'am', 'a', 'student', 'here']))")
    outs = {subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True,
                           env={**os.environ, "PYTHONHASHSEED": str(seed)},
                           capture_output=True, text=True).stdout
            for seed in (1, 2, 3)}
    assert len(outs) == 1


# ---------- #6 серия идеальных тестов ----------

def test_three_clean_in_a_row_gives_achievement(make_student):
    c = make_student()
    for n in (1, 2, 3):
        submit_lesson(c, N(n))
    assert "clean_three" in earned_keys()


def test_failure_breaks_clean_run(make_student):
    c = make_student()
    submit_lesson(c, N(1))
    submit_lesson(c, N(2), wrong=True)      # провал сбрасывает серию
    submit_lesson(c, N(2))
    submit_lesson(c, N(3))
    assert "clean_three" not in earned_keys()


# ---------- #4 пароль родителя ----------

def test_check_parent_password():
    assert security.check_parent_password(config.PARENT_PASSWORD)
    assert not security.check_parent_password("definitely-wrong")
    assert not security.check_parent_password("")


# ---------- #5 CSRF ----------

@pytest.fixture
def csrf_on(flask_app, monkeypatch):
    monkeypatch.setitem(flask_app.config, "CSRF_ENABLED", True)


def token_from(html):
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, "в форме нет csrf_token"
    return m.group(1)


def test_post_without_token_is_rejected(anon, csrf_on):
    r = anon.post("/login/parent", data={"password": config.PARENT_PASSWORD})
    assert r.status_code == 400


def test_post_with_wrong_token_is_rejected(anon, csrf_on):
    anon.get("/")
    r = anon.post("/login/parent", data={"password": config.PARENT_PASSWORD,
                                         "csrf_token": "wrong"})
    assert r.status_code == 400


def test_login_with_valid_token(anon, csrf_on):
    tok = token_from(anon.get("/").get_data(as_text=True))
    r = anon.post("/login/parent", data={"password": config.PARENT_PASSWORD,
                                         "csrf_token": tok})
    assert r.status_code == 302 and r.headers["Location"].endswith("/parent")


def test_parent_can_add_student_through_real_forms(anon, csrf_on):
    tok = token_from(anon.get("/").get_data(as_text=True))
    anon.post("/login/parent", data={"password": config.PARENT_PASSWORD, "csrf_token": tok})
    tok = token_from(anon.get("/parent/students").get_data(as_text=True))
    r = anon.post("/parent/students/add", follow_redirects=True, data={
        "display_name": "Маша", "username": "masha", "password": "secret1",
        "emoji": "🦄", "csrf_token": tok})
    assert "Аккаунт для Маша создан" in r.get_data(as_text=True)


def test_every_post_form_in_templates_has_token():
    for path in sorted((ROOT / "templates").glob("*.html")):
        text = path.read_text(encoding="utf-8")
        forms = re.findall(r"<form\b[^>]*\bmethod\s*=\s*[\"']post[\"']", text, re.I)
        assert text.count("csrf_token()") >= len(forms), path.name


# ---------------------------------------------------------------- вход администратора

def test_index_has_only_student_form_and_admin_corner(anon):
    html = anon.get("/").get_data(as_text=True)
    assert "Пароль администратора" not in html and 'class="admin-corner"' in html and 'href="/admin"' in html


def test_admin_login_page_and_redirects(anon, parent):
    html = anon.get("/admin").get_data(as_text=True)
    assert "Пароль администратора" in html and "/login/parent" in html
    r = anon.post("/login/parent", data={"password": "0000"})
    assert r.headers["Location"].endswith("/admin")
    assert parent.get("/admin").headers["Location"].endswith("/parent")
    assert "Кабинет администратора" in parent.get("/parent").get_data(as_text=True)
