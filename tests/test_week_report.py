# -*- coding: utf-8 -*-
"""Цель дня от родителя и недельный отчёт в кабинете родителя."""
import sqlite3
from datetime import date, timedelta

import database
import goals
import report
from tests.helpers import N, db_all, db_scalar, submit_lesson


def _sid():
    return db_scalar("SELECT id FROM students WHERE username='masha'")


def _db():
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# --- цель дня ---

def test_needs_uses_custom_goal_and_lessons_left():
    assert goals.needs({"lessons_completed": 3}, 20, (2, 25)) == (2, 25)
    assert goals.needs({"lessons_completed": 3}, 20, (0, 5)) == (0, 5)
    almost = {"lessons_completed": goals.MAIN_COUNT - 1}
    assert goals.needs(almost, 20, (3, 10)) == (1, 10)               # осталось меньше уроков, чем в цели


def test_parent_sets_goal_and_student_sees_it(parent, make_student):
    c = make_student()
    sid = _sid()
    r = parent.post(f"/parent/students/{sid}/goal", data={"lessons": "2", "words": "20"}, follow_redirects=True)
    assert "Цель дня сохранена" in r.get_data(as_text=True)
    assert db_all("SELECT lessons, words FROM goal_settings WHERE student_id=?", (sid,)) == [(2, 20)]
    html = c.get("/student").get_data(as_text=True)
    assert "Пройти уроки" in html and "0/2" in html
    # вернули стандарт — отдельная настройка не хранится
    parent.post(f"/parent/students/{sid}/goal", data={"lessons": "1", "words": "10"})
    assert db_all("SELECT * FROM goal_settings") == []


def test_goal_rejects_bad_values(parent, make_student):
    make_student()
    sid = _sid()
    for data in ({"lessons": "0", "words": "0"}, {"lessons": "9", "words": "5"},
                 {"lessons": "1", "words": "-1"}, {"lessons": "x", "words": "5"}):
        r = parent.post(f"/parent/students/{sid}/goal", data=data, follow_redirects=True)
        assert "хотя бы что-то одно" in r.get_data(as_text=True)
    assert db_all("SELECT * FROM goal_settings") == []
    assert parent.post("/parent/students/999/goal", data={"lessons": "1", "words": "5"}).status_code == 404


def test_custom_goal_completes_with_coins(flask_app, make_student):
    make_student()
    db = _db()
    goals.set_target(db, _sid(), 0, 5)
    stats, today = {"lessons_completed": 3}, date(2026, 3, 3)
    _r, c, just = goals.add(db, _sid(), stats, 20, words=4, today=today)
    assert not just
    _r, c, just = goals.add(db, _sid(), stats, 20, words=1, today=today)
    assert just and c == goals.GOAL_COINS
    db.close()


def test_goal_needs_parent(anon, make_student):
    make_student()
    r = anon.post(f"/parent/students/{_sid()}/goal", data={"lessons": "2", "words": "20"})
    assert r.status_code in (302, 403)
    assert db_all("SELECT * FROM goal_settings") == []


def test_delete_student_removes_goal(parent, make_student):
    make_student()
    sid = _sid()
    parent.post(f"/parent/students/{sid}/goal", data={"lessons": "2", "words": "20"})
    parent.post(f"/parent/students/{sid}/delete")
    assert db_all("SELECT * FROM goal_settings") == []


# --- недельный отчёт ---

def test_week_report_counts(parent, make_student):
    c = make_student()
    sid = _sid()
    parent.post(f"/parent/students/{sid}/credit", data={"upto": "3", "action": "add"})  # зачёт не в отчёте
    submit_lesson(c, N(4), seconds=300)
    submit_lesson(c, N(5), wrong=True, seconds=240)
    db = _db()
    w = report.week_report(db, sid)
    db.close()
    assert len(w["days"]) == 7 and w["days"][0]["label"] == "Пн"
    assert w["active_days"] == 1 and w["minutes"] == 9
    assert len(w["lessons"]) == 2 and w["passed"] == 1
    assert w["mistakes_total"] > 0 and w["top_mistakes"]
    assert {k["label"]: k["n"] for k in w["kinds"]}["уроков сдано"] == 1


def test_week_report_previous_week_and_vacation(flask_app, make_student):
    make_student()
    sid = _sid()
    db = _db()
    today = date(2026, 10, 22)                                      # четверг
    prev_tue = date(2026, 10, 13)
    db.execute("INSERT INTO activity (student_id, day, kind) VALUES (?, ?, 'game')", (sid, prev_tue.isoformat()))
    db.execute("INSERT INTO daily_goal (student_id, day, lessons, words, done) VALUES (?, ?, 1, 10, 1)",
               (sid, prev_tue.isoformat()))
    db.execute("INSERT INTO vacations (student_id, start_day, end_day) VALUES (?, ?, ?)",
               (sid, "2026-10-14", "2026-10-15"))
    db.commit()
    now = report.week_report(db, sid, 0, today)
    assert now["monday"] == date(2026, 10, 19) and now["active_days"] == 0
    assert now["days"][4]["future"] and not now["days"][2]["future"]
    prev = report.week_report(db, sid, 1, today)
    db.close()
    assert prev["monday"] == today - timedelta(days=10)
    assert prev["active_days"] == 1 and prev["goal_days"] == 1 and prev["words"] == 10
    assert prev["days"][1]["active"] and prev["days"][2]["vacation"]
    assert {k["label"]: k["n"] for k in prev["kinds"]}["игр"] == 1


def test_dashboard_shows_week(parent, make_student):
    c = make_student()
    submit_lesson(c, N(1))
    html = parent.get("/parent/progress").get_data(as_text=True)
    assert "Дней с занятиями: 1 из 7" in html and "Тесты за неделю" in html
    sid = db_scalar("SELECT id FROM students")
    assert "Сейчас: 1 ур. + 10 слов" in parent.get(f"/parent/students/{sid}").get_data(as_text=True)
    html = parent.get("/parent/progress?week=1").get_data(as_text=True)
    assert "Дней с занятиями: 0 из 7" in html and "эта неделя" in html
    assert parent.get("/parent/progress?week=-5").status_code == 200
    assert parent.get("/parent/progress?week=abc").status_code == 200
