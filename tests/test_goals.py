# -*- coding: utf-8 -*-
"""Цель дня (урок + повторение), эмодзи-картинки к словам."""
import sqlite3
from datetime import date, timedelta

import database
import goals
from curriculum import LESSONS
from data.emoji import emoji_for
from tests.helpers import N, db_all, db_scalar, submit_lesson


def _sid():
    return db_scalar("SELECT id FROM students WHERE username='masha'")


def _db():
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def test_needs_shrink_when_nothing_to_do():
    full = {"lessons_completed": 3}
    assert goals.needs(full, 20) == (1, 10)
    assert goals.needs(full, 2) == (1, 0)                       # слов для повторения ещё нет
    assert goals.needs({"lessons_completed": len(LESSONS)}, 20) == (0, 10)


def test_goal_completes_once_and_gives_coins(flask_app, make_student):
    make_student()
    db = _db()
    stats = {"lessons_completed": 3}
    today = date(2026, 3, 3)
    _r, c, just = goals.add(db, _sid(), stats, 20, lessons=1, today=today)
    assert not just and c == 0
    _r, c, just = goals.add(db, _sid(), stats, 20, words=9, today=today)
    assert not just
    _r, c, just = goals.add(db, _sid(), stats, 20, words=1, today=today)
    assert just and c == goals.GOAL_COINS
    _r, c, just = goals.add(db, _sid(), stats, 20, words=5, today=today)
    assert not just and c == 0                                    # повторно не награждаем
    assert goals.goal_days(db, _sid()) == 1
    assert db.execute("SELECT coins FROM garden WHERE student_id=?", (_sid(),)).fetchone()["coins"] == goals.GOAL_COINS
    goals.add(db, _sid(), stats, 20, lessons=1, words=10, today=today + timedelta(days=1))
    assert goals.goal_days(db, _sid()) == 2
    db.close()


def test_home_shows_goal_card_and_progress(parent, make_student):
    c = make_student()
    html = c.get("/student").get_data(as_text=True)
    assert "Цель на сегодня" in html and "0/1" in html
    submit_lesson(c, N(1))
    html = c.get("/student").get_data(as_text=True)
    assert "1/1" in html


def test_lesson_and_review_complete_goal_with_achievement(parent, make_student):
    c = make_student()
    sid = _sid()
    parent.post(f"/parent/students/{sid}/credit", data={"upto": "10", "action": "add"})
    submit_lesson(c, N(11))                                        # пройден «настоящий» урок
    last = None
    for _ in range(10):
        last = c.post("/api/review", json={"key": "cat", "ok": True}).get_json()
    assert last["goalDone"] and last["goalCoins"] == goals.GOAL_COINS
    assert db_scalar("SELECT done FROM daily_goal WHERE student_id=?", (sid,)) == 1
    assert "goal_1" in {r[0] for r in db_all("SELECT key FROM achievements")}


def test_failed_lesson_does_not_count(make_student):
    c = make_student()
    submit_lesson(c, N(1), wrong=True)
    assert db_all("SELECT lessons FROM daily_goal") in ([], [(0,)])


def test_emoji_for_words():
    assert emoji_for("cat") == "🐱" and emoji_for("Mother / Mom") == "👩"
    assert emoji_for("Ice cream") == "🍦" and emoji_for("I have got a cat.") == ""


def test_flashcards_and_dictionary_show_pictures(parent, make_student):
    c = make_student()
    html = c.get(f"/lesson/{N(1)}").get_data(as_text=True)
    assert 'id="wd-data"' in html and '"pic"' in html
    parent.post(f"/parent/students/{_sid()}/credit", data={"upto": "1", "action": "add"})
    assert 'class="dict-pic"' in c.get("/student/words").get_data(as_text=True)
