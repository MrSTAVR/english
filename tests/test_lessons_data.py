# -*- coding: utf-8 -*-
from curriculum import ALL_LESSONS, LESSONS_BY_ID, validate_lessons
from data.extra_lessons import EXTRA_LESSONS
from data.lessons import LESSONS


def test_lessons_pass_validation():
    assert validate_lessons() == []


def test_lesson_ids_unique_and_main_are_sequential():
    ids = [l["id"] for l in ALL_LESSONS]
    assert len(ids) == len(set(ids))
    assert [l["id"] for l in LESSONS] == list(range(1, len(LESSONS) + 1))


def test_extra_lessons_flagged_and_separate():
    assert all(l.get("is_extra") for l in EXTRA_LESSONS)
    assert not any(l.get("is_extra") for l in LESSONS)
    assert all(l["id"] > len(LESSONS) for l in EXTRA_LESSONS)


def test_every_lesson_has_material_and_test():
    for l in ALL_LESSONS:
        assert l["material"], l["id"]
        assert l["test"], l["id"]
        assert LESSONS_BY_ID[l["id"]] is l
