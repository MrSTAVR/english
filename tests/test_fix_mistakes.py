# -*- coding: utf-8 -*-
"""Тест урока: короче, без лишнего письма по памяти; «Исправь ошибки» — заново только неверные вопросы."""
import re

from curriculum import LESSONS, LESSONS_BY_ID
from practice import MAX_WRITE
from tests.helpers import build_form, correct_fields, db_scalar, open_lesson, wrong_fields

CYR = re.compile("[а-яё]", re.I)


def test_tests_are_short_and_ask_little_writing():
    for l in LESSONS:
        assert len(l["test"]) <= 10, l["id"]
    colors = LESSONS_BY_ID[12]                       # «Цвета» — тут Маша застряла (было 11 вопросов, 5 «напиши»)
    write = [q for q in colors["test"] if q["type"] == "type_in" and not CYR.search(str(q["answer"]))]
    assert len(colors["test"]) <= 9 and len(write) <= MAX_WRITE
    assert not any(q.get("audio") and q["type"] == "type_in" for q in colors["test"])   # диктант — в тренировке


def _fail_half(lesson, aid):
    """Половина вопросов верно, половина — нет. Возвращает форму и номера неверных."""
    form = {"attempt_id": aid, "seconds": 300}
    wrong = set()
    for i, q in enumerate(lesson["test"]):
        if i % 2:
            form.update(wrong_fields(q, i)); wrong.add(i)
        else:
            form.update(correct_fields(q, i))
    return form, wrong


def test_fix_mistakes_asks_only_wrong_questions(parent, make_student):
    c = make_student()
    parent.post("/parent/students/1/credit", data={"upto": "60", "action": "add"})
    l = next(x for x in LESSONS if not x.get("scene"))      # обычный тест (сцены — tests/test_scenes.py)
    aid = open_lesson(c, l["id"])
    form, wrong = _fail_half(l, aid)
    body = c.post(f"/lesson/{l['id']}/submit", data=form).get_data(as_text=True)
    assert f"fix={aid}" in body and "Исправь ошибки" in body
    page = c.get(f"/lesson/{l['id']}?step=test&fix={aid}").get_data(as_text=True)
    assert page.count("hidden fix-done") == len(l["test"]) - len(wrong) and f'name="fix_from" value="{aid}"' in page
    new_aid = int(re.search(r'name="attempt_id" value="(\d+)"', page).group(1))
    fix = {"attempt_id": new_aid, "seconds": 60, "fix_from": aid}
    for i in wrong:                                     # отвечаем только на прошлые ошибки — и верно
        fix.update(correct_fields(l["test"][i], i))
    c.post(f"/lesson/{l['id']}/submit", data=fix)
    assert db_scalar("SELECT passed FROM attempts WHERE id=?", (new_aid,)) == 1


def test_fix_from_other_or_passed_attempt_is_ignored(parent, make_student):
    c = make_student()
    parent.post("/parent/students/1/credit", data={"upto": "60", "action": "add"})
    l = next(x for x in LESSONS if not x.get("scene"))      # обычный тест (сцены — tests/test_scenes.py)
    aid = open_lesson(c, l["id"])
    c.post(f"/lesson/{l['id']}/submit", data=build_form(l, aid))       # сдан — исправлять нечего
    page = c.get(f"/lesson/{l['id']}?step=test&fix={aid}").get_data(as_text=True)
    assert "hidden fix-done" not in page and 'name="fix_from"' not in page
    assert "hidden fix-done" not in c.get(f"/lesson/{l['id']}?step=test&fix=999").get_data(as_text=True)
