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
    assert r.status_code == 302 and r.headers["Location"].endswith("/student/castle/kitchen?up=1")
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
    for t in ("castle", "castle_rooms", "castle_bricks", "castle_coins"):
        assert db_scalar(f"SELECT COUNT(*) FROM {t}") == 0, t


def test_every_room_word_has_place():
    from castle_art import POS
    for key in castle.ROOMS:
        for w in castle.room_words(key, 3):
            p = POS[key].get(w["en"].lower())
            assert p, (key, w["en"])
            assert p[2] == 0 or len(p) > 3 or w.get("pic"), (key, w["en"])        # есть что нарисовать
            assert 0 < p[0] < 300 and 0 < p[1] < 180


def test_scene_grows_with_level():
    art1, pins1 = castle.scene("kitchen", 1)
    art3, pins3 = castle.scene("kitchen", 3)
    assert len(pins1) == 6 and len(pins3) == len(castle.room_words("kitchen", 3))
    assert "🍳" not in art1 and "🍳" in art3                                   # сковородка появляется на 3 уровне


def test_room_page_pins_and_find(make_student):
    c = make_student(); sid = sid_of(); c.get("/student/castle")
    body = c.get("/student/castle/bedroom").get_data(as_text=True)
    assert body.count('class="cs-pin"') == 6 and 'id="cs-find-go"' in body
    r = c.post("/api/castle/bedroom/find").get_json()
    assert r["ok"] and r["bricks"] == castle.BRICKS_FIND
    assert c.post("/api/castle/bedroom/find").get_json()["bricks"] == 0     # раз в день
    assert c.post("/api/castle/kitchen/find").status_code == 404            # комната не построена


def _with_kitchen(c, sid, level=1):
    c.get("/student/castle")
    cn = conn()
    cn.execute("INSERT OR REPLACE INTO castle_rooms (student_id, room, level, at) VALUES (?, 'kitchen', ?, '')", (sid, level)); cn.commit()
    return cn


def test_income_needs_study_and_once_a_day(make_student):
    c = make_student(); sid = sid_of(); cn = _with_kitchen(c, sid, 2)
    inc = castle.income(cn, sid)
    assert inc["amount"] == castle.INCOME[2] and not inc["studied"]
    assert "позанимайся" in c.get("/student/castle").get_data(as_text=True).lower()
    coins0 = db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,))
    c.post("/student/castle/income")
    assert db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) == coins0      # не занимался — нет дохода
    import activity
    activity.log(cn, sid, "game")
    c.post("/student/castle/income"); c.post("/student/castle/income")
    assert db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) == coins0 + castle.INCOME[2]
    assert "уже собрано" in c.get("/student/castle").get_data(as_text=True)


def test_no_residents_no_income(make_student):
    c = make_student(); sid = sid_of(); c.get("/student/castle")
    assert castle.income(conn(), sid)["amount"] == 0 and castle.tasks(conn(), sid) == []
    assert not castle.collect_income(conn(), sid)[0]


def test_tasks_rotate_and_claim(make_student):
    from datetime import date, timedelta
    c = make_student(); sid = sid_of(); cn = _with_kitchen(c, sid)
    kinds = {castle.tasks(cn, sid, date(2026, 10, 1) + timedelta(days=i))[0]["kind"] for i in range(14)}
    assert len(kinds) >= 4 and kinds <= set(castle.TASKS)
    t = castle.tasks(cn, sid)[0]
    assert t["room"] == "kitchen" and not t["done"]
    ok, msg = castle.claim_task(cn, sid, "kitchen")
    assert not ok and "не выполнено" in msg
    # выполняем поручение того вида, что выпал сегодня
    if t["kind"] == "find":
        castle.on_find_done(cn, sid, "kitchen")
    elif t["kind"] == "words":
        cn.execute("INSERT INTO daily_goal (student_id, day, words) VALUES (?, ?, 5)", (sid, date.today().isoformat())); cn.commit()
    else:
        import activity
        activity.log(cn, sid, t["kind"])
    assert castle.tasks(cn, sid)[0]["done"]
    coins0 = db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,))
    c.post("/student/castle/task/kitchen", data={"back": "room"})
    c.post("/student/castle/task/kitchen")
    assert db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) == coins0 + castle.TASK_COINS
    assert castle.tasks(cn, sid)[0]["taken"]
    assert not castle.claim_task(cn, sid, "gym")[0]                      # у соседа нет поручения


def test_find_task_flag(make_student, monkeypatch):
    c = make_student(); sid = sid_of(); _with_kitchen(c, sid)
    monkeypatch.setattr(castle, "TASK_ORDER", ["find"])
    r = c.post("/api/castle/kitchen/find").get_json()
    assert r["task"]
    body = c.get("/student/castle/kitchen").get_data(as_text=True)
    assert 'id="cs-task"' in body and "/student/castle/task/kitchen" in body


def test_at_most_three_tasks(make_student):
    c = make_student(); sid = sid_of(); c.get("/student/castle"); cn = conn()
    for k in ("kitchen", "living", "gym", "classroom", "library"):
        cn.execute("INSERT INTO castle_rooms (student_id, room, level, at) VALUES (?, ?, 1, '')", (sid, k))
    cn.commit()
    ts = castle.tasks(cn, sid)
    assert len(ts) == castle.TASKS_PER_DAY and len({t["room"] for t in ts}) == castle.TASKS_PER_DAY
    assert len({t["kind"] for t in ts}) == castle.TASKS_PER_DAY
    assert castle.income(cn, sid)["amount"] == 5 * castle.INCOME[1]


def test_level_decorations_differ():
    a1, _ = castle.scene("bedroom", 1)
    a2, _ = castle.scene("bedroom", 2)
    a3, _ = castle.scene("bedroom", 3)
    assert a1 != a2 != a3 and "#E8618C" in a2 and 'fill="#FFF3B0"' in a3 and 'fill="#FFF3B0"' not in a2


def test_upgrade_shows_celebration(make_student):
    c = make_student(); sid = sid_of(); c.get("/student/castle"); give(sid, 100, 30)
    r = c.post("/student/castle/bedroom/build")
    assert r.headers["Location"].endswith("/student/castle/bedroom?up=1")
    body = c.get("/student/castle/bedroom?up=1").get_data(as_text=True)
    assert "Уровень 2!" in body and body.count("cs-pin is-new") == 4
    assert "cs-levelup" not in c.get("/student/castle/bedroom").get_data(as_text=True)


def test_admin_sets_bricks(parent, make_student):
    c = make_student(); sid = sid_of(); c.get("/student/castle"); give(sid, 0, 7)
    assert "кирпичиков <b>7</b>" in parent.get(f"/parent/students/{sid}").get_data(as_text=True)
    parent.post(f"/parent/students/{sid}/garden", data={"bricks": "25"})
    assert castle.bricks(conn(), sid) == 25
    parent.post(f"/parent/students/{sid}/garden", data={"bricks": "3"})
    assert castle.bricks(conn(), sid) == 3


def test_drawn_things_appear_with_their_words():
    import castle_art
    for key in castle.ROOMS:
        parts = castle_art.ART[key]()
        if isinstance(parts, str):
            continue
        for lv in (1, 2, 3):
            art, _ = castle.scene(key, lv)
            have = {w["en"].lower() for w in castle.room_words(key, lv)}
            for word, svg in parts:
                if word:
                    assert (svg in art) == (word in have), (key, lv, word)


def test_castle_awards(make_student):
    from achievements import ACHIEVEMENTS
    keys = {a["key"] for a in ACHIEVEMENTS if a["cat"] == "castle"}
    assert {"house_1", "castle_all", "castle_max", "castle_tasks_10", "castle_find_10"} <= keys
    c = make_student(); sid = sid_of(); c.get("/student/castle"); cn = conn()
    for i in range(10):
        castle.on_find_done(cn, sid, "bedroom", __import__("datetime").date(2026, 1, 1 + i))
    c.post("/api/castle/bedroom/find")
    assert db_scalar("SELECT COUNT(*) FROM achievements WHERE key='castle_find_10'") == 1
    body = c.get("/student/achievements").get_data(as_text=True)
    assert "Замок" in body and "Зоркий глаз" in body


def test_every_level_adds_things():
    for key in castle.ROOMS:
        n1, n2, n3 = (len(castle.room_words(key, lv)) for lv in (1, 2, 3))
        assert n1 == 6 and n2 - n1 >= 2 and n3 - n2 >= 2, key
        arts = [castle.scene(key, lv)[0] for lv in (1, 2, 3)]
        assert len(set(arts)) == 3, key
