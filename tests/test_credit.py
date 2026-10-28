# -*- coding: utf-8 -*-
"""Зачёт пройденных уроков родителем."""
from curriculum import ALL_LESSONS, MAIN_COUNT, LESSONS_BY_ID
from tests.helpers import db_all, db_scalar, submit_lesson
from tests.helpers import N


def sid_of(username="masha"):
    return db_scalar("SELECT id FROM students WHERE username=?", (username,))


def credit(parent, sid, **data):
    return parent.post(f"/parent/students/{sid}/credit", data=data, follow_redirects=True).get_data(as_text=True)


def home(student):
    return student.get("/student").get_data(as_text=True)


def test_credit_upto_opens_next_lessons(parent, make_student):
    student = make_student()
    assert student.get(f"/lesson/{N(4)}").status_code != 200          # урок 4 закрыт
    body = credit(parent, sid_of(), upto="3", action="add")
    assert "зачтено уроков — 3" in body
    assert student.get(f"/lesson/{N(4)}").status_code == 200           # открылся следующий
    assert "Зачтено родителем" in home(student)


def test_credit_specific_lessons_by_checkbox(parent, make_student):
    make_student()
    credit(parent, sid_of(), lessons=[str(N(1)), str(N(2))], action="add")
    rows = db_all("SELECT lesson_id, passed, manual FROM attempts")
    assert sorted(rows) == sorted([(N(1), 1, 1), (N(2), 1, 1)])


def test_credit_is_idempotent_and_skips_really_passed(parent, make_student):
    student = make_student()
    submit_lesson(student, N(1))                                      # урок 1 пройден по-настоящему
    credit(parent, sid_of(), upto="2", action="add")
    assert sorted(db_all("SELECT lesson_id, manual FROM attempts")) == sorted([(N(1), 0), (N(2), 1)])
    body = credit(parent, sid_of(), upto="2", action="add")
    assert "уже пройдены" in body
    assert db_scalar("SELECT COUNT(*) FROM attempts") == 2


def test_credit_does_not_fake_stats_or_rewards(parent, make_student):
    student = make_student()
    credit(parent, sid_of(), upto="5", action="add")
    assert db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid_of(),)) in (None, 0)
    keys = {r[0] for r in db_all("SELECT key FROM achievements")}
    assert "perfect_test" not in keys and "clean_three" not in keys and "time60" not in keys
    assert {"first_lesson", "three_lessons", "five_lessons"} <= keys   # за уроки — выдаются
    html = home(student)
    assert "Лучший результат: <b>100%" not in html
    body = parent.get(f"/parent/students/{sid_of()}").get_data(as_text=True)
    assert "<span><b>0</b><small>тестов сдано</small></span>" in body


def test_real_attempt_after_credit_replaces_score(parent, make_student):
    student = make_student()
    credit(parent, sid_of(), upto="1", action="add")
    submit_lesson(student, N(1), wrong=True)                          # провал: зачёт остаётся
    assert "Зачтено родителем" in home(student)
    submit_lesson(student, N(1))                                      # успех: показывается результат
    assert "Лучший результат: <b>100%" in home(student)


def test_remove_credit_keeps_real_attempts(parent, make_student):
    student = make_student()
    submit_lesson(student, N(1))
    credit(parent, sid_of(), upto="2", action="add")
    body = credit(parent, sid_of(), lessons=[str(N(1)), str(N(2))], action="remove")
    assert "Зачёт снят с уроков: 1" in body
    assert db_all("SELECT lesson_id, manual FROM attempts") == [(N(1), 0)]
    assert student.get(f"/lesson/{N(3)}").status_code != 200


def test_credit_validation(parent, make_student):
    make_student()
    assert "Выбери уроки" in credit(parent, sid_of(), action="add")
    credit(parent, sid_of(), upto="9999", lessons=["abc", "777"], action="add")
    assert db_scalar("SELECT COUNT(*) FROM attempts") == MAIN_COUNT      # только настоящие уроки


def test_credit_extra_lesson_and_all_lessons_achievement(parent, make_student):
    make_student()
    extra = next(l["id"] for l in ALL_LESSONS if l.get("is_extra"))
    credit(parent, sid_of(), upto=str(MAIN_COUNT), lessons=[str(extra)], action="add")
    keys = {r[0] for r in db_all("SELECT key FROM achievements")}
    assert "all_lessons" in keys
    assert extra in {r[0] for r in db_all("SELECT lesson_id FROM attempts")}


def test_credit_requires_parent_and_existing_student(anon, parent, make_student):
    make_student()
    assert anon.post(f"/parent/students/{sid_of()}/credit", data={"upto": "3", "action": "add"}).status_code == 302
    assert db_scalar("SELECT COUNT(*) FROM attempts") == 0
    assert parent.post("/parent/students/999/credit", data={"upto": "3"}).status_code == 404


def test_credit_only_affects_chosen_student(parent, make_student):
    make_student("masha", "Маша", "secret1")
    make_student("petya", "Петя", "secret2")
    credit(parent, sid_of("masha"), upto="2", action="add")
    assert db_scalar("SELECT COUNT(*) FROM attempts WHERE student_id=?", (sid_of("petya"),)) == 0


def test_dashboard_shows_credit_section(parent, make_student):
    make_student()
    credit(parent, sid_of(), lessons=["1"], action="add")
    body = parent.get(f"/parent/students/{sid_of()}").get_data(as_text=True)
    assert "Зачесть пройденные уроки" in body and "зачтён родителем" in body


def test_old_database_gets_manual_column(tmp_path, monkeypatch):
    import sqlite3, database
    path = str(tmp_path / "old.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE attempts (id INTEGER PRIMARY KEY, student_id INTEGER, lesson_id INTEGER NOT NULL, "
                 "started_at TEXT NOT NULL, finished_at TEXT, seconds_spent INTEGER DEFAULT 0, "
                 "score_percent REAL DEFAULT 0, passed INTEGER DEFAULT 0, total_q INTEGER DEFAULT 0, "
                 "correct_q INTEGER DEFAULT 0, mistakes_json TEXT DEFAULT '[]', details_json TEXT DEFAULT '{}')")
    conn.execute("INSERT INTO attempts (lesson_id, started_at) VALUES (1, 'x')")
    conn.commit(); conn.close()
    monkeypatch.setattr(database, "DB_PATH", path)
    database.init_db()
    cols = {r[1] for r in sqlite3.connect(path).execute("PRAGMA table_info(attempts)")}
    assert "manual" in cols
