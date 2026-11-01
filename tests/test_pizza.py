# -*- coding: utf-8 -*-
"""Пиццерия: страница, расход продуктов, награда и блокировка (pizza.py)."""
import json
import sqlite3

import database
from tests.helpers import db_scalar


def coins_of(sid):
    return db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) or 0


def history_of(sid):
    return db_scalar("SELECT COUNT(*) FROM pizza_history WHERE student_id=?", (sid,)) or 0


def barn_of(sid, item):
    return db_scalar("SELECT qty FROM farm_barn WHERE student_id=? AND item=?", (sid, item)) or 0


def last_sid():
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


def page_data(client):
    html = client.get("/student/pizza").get_data(as_text=True)
    return json.loads(html.split('id="pz-data">', 1)[1].split("</script>", 1)[0])


def test_page_available_and_has_four_recipes(make_student):
    c = make_student()
    data = page_data(c)
    assert [x["key"] for x in data["recipes"]] == ["margherita", "pepperoni", "mushroom", "caesar"]
    assert [len(x["toppings"]) for x in data["recipes"]] == [2, 1, 2, 4]
    assert all(x["can"] for x in data["recipes"])          # стартового набора хватает на все 4
    assert data["reward"] == 3


def test_starter_given_once(make_student):
    c = make_student()
    sid = last_sid()
    page_data(c)
    assert barn_of(sid, "dough") == 4
    page_data(c)
    assert barn_of(sid, "dough") == 4


def test_grandma_daily_stock_once_per_day(make_student):
    c = make_student()
    sid = last_sid()
    page_data(c)
    assert barn_of(sid, "milk") == 16          # 12 стартовых + 4 бабушкиных
    page_data(c)
    assert barn_of(sid, "milk") == 16


def test_first_recipe_spends_stock_and_gives_coins_once(make_student):
    c = make_student()
    sid = last_sid()
    page_data(c)
    r = c.post("/api/pizza/finish", json={"recipe": "margherita"})
    assert r.status_code == 200
    got = r.get_json()
    assert got["gained"] == 3 and got["already"] is False
    assert coins_of(sid) == 3 and history_of(sid) == 1
    assert barn_of(sid, "dough") == 3 and barn_of(sid, "mozzarella") == 6
    # повторное приготовление тратит продукты, но монет не даёт
    give(sid, dough=1, tomato_sauce=1, mozzarella=2, basil=1, cherry_tomato=2)
    got = c.post("/api/pizza/finish", json={"recipe": "margherita"}).get_json()
    assert got["gained"] == 0 and got["already"] is True
    assert coins_of(sid) == 3 and history_of(sid) == 1


def test_each_recipe_gives_once(make_student):
    c = make_student()
    sid = last_sid()
    page_data(c)
    for key in ("margherita", "pepperoni", "mushroom", "caesar"):
        assert c.post("/api/pizza/finish", json={"recipe": key}).get_json()["gained"] == 3
    assert coins_of(sid) == 12 and history_of(sid) == 4
    assert c.post("/api/pizza/finish", json={"recipe": "caesar"}).status_code == 400


def test_missing_products_block_without_spending(make_student):
    c = make_student()
    sid = last_sid()
    page_data(c)
    conn = sqlite3.connect(database.DB_PATH)
    conn.execute("DELETE FROM farm_barn WHERE student_id=? AND item='dough'", (sid,))
    conn.commit()
    conn.close()
    before = coins_of(sid)
    r = c.post("/api/pizza/finish", json={"recipe": "margherita"})
    assert r.status_code == 400
    assert "dough" in r.get_json()["missing"]
    assert coins_of(sid) == before and history_of(sid) == 0


def test_second_student_has_own_history(make_student):
    a = make_student("masha", "Маша")
    sid_a = last_sid()
    assert a.post("/api/pizza/finish", json={"recipe": "pepperoni"}).get_json()["gained"] == 3
    b = make_student("masha2", "Маша 2")
    sid_b = last_sid()
    data = page_data(b)
    assert data["completed"] == [] and data["coins"] == 0
    assert b.post("/api/pizza/finish", json={"recipe": "pepperoni"}).get_json()["gained"] == 3
    assert history_of(sid_a) == 1 and history_of(sid_b) == 1


def test_unknown_recipe_and_bad_json_rejected(make_student):
    c = make_student()
    assert c.post("/api/pizza/finish", json={"recipe": "hawaii"}).status_code == 400
    assert c.post("/api/pizza/finish", json=[]).status_code == 400
    assert c.post("/api/pizza/finish", data="not-json", content_type="application/json").status_code == 400


def test_anonymous_and_parent_cannot_open(anon, parent):
    assert anon.get("/student/pizza").status_code in (302, 403)
    assert anon.post("/api/pizza/finish", json={"recipe": "margherita"}).status_code in (302, 403)
    assert parent.get("/student/pizza").status_code in (302, 403)


def test_delete_student_cleans_pizza(make_student, parent):
    c = make_student()
    sid = last_sid()
    page_data(c)
    c.post("/api/pizza/finish", json={"recipe": "caesar"})
    assert history_of(sid) == 1
    parent.post(f"/parent/students/{sid}/delete")
    assert db_scalar("SELECT COUNT(*) FROM pizza_history WHERE student_id=?", (sid,)) == 0
    assert db_scalar("SELECT COUNT(*) FROM pizza_starter WHERE student_id=?", (sid,)) == 0
    assert db_scalar("SELECT COUNT(*) FROM pizza_daily WHERE student_id=?", (sid,)) == 0
