# -*- coding: utf-8 -*-
"""Кабинет администратора: календарь занятий, средний балл по неделям, трудные слова."""
import sqlite3
from datetime import date, timedelta

import database
import report
from tests.helpers import N, db_all, db_scalar, submit_lesson


def _db():
    c = sqlite3.connect(database.DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def test_heatmap_and_trend(make_student):
    c = make_student()
    submit_lesson(c, N(1))
    submit_lesson(c, N(2), wrong=True)
    sid = db_scalar("SELECT id FROM students")
    db = _db()
    hm = report.activity_heatmap(db, sid)
    assert len(hm["weeks"]) == 12 and all(len(col) == 7 for col in hm["weeks"])
    today = [d for col in hm["weeks"] for d in col if d["date"] == date.today()][0]
    assert today["n"] >= 2 and today["level"] >= 2 and hm["active_days"] == 1
    tr = report.score_trend(db, sid)
    assert len(tr) == 12 and tr[-1]["n"] == 2 and tr[-1]["avg"] is not None and tr[0]["avg"] is None
    db.close()


def test_hard_words_and_send_to_review(make_student, parent):
    make_student()
    sid = db_scalar("SELECT id FROM students")
    db = _db()
    far = (date.today() + timedelta(days=8)).isoformat()
    db.executemany("INSERT INTO word_review (student_id, key, box, due, n_ok, n_bad) VALUES (?, ?, ?, ?, ?, ?)",
                   [(sid, "cat", 2, far, 3, 4), (sid, "dog", 1, far, 1, 1), (sid, "pen", 5, far, 9, 7)])
    db.commit()
    hard = report.hard_words(db, sid)
    assert [h["key"] for h in hard] == ["cat", "dog"] and hard[0]["ru"] == "кот"      # выученное (pen) не трудное
    html = parent.get("/parent/progress").get_data(as_text=True)
    assert f'id="s{sid}"' in html and "cat — кот · ✗4" in html and "Календарь за 12 недель" in html
    r = parent.post(f"/parent/students/{sid}/review_hard", follow_redirects=True).get_data(as_text=True)
    assert "Слов отправлено в повторение на сегодня: 2" in r
    assert db_all("SELECT key, box, due FROM word_review WHERE key IN ('cat','dog') ORDER BY key") == \
        [("cat", 0, date.today().isoformat()), ("dog", 0, date.today().isoformat())]
    assert parent.post("/parent/students/999/review_hard").status_code == 404
    db.close()


def test_review_hard_needs_admin(make_student):
    c = make_student()
    sid = db_scalar("SELECT id FROM students")
    assert c.post(f"/parent/students/{sid}/review_hard").status_code == 302
