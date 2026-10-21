# -*- coding: utf-8 -*-
"""Повторение слов (система Лейтнера), слово дня и повторные вопросы в тестах."""
import random
import sqlite3
from datetime import date, timedelta

import database
import review
from curriculum import LESSONS
from tests.helpers import db_all, db_scalar


def _db(flask_app):
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _credit(parent, n=10):
    sid = db_scalar("SELECT id FROM students WHERE username='masha'")
    parent.post(f"/parent/students/{sid}/credit", data={"upto": str(n), "action": "add"})
    return sid


def test_leitner_boxes_and_intervals(flask_app, make_student):
    make_student()
    sid = db_scalar("SELECT id FROM students WHERE username='masha'")
    db = _db(flask_app)
    today = date(2026, 1, 1)
    assert review.record(db, sid, "cat", True, today) == 1
    assert db.execute("SELECT due FROM word_review WHERE key='cat'").fetchone()["due"] == "2026-01-02"      # коробка 1 → через 1 день
    assert review.record(db, sid, "cat", True, today) == 2
    assert db.execute("SELECT due FROM word_review WHERE key='cat'").fetchone()["due"] == (today + timedelta(days=2)).isoformat()
    for _ in range(10):
        review.record(db, sid, "cat", True, today)
    assert db.execute("SELECT box FROM word_review WHERE key='cat'").fetchone()["box"] == review.MAX_BOX
    assert review.record(db, sid, "cat", False, today) == 0      # ошибка — снова в начало
    assert db.execute("SELECT due FROM word_review WHERE key='cat'").fetchone()["due"] == today.isoformat()
    row = db.execute("SELECT n_ok, n_bad FROM word_review WHERE key='cat'").fetchone()
    assert row["n_bad"] == 1 and row["n_ok"] >= 12
    db.close()


def test_pick_due_prefers_overdue_then_new():
    pool = [{"key": k, "en": k, "accept": [k], "ru": k + "ru", "hint": "", "lesson": 1} for k in "abcdefgh"]
    st = {"a": {"due": "2026-01-01", "box": 3}, "b": {"due": "2025-12-01", "box": 1},
          "c": {"due": "2099-01-01", "box": 2}}
    picked = review.pick_due(pool, st, today=date(2026, 1, 2), n=4)
    assert [w["key"] for w in picked][:2] == ["b", "a"]            # сначала самые просроченные
    assert "c" not in [w["key"] for w in picked]                    # «ещё не пора»
    extra = review.pick_due(pool, st, today=date(2026, 1, 2), n=8, extra=True)
    assert len(extra) == 8


def test_questions_are_valid_for_every_box():
    pool = review.pool_from(LESSONS) if hasattr(review, "pool_from") else review._pool_from(LESSONS)
    rng = random.Random(5)
    for w in pool:
        for box in (0, 2, 5):
            q = review.make_question(w, pool, box, rng)
            assert q["key"] == w["key"]
            if q["type"] == "choice":
                assert len(set(q["options"])) == len(q["options"]) >= 4
                assert 0 <= q["answer"] < len(q["options"])
            elif q["type"] == "scramble":
                assert sorted(q["letters"]) == sorted(q["answer"])


def test_word_of_day_is_stable_per_day():
    pool = review._pool_from(LESSONS[:8])
    a = review.word_of_day(pool, {}, 1, date(2026, 5, 5))
    assert a == review.word_of_day(pool, {}, 1, date(2026, 5, 5))
    assert {review.word_of_day(pool, {}, 1, date(2026, 5, d))["key"] for d in range(1, 20)} != {a["key"]}
    assert review.word_of_day([], {}, 1) is None


def test_review_page_empty_then_filled(parent, make_student):
    student = make_student()
    html = student.get("/student/review").get_data(as_text=True)
    assert "Пока нечего повторять" in html
    assert 'class="rv-card' not in student.get("/student").get_data(as_text=True)    # на главной пока нет
    _credit(parent)
    html = student.get("/student/review").get_data(as_text=True)
    assert 'id="rv-stage"' in html and "review.js" in html
    home = student.get("/student").get_data(as_text=True)
    assert "review" in home and "Повторение" in home and "Слово дня" in home


def test_review_api_validates_and_records(parent, make_student):
    student = make_student()
    assert student.post("/api/review", json={"key": "cat", "ok": True}).status_code == 400   # ещё не изучено
    _credit(parent)
    r = student.post("/api/review", json={"key": "cat", "ok": True})
    assert r.status_code == 200 and r.get_json()["box"] == 1
    assert student.post("/api/review", json={"key": "zzz", "ok": True}).status_code == 400
    assert db_all("SELECT key, box FROM word_review") == [("cat", 1)]


def test_review_api_needs_student(anon):
    assert anon.post("/api/review", json={"key": "cat", "ok": True}).status_code == 403


def test_review_achievements(parent, make_student):
    student = make_student()
    _credit(parent)
    new = []
    for _ in range(20):
        new += student.post("/api/review", json={"key": "cat", "ok": True}).get_json()["newAchievements"]
    assert any(a["key"] == "rev_20" for a in new)


def test_old_words_come_back_in_test():
    qs = [q for l in LESSONS for q in l["test"] if q["q"].startswith("🔁")]
    assert len(qs) > 20
    first = LESSONS[0]
    assert not any(q["q"].startswith("🔁") for q in first["test"])
    for q in qs:
        assert q["options"][q["answer"]] and len(set(q["options"])) == len(q["options"])
