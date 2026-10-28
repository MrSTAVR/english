# -*- coding: utf-8 -*-
"""Монетки за тест урока: первая сдача, пересдача только за рекорд, «за старание» при провале."""
import sqlite3

import database
from curriculum import LESSONS
from tests.helpers import correct_fields, db_scalar, open_lesson, wrong_fields
from tests.test_vacation import sid_of


def coins(sid):
    return db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) or 0


def take(c, lesson, n_right):
    aid = open_lesson(c, lesson["id"])
    form = {"attempt_id": aid, "seconds": 300}
    for i, q in enumerate(lesson["test"]):
        form.update((correct_fields if i < n_right else wrong_fields)(q, i))
    c.post(f"/lesson/{lesson['id']}/submit", data=form)
    return aid


def test_first_pass_pays_repeat_does_not(make_student):
    c = make_student(); sid = sid_of()
    l = LESSONS[0]
    take(c, l, len(l["test"]))
    assert coins(sid) == 10                                  # сдан впервые и на 100%
    take(c, l, len(l["test"]))
    assert coins(sid) == 10                                  # пересдача без рекорда — без монеток


def test_retry_pays_only_for_new_best_once_a_day(make_student):
    c = make_student(); sid = sid_of()
    l = LESSONS[0]
    n = len(l["test"])
    aid = take(c, l, n - 2)                                  # сдан, но не на 100%
    assert coins(sid) == 5
    conn = sqlite3.connect(database.DB_PATH)
    conn.execute("UPDATE attempts SET finished_at='2026-01-01T10:00:00' WHERE id=?", (aid,))
    conn.commit(); conn.close()
    take(c, l, n)                                            # на другой день — рекорд
    assert coins(sid) == 7
    take(c, l, n)
    assert coins(sid) == 7


def test_effort_coins_once_a_day(make_student):
    c = make_student(); sid = sid_of()
    l = LESSONS[0]
    n = len(l["test"])
    half = next(k for k in range(n) if 40 <= 100 * k / n < 60)
    take(c, l, half)
    assert coins(sid) == 2                                   # не сдан, но старалась
    take(c, l, half)
    assert coins(sid) == 2                                   # «за старание» — раз в день
    take(c, l, 0)
    assert coins(sid) == 2
