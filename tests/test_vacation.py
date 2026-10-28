# -*- coding: utf-8 -*-
"""Каникулы (серия не сгорает) и офлайн-страницы в service worker."""
import re
import sqlite3
from datetime import datetime, timedelta

import database
import garden
from tests.helpers import db_scalar


def D(n):
    return (datetime.now().date() + timedelta(days=n)).isoformat()


def sid_of():
    return db_scalar("SELECT id FROM students WHERE username=?", ("masha",))


def conn():
    c = sqlite3.connect(database.DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def add_attempt(c, sid, day):
    c.execute("INSERT INTO attempts (student_id, lesson_id, started_at, finished_at) VALUES (?,?,?,?)",
              (sid, 1, day + "T10:00:00", day + "T10:10:00"))     # пройденный тест — день занятий
    c.commit()


def add_vac(c, sid, a, b):
    c.execute("INSERT INTO vacations (student_id, start_day, end_day) VALUES (?,?,?)", (sid, a, b))
    c.commit()


def test_gap_without_vacation_breaks_streak(make_student):
    make_student(); sid = sid_of(); c = conn()
    for n in (-5, -4):
        add_attempt(c, sid, D(n))
    assert garden.compute_streak_from_history(c, sid)[0] == 0


def test_vacation_keeps_streak(make_student):
    make_student(); sid = sid_of(); c = conn()
    for n in (-6, -5, -4):
        add_attempt(c, sid, D(n))
    add_vac(c, sid, D(-3), D(-1))
    assert garden.compute_streak_from_history(c, sid)[0] == 3   # каникулы не прерывают и не считаются


def test_vacation_inside_streak(make_student):
    make_student(); sid = sid_of(); c = conn()
    for n in (-8, -7, -1, 0):
        add_attempt(c, sid, D(n))
    add_vac(c, sid, D(-6), D(-2))
    assert garden.compute_streak_from_history(c, sid)[0] == 4


def test_touch_streak_continues_after_vacation(make_student):
    make_student(); sid = sid_of(); c = conn()
    c.execute("UPDATE garden SET streak_days=5, last_study_day=? WHERE student_id=?", (D(-4), sid))
    c.commit()
    add_vac(c, sid, D(-3), D(-1))
    assert garden.touch_streak(c, sid)["streak_days"] == 6


def test_touch_streak_resets_without_vacation(make_student):
    make_student(); sid = sid_of(); c = conn()
    c.execute("UPDATE garden SET streak_days=5, last_study_day=? WHERE student_id=?", (D(-4), sid))
    c.commit()
    assert garden.touch_streak(c, sid)["streak_days"] == 1


def test_parent_sets_and_cancels_vacation(parent, make_student):
    c = make_student(); sid = sid_of()
    r = parent.post(f"/parent/students/{sid}/vacation",
                    data={"action": "add", "start_day": D(0), "end_day": D(5)})
    assert r.status_code == 302
    assert db_scalar("SELECT COUNT(*) FROM vacations WHERE student_id=?", (sid,)) == 1
    assert "каникулы" in parent.get("/parent").get_data(as_text=True)
    assert "У тебя каникулы" in c.get("/student").get_data(as_text=True)
    parent.post(f"/parent/students/{sid}/vacation", data={"action": "cancel"})
    assert db_scalar("SELECT COUNT(*) FROM vacations WHERE student_id=?", (sid,)) == 0
    assert "У тебя каникулы" not in c.get("/student").get_data(as_text=True)


def test_vacation_validation(parent, make_student):
    make_student(); sid = sid_of()
    for a, b in ((D(5), D(2)), (D(0), D(90)), (D(-10), D(-5)), ("", "")):
        parent.post(f"/parent/students/{sid}/vacation", data={"action": "add", "start_day": a, "end_day": b})
    assert db_scalar("SELECT COUNT(*) FROM vacations") == 0


def test_vacation_requires_parent(make_student, anon):
    c = make_student(); sid = sid_of()
    c.post(f"/parent/students/{sid}/vacation", data={"action": "add", "start_day": D(0), "end_day": D(1)})
    assert db_scalar("SELECT COUNT(*) FROM vacations") == 0


def test_delete_student_removes_vacations(parent, make_student):
    make_student(); sid = sid_of()
    parent.post(f"/parent/students/{sid}/vacation", data={"action": "add", "start_day": D(0), "end_day": D(1)})
    parent.post(f"/parent/students/{sid}/delete")
    assert db_scalar("SELECT COUNT(*) FROM vacations") == 0


def test_sw_caches_study_pages_offline(anon):
    body = anon.get("/sw.js").get_data(as_text=True)
    assert "english-pages" in body and "OFFLINE_OK" in body and "clear-pages" in body
    assert "/lesson" in body and "games" in body and "stories" in body
    pj = anon.get("/static/pwa.js").get_data(as_text=True)
    assert "offline-bar" in pj and "clear-pages" in pj


def test_one_missed_day_does_not_break_streak(make_student):
    """«Запасной день»: один пропуск серию не рвёт, но не чаще раза в 7 дней; пропущенный день не считается."""
    make_student(); sid = sid_of(); c = conn()
    for n in (-4, -3, -1, 0):                                     # пропущен позавчера
        add_attempt(c, sid, D(n))
    assert garden.compute_streak_from_history(c, sid)[0] == 4


def test_missed_yesterday_keeps_streak_until_today(make_student):
    make_student(); sid = sid_of(); c = conn()
    for n in (-4, -3, -2):                                        # вчера не занималась — серия ещё жива
        add_attempt(c, sid, D(n))
    assert garden.compute_streak_from_history(c, sid)[0] == 3


def test_two_missed_days_break_streak(make_student):
    make_student(); sid = sid_of(); c = conn()
    for n in (-5, -4, -1):
        add_attempt(c, sid, D(n))
    assert garden.compute_streak_from_history(c, sid)[0] == 1


def test_freeze_not_more_often_than_weekly(make_student):
    make_student(); sid = sid_of(); c = conn()
    for n in (-6, -4, -2, -1, 0):                                 # два одиночных пропуска за неделю
        add_attempt(c, sid, D(n))
    assert garden.compute_streak_from_history(c, sid)[0] == 4    # второй пропуск рвёт: -1, 0, -2 и -4


def test_game_or_review_day_counts_but_opening_lesson_does_not(make_student):
    make_student(); sid = sid_of(); c = conn()
    c.execute("INSERT INTO activity (student_id, day, kind) VALUES (?, ?, 'game')", (sid, D(-1)))
    c.execute("INSERT INTO daily_goal (student_id, day, lessons, words, done) VALUES (?, ?, 0, 5, 0)", (sid, D(0)))
    c.execute("INSERT INTO attempts (student_id, lesson_id, started_at) VALUES (?, 1, ?)", (sid, D(-2) + "T10:00:00"))
    c.commit()
    assert garden.compute_streak_from_history(c, sid)[0] == 2
