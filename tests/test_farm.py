# -*- coding: utf-8 -*-
"""Ферма: капли только за учёбу, грядки и животные по времени, амбар, заказы героев (farm.py)."""
import json
import pathlib
import re
import sqlite3
from datetime import datetime, timedelta

import pytest

import database
import farm
from curriculum import LESSONS
from tests.helpers import correct_fields, open_lesson, wrong_fields
from tests.test_vacation import sid_of

T0 = datetime(2026, 11, 2, 10, 0)      # понедельник
ROOT = pathlib.Path(__file__).resolve().parent.parent      # тесты не зависят от текущего каталога
FARM = ROOT / "static" / "farm"


def glb_json(name):
    """JSON-чанк файла GLB: материалы и атрибуты мешей без three.js."""
    data = (FARM / f"{name}.glb").read_bytes()
    length = int.from_bytes(data[12:16], "little")
    return json.loads(data[20:20 + length])


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
    ok, _ = farm.plant(db, sid, 0, "carrot", stats={"completed_ids": set()})
    assert ok and not farm.plant(db, sid, 0, "tomato", stats={"completed_ids": set()})[0]      # грядка занята
    assert not farm.water(db, sid, 0)[0]                      # капель нет — полить нечем
    farm.give(db, sid, "lesson", 1, 12)
    assert farm.water(db, sid, 0)[0] and farm.drops(db, sid) == 12 - farm.WATER_COST
    assert not farm.water(db, sid, 0)[0]                      # уже полито
    assert farm.harvest(db, sid, 0) == (False, 0)             # ещё растёт
    clock["now"] = T0 + timedelta(days=30)                    # урожай не вянет
    assert farm.harvest(db, sid, 0) == (True, 3)
    assert farm.barn(db, sid) == {"carrot": 3}
    assert farm.plant(db, sid, 0, "tomato", stats={"completed_ids": set()})[0]        # грядка снова свободна


def test_seeds_open_with_lessons(make_student, db):
    make_student(); sid = sid_of()
    assert not farm.plant(db, sid, 1, "potato", stats={"completed_ids": set()})[0]
    assert farm.plant(db, sid, 1, "potato", stats={"completed_ids": {farm.WORDS_LESSON}})[0]
    assert not farm.plant(db, sid, 9, "carrot", stats={"completed_ids": set()})[0]    # грядок шесть


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
    stats = {"completed_ids": {farm.NUMBERS_LESSON, farm.WORDS_LESSON, farm.ANIMALS_LESSON}}
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
    assert res["ok"] and res["coins"] == farm.order_coins(o["items"])
    assert all(farm.barn(db, sid).get(k) == 1 for k in o["items"])
    assert len(farm.orders(db, sid, done=0, stats=stats)) == 2         # сегодня уже было три — новых нет
    clock["now"] = T0 + timedelta(days=1)
    assert len(farm.orders(db, sid, done=0, stats=stats)) == 3         # назавтра — до трёх открытых


def test_order_text_numbers_and_words(make_student, db, clock, monkeypatch):
    make_student(); sid = sid_of()
    monkeypatch.setattr(farm, "order_slots", lambda *a, **k: 3)
    o = farm.orders(db, sid, done=0, stats={"completed_ids": set()})[0]
    assert o["en"] == "" and not o["names"]                  # до урока 19 — только картинки и число
    assert farm.order_text("Grandma", {"carrot": 3, "egg": 1}, True) == "Grandma needs three carrots and an egg."
    assert farm.order_text("Grandma", {"carrot": 3}, False) == "Grandma needs 3 carrots."
    assert farm.order_text("Tom", {"milk": 2}, True) == "Tom needs two glasses of milk."


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
    assert farm.plant(db, sid, farm.PLOTS + 2, "carrot", stats={"completed_ids": set()})[0]


def test_time_words():
    assert farm.time_words((T0 + timedelta(minutes=3)).isoformat(), T0) == "через 3 минуты"
    assert farm.time_words((T0 + timedelta(hours=5)).isoformat(), T0) == "через 5 часов"
    assert farm.time_words((T0 + timedelta(hours=22)).isoformat(), T0) == "завтра утром"
    assert farm.time_words(T0.isoformat(), T0) == "готово!"


def test_delete_student_clears_farm(make_student, parent, db):
    make_student(); sid = sid_of()
    farm.give(db, sid, "lesson", 1, 12)
    farm.plant(db, sid, 0, "carrot", stats={"completed_ids": set()})
    parent.post(f"/parent/students/{sid}/delete")
    for t in ("farm_drops", "farm_plots", "farm_barn", "farm_animals", "farm_orders"):
        assert db.execute(f"SELECT COUNT(*) FROM {t} WHERE student_id=?", (sid,)).fetchone()[0] == 0


def test_farm_page_and_api(make_student, db, anon):
    c = make_student(); sid = sid_of()
    html = c.get("/student/farm").get_data(as_text=True)
    assert 'id="fm-data"' in html and "vendor/three/three.module.min.js" in html and "farm.js" in html
    assert anon.get("/api/farm").status_code == 403
    st = c.get("/api/farm").get_json()
    assert st["drops"] == 0 and len(st["plots"]) == farm.PLOTS and st["orders"] == []
    assert st["garden"]["days"] == 0 and st["garden"]["cap"] > 0                # сад (серия) — уголок фермы
    assert any(x["key"] == "carrot" and x["open"] for x in st["crops"])
    r = c.post("/api/farm/plant", json={"slot": 0, "crop": "carrot"}).get_json()
    assert r["ok"] and r["state"]["plots"][0]["state"] == "planted"
    r = c.post("/api/farm/water", json={"slot": 0}).get_json()
    assert not r["ok"] and "капли" in r["msg"]                          # капель нет
    farm.give(db, sid, "lesson", 1, 12)
    r = c.post("/api/farm/water", json={"slot": 0}).get_json()
    assert r["ok"] and r["state"]["plots"][0]["state"] == "growing" and r["state"]["drops"] == 12 - farm.WATER_COST
    assert c.post("/api/farm/plant", json={"slot": "x", "crop": "carrot"}).status_code == 400
    assert c.post("/api/farm/nope", json={}).status_code == 404
    assert c.post("/api/farm/order", json={"id": 1, "items": "x"}).status_code == 400
    r = c.post("/api/farm/order", json={"id": 999, "items": {}}).get_json()
    assert not r["ok"] and r["why"] == "gone"


def test_words_appear_only_after_their_lesson(make_student, db):
    """Названия культур и животных — только после урока, где слово вводится:
    до «Фруктов и овощей» ребёнок видит картинку и русское слово, а не незнакомое английское."""
    make_student(); sid = sid_of()
    st = farm.state(db, sid, {"lessons_completed": 0, "completed_ids": set()})
    crops = {c["key"]: c for c in st["crops"]}
    assert crops["carrot"]["open"] and not crops["carrot"]["known"]        # посадить можно, слово — нет
    assert not crops["potato"]["open"]                                     # картофель ждёт урок 19
    assert not st["animals"][0]["known"]                                   # курица: слово из урока 17
    assert not any(st["known"].values())                                    # в амбаре и заказах тоже молчим

    done = {"lessons_completed": 30, "completed_ids": {farm.WORDS_LESSON, farm.ANIMALS_LESSON}}
    st = farm.state(db, sid, done)
    crops = {c["key"]: c for c in st["crops"]}
    assert all(c["known"] and c["open"] for c in crops.values())
    assert all(a["known"] for a in st["animals"])
    assert all(st["known"].values())


def test_order_is_pictures_before_words_lesson(make_student, db, clock):
    """До урока 19 заказ без английского текста: картинка + число (слово ребёнок ещё не проходил)."""
    make_student(); sid = sid_of()
    db.execute("INSERT INTO activity (student_id, day, kind) VALUES (?, ?, 'game')", (sid, farm._today().isoformat()))
    db.commit()
    early = farm.orders(db, sid, stats={"completed_ids": set(), "lessons_completed": 0})
    assert early and not early[0]["en"] and early[0]["names"] is False
    assert early[0]["ru"]                                              # перевод для взрослого остаётся
    late = farm.orders(db, sid, stats={"completed_ids": {farm.WORDS_LESSON, farm.ANIMALS_LESSON}, "lessons_completed": 30})
    assert late[0]["en"] and late[0]["names"] is True


def test_farm_static_files_exist():
    for f in ("farm.js", "farm.css", "vendor/three/three.module.min.js", "vendor/three/addons/loaders/GLTFLoader.js",
              "vendor/three/addons/environments/RoomEnvironment.js", "vendor/three/addons/utils/SkeletonUtils.js",
              "vendor/three/addons/utils/BufferGeometryUtils.js"):
        assert (ROOT / "static" / f).exists(), f
    src = (ROOT / "static" / "farm.js").read_text(encoding="utf-8")
    assert "?v=${MODELS}" in src                                        # модели грузятся с версией: иначе кэш SW отдаст старые
    names = set(re.findall(r"""(?:at|put)\(\s*['"]([a-z0-9]+)['"]""", src))      # и одинарные, и двойные кавычки
    assert len(names) > 10, names                                      # разбор не «поплыл» и не вернул пустоту
    for name in names | {"carrot", "tomato", "corn", "pumpkin"}:
        assert (FARM / f"{name}.glb").exists(), name


def test_farm_models_and_credits():
    """Модели фермы: курица из Everything Library (CC BY 4.0, статичная), декор из Nature Pack (CC0)."""
    lic = (FARM / "LICENSE.txt").read_text(encoding="utf-8")
    assert "Quaternius" in lic and "CC0" in lic
    assert "David O'Reilly" in lic and "CC BY 4.0" in lic               # атрибуция обязательна
    for name in ("hen", "oak1", "birch1", "fruittree", "rock1", "rock2", "rock3", "grass1", "grass2", "wheat1", "stump1", "log1", "bush4", "berries1", "pine1"):
        assert (FARM / f"{name}.glb").stat().st_size > 5000, name
    for gone in ("tree2", "tree3", "tree4", "chicken"):
        assert not (FARM / f"{gone}.glb").exists(), gone                # подменённые модели живут по новому адресу (кэш SW)
    hen = glb_json("hen")
    assert any("COLOR_0" in p["attributes"] for m in hen["meshes"] for p in m["primitives"])
    assert "animations" not in hen                                     # скелета нет: ходит покачиванием (farm.js)


def test_vertex_colors_only_for_converter_red():
    """Цвет курицы лежит в вершинах, а материал конвертер оставил красным [1,0,0];
    у коровы COLOR_0 тоже есть, но цвета (белый, чёрный, розовый) заданы материалами —
    поэтому в белый красим только «красные» материалы, иначе корова становится белой."""
    red = lambda m: [round(c, 2) for c in (m.get("pbrMetallicRoughness", {}).get("baseColorFactor") or [0, 0, 0, 1])[:3]] == [1.0, 0.0, 0.0]
    hen, cow = glb_json("hen"), glb_json("cow")
    assert hen["materials"] and all(red(m) for m in hen["materials"])
    assert cow["materials"] and not any(red(m) for m in cow["materials"])
    assert any("COLOR_0" in p["attributes"] for m in cow["meshes"] for p in m["primitives"])
    src = (ROOT / "static" / "farm.js").read_text(encoding="utf-8")
    assert "vertexColors" in src and "COLOR_0" in src


def test_decor_does_not_stand_on_plots():
    """Грядки 7–9 покупаются позже, а декор ставится сразу: камень или трава посреди будущей грядки
    вырастали бы из земли вместе с урожаем (найдено критиками 30.10.2026)."""
    src = (ROOT / "static" / "farm.js").read_text(encoding="utf-8")
    bed = float(re.search(r"const BED = ([\d.]+)", src).group(1))
    bx, bz = 3.2 / 2 ** .5, 3.2 / 2 ** .5                              # W(0, 3.2) — центр сетки грядок
    step = bed + .35
    plots = [(bx + (i % 3 - 1) * step, bz + (i // 3 - .5) * step) for i in range(9)]
    decor = re.findall(r"""at\(\s*['"](rock\d|grass\d|stump1|log1|wheat1|berries1|bush4|hay)['"],\s*(-?[\d.]+),\s*(-?[\d.]+)""", src)
    assert len(decor) > 8, decor
    for name, u, v in decor:
        u, v = float(u) * .72, float(v)
        x, z = (v + u) / 2 ** .5, (v - u) / 2 ** .5
        for px, pz in plots:
            assert ((x - px) ** 2 + (z - pz) ** 2) ** .5 > bed / 2 + .4, f"{name} стоит на грядке {plots.index((px, pz)) + 1}"


def test_move_from_castle_refunds_once(make_student, db):
    import castle
    c = make_student(); sid = sid_of()
    castle.ensure(db, sid, ())
    from garden import get_garden
    get_garden(db, sid)
    db.execute("UPDATE garden SET coins=0 WHERE student_id=?", (sid,))
    db.execute("UPDATE castle_rooms SET level=3 WHERE student_id=? AND room='bedroom'", (sid,))   # спальня 1→3: 40 + 60
    db.execute("INSERT INTO castle_rooms (student_id, room, level, at) VALUES (?, 'kitchen', 1, 'x')", (sid,))  # кухня: 20
    castle.earn(db, sid, "test", 7, 7)                                  # 7 кирпичиков → 14 монеток
    db.commit()
    html = c.get("/student/farm").get_data(as_text=True)
    want = castle.COST[2][1] + castle.COST[3][1] + castle.COST[1][1] + 7 * farm.BRICK_COINS
    assert db.execute("SELECT coins FROM garden WHERE student_id=?", (sid,)).fetchone()[0] == want
    assert "переехал на ферму" in html and f"+{want}" in html
    html = c.get("/student/farm").get_data(as_text=True)                # второй раз — без возврата и плашки
    assert "переехал на ферму" not in html
    assert db.execute("SELECT coins FROM garden WHERE student_id=?", (sid,)).fetchone()[0] == want


def test_new_student_has_no_move_note(make_student, db):
    c = make_student(); sid = sid_of()
    assert "переехал на ферму" not in c.get("/student/farm").get_data(as_text=True)
    assert db.execute("SELECT coins FROM farm_moves WHERE student_id=?", (sid,)).fetchone()[0] == 0


def test_lesson_shows_drops_not_bricks(make_student, db):
    c = make_student()
    l = LESSONS[0]
    aid = open_lesson(c, l["id"])
    form = {"attempt_id": aid, "seconds": 300}
    for i, q in enumerate(l["test"]):
        form.update(correct_fields(q, i))
    html = c.post(f"/lesson/{l['id']}/submit", data=form).get_data(as_text=True)
    assert "Капли для фермы" in html and "Кирпичики" not in html


def test_castle_awards_archived(make_student, db):
    from achievements import ACHIEVEMENTS, views
    c = make_student(); sid = sid_of()
    assert not any(v["cat"] == "castle" for v in views(db, _stats(db, sid), sid))
    db.execute("INSERT INTO achievements (student_id, key, earned_at) VALUES (?, 'house_1', '2026-01-01')", (sid,)); db.commit()
    html = c.get("/student/achievements").get_data(as_text=True)
    assert "Архив" in html and "Новоселье" in html
    assert any(a["cat"] == "castle" for a in ACHIEVEMENTS)


def _stats(db, sid):
    from stats import compute_stats
    return compute_stats(db, sid)


def test_admin_sets_drops(parent, make_student, db):
    make_student(); sid = sid_of()
    farm.give(db, sid, "lesson", 1, 7)
    assert "капель <b>7</b>" in parent.get(f"/parent/students/{sid}").get_data(as_text=True)
    parent.post(f"/parent/students/{sid}/garden", data={"drops": "25"})
    assert farm.drops(db, sid) == 25
    parent.post(f"/parent/students/{sid}/garden", data={"drops": "3"})
    assert farm.drops(db, sid) == 3


def test_repeated_taps_do_not_pay_twice(make_student, db, clock, monkeypatch):
    make_student(); sid = sid_of()
    monkeypatch.setattr(farm, "order_slots", lambda *a, **k: 3)
    assert not farm.water(db, sid, 0)[0]
    farm.plant(db, sid, 0, "carrot", stats={"completed_ids": set()})
    assert not farm.water(db, sid, 0)[0] and farm.drops(db, sid) == 0         # капель нет — в минус не уходим
    farm.give(db, sid, "lesson", 1, 3)
    assert farm.water(db, sid, 0)[0] and not farm.water(db, sid, 0)[0] and farm.drops(db, sid) == 1
    assert not farm.feed(db, sid, "chicken")[0] and farm.drops(db, sid) == 1  # 1 капли не хватает
    clock["now"] = T0 + timedelta(days=1)
    assert farm.harvest(db, sid, 0) == (True, 3) and farm.harvest(db, sid, 0) == (False, 0)
    o = farm.orders(db, sid, done=0, stats={"completed_ids": set()})[0]
    for k, n in o["items"].items():
        farm._add_barn(db, sid, k, n)
    db.commit()
    assert farm.fulfil(db, sid, o["id"], o["items"])["ok"]
    assert farm.fulfil(db, sid, o["id"], o["items"]) == {"ok": False, "why": "gone"}


def test_harvest_all(make_student, db, clock):
    c = make_student(); sid = sid_of()
    farm.give(db, sid, "lesson", 1, 12)
    for slot, crop in ((0, "carrot"), (1, "tomato")):
        farm.plant(db, sid, slot, crop, stats={"completed_ids": set()}); farm.water(db, sid, slot)
    clock["now"] = T0 + timedelta(days=1)
    assert farm.harvest_all(db, sid) == {"carrot": 3, "tomato": 3}
    assert farm.harvest_all(db, sid) == {}


def test_order_coins_less_than_lesson():
    from garden import COIN_PASS
    assert farm.order_coins({"carrot": 3}) == 3 and farm.order_coins({"milk": 2}) == 3
    assert farm.order_coins({"carrot": 1}) <= COIN_PASS


def test_move_without_castle_returns_house_items(make_student, db):
    c = make_student(); sid = sid_of()
    from garden import get_garden
    get_garden(db, sid)
    db.execute("UPDATE garden SET coins=5 WHERE student_id=?", (sid,))
    db.execute("INSERT INTO house_items (student_id, item_key) VALUES (?, 'wall-blue')", (sid,)); db.commit()   # 15 монеток
    html = c.get("/student/farm").get_data(as_text=True)
    assert "переехал на ферму" in html and "+15" in html
    assert db.execute("SELECT coins FROM garden WHERE student_id=?", (sid,)).fetchone()[0] == 20


def test_old_castle_addresses(make_student, parent):
    c = make_student()
    for url in ("/student/castle", "/student/castle/kitchen", "/student/house"):
        assert c.get(url).status_code == 302
    assert c.post("/student/castle/kitchen/build").headers["Location"].endswith("/student/farm")
    assert c.post("/api/castle/kitchen/find").status_code == 410


def test_garden_waits_by_best_streak(make_student, db):
    make_student(); sid = sid_of()
    from garden import garden_view, get_garden
    get_garden(db, sid)
    db.execute("UPDATE garden SET streak_days=0, best_streak=12, broken=1 WHERE student_id=?", (sid,)); db.commit()
    v = garden_view(db, sid)
    assert v["stage"]["min"] > 0                                         # дерево не уменьшилось
