# -*- coding: utf-8 -*-
"""Ферма: капли только за учёбу, грядки и животные по времени, амбар, заказы героев (farm.py)."""
import sqlite3
from datetime import datetime, timedelta

import pytest

import database
import farm
from curriculum import LESSONS
from tests.helpers import correct_fields, open_lesson, wrong_fields
from tests.test_vacation import sid_of

T0 = datetime(2026, 11, 2, 10, 0)      # понедельник


@pytest.fixture
def db():
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def clock(monkeypatch):
    t = {"now": T0}
    monkeypatch.setattr(farm, "now", lambda: t["now"])
    return t


def take(c, lesson, n_right):
    aid = open_lesson(c, lesson["id"])
    form = {"attempt_id": aid, "seconds": 300}
    for i, q in enumerate(lesson["test"]):
        form.update((correct_fields if i < n_right else wrong_fields)(q, i))
    c.post(f"/lesson/{lesson['id']}/submit", data=form)
    return aid


def test_lesson_gives_drops_once(make_student, db):
    c = make_student(); sid = sid_of()
    l = LESSONS[0]
    take(c, l, len(l["test"]))
    assert farm.drops(db, sid) == farm.DROPS_PASS + farm.DROPS_PERFECT      # сдан впервые на 100%
    take(c, l, len(l["test"]))
    assert farm.drops(db, sid) == farm.DROPS_PASS + farm.DROPS_PERFECT      # пересдача сданного — без капель


def test_fix_gives_drops_once_a_day(make_student, db):
    make_student(); sid = sid_of()
    assert farm.on_test(db, sid, 5, 1, 80, True, False, True, False) == farm.DROPS_FIX
    assert farm.on_test(db, sid, 5, 2, 90, True, False, True, False) == 0
    assert farm.on_test(db, sid, 6, 3, 20, False, False, True, False) == 0  # исправление не сдано и меньше 40%


def test_failed_test_gives_effort_once_a_day(make_student, db):
    c = make_student(); sid = sid_of()
    l = LESSONS[0]
    n = len(l["test"])
    take(c, l, n // 2)                                       # 50% — не сдан, но старался
    assert farm.drops(db, sid) == farm.DROPS_EFFORT
    take(c, l, n // 2)
    assert farm.drops(db, sid) == farm.DROPS_EFFORT
    take(c, l, 0)
    assert farm.drops(db, sid) == farm.DROPS_EFFORT


def test_small_drops_capped_per_day(make_student, db):
    c = make_student(); sid = sid_of()
    c.post("/api/game", json={"game": "pairs", "stars": 0})
    assert farm.drops(db, sid) == 0                           # игра без звёзд — без капли
    for _ in range(15):
        c.post("/api/game", json={"game": "pairs", "stars": 3})
    assert farm.drops(db, sid) == farm.SMALL_CAP              # игры не заменяют уроки
    assert farm.on_goal_done(db, sid) == farm.DROPS_GOAL      # цель дня — не мелочь, сверх лимита
    assert farm.on_goal_done(db, sid) == 0                    # и один раз за день


def test_review_every_ten_words(make_student, db):
    make_student(); sid = sid_of()
    assert farm.on_review(db, sid, 9) == 0
    assert farm.on_review(db, sid, 10) == farm.DROPS_REVIEW
    assert farm.on_review(db, sid, 10) == 0
    assert farm.on_review(db, sid, 20) == farm.DROPS_REVIEW


def test_plot_cycle(make_student, db, clock):
    make_student(); sid = sid_of()
    ok, _ = farm.plant(db, sid, 0, "carrot", done=0)
    assert ok and not farm.plant(db, sid, 0, "tomato", done=0)[0]      # грядка занята
    assert not farm.water(db, sid, 0)[0]                      # капель нет — полить нечем
    farm.give(db, sid, "lesson", 1, 12)
    assert farm.water(db, sid, 0)[0] and farm.drops(db, sid) == 12 - farm.WATER_COST
    assert not farm.water(db, sid, 0)[0]                      # уже полито
    assert farm.harvest(db, sid, 0) == (False, 0)             # ещё растёт
    clock["now"] = T0 + timedelta(days=30)                    # урожай не вянет
    assert farm.harvest(db, sid, 0) == (True, 3)
    assert farm.barn(db, sid) == {"carrot": 3}
    assert farm.plant(db, sid, 0, "tomato", done=0)[0]        # грядка снова свободна


def test_seeds_open_with_lessons(make_student, db):
    make_student(); sid = sid_of()
    assert not farm.plant(db, sid, 1, "potato", done=0)[0]
    assert farm.plant(db, sid, 1, "potato", done=5)[0]
    assert not farm.plant(db, sid, 9, "carrot", done=0)[0]    # грядок шесть


def test_chicken_eggs(make_student, db, clock):
    make_student(); sid = sid_of()
    assert not farm.feed(db, sid, "chicken")[0]               # без капель не покормить
    farm.give(db, sid, "goal", "d", 4)
    assert farm.feed(db, sid, "chicken")[0]
    assert not farm.feed(db, sid, "chicken")[0]
    assert farm.collect(db, sid, "chicken") == (False, 0)
    clock["now"] = T0 + timedelta(minutes=farm.ANIMALS["chicken"]["minutes"])
    assert farm.collect(db, sid, "chicken") == (True, 3)
    assert farm.barn(db, sid) == {"egg": 3}
    assert not farm.feed(db, sid, "cow")[0]                   # коровы пока нет


def test_cow_needs_lesson_and_coins(make_student, db):
    make_student(); sid = sid_of()
    from garden import get_garden
    get_garden(db, sid)
    db.execute("UPDATE garden SET coins=500 WHERE student_id=?", (sid,)); db.commit()
    assert not farm.buy_cow(db, sid, {"completed_ids": set()})[0]
    assert farm.buy_cow(db, sid, {"completed_ids": {farm.COW_LESSON}})[0]
    assert db.execute("SELECT coins FROM garden WHERE student_id=?", (sid,)).fetchone()[0] == 500 - farm.COWSHED_COST
    assert not farm.buy_cow(db, sid, {"completed_ids": {farm.COW_LESSON}})[0]


def test_orders_open_only_by_study(make_student, db, clock):
    make_student(); sid = sid_of()
    stats = {"completed_ids": set()}
    assert farm.orders(db, sid, done=0, stats=stats) == []              # не занимался — заказов нет
    db.execute("INSERT INTO activity (student_id, day, kind) VALUES (?, ?, 'game')", (sid, T0.date().isoformat()))
    db.commit()
    assert len(farm.orders(db, sid, done=0, stats=stats)) == 1          # любое занятие — первый заказ
    db.execute("INSERT INTO daily_goal (student_id, day, lessons, words, done) VALUES (?, ?, 1, 10, 1)",
               (sid, T0.date().isoformat()))
    db.commit()
    assert len(farm.orders(db, sid, done=0, stats=stats)) == 2          # цель дня — ещё один


def test_orders_daily_and_fulfil(make_student, db, clock, monkeypatch):
    make_student(); sid = sid_of()
    monkeypatch.setattr(farm, "order_slots", lambda *a, **k: 3)
    stats = {"completed_ids": {farm.NUMBERS_LESSON}}
    first = farm.orders(db, sid, done=0, stats=stats)
    assert len(first) == farm.ORDERS_PER_DAY
    assert farm.orders(db, sid, done=0, stats=stats) == first          # в тот же день новых нет
    o = first[0]
    assert o["en"].split()[0] in ("Grandma", "Tom", "Anna") and any(w in o["en"] for w in farm.NUMBERS[1:] + ["a ", "an "])
    wrong = {k: n + 1 for k, n in o["items"].items()}
    assert farm.fulfil(db, sid, o["id"], wrong) == {"ok": False, "why": "wrong"}     # без штрафа
    assert farm.fulfil(db, sid, o["id"], o["items"])["why"] == "short"               # в амбаре пусто
    for k, n in o["items"].items():
        farm._add_barn(db, sid, k, n + 1)
    db.commit()
    res = farm.fulfil(db, sid, o["id"], o["items"])
    assert res["ok"] and res["coins"] == farm.ORDER_BASE + sum(o["items"].values())
    assert all(farm.barn(db, sid).get(k) == 1 for k in o["items"])
    assert len(farm.orders(db, sid, done=0, stats=stats)) == 2         # сегодня уже было три — новых нет
    clock["now"] = T0 + timedelta(days=1)
    assert len(farm.orders(db, sid, done=0, stats=stats)) == 3         # назавтра — до трёх открытых


def test_order_numbers_digits_before_lesson(make_student, db, clock, monkeypatch):
    make_student(); sid = sid_of()
    monkeypatch.setattr(farm, "order_slots", lambda *a, **k: 3)
    o = farm.orders(db, sid, done=0, stats={"completed_ids": set()})[0]
    assert any(ch.isdigit() for ch in o["en"])
    assert farm.order_text("Grandma", {"carrot": 3, "egg": 1}, True) == "Grandma needs three carrots and an egg."
    assert farm.order_text("Tom", {"milk": 2}, True) == "Tom needs two bottles of milk."
    assert farm.order_text("Anna", {"corn": 1}, True) == "Anna needs a corn cob."


def test_week_bonus(make_student, db, clock, monkeypatch):
    make_student(); sid = sid_of()
    monkeypatch.setattr(farm, "order_slots", lambda *a, **k: 3)
    from garden import get_garden
    get_garden(db, sid)
    stats = {"completed_ids": set()}
    bonuses = []
    for day in range(5):
        clock["now"] = T0 + timedelta(days=day)
        for o in farm.orders(db, sid, done=0, stats=stats):
            for k, n in o["items"].items():
                farm._add_barn(db, sid, k, n)
            db.commit()
            bonuses.append(farm.fulfil(db, sid, o["id"], o["items"])["bonus"])
    assert bonuses.count(farm.WEEK_COINS) == 1 and bonuses[farm.WEEK_GOAL - 1] == farm.WEEK_COINS


def test_buy_extra_plots(make_student, db):
    make_student(); sid = sid_of()
    from garden import get_garden
    get_garden(db, sid)
    assert not farm.buy_plot(db, sid)[0]                      # монеток нет
    db.execute("UPDATE garden SET coins=1000 WHERE student_id=?", (sid,)); db.commit()
    for _ in farm.PLOT_COSTS:
        assert farm.buy_plot(db, sid)[0]
    assert not farm.buy_plot(db, sid)[0]
    assert farm.plots_count(db, sid) == farm.PLOTS + len(farm.PLOT_COSTS)
    assert db.execute("SELECT coins FROM garden WHERE student_id=?", (sid,)).fetchone()[0] == 1000 - sum(farm.PLOT_COSTS)
    assert farm.plant(db, sid, farm.PLOTS + 2, "carrot", done=0)[0]


def test_time_words():
    assert farm.time_words((T0 + timedelta(minutes=3)).isoformat(), T0) == "через 3 минуты"
    assert farm.time_words((T0 + timedelta(hours=5)).isoformat(), T0) == "через 5 часов"
    assert farm.time_words((T0 + timedelta(hours=22)).isoformat(), T0) == "завтра утром"
    assert farm.time_words(T0.isoformat(), T0) == "готово!"


def test_delete_student_clears_farm(make_student, parent, db):
    make_student(); sid = sid_of()
    farm.give(db, sid, "lesson", 1, 12)
    farm.plant(db, sid, 0, "carrot", done=0)
    parent.post(f"/parent/students/{sid}/delete")
    for t in ("farm_drops", "farm_plots", "farm_barn", "farm_animals", "farm_orders"):
        assert db.execute(f"SELECT COUNT(*) FROM {t} WHERE student_id=?", (sid,)).fetchone()[0] == 0
