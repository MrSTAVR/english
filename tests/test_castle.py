# -*- coding: utf-8 -*-
"""Замок Чик-чика: переезд из домика, кирпичики, постройка и улучшение комнат."""
import castle
from curriculum import LESSONS, LESSONS_BY_ID
from tests.helpers import db_scalar, submit_lesson
from tests.test_vacation import conn, sid_of


def give(sid, coins, bricks=0):
    c = conn()
    c.execute("UPDATE garden SET coins=? WHERE student_id=?", (coins, sid))
    if bricks:
        castle.earn(c, sid, "test", bricks, bricks)
    c.commit()
    return c


def test_first_visit_moves_and_refunds(make_student):
    c = make_student(); sid = sid_of(); cn = conn()
    c.get("/student/garden")
    cn.execute("UPDATE garden SET coins=5 WHERE student_id=?", (sid,))
    cn.execute("INSERT INTO house_items (student_id, item_key) VALUES (?, 'wall-blue')", (sid,))      # 15 монеток
    cn.execute("INSERT INTO house_place (student_id, slot, item_key) VALUES (?, 'wall', 'wall-blue')", (sid,)); cn.commit()
    body = c.get("/student/castle").get_data(as_text=True)
    assert "Замок Чик-чика" in body and "Чик-чик переехал в замок" in body and "+15" in body
    assert db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) == 20
    assert db_scalar("SELECT COUNT(*) FROM house_items") == 0 and db_scalar("SELECT COUNT(*) FROM house_place") == 0
    assert castle.levels(conn(), sid) == {"bedroom": 1}
    body = c.get("/student/castle").get_data(as_text=True)            # повторно — без возврата и плашки
    assert "переехал" not in body and db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) == 20


def test_start_bricks_for_done_lessons(make_student):
    c = make_student(); sid = sid_of()
    submit_lesson(c, LESSONS[0]["id"]); submit_lesson(c, LESSONS[1]["id"])
    c.get("/student/castle")
    # 2 урока: по 3 кирпичика за сдачу + 2 стартовых при переезде
    assert castle.bricks(conn(), sid) == 2 * castle.BRICKS_LESSON + 2 * castle.START_PER_LESSON


def test_lesson_bricks_once_and_result_page(make_student):
    c = make_student(); sid = sid_of()
    body = submit_lesson(c, LESSONS[0]["id"])
    assert "Кирпичики для замка" in body and f"+{castle.BRICKS_LESSON}" in body
    body = submit_lesson(c, LESSONS[0]["id"])
    assert "Кирпичики для замка" not in body
    assert castle.bricks(conn(), sid) == castle.BRICKS_LESSON
    submit_lesson(c, LESSONS[1]["id"], wrong=True)                     # не сдан — ничего
    assert castle.bricks(conn(), sid) == castle.BRICKS_LESSON


def test_goal_bricks_once_a_day():
    import sqlite3
    import database
    cn = sqlite3.connect(database.DB_PATH)
    assert castle.on_goal_done(cn, 1) == castle.BRICKS_GOAL
    assert castle.on_goal_done(cn, 1) == 0


def test_locked_room_needs_lesson(make_student):
    c = make_student(); sid = sid_of(); c.get("/student/castle"); give(sid, 100, 30)
    body = c.get("/student/castle").get_data(as_text=True)
    assert "Пройди урок замка" in body
    c.post("/student/castle/kitchen/build")
    assert "kitchen" not in castle.levels(conn(), sid)
    submit_lesson(c, 20002)                                             # урок замка «Кухня»
    assert "kitchen" not in castle.levels(conn(), sid)
    r = c.post("/student/castle/kitchen/build")
    assert r.status_code == 302 and r.headers["Location"].endswith("/student/castle/kitchen")
    assert castle.levels(conn(), sid)["kitchen"] == 1
    b, coins = castle.COST[1]
    assert db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) < 100 + 1   # монетки списаны (урок мог дать свои)
    assert castle.bricks(conn(), sid) == 30 + castle.BRICKS_CASTLE_LESSON - b


def test_build_upgrade_and_max(make_student):
    c = make_student(); sid = sid_of(); c.get("/student/castle"); cn = give(sid, 1000, 100)
    for lv in (2, 3):
        ok, _ = castle.build(cn, sid, "bedroom", {"completed_ids": set()}, cn.execute("SELECT * FROM garden WHERE student_id=?", (sid,)).fetchone())
        assert ok and castle.levels(cn, sid)["bedroom"] == lv
    ok, msg = castle.build(cn, sid, "bedroom", {"completed_ids": set()}, cn.execute("SELECT * FROM garden WHERE student_id=?", (sid,)).fetchone())
    assert not ok and "самого высокого" in msg
    assert castle.bricks(cn, sid) == 100 - castle.COST[2][0] - castle.COST[3][0]
    assert castle.builds_count(cn, sid) == 2


def test_not_enough(make_student):
    c = make_student(); sid = sid_of(); c.get("/student/castle"); cn = give(sid, 0)
    ok, msg = castle.build(cn, sid, "bedroom", {"completed_ids": set()}, cn.execute("SELECT * FROM garden WHERE student_id=?", (sid,)).fetchone())
    assert not ok and "Не хватает" in msg and "кирпичиков" in msg and "монеток" in msg
    assert castle.levels(cn, sid)["bedroom"] == 1


def test_room_page(make_student):
    c = make_student(); sid = sid_of(); c.get("/student/castle")
    body = c.get("/student/castle/bedroom").get_data(as_text=True)
    assert "Спальня" in body and "cs-word" in body
    assert c.get("/student/castle/kitchen").status_code == 302          # не построена
    assert c.get("/student/castle/nope").status_code == 404


def test_room_words_grow_with_level():
    for key in castle.ROOMS:
        w1, w2, w3 = (castle.room_words(key, lv) for lv in (1, 2, 3))
        assert 4 <= len(w1) <= 6 and len(w1) <= len(w2) <= len(w3), key
        assert all(" " not in w["en"].strip() for w in w3), key


def test_rooms_lessons_exist():
    for key, r in castle.ROOMS.items():
        assert r["lesson"] is None or r["lesson"] in LESSONS_BY_ID, key
    assert sorted(k for fl in castle.FLOORS for k in fl) == sorted(castle.ROOMS)


def test_achievement_first_room(make_student):
    c = make_student(); sid = sid_of(); c.get("/student/castle"); give(sid, 100, 30)
    submit_lesson(c, 20002)
    c.post("/student/castle/kitchen/build")
    assert db_scalar("SELECT COUNT(*) FROM achievements WHERE key='house_1'") == 1


def test_delete_student_clears_castle(parent, make_student):
    c = make_student(); sid = sid_of(); c.get("/student/castle"); give(sid, 0, 5)
    parent.post(f"/parent/students/{sid}/delete")
    for t in ("castle", "castle_rooms", "castle_bricks"):
        assert db_scalar(f"SELECT COUNT(*) FROM {t}") == 0, t
