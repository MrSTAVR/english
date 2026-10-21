# -*- coding: utf-8 -*-
"""Домик Чик-чика и наклейки."""
import house
from curriculum import LESSONS
from tests.helpers import db_scalar, submit_lesson
from tests.test_vacation import conn, sid_of


def give(sid, coins):
    c = conn()
    c.execute("UPDATE garden SET coins=? WHERE student_id=?", (coins, sid)); c.commit()
    return c


def test_house_page_and_defaults(make_student):
    c = make_student(); sid = sid_of()
    r = c.get("/student/house")
    assert r.status_code == 200 and "Домик Чик-чика" in r.get_data(as_text=True)
    assert house.placed(conn(), sid) == {"wall": "wall-cream", "floor": "floor-wood"}


def test_buy_place_remove(make_student):
    c = make_student(); sid = sid_of()
    cn = give(sid, 30)
    c.post("/student/house/buy", data={"key": "bed-small"})
    assert db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) == 10
    assert house.placed(cn, sid)["bed"] == "bed-small"
    c.post("/student/house/place", data={"key": "bed-small"})          # повторно — убрать
    assert "bed" not in house.placed(cn, sid)
    c.post("/student/house/place", data={"key": "bed-small"})
    assert house.placed(cn, sid)["bed"] == "bed-small"


def test_not_enough_coins_and_unknown(make_student):
    c = make_student(); sid = sid_of(); cn = give(sid, 5)
    assert not house.buy(cn, sid, "bed-royal")[0]
    assert not house.buy(cn, sid, "nope")[0]
    assert not house.place(cn, sid, "lamp-floor")[0]        # не куплено
    assert db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) == 5


def test_default_wall_cannot_be_removed(make_student):
    make_student(); sid = sid_of(); cn = conn()
    assert not house.place(cn, sid, "wall-cream")[0]


def test_same_slot_replaces(make_student):
    make_student(); sid = sid_of(); cn = give(sid, 100)
    house.buy(cn, sid, "wall-blue"); house.buy(cn, sid, "wall-pink")
    assert house.placed(cn, sid)["wall"] == "wall-pink"
    assert house.place(cn, sid, "wall-blue")[0] and house.placed(cn, sid)["wall"] == "wall-blue"


def test_house_achievement(make_student):
    c = make_student(); sid = sid_of(); give(sid, 50)
    c.post("/student/house/buy", data={"key": "plant-pot"})
    assert db_scalar("SELECT COUNT(*) FROM achievements WHERE key='house_1'") == 1


def test_all_items_have_art():
    import re
    from pathlib import Path
    js = (Path(__file__).resolve().parent.parent / "static" / "house.js").read_text(encoding="utf-8")
    for it in house.ITEMS:
        assert f"'{it['key']}'" in js, it["key"]


def test_stickers_page(make_student):
    c = make_student()
    body = c.get("/student/stickers").get_data(as_text=True)
    assert "Мои наклейки" in body and "Собрано: 0 из" in body
    submit_lesson(c, LESSONS[0]["id"])
    body = c.get("/student/stickers").get_data(as_text=True)
    assert "Собрано: 1 из" in body and "sk-gold" in body


def test_delete_student_clears_house(parent, make_student):
    make_student(); sid = sid_of(); cn = give(sid, 50)
    house.buy(cn, sid, "plant-pot")
    parent.post(f"/parent/students/{sid}/delete")
    assert db_scalar("SELECT COUNT(*) FROM house_items") == 0 and db_scalar("SELECT COUNT(*) FROM house_place") == 0
