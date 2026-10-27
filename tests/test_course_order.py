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
    assert 33 in lesson_ids_upto(3) and 33 not in lesson_ids_upto(2)


def test_all_new_lesson_pages_render_and_pass(parent, make_student):
    student = make_student()
    sid = db_scalar("SELECT id FROM students WHERE username='masha'")
    parent.post(f"/parent/students/{sid}/credit", data={"upto": "99", "action": "add"})
    for l in NEW_LESSONS:
        html = student.get(f"/lesson/{l['id']}").get_data(as_text=True)
        assert f"Урок {l['num']} из " in html
        assert "Идеально" in submit_lesson(student, l["id"]), l["id"]


def test_letters_lessons_use_letter_listening():
    for i in (33, 34, 35):
        l = LESSONS_BY_ID[i]
        listen = [q for q in l["practice"] if q.get("audio")]
        assert listen and all(len(q["audio"]) == 1 for q in listen)
        for q in listen:
            if q["type"] == "choice":
                assert q["options"][q["answer"]] == q["audio"]


def test_no_long_runs_of_same_kind():
    phonetics = {1, 2, 3, 4, 5, 6, 7, 8, 33, 34, 35}
    grammar = {14, 15, 22, 23, 25, 31, 40, 41, 42, 43}
    numbers = {10, 11, 38}
    for group in (phonetics, numbers, grammar):
        run = 0
        for l in LESSONS:
            run = run + 1 if l["id"] in group else 0
            assert run <= (1 if group is numbers else 2), (l["num"], l["title"])


def test_grammar_comes_after_its_vocabulary():
    pos = {l["id"]: l["num"] for l in LESSONS}
    assert pos[14] < pos[15] < pos[39]          # to be → вопросы
    assert pos[17] < pos[18]                    # животные → can
    assert pos[19] < pos[20]                    # еда → I like
    assert pos[22] < pos[23] < pos[24]          # Present Simple
    assert pos[25] < pos[31]                    # Present Continuous
    assert pos[27] < pos[28]                    # предлоги → дом
    assert pos[10] < pos[11] and pos[17] < pos[5]   # числа 1–10 → 11–20; животные → окончание -s
    assert pos[13] < pos[41] and pos[14] < pos[41]   # притяжательные — после семьи и to be
    assert pos[19] < pos[42]                    # this/that с apple, egg — после еды
    assert pos[17] < pos[44]                    # прилагательные описывают уже знакомых животных
    assert pos[21] < pos[40] and pos[5] < pos[43]   # have got — после частей тела; исключения — после правила -s
    assert LESSONS[-1]["id"] == 32               # финал — последний


def test_soft_pass_mark_for_dry_lessons(make_student):
    from curriculum import pass_mark
    assert pass_mark(LESSONS_BY_ID[1]) == 60 and pass_mark(LESSONS_BY_ID[33]) == 60
    assert pass_mark(LESSONS_BY_ID[14]) == 70 and pass_mark(LESSONS_BY_ID[10001]) == 70
    c = make_student()
    html = c.get("/lesson/1").get_data(as_text=True)
    assert "минимум 60%" in html


def _partial(client, lid, n_right):
    """Сдаёт тест, где верны только первые n_right ответов; возвращает html результата."""
    from tests.helpers import attempt_id_from, correct_fields, wrong_fields
    html = client.get(f"/lesson/{lid}").get_data(as_text=True)
    form = {"attempt_id": attempt_id_from(html), "seconds": 600}
    for i, q in enumerate(LESSONS_BY_ID[lid]["test"]):
        form.update((correct_fields if i < n_right else wrong_fields)(q, i))
    return client.post(f"/lesson/{lid}/submit", data=form).get_data(as_text=True)


def test_score_between_60_and_70_passes_only_on_soft_lessons(make_student):
    c = make_student()
    n = len(LESSONS_BY_ID[1]["test"])
    right = -(-n * 62 // 100)                      # ≈62%
    assert 60 <= 100 * right / n < 70
    assert "Пройти тест ещё раз" not in _partial(c, 1, right)          # урок 1: порог 60% — сдан
    assert db_scalar("SELECT passed FROM attempts ORDER BY id DESC LIMIT 1") == 1
    n2 = len(LESSONS_BY_ID[9]["test"])
    html = _partial(c, 9, -(-n2 * 62 // 100))                     # обычный урок: 62% — мало
    assert "Нужно 70%" in html


def test_new_topic_lessons_are_placed_sensibly():
    from data.course import ORDER
    pos = {lid: i for i, lid in enumerate(ORDER)}
    assert all(i in pos for i in range(45, 52))
    assert ORDER[-1] == 32                                  # финал остаётся последним
    assert pos[16] < pos[45]                                # вежливость — после простых команд
    assert pos[19] < pos[51] and pos[45] < pos[51]          # кафе — после еды и вежливых слов
    assert pos[24] < pos[48]                                # время — после «Моего дня»
    assert pos[26] < pos[49] and pos[38] < pos[49]          # покупки — после одежды и чисел до 100
    assert pos[28] < pos[50]                                # город — после дома


def test_new_topic_lessons_have_dialogs():
    from curriculum import LESSONS_BY_ID
    for lid in range(45, 52):
        assert LESSONS_BY_ID[lid]["dialogs"], lid


def test_new_topic_lessons_can_be_passed(parent, make_student):
    import re
    from tests.helpers import db_scalar, submit_lesson
    c = make_student()
    sid = db_scalar("SELECT id FROM students WHERE username='masha'")
    parent.post(f"/parent/students/{sid}/credit", data={"upto": "10", "action": "add"})
    from curriculum import LESSONS_BY_ID
    for lid in range(45, 52):
        num = LESSONS_BY_ID[lid]["num"]
        parent.post(f"/parent/students/{sid}/credit", data={"upto": str(num - 1), "action": "add"})
        html = submit_lesson(c, lid)
        assert db_scalar("SELECT passed FROM attempts WHERE lesson_id=? AND manual=0", (lid,)) == 1, (lid, re.sub("<[^>]+>", " ", html)[:300])
