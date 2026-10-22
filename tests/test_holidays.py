# -*- coding: utf-8 -*-
"""8 Марта, Пасха (православная), «каждый год» у своих дат и день рождения ученика."""
from datetime import date

import seasons
import wardrobe
from tests.helpers import db_all, db_scalar
from tests.test_vacation import conn, sid_of


def _day(monkeypatch, d):
    monkeypatch.setattr(seasons, "today", lambda: d)


def test_orthodox_easter_dates():
    assert [seasons.orthodox_easter(y) for y in (2024, 2025, 2026, 2027)] == \
        [date(2024, 5, 5), date(2025, 4, 20), date(2026, 4, 12), date(2027, 5, 2)]


def test_march8_and_easter_windows():
    assert seasons.active_season(date(2027, 3, 1)) == "march8" and seasons.active_season(date(2027, 3, 11)) is None
    assert seasons.active_season(date(2026, 4, 12)) == "easter" and seasons.active_season(date(2026, 4, 6)) == "easter"
    assert seasons.active_season(date(2026, 4, 19)) == "easter" and seasons.active_season(date(2026, 4, 20)) is None
    assert seasons.active_season(date(2026, 4, 5)) is None


def test_march8_page_quiz_and_outfit(make_student, monkeypatch):
    c = make_student(); sid = sid_of()
    _day(monkeypatch, date(2027, 3, 5))
    assert "8 Марта!" in c.get("/student").get_data(as_text=True)
    html = c.get("/student/march8").get_data(as_text=True)
    assert "Happy Women" in html and "tulip" in html
    r = c.post("/api/march8", json={"correct": 7}).get_json()
    assert r["coins"] == 3 and any(a["key"] == "march8_1" for a in r["newAchievements"])
    cn = conn(); cn.execute("UPDATE garden SET coins=100 WHERE student_id=?", (sid,)); cn.commit()
    assert wardrobe.buy(cn, sid, "hat-tulip")[0] and not wardrobe.buy(cn, sid, "hat-eggshell")[0]
    assert c.get("/student/easter").status_code == 302


def test_seasonal_items_have_art():
    js = open("static/chick.js", encoding="utf-8").read()
    for it in wardrobe.ITEMS:
        if it["source"] in ("march8", "easter"):
            assert f"'{it['key']}'" in js, it["key"]


def test_yearly_custom_dates(parent, make_student, monkeypatch):
    c = make_student()
    parent.post("/parent/season", data={"season": "march8", "mode": "auto", "date_from": "2026-03-05",
                                        "date_to": "2026-03-09", "yearly": "1"})
    _day(monkeypatch, date(2029, 3, 7))
    assert c.get("/student/march8").status_code == 200                 # через три года — снова праздник
    _day(monkeypatch, date(2029, 3, 2))
    assert c.get("/student/march8").status_code == 302
    assert "каждый год" in parent.get("/parent/holidays").get_data(as_text=True)
    parent.post("/parent/season", data={"season": "march8", "mode": "auto", "date_from": "2026-03-05", "date_to": "2026-03-09"})
    _day(monkeypatch, date(2029, 3, 7))
    assert c.get("/student/march8").status_code == 302                 # без галочки — только 2026 год


def test_birthday_gift_page_and_privacy(parent, make_student, flask_app, monkeypatch):
    c = make_student(); sid = sid_of()
    make_student("petya", "Петя", "secret2")
    _day(monkeypatch, date(2026, 5, 12))
    assert c.get("/student/birthday").status_code == 302                # дня рождения нет
    r = parent.post(f"/parent/students/{sid}/birthday", data={"birthday": "2016-05-10"}, follow_redirects=True)
    assert "День рождения сохранён" in r.get_data(as_text=True)
    assert "С днём рождения, Маша!" in c.get("/student").get_data(as_text=True)
    html = c.get("/student/birthday").get_data(as_text=True)
    assert "Подарок от Чик-чика: <b>+25 монеток" in html and "Happy birthday to you" in html
    assert "Подарок от Чик-чика" not in c.get("/student/birthday").get_data(as_text=True)   # раз в год
    assert db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) == seasons.BIRTHDAY_GIFT
    r = c.post("/api/birthday", json={"correct": 8}).get_json()
    assert r["coins"] == 3 and any(a["key"] == "birthday_1" for a in r["newAchievements"])
    petya = flask_app.test_client()
    petya.post("/login/student", data={"username": "petya", "password": "secret2"})
    assert petya.get("/student/birthday").status_code == 302           # праздник только у Маши
    assert petya.post("/api/birthday", json={"correct": 8}).status_code == 403
    _day(monkeypatch, date(2026, 5, 20))
    assert c.get("/student/birthday").status_code == 302                # неделя прошла
    parent.post(f"/parent/students/{sid}/birthday", data={"birthday": "bad"})
    assert db_all("SELECT birthday FROM students WHERE id=?", (sid,)) == [("2016-05-10",)]
    parent.post(f"/parent/students/{sid}/delete")
    assert db_scalar("SELECT COUNT(*) FROM birthday_gifts") == 0


def test_birthday_column_migration(tmp_path, monkeypatch):
    import sqlite3
    import database
    path = tmp_path / "old.db"
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE students (id INTEGER PRIMARY KEY, username TEXT, display_name TEXT, password_hash TEXT, "
              "emoji TEXT, created_at TEXT)")
    c.commit(); c.close()
    monkeypatch.setattr(database, "DB_PATH", str(path))
    database.init_db()
    assert "birthday" in {r[1] for r in sqlite3.connect(path).execute("PRAGMA table_info(students)")}
