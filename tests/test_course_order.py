# -*- coding: utf-8 -*-
"""Порядок курса отдельно от id и новые уроки (алфавит, дни, месяцы, числа, вопросы)."""
from curriculum import LESSONS, LESSONS_BY_ID, unlocked_lesson_ids, validate_lessons
from data.course import ORDER
from data.new_lessons import NEW_LESSONS
from progress import lesson_ids_upto
from tests.helpers import db_scalar, submit_lesson


def test_order_is_permutation_and_numbered():
    assert len(set(ORDER)) == len(ORDER)
    assert [l["id"] for l in LESSONS] == ORDER
    assert [l["num"] for l in LESSONS] == list(range(1, len(ORDER) + 1))
    assert validate_lessons() == []


def test_new_lessons_have_unique_ids_and_full_content():
    ids = [l["id"] for l in NEW_LESSONS]
    assert len(ids) == len(set(ids)) and min(ids) >= 33
    for l in NEW_LESSONS:
        assert l["theory"]["blocks"] and len(l["material"]) >= 8
        assert len(l["exercises"]) >= 3 and len(l["test"]) >= 6
        assert any(q.get("audio") for q in l["test"])      # аудирование добавлено автоматически


def test_fresh_student_has_only_first_lesson_open():
    stats = {"completed_ids": set()}
    assert unlocked_lesson_ids(stats) & {l["id"] for l in LESSONS} == {LESSONS[0]["id"]}


def test_unlock_follows_course_order_not_id():
    stats = {"completed_ids": {LESSONS[0]["id"]}}
    opened = unlocked_lesson_ids(stats)
    assert LESSONS[1]["id"] in opened and LESSONS[2]["id"] not in opened


def test_progress_is_not_lost_when_new_lessons_are_inserted():
    # ребёнок уже прошёл старый урок 5 (раньше новых уроков в порядке не было) —
    # всё, что стоит перед ним, остаётся доступным
    stats = {"completed_ids": {5}}
    opened = unlocked_lesson_ids(stats)
    before = [l["id"] for l in LESSONS[:[l["id"] for l in LESSONS].index(5) + 2]]
    assert set(before) <= opened


def test_credit_upto_uses_course_order():
    assert lesson_ids_upto(3) == {l["id"] for l in LESSONS[:3]}
    assert 33 in lesson_ids_upto(2)


def test_all_new_lesson_pages_render_and_pass(parent, make_student):
    student = make_student()
    sid = db_scalar("SELECT id FROM students WHERE username='masha'")
    parent.post(f"/parent/students/{sid}/credit", data={"upto": "99", "action": "add"})
    for l in NEW_LESSONS:
        html = student.get(f"/lesson/{l['id']}").get_data(as_text=True)
        assert f"Урок {l['num']}: " in html
        assert "Идеально" in submit_lesson(student, l["id"]), l["id"]


def test_letters_lessons_use_letter_listening():
    for i in (33, 34, 35):
        l = LESSONS_BY_ID[i]
        listen = [q for q in l["practice"] if q.get("audio")]
        assert listen and all(len(q["audio"]) == 1 for q in listen)
        for q in listen:
            if q["type"] == "choice":
                assert q["options"][q["answer"]] == q["audio"]
