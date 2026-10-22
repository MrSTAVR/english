# -*- coding: utf-8 -*-
"""Новый год: даты через границу года, викторина, наряды, адвент-календарь, снег."""
from datetime import date

import seasons
import wardrobe
from data import newyear
from tests.helpers import db_scalar
from tests.test_vacation import conn, sid_of


def _day(monkeypatch, d):
    monkeypatch.setattr(seasons, "today", lambda: d)


def test_newyear_dates_cross_year():
    assert seasons.active_season(date(2026, 12, 14)) is None
    assert seasons.active_season(date(2026, 12, 15)) == "newyear"
    assert seasons.active_season(date(2026, 12, 31)) == "newyear"
    assert seasons.active_season(date(2027, 1, 1)) == "newyear"
    assert seasons.active_season(date(2027, 1, 14)) == "newyear"
    assert seasons.active_season(date(2027, 1, 15)) is None
    assert seasons.active_season(date(2026, 10, 20)) == "halloween"     # Хэллоуин не сломан


def test_advent_window(flask_app):
    assert seasons.advent_open(date(2026, 12, 1)) and seasons.advent_open(date(2026, 12, 31))
    assert not seasons.advent_open(date(2026, 11, 30)) and not seasons.advent_open(date(2027, 1, 2))
    assert len(newyear.ADVENT) == 31


def test_newyear_page_quiz_and_achievement(make_student, monkeypatch):
    c = make_student(); sid = sid_of()
    _day(monkeypatch, date(2026, 6, 1))
    assert c.get("/student/newyear").status_code == 302
    _day(monkeypatch, date(2026, 12, 20))
    html = c.get("/student/newyear").get_data(as_text=True)
    assert "Happy New Year!" in html and "snowman" in html and "/api/newyear" in html
    assert c.get("/student/halloween").status_code == 302             # чужой сезон закрыт
    assert c.post("/api/halloween", json={"correct": 8}).status_code == 403
    r = c.post("/api/newyear", json={"correct": 7}).get_json()
    assert r["coins"] == newyear.DAILY_COINS and any(a["key"] == "newyear_1" for a in r["newAchievements"])
    assert c.post("/api/newyear", json={"correct": 8}).get_json()["coins"] == 0
    assert c.post("/api/newyear", json={"correct": 99}).status_code == 400
    assert db_scalar("SELECT season FROM season_log WHERE student_id=?", (sid,)) == "newyear"


def test_home_banners_and_snow(make_student, monkeypatch):
    c = make_student()
    _day(monkeypatch, date(2026, 12, 3))                               # адвент уже идёт, сезон ещё нет
    body = c.get("/student").get_data(as_text=True)
    assert "Адвент-календарь" in body and "Новый год!" not in body and 'class="snow"' not in body
    _day(monkeypatch, date(2026, 12, 20))
    body = c.get("/student").get_data(as_text=True)
    assert "Новый год!" in body and 'class="snow"' in body
    _day(monkeypatch, date(2027, 1, 5))
    body = c.get("/student").get_data(as_text=True)
    assert "Новый год!" in body and "Адвент-календарь" not in body


def test_newyear_items_only_in_season(make_student, monkeypatch):
    c = make_student(); sid = sid_of()
    cn = conn()
    cn.execute("UPDATE garden SET coins=500 WHERE student_id=?", (sid,)); cn.commit()
    _day(monkeypatch, date(2026, 10, 25))
    assert not wardrobe.buy(cn, sid, "hat-antlers")[0]
    assert "Оленьи рожки" not in c.get("/student/wardrobe").get_data(as_text=True)
    _day(monkeypatch, date(2026, 12, 25))
    assert "Оленьи рожки" in c.get("/student/wardrobe").get_data(as_text=True)
    assert wardrobe.buy(cn, sid, "hat-antlers")[0]


def test_newyear_items_have_art():
    js = open("static/chick.js", encoding="utf-8").read()
    for it in wardrobe.ITEMS:
        if it["source"] == "newyear":
            assert f"'{it['key']}'" in js, it["key"]


def test_advent_open_coins_and_rules(make_student, monkeypatch):
    c = make_student(); sid = sid_of()
    _day(monkeypatch, date(2026, 11, 30))
    assert c.get("/student/advent").status_code == 302
    assert c.post("/api/advent", json={"day": 1}).status_code == 403
    _day(monkeypatch, date(2026, 12, 5))
    html = c.get("/student/advent").get_data(as_text=True)
    assert html.count('data-day="') == 5 and "Откроется 6 декабря" in html
    assert c.post("/api/advent", json={"day": 6}).status_code == 400   # будущее окошко
    assert c.post("/api/advent", json={"day": "x"}).status_code == 400
    r = c.post("/api/advent", json={"day": 5}).get_json()
    assert r["coins"] == newyear.ADVENT_COINS and r["word"] == newyear.ADVENT[4]
    assert c.post("/api/advent", json={"day": 5}).get_json()["coins"] == 0        # второй раз — без монетки
    assert c.post("/api/advent", json={"day": 2}).get_json()["coins"] == 0        # пропущенное — без монетки
    assert db_scalar("SELECT COUNT(*) FROM advent WHERE student_id=?", (sid,)) == 2
    assert db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) == newyear.ADVENT_COINS
    assert "сегодняшнее окошко открыто" in c.get("/student").get_data(as_text=True)


def test_advent_achievement(make_student, monkeypatch):
    c = make_student()
    _day(monkeypatch, date(2026, 12, 12))
    got = []
    for d in range(1, 11):
        got += c.post("/api/advent", json={"day": d}).get_json()["newAchievements"]
    assert any(a["key"] == "advent_10" for a in got)


def test_parent_turns_newyear_off_hides_advent(parent, make_student, monkeypatch):
    c = make_student()
    _day(monkeypatch, date(2026, 12, 20))
    assert "Новый год" in parent.get("/parent/holidays").get_data(as_text=True)
    parent.post("/parent/season", data={"season": "newyear", "mode": "off"})
    assert c.get("/student/newyear").status_code == 302 and c.get("/student/advent").status_code == 302
    body = c.get("/student").get_data(as_text=True)
    assert "Новый год!" not in body and 'class="snow"' not in body
    parent.post("/parent/season", data={"season": "halloween", "mode": "on"})   # Хэллоуин вручную
    assert c.get("/student/halloween").status_code == 200


def test_delete_student_cleans_advent(parent, make_student, monkeypatch):
    c = make_student(); sid = sid_of()
    _day(monkeypatch, date(2026, 12, 3))
    c.post("/api/advent", json={"day": 3})
    parent.post(f"/parent/students/{sid}/delete")
    assert db_scalar("SELECT COUNT(*) FROM advent") == 0


def test_sw_knows_newyear_pages(anon):
    body = anon.get("/sw.js").get_data(as_text=True)
    import re
    pages = re.search(r"student\\/\((.*?)\)", body).group(1).split("|")
    assert {"newyear", "advent", "march8", "easter", "birthday"} <= set(pages)
