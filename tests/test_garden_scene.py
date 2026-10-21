# -*- coding: utf-8 -*-
"""SVG-сцена сада: чистые функции, без БД и Flask."""
import re
import xml.etree.ElementTree as ET

import pytest

import garden
import garden_scene as gs

BAD = re.compile(r"\bNone\b|\bnan\b|\binf\b|\d[eE][+-]\d")
KEYS = [d["key"] for d in garden.DECORATIONS]


def valid(svg):
    s = str(svg)
    assert not BAD.search(s), BAD.search(s).group()
    ET.fromstring(s)                      # корректный XML (нет дублей атрибутов и т. п.)


@pytest.mark.parametrize("day", range(0, 31))
def test_scene_and_mini_tree_valid_every_day(day):
    valid(gs.render_scene(day))
    valid(gs.tree_mini_svg(day))


@pytest.mark.parametrize("key", KEYS)
def test_each_decoration_renders_and_changes_scene(key):
    for day in (0, 12, 30):
        valid(gs.render_scene(day, [key]))
    valid(gs.render_scene(12, [key], thumb=True))
    assert str(gs.render_scene(12, [key])) != str(gs.render_scene(12))


def test_all_decorations_together():
    valid(gs.render_scene(30, KEYS))


def test_every_day_looks_different_from_the_previous_one():
    prev = str(gs.render_scene(0))
    for day in range(1, 31):
        cur = str(gs.render_scene(day))
        assert cur != prev, f"день {day} не отличается от предыдущего"
        prev = cur


def test_one_unique_find_per_day():
    assert [x["day"] for x in gs.FINDS] == list(range(1, 31))
    assert len({x["title"] for x in gs.FINDS}) == 30


def test_tree_births_match_garden_rules():
    assert [b for b, *_ in gs.EXTRA_TREES] == sorted(garden.TREES_EVERY)
    for day in range(0, 31):
        born = sum(1 for b, *_ in gs.EXTRA_TREES if day >= b)
        assert 1 + born == garden.tree_count_for(day), day


def test_growth_is_fast_at_start_and_reaches_one():
    assert gs.growth(0) == 0
    assert abs(gs.growth(30) - 1) < 1e-9
    assert gs.growth(5) > 0.35                    # линейный рост дал бы 0.17
    vals = [gs.growth(d) for d in range(31)]
    assert vals == sorted(vals)


def test_todays_find_is_highlighted_only_on_that_day():
    assert str(gs.render_scene(7)).count('class="g-new"') == 1
    assert "g-new" not in str(gs.render_scene(7, thumb=True))
    assert "g-new" not in str(gs.render_scene(0))


def test_theme_changes_sky_and_last_theme_wins():
    assert "#1B2A5E" in str(gs.render_scene(5, ["night"]))
    assert "#FFB56B" in str(gs.render_scene(5, ["night", "sunset"]))
    assert "#1B2A5E" not in str(gs.render_scene(5, ["night", "sunset"]))


def test_decoration_catalog_is_consistent():
    assert len(KEYS) == len(set(KEYS)) == 15
    assert {d["category"] for d in garden.DECORATIONS} == {"span", "sky", "effect", "theme"}
    assert "rainbow" not in KEYS                   # радуга теперь находка 21-го дня
