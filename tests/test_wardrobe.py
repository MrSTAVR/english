# -*- coding: utf-8 -*-
"""Гардероб Чик-чика: покупка за монетки, ношение, наряд в настройках помощника."""
import sqlite3

import database
from tests.helpers import db_all, db_scalar
from wardrobe import ITEMS, ITEMS_BY_KEY, SLOTS


def _give_coins(n):
    con = sqlite3.connect(database.DB_PATH)
    sid = con.execute("SELECT id FROM students WHERE username='masha'").fetchone()[0]
    con.execute("INSERT OR IGNORE INTO garden (student_id) VALUES (?)", (sid,))
    con.execute("UPDATE garden SET coins=? WHERE student_id=?", (n, sid))
    con.commit()
    con.close()


def test_catalog_is_consistent():
    assert len(ITEMS_BY_KEY) == len(ITEMS)
    assert {i["slot"] for i in ITEMS} == {s["key"] for s in SLOTS}
    assert all(i["cost"] >= 0 for i in ITEMS)


def test_every_item_has_art():
    import re
    from pathlib import Path
    js = (Path(__file__).resolve().parent.parent / "static" / "chick.js").read_text(encoding="utf-8")
    for i in ITEMS:
        if i["slot"] != "color":
            assert f"'{i['key']}'" in js, i["key"]
        else:
            assert re.search(rf"'{i['key']}'\s*:", js), i["key"]


def test_wardrobe_page_opens(make_student):
    c = make_student()
    html = c.get("/student/wardrobe").get_data(as_text=True)
    assert "Гардероб Чик-чика" in html and "hat-crown" in html and "chick.js" in html


def test_cannot_buy_without_coins(make_student):
    c = make_student()
    c.post("/student/wardrobe/buy", data={"key": "hat-crown"})
    assert db_scalar("SELECT COUNT(*) FROM wardrobe_items") == 0


def test_buy_wear_and_take_off(make_student):
    c = make_student()
    c.get("/student/garden")
    _give_coins(30)
    c.post("/student/wardrobe/buy", data={"key": "hat-cap"})
    assert db_scalar("SELECT coins FROM garden") == 30 - ITEMS_BY_KEY["hat-cap"]["cost"]
    assert db_all("SELECT slot, item_key FROM wardrobe_wear")[0][1] == "hat-cap"
    assert '"hat-cap"' in c.get("/student/garden").get_data(as_text=True)        # наряд попал в настройки помощника
    c.post("/student/wardrobe/wear", data={"key": "hat-cap"})                      # повторное нажатие — снять
    assert db_scalar("SELECT COUNT(*) FROM wardrobe_wear") == 0
    c.post("/student/wardrobe/wear", data={"key": "hat-cap"})
    assert db_scalar("SELECT COUNT(*) FROM wardrobe_wear") == 1
    c.post("/student/wardrobe/buy", data={"key": "hat-cap"})                       # повторно не списывает
    assert db_scalar("SELECT coins FROM garden") == 30 - ITEMS_BY_KEY["hat-cap"]["cost"]


def test_wear_unowned_and_unknown(make_student):
    c = make_student()
    c.post("/student/wardrobe/wear", data={"key": "hat-crown"})
    c.post("/student/wardrobe/buy", data={"key": "nope"})
    assert db_scalar("SELECT COUNT(*) FROM wardrobe_wear") == 0


def test_one_item_per_slot_and_achievement(make_student):
    c = make_student()
    c.get("/student/garden")
    _give_coins(100)
    c.post("/student/wardrobe/buy", data={"key": "hat-cap"})
    c.post("/student/wardrobe/buy", data={"key": "hat-party"})
    worn = db_all("SELECT item_key FROM wardrobe_wear WHERE slot='hat'")
    assert [w[0] for w in worn] == ["hat-party"]
    assert db_scalar("SELECT COUNT(*) FROM achievements WHERE key='wardrobe_1'") == 1


def test_wardrobe_needs_student(anon):
    assert anon.get("/student/wardrobe").status_code in (302, 303)
    assert anon.post("/student/wardrobe/buy", data={"key": "hat-cap"}).status_code in (302, 303, 400, 403)
