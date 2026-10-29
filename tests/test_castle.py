# -*- coding: utf-8 -*-
"""Замок Чик-чика (закрыт — его заменила ферма): данные комнат и рисунки. Переезд на ферму — tests/test_farm.py."""
import castle
from curriculum import LESSONS_BY_ID
from tests.helpers import db_scalar
from tests.test_vacation import conn, sid_of


def give(sid, coins, bricks=0):
    c = conn()
    c.execute("UPDATE garden SET coins=? WHERE student_id=?", (coins, sid))
    if bricks:
        castle.earn(c, sid, "test", bricks, bricks)
    c.commit()
    return c


def test_goal_bricks_once_a_day():
    import sqlite3
    import database
    cn = sqlite3.connect(database.DB_PATH)
    assert castle.on_goal_done(cn, 1) == castle.BRICKS_GOAL
    assert castle.on_goal_done(cn, 1) == 0


def test_room_words_grow_with_level():
    for key in castle.ROOMS:
        w1, w2, w3 = (castle.room_words(key, lv) for lv in (1, 2, 3))
        assert 4 <= len(w1) <= 6 and len(w1) <= len(w2) <= len(w3), key
        assert all(" " not in w["en"].strip() for w in w3), key


def test_rooms_lessons_exist():
    for key, r in castle.ROOMS.items():
        assert r["lesson"] is None or r["lesson"] in LESSONS_BY_ID, key
    assert sorted(k for fl in castle.FLOORS for k in fl) == sorted(castle.ROOMS)


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


def _with_kitchen(c, sid, level=1):
    c.get("/student/castle")
    cn = conn()
    cn.execute("INSERT OR REPLACE INTO castle_rooms (student_id, room, level, at) VALUES (?, 'kitchen', ?, '')", (sid, level)); cn.commit()
    return cn


def test_no_residents_no_income(make_student):
    c = make_student(); sid = sid_of(); c.get("/student/castle")
    assert castle.income(conn(), sid)["amount"] == 0 and castle.tasks(conn(), sid) == []
    assert not castle.collect_income(conn(), sid)[0]


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


def test_every_level_adds_things():
    for key in castle.ROOMS:
        n1, n2, n3 = (len(castle.room_words(key, lv)) for lv in (1, 2, 3))
        assert n1 == 6 and n2 - n1 >= 2 and n3 - n2 >= 2, key
        arts = [castle.scene(key, lv)[0] for lv in (1, 2, 3)]
        assert len(set(arts)) == 3, key


def test_roof_opens_after_ten_study_days_not_in_a_row(make_student):
    """Крыша — за 10 дней занятий всего: Маша занимается через день, 7 подряд ей недостижимы."""
    import sqlite3
    import castle
    import database
    from datetime import date, timedelta
    make_student()
    conn = sqlite3.connect(database.DB_PATH); conn.row_factory = sqlite3.Row
    sid = conn.execute("SELECT id FROM students").fetchone()[0]
    stats = {"completed_ids": set(), "stories_done": 0}
    for k in range(0, 18, 2):                                     # 9 дней через день
        conn.execute("INSERT INTO activity (student_id, day, kind) VALUES (?, ?, 'game')",
                     (sid, (date.today() - timedelta(days=k)).isoformat()))
    conn.commit()
    assert "уже 9" in castle.lock_reason(conn, sid, "roof", stats, None)
    conn.execute("INSERT INTO activity (student_id, day, kind) VALUES (?, ?, 'story')",
                 ((sid, (date.today() - timedelta(days=30)).isoformat())))
    conn.commit()
    assert castle.lock_reason(conn, sid, "roof", stats, None) is None
