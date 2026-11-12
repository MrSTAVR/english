# -*- coding: utf-8 -*-
"""Пиццерия: идемпотентность, откат, флаги начинок и выключенный раздел (P-05, P-06, P-10, P-11)."""
import json
import sqlite3

import database
from tests.helpers import db_all, db_scalar


def last_sid():
    return db_scalar("SELECT id FROM students ORDER BY id DESC LIMIT 1")


def coins_of(sid):
    return db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) or 0


def history_of(sid):
    return db_scalar("SELECT COUNT(*) FROM pizza_history WHERE student_id=?", (sid,)) or 0


def barn_of(sid, item):
    return db_scalar("SELECT qty FROM farm_barn WHERE student_id=? AND item=?", (sid, item)) or 0


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


def test_repeat_finish_does_not_spend_or_pay_again(make_student):
    c = make_student(pizza=True)
    sid = last_sid()
    page_data(c)
    first = c.post("/api/pizza/finish", json={"recipe": "margherita"}).get_json()
    assert first["gained"] == 3 and first["already_done"] is False
    before = {item: barn_of(sid, item)
              for item in ("dough", "tomato_sauce", "mozzarella", "basil", "cherry_tomato")}
    coins_before = coins_of(sid)

    r = c.post("/api/pizza/finish", json={"recipe": "margherita"})
    assert r.status_code == 200
    got = r.get_json()
    assert got["ok"] is True
    assert got["gained"] == 0 and got["already"] is True and got["already_done"] is True
    assert got["coins"] == coins_before == coins_of(sid)
    assert history_of(sid) == 1
    for item, qty in before.items():
        assert barn_of(sid, item) == qty, f"{item} списан повторно"


def test_repeat_finish_ok_even_with_empty_barn(make_student):
    """Двойное нажатие: первый запрос всё съел, второй всё равно отвечает ok."""
    c = make_student(pizza=True)
    sid = last_sid()
    page_data(c)
    assert c.post("/api/pizza/finish", json={"recipe": "caesar"}).get_json()["gained"] == 3
    conn = sqlite3.connect(database.DB_PATH)
    try:
        conn.execute("DELETE FROM farm_barn WHERE student_id=?", (sid,))
        conn.commit()
    finally:
        conn.close()

    r = c.post("/api/pizza/finish", json={"recipe": "caesar"})
    assert r.status_code == 200
    assert r.get_json()["already_done"] is True
    assert r.get_json()["gained"] == 0
    assert coins_of(sid) == 3 and history_of(sid) == 1


def test_missing_products_roll_back_without_partial_spend(make_student):
    c = make_student(pizza=True)
    sid = last_sid()
    page_data(c)
    conn = sqlite3.connect(database.DB_PATH)
    try:
        conn.execute("DELETE FROM farm_barn WHERE student_id=? AND item='dough'", (sid,))
        conn.commit()
    finally:
        conn.close()
    before = {item: barn_of(sid, item)
              for item in ("tomato_sauce", "mozzarella", "basil", "cherry_tomato")}
    coins_before = coins_of(sid)

    r = c.post("/api/pizza/finish", json={"recipe": "margherita"})
    assert r.status_code == 400
    body = r.get_json()
    assert body["ok"] is False and "dough" in body["missing"]
    assert body["error"] == "missing_products"
    for item, qty in before.items():
        assert barn_of(sid, item) == qty, f"{item} списан при откате"
    assert coins_of(sid) == coins_before and history_of(sid) == 0


def test_pieces_are_optional_but_validated(make_student):
    c = make_student(pizza=True)
    sid = last_sid()
    page_data(c)
    for bad in (0, 21, -3, "5", True):
        r = c.post("/api/pizza/finish", json={"recipe": "margherita", "pieces": bad})
        assert r.status_code == 400, bad
        assert r.get_json()["error"] == "bad_pieces"
    assert history_of(sid) == 0 and coins_of(sid) == 0

    r = c.post("/api/pizza/finish", json={"recipe": "margherita", "pieces": 8})
    assert r.status_code == 200 and r.get_json()["gained"] == 3
    assert history_of(sid) == 1


def test_pizza_disabled_api_returns_403(make_student):
    c = make_student()                                  # пиццерия выключена
    assert c.post("/api/pizza/finish", json={"recipe": "margherita"}).status_code == 403
    assert c.post("/api/pizza/finish", json=[]).status_code == 403


def test_unknown_recipe_has_message(make_student):
    c = make_student(pizza=True)
    r = c.post("/api/pizza/finish", json={"recipe": "hawaii"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "unknown_recipe"
    assert r.get_json()["message"]


def test_state_has_stock_and_known_toppings(make_student):
    c = make_student(pizza=True)
    last_sid()
    data = page_data(c)
    assert data["stock"]["dough"] == 4
    assert data["stock"]["mozzarella"] == 8             # стартовый набор (молоко/муку даёт бабушка)
    for recipe in data["recipes"]:
        for top in recipe["toppings"]:
            assert top["en"] and top["ru"]               # показываем EN и RU всегда
            assert isinstance(top["known"], bool)

    caesar = next(r for r in data["recipes"] if r["key"] == "caesar")
    parmesan = next(t for t in caesar["toppings"] if t["key"] == "parmesan")
    assert parmesan["known"] is False                    # слово ещё не проходили
    pepperoni = next(t for t in data["recipes"][1]["toppings"] if t["key"] == "pepperoni")
    assert pepperoni["known"] is True                    # кладовая — знакома сразу


def test_daily_stock_uses_farm_now(make_student, monkeypatch):
    import datetime as dt

    import farm

    c = make_student(pizza=True)
    sid = last_sid()
    monkeypatch.setattr(farm, "now", lambda: dt.datetime(2030, 1, 2, 12, 0, 0))
    page_data(c)
    assert db_scalar("SELECT day FROM pizza_daily WHERE student_id=?", (sid,)) == "2030-01-02"


def test_next_day_basket_refilled_once(make_student, monkeypatch):
    """farm.now() подменён: на следующий день бабушка снова даёт запас, в тот же день — нет."""
    import datetime as dt

    import farm

    c = make_student(pizza=True)
    sid = last_sid()
    daily = ("milk", "egg", "flour", "tomato", "water")

    monkeypatch.setattr(farm, "now", lambda: dt.datetime(2030, 3, 1, 9, 0, 0))
    page_data(c)
    day1 = {item: barn_of(sid, item) for item in daily}
    # стартовый набор (12 молока, 6 яиц, 4 воды) + бабушкин запас
    assert day1 == {"milk": 16, "egg": 8, "flour": 2, "tomato": 2, "water": 6}
    page_data(c)                                        # второй заход в тот же день — без добавки
    assert {item: barn_of(sid, item) for item in daily} == day1

    monkeypatch.setattr(farm, "now", lambda: dt.datetime(2030, 3, 2, 9, 0, 0))
    page_data(c)
    assert {item: barn_of(sid, item) for item in daily} == {
        "milk": 20, "egg": 10, "flour": 4, "tomato": 4, "water": 8}
    assert db_scalar("SELECT COUNT(*) FROM pizza_daily WHERE student_id=?", (sid,)) == 2
    days = {row[0] for row in db_all("SELECT day FROM pizza_daily WHERE student_id=?", (sid,))}
    assert days == {"2030-03-01", "2030-03-02"}


def test_missing_products_short_qty_spends_nothing(make_student):
    """Одного продукта мало: не списываем ни его, ни остальные (частичного списания нет)."""
    c = make_student(pizza=True)
    sid = last_sid()
    page_data(c)
    conn = sqlite3.connect(database.DB_PATH)
    try:
        conn.execute("UPDATE farm_barn SET qty=1 WHERE student_id=? AND item='mozzarella'", (sid,))
        conn.commit()
    finally:
        conn.close()
    items = ("dough", "tomato_sauce", "mozzarella", "mushroom", "oregano")
    before = {item: barn_of(sid, item) for item in items}
    coins_before = coins_of(sid)

    r = c.post("/api/pizza/finish", json={"recipe": "mushroom"})
    assert r.status_code == 400
    body = r.get_json()
    assert body["error"] == "missing_products" and body["missing"] == ["mozzarella"]
    assert {item: barn_of(sid, item) for item in items} == before
    assert coins_of(sid) == coins_before and history_of(sid) == 0


def test_pieces_boundaries_accepted(make_student):
    """1 и 20 — границы диапазона; без pieces и с null — тоже можно."""
    c = make_student(pizza=True)
    sid = last_sid()
    page_data(c)
    for recipe, pieces in (("margherita", 1), ("pepperoni", 20), ("mushroom", None)):
        r = c.post("/api/pizza/finish", json={"recipe": recipe, "pieces": pieces})
        assert r.status_code == 200, (recipe, pieces)
        assert r.get_json()["gained"] == 3
    r = c.post("/api/pizza/finish", json={"recipe": "caesar"})     # pieces не передан
    assert r.status_code == 200 and r.get_json()["gained"] == 3
    assert history_of(sid) == 4 and coins_of(sid) == 12


def test_pieces_float_rejected(make_student):
    c = make_student(pizza=True)
    sid = last_sid()
    page_data(c)
    for bad in (5.5, 0.0, 20.1):
        r = c.post("/api/pizza/finish", json={"recipe": "margherita", "pieces": bad})
        assert r.status_code == 400, bad
        assert r.get_json()["error"] == "bad_pieces"
    assert history_of(sid) == 0 and coins_of(sid) == 0


def test_disabled_pizza_page_redirects_home(make_student):
    c = make_student()                                  # pizza_enabled=0
    r = c.get("/student/pizza")
    assert r.status_code == 302
    location = r.headers["Location"]
    assert "/student" in location and "pizza" not in location


def test_state_exposes_stock_and_known(make_student, flask_app):
    """pizza.state() отдаёт stock (все продукты рецептов, даже нулевые) и known у начинок."""
    import database
    import pizza

    make_student(pizza=True)
    sid = last_sid()
    with flask_app.app_context():
        db = database.get_db()
        st = pizza.state(db, sid)

    assert {"coins", "completed", "recipes", "stock", "reward"} <= set(st)
    assert st["coins"] == 0 and st["completed"] == [] and st["reward"] == pizza.COINS_FIRST
    expected = {item for need in pizza.NEEDS.values() for item in need}
    assert set(st["stock"]) == expected
    assert all(isinstance(v, int) and v >= 0 for v in st["stock"].values())
    assert st["stock"]["dough"] == 4                    # стартовый набор уже выдан
    assert st["stock"]["mozzarella"] == 8

    toppings = {t["key"]: t["known"] for r in st["recipes"] for t in r["toppings"]}
    assert toppings["basil"] is True                    # early-культура — знакома сразу
    assert toppings["pepperoni"] is True                # кладовая
    assert toppings["parmesan"] is False                # урок 999 ещё не пройден


def test_process_route_passes_qty(make_student):
    c = make_student()
    sid = last_sid()
    give(sid, wheat=6)
    r = c.post("/api/farm/process", json={"key": "flour", "qty": 2})
    assert r.status_code == 200 and r.get_json()["ok"] is True
    assert barn_of(sid, "flour") == 2 and barn_of(sid, "wheat") == 2
    assert c.post("/api/farm/process", json={"key": "flour", "qty": "много"}).status_code == 400


def test_process_route_qty_three_and_zero(make_student):
    """qty из тела запроса доходит до pizza_farm.process: 3 порции за раз, 0 — отказ без списания."""
    c = make_student()
    sid = last_sid()
    give(sid, wheat=6)
    r = c.post("/api/farm/process", json={"key": "flour", "qty": 3})
    assert r.status_code == 200 and r.get_json()["ok"] is True
    assert barn_of(sid, "flour") == 3 and barn_of(sid, "wheat") == 0

    r = c.post("/api/farm/process", json={"key": "dough", "qty": 0})
    assert r.status_code == 200 and r.get_json()["ok"] is False
    assert barn_of(sid, "flour") == 3 and barn_of(sid, "dough") == 0
