# -*- coding: utf-8 -*-
"""Страница сада: сцена, альбом, магазин, жёсткий сброс серии."""
import re
import sqlite3

import database
import garden
from tests.helpers import db_scalar


def sid_of(username="masha"):
    return db_scalar("SELECT id FROM students WHERE username=?", (username,))


def set_garden(parent, sid, **fields):
    parent.post(f"/parent/students/{sid}/garden", data=fields)


def coins(sid):
    return db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,))


def stage_of(body):
    """Только сама сцена сада (без превью в магазине, где есть цвета всех фонов)."""
    return body.split('class="garden-stage')[1].split('class="tree-info"')[0]


def page(client):
    r = client.get("/student/garden")
    assert r.status_code == 200
    return r.get_data(as_text=True)


def test_new_scene_album_and_shop_previews(parent, make_student):
    c = make_student()
    set_garden(parent, sid_of(), streak_days=12, coins=100)
    body = page(c)
    assert "garden-stage" in body and 'aria-label="Сад, день серии 12"' in body
    m = re.search(r"открыто (\d+) из (\d+)", body)
    assert m and (m.group(1), m.group(2)) == ("12", "30")
    assert body.count('class="garden-svg thumb"') == len(garden.DECORATIONS)
    assert "Набежали облачка" in body              # находка 12-го дня


def test_buy_decoration_and_swap_theme(parent, make_student):
    c = make_student()
    sid = sid_of()
    set_garden(parent, sid, streak_days=12, coins=100)
    body = c.post("/student/garden/buy", data={"deco_key": "night"},
                  follow_redirects=True).get_data(as_text=True)
    assert "Новый фон сада" in body and coins(sid) == 72
    assert "#1B2A5E" in stage_of(body)
    body = c.post("/student/garden/buy", data={"deco_key": "sunset"},
                  follow_redirects=True).get_data(as_text=True)
    assert "старый фон снят" in body and coins(sid) == 58     # 72 - 28 + 14
    stage = stage_of(body)
    assert "#FFB56B" in stage and "#1B2A5E" not in stage       # остался один фон — закат
    assert body.count("worn-item") == 1


def test_remove_decoration_refunds_half(parent, make_student):
    c = make_student()
    sid = sid_of()
    set_garden(parent, sid, streak_days=5, coins=20)
    c.post("/student/garden/buy", data={"deco_key": "flags"})      # 12 монет
    assert coins(sid) == 8
    slot = db_scalar("SELECT slot FROM decorations WHERE student_id=?", (sid,))
    c.post(f"/student/garden/remove/{slot}")
    assert coins(sid) == 14                                          # вернулась половина


def test_broken_streak_garden_waits_and_keeps_decorations(parent, make_student):
    """Пропуск — не наказание: дерево не засыпает и не уменьшается («ждёт тебя»), купленное остаётся."""
    c = make_student()
    sid = sid_of()
    set_garden(parent, sid, streak_days=12, coins=100)
    c.post("/student/garden/buy", data={"deco_key": "sun"})
    assert db_scalar("SELECT COUNT(*) FROM decorations WHERE student_id=?", (sid,)) == 1
    set_garden(parent, sid, streak_days=0)                           # «пропущенный день»
    body = page(c)
    assert "is-broken" not in body and "Дерево ждёт тебя" in body and 'день серии 0"' not in body
    assert db_scalar("SELECT COUNT(*) FROM decorations WHERE student_id=?", (sid,)) == 1
    assert coins(sid) == 92                                          # монеты остаются
    assert body.count("Сначала позанимайся") == len(garden.DECORATIONS)


def test_student_home_garden_tile_has_outline_icon(make_student):
    c = make_student()
    assert '#o-sprout' in c.get("/student").get_data(as_text=True)    # дизайн 3.0: контурные значки


def test_retired_rainbow_is_refunded(parent, make_student):
    c = make_student()
    sid = sid_of()
    c.get("/student")                                                # создаёт строку сада
    conn = sqlite3.connect(database.DB_PATH)
    conn.execute("UPDATE garden SET coins=0 WHERE student_id=?", (sid,))
    conn.execute("INSERT INTO decorations (student_id, deco_key, slot) VALUES (?, 'rainbow', 0)", (sid,))
    conn.commit()
    conn.close()
    database.init_db()
    assert coins(sid) == 30
    assert db_scalar("SELECT COUNT(*) FROM decorations WHERE deco_key='rainbow'") == 0
