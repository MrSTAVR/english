# -*- coding: utf-8 -*-
"""Испорченные данные не роняют страницы, а оставляют запись в журнале (вместо «глухого» except Exception)."""
import logging
import sqlite3

import config
import database
import seasons
import speech_schedule
from security import verify_password
from tests.helpers import N, db_scalar, submit_lesson


def test_broken_attempt_json_is_logged_not_fatal(parent, make_student, caplog):
    c = make_student()
    submit_lesson(c, N(1), wrong=True)
    con = sqlite3.connect(database.DB_PATH)
    con.execute("UPDATE attempts SET details_json='{oops', mistakes_json='[bad'")
    con.commit(); con.close()
    sid = db_scalar("SELECT id FROM students")
    with caplog.at_level(logging.WARNING):
        assert parent.get(f"/parent/students/{sid}").status_code == 200
        assert parent.get("/api/mistakes").get_json() == []
        assert c.get("/student").status_code == 200
    assert "не читается details_json" in caplog.text and "не читается mistakes_json" in caplog.text


def test_verify_password_with_broken_hash():
    assert verify_password("garbage", "x") is False
    assert verify_password("pbkdf2$zz$zz", "x") is False
    assert verify_password(None, "x") is False


def test_season_setting_outside_request_is_none():
    assert seasons._setting("season_halloween") is None


def test_bad_timezone_falls_back_and_warns(monkeypatch, caplog):
    monkeypatch.setattr(config, "TIMEZONE", "Nowhere/Nothing")
    speech_schedule._warn_tz.cache_clear()
    with caplog.at_level(logging.WARNING):
        assert speech_schedule.now().second == 0
    assert "часовой пояс Nowhere/Nothing недоступен" in caplog.text
