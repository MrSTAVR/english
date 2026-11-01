# -*- coding: utf-8 -*-
"""Пиццерия v1: страница, завершение рецепта и награда один раз (pizza.py)."""
import json

from tests.helpers import db_scalar


def coins_of(sid):
    return db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) or 0


def history_of(sid):
    return db_scalar("SELECT COUNT(*) FROM pizza_history WHERE student_id=?", (sid,)) or 0


def last_sid():
    return db_scalar("SELECT id FROM students ORDER BY id DESC LIMIT 1")


def page_data(client):
    html = client.get("/student/pizza").get_data(as_text=True)
    return json.loads(html.split('id="pz-data">', 1)[1].split("</script>", 1)[0])


def test_page_available_and_has_four_recipes(make_student):
    c = make_student()
    data = page_data(c)
    assert [x["key"] for x in data["recipes"]] == ["margherita", "pepperoni", "mushroom", "caesar"]
    assert data["reward"] == 3


def test_first_recipe_gives_coins_once(make_student):
    c = make_student()
    sid = last_sid()
    r = c.post("/api/pizza/finish", json={"recipe": "margherita"})
    assert r.status_code == 200
    got = r.get_json()
    assert got["gained"] == 3 and got["already"] is False
    assert coins_of(sid) == 3 and history_of(sid) == 1
    got = c.post("/api/pizza/finish", json={"recipe": "margherita"}).get_json()
    assert got["gained"] == 0 and got["already"] is True
    assert coins_of(sid) == 3 and history_of(sid) == 1


def test_each_recipe_gives_once(make_student):
    c = make_student()
    sid = last_sid()
    for key in ("margherita", "pepperoni", "mushroom", "caesar"):
        assert c.post("/api/pizza/finish", json={"recipe": key}).get_json()["gained"] == 3
    assert coins_of(sid) == 12 and history_of(sid) == 4
    assert c.post("/api/pizza/finish", json={"recipe": "caesar"}).get_json()["gained"] == 0


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
    c.post("/api/pizza/finish", json={"recipe": "caesar"})
    assert history_of(sid) == 1
    parent.post(f"/parent/students/{sid}/delete")
    assert db_scalar("SELECT COUNT(*) FROM pizza_history WHERE student_id=?", (sid,)) == 0
