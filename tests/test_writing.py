# -*- coding: utf-8 -*-
"""Письмо и работа над ошибками."""
from review import hard_words, record
from tests.helpers import db_all, db_scalar, submit_lesson
from writing import MIN_SENTENCES, norm, sentences_for


def _credit(parent, n):
    sid = db_scalar("SELECT id FROM students WHERE username='masha'")
    parent.post(f"/parent/students/{sid}/credit", data={"upto": str(n), "action": "add"})


def test_norm():
    assert norm("I'm fine, thank you.") == norm("i’m FINE thank you")
    assert norm("  Hello,   world!! ") == "hello world"


def test_sentences_only_from_completed_lessons():
    assert sentences_for(set()) == []
    some = sentences_for({9})
    assert len(some) >= MIN_SENTENCES
    assert all(3 <= len(s["en"].split()) <= 9 and "..." not in s["en"] and s["ru"] and s["pic"] for s in some)
    assert len({norm(s["en"]) for s in some}) == len(some)            # без повторов


def test_hub_needs_progress_and_play(parent, make_student):
    c = make_student()
    assert "Пока мало фраз" in c.get("/student/writing").get_data(as_text=True)
    assert c.get("/student/writing/build").status_code == 302
    _credit(parent, 3)
    html = c.get("/student/writing").get_data(as_text=True)
    assert "Собери предложение" in html and "Мини-диктант" in html and "Работа над ошибками" in html
    for mode in ("build", "dictation"):
        h = c.get(f"/student/writing/{mode}").get_data(as_text=True)
        assert 'id="write"' in h and "writing.js" in h and "data-items" in h
    assert c.get("/student/writing/nope").status_code == 404


def test_api_saves_stars_and_feeds_review(parent, make_student, anon):
    c = make_student()
    _credit(parent, 3)
    r = c.post("/api/writing", json={"mode": "dictation", "stars": 2, "wrong": ["hello", "zzzz"]}).get_json()
    assert r["ok"] and any(a["key"] == "write_1" for a in r["newAchievements"])
    assert db_scalar("SELECT best FROM game_scores WHERE game='dictation'") == 2
    rows = {k: bad for k, bad in db_all("SELECT key, n_bad FROM word_review")}
    assert rows.get("hello") == 1 and "zzzz" not in rows                # только изученные слова
    assert c.post("/api/writing", json={"mode": "x", "stars": 1}).status_code == 400
    assert c.post("/api/writing", json={"mode": "build", "stars": 9}).status_code == 400
    assert anon.post("/api/writing", json={"mode": "build", "stars": 1}).status_code == 403


def test_hard_words_and_review_mode(parent, make_student):
    c = make_student()
    _credit(parent, 3)
    page = c.get("/student/review?mode=hard").get_data(as_text=True)
    assert "Сложных слов нет" in page
    c.post("/api/writing", json={"mode": "build", "stars": 1, "wrong": ["hello", "goodbye"]})
    page = c.get("/student/review?mode=hard").get_data(as_text=True)
    assert "Работа над ошибками" in page and 'id="rv-stage"' in page
    c.post("/api/review", json={"key": "hello", "ok": True})
    c.post("/api/review", json={"key": "hello", "ok": True})
    # слово выучено надолго → исчезнет из сложных
    for _ in range(5):
        c.post("/api/review", json={"key": "hello", "ok": True})


def test_writing_does_not_break_games_perfect_count(parent, make_student):
    c = make_student()
    _credit(parent, 3)
    c.post("/api/writing", json={"mode": "build", "stars": 3, "wrong": []})
    from stats import compute_stats
    import database
    import sqlite3
    con = sqlite3.connect(database.DB_PATH); con.row_factory = sqlite3.Row
    sid = con.execute("SELECT id FROM students").fetchone()[0]
    st = compute_stats(con, sid)
    assert st["games_perfect"] == 0 and st["writing_perfect"] == 1 and st["writing_played"] == 1
