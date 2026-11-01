# -*- coding: utf-8 -*-
"""Фермерская переработка ингредиентов для пиццы (pizza_farm.py)."""
import sqlite3

import database
import pizza_farm
from tests.helpers import db_scalar


def sid_of():
    return db_scalar("SELECT id FROM students ORDER BY id DESC LIMIT 1")


def give(sid, **items):
    conn = sqlite3.connect(database.DB_PATH)
    try:
        for item, qty in items.items():
            conn.execute("INSERT INTO farm_barn (student_id, item, qty) VALUES (?, ?, ?) "
                         "ON CONFLICT(student_id, item) DO UPDATE SET qty=qty+excluded.qty",
                         (sid, item, qty))
        conn.commit()
    finally:
        conn.close()


def have(sid, item):
    return db_scalar("SELECT qty FROM farm_barn WHERE student_id=? AND item=?", (sid, item)) or 0


def test_mill_wheat_to_flour(make_student):
    c = make_student()
    sid = sid_of()
    give(sid, wheat=2)
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        ok, msg = pizza_farm.process(conn, sid, "flour")
        assert ok, msg
    finally:
        conn.close()
    assert have(sid, "wheat") == 0
    assert have(sid, "flour") == 1


def test_process_quantity(make_student):
    make_student()
    sid = sid_of()
    give(sid, wheat=6)
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        ok, _ = pizza_farm.process(conn, sid, "flour", qty=2)
        assert ok
    finally:
        conn.close()
    assert have(sid, "flour") == 2
    assert have(sid, "wheat") == 2


def test_missing_products_do_not_spend(make_student):
    make_student()
    sid = sid_of()
    give(sid, flour=1, egg=1)
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        ok, _ = pizza_farm.process(conn, sid, "dough")
        assert not ok
    finally:
        conn.close()
    assert have(sid, "flour") == 1
    assert have(sid, "egg") == 1
    assert have(sid, "dough") == 0


def test_caesar_sauce_needs_parmesan(make_student):
    make_student()
    sid = sid_of()
    give(sid, egg=1, parmesan=1)
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        assert pizza_farm.can_process(conn, sid, "caesar_sauce")
        ok, _ = pizza_farm.process(conn, sid, "caesar_sauce")
        assert ok
    finally:
        conn.close()
    assert have(sid, "caesar_sauce") == 1
    assert have(sid, "egg") == 0
    assert have(sid, "parmesan") == 0


def test_unknown_recipe_and_bad_quantity(make_student):
    make_student()
    sid = sid_of()
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        assert pizza_farm.process(conn, sid, "pizza")[0] is False
        assert pizza_farm.process(conn, sid, "flour", qty=0)[0] is False
    finally:
        conn.close()


def test_known_items_include_pantry_and_early_crops():
    known = pizza_farm.known_items(set())
    for item in ("salt", "yeast", "oil", "pepperoni", "chicken", "wheat", "mushroom", "basil"):
        assert item in known


def test_process_api_route(make_student):
    c = make_student()
    sid = sid_of()
    give(sid, wheat=2)
    r = c.post("/api/farm/process", json={"key": "flour"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert have(sid, "flour") == 1


def test_well_gives_water_once_per_day(make_student):
    c = make_student()
    sid = sid_of()
    r = c.post("/api/farm/well")
    assert r.get_json()["ok"] is True
    assert r.get_json()["got"] == 5
    assert have(sid, "water") == 5
    assert c.post("/api/farm/well").get_json()["ok"] is False
    assert have(sid, "water") == 5


def test_dough_needs_water(make_student):
    make_student()
    sid = sid_of()
    give(sid, flour=2, egg=1)
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        assert not pizza_farm.process(conn, sid, "dough")[0]
    finally:
        conn.close()
    give(sid, water=1)
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        assert pizza_farm.process(conn, sid, "dough")[0]
    finally:
        conn.close()
