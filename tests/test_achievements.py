# -*- coding: utf-8 -*-
"""Награды: каталог, медали, страница коллекции, новые условия."""
import re

from achievements import ACHIEVEMENTS, BY_KEY, CATEGORIES, progress, public, tier_counts
from badges import TIERS, badge_svg, medal
from tests.helpers import N, db_all, submit_lesson


def earned_keys():
    return {r[0] for r in db_all("SELECT key FROM achievements")}


def test_catalog_is_consistent():
    keys = [a["key"] for a in ACHIEVEMENTS]
    assert len(keys) == len(set(keys)) >= 30
    cats = {k for k, _, _ in CATEGORIES}
    for a in ACHIEVEMENTS:
        assert a["tier"] in TIERS and a["cat"] in cats
        assert a["emoji"] and a["title"] and a["desc"]
        assert (a["metric"] and a["goal"]) or a["check"], a["key"]
    assert {t: 1 for t in TIERS} == {t: 1 for t in {a["tier"] for a in ACHIEVEMENTS}}   # есть все уровни


def test_old_keys_kept_for_existing_databases():
    for k in ("first_lesson", "three_lessons", "all_lessons", "perfect_test", "streak5", "clean_three", "words50",
              "time60", "five_lessons", "half_way", "streak10", "words100", "attempts5", "time180", "diamond",
              "first_try_perfect"):
        assert k in BY_KEY


def test_badge_svg_outline_icon_palette_and_locked_variant():
    a, b = badge_svg("book", "gold"), badge_svg("book", "gold")
    ids = re.findall(r'id="([^"]+)"', a) + re.findall(r'id="([^"]+)"', b)
    assert len(ids) == len(set(ids))                       # clipPath не пересекаются между медалями
    assert 'href="#o-book"' in a and "Gradient" not in a   # контурный значок, плоские цвета
    locked = badge_svg("book", "gold", locked=True)
    assert 'href="#o-lock"' in locked and "#o-book" not in locked
    html = str(medal({"emoji": "🏆", "cat": "lessons", "tier": "legend", "earned": False}, 80))
    assert "is-locked" in html and "--s:80px" in html and "🏆" not in html
    assert 'href="#o-book"' in str(medal({"cat": "lessons", "tier": "bronze", "earned": True}))
    from badges import CAT_ICONS
    from achievements import CATEGORIES
    sprite = open("templates/base.html", encoding="utf-8").read()
    for k, _n, _e in CATEGORIES:                           # у каждой категории есть значок в спрайте
        assert f'id="o-{CAT_ICONS[k]}"' in sprite


def test_progress_values():
    s = {"lessons_completed": 2}
    assert progress(BY_KEY["three_lessons"], s) == (2, 3, 67)
    assert progress(BY_KEY["comeback"], {}) is None
    assert progress(BY_KEY["first_lesson"], {"lessons_completed": 9}) == (1, 1, 100)


def test_public_payload_for_ceremony():
    p = public(BY_KEY["all_lessons"])
    assert p["tier"] == "legend" and p["tierName"] == "Легендарная" and p["svg"].startswith("<svg")


def test_collection_page(make_student):
    c = make_student()
    html = c.get("/student/achievements").get_data(as_text=True)
    assert "Мои награды" in html and "0</b>" in html
    assert html.count("ach-card ") >= len([a for a in ACHIEVEMENTS if a["cat"] != "castle"])   # замок — только архив полученных
    assert "Архив" not in html
    assert '"page": "achievements"' in html
    submit_lesson(c, N(1))
    html = c.get("/student/achievements").get_data(as_text=True)
    assert "is-earned" in html and "получено" in html


def test_new_achievements_payload_on_result_page(make_student):
    c = make_student()
    body = submit_lesson(c, N(1))
    assert '"tierName"' in body and '"svg"' in body          # данные для анимации вручения
    assert "Новые награды" in body


def test_comeback_and_counters(make_student):
    c = make_student()
    submit_lesson(c, N(1), wrong=True)
    assert "comeback" not in earned_keys()
    submit_lesson(c, N(1))
    assert "comeback" in earned_keys()
    assert "first_lesson" in earned_keys()
    home = c.get("/student").get_data(as_text=True)
    assert "Мои награды" in home and "вся коллекция" in home


def test_tier_counts():
    items = [{"tier": "gold", "earned": True}, {"tier": "gold", "earned": False}, {"tier": "bronze", "earned": True}]
    tc = tier_counts(items)
    assert tc["gold"] == (1, 2) and tc["bronze"] == (1, 1) and tc["legend"] == (0, 0)
