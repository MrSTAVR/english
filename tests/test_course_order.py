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
    assert pos[44] < pos[15]                    # прилагательные (happy, sad, big) — до отрицаний to be
    assert pos[21] < pos[40] and pos[5] < pos[43]   # have got — после частей тела; исключения — после правила -s
    assert LESSONS[-1]["id"] == 60               # курс заканчивается «В гостях» (финал настоящего — 32 — раньше)


def test_soft_pass_mark_for_dry_lessons(parent, make_student):
    from curriculum import pass_mark
    assert pass_mark(LESSONS_BY_ID[1]) == 60 and pass_mark(LESSONS_BY_ID[33]) == 60
    from curriculum import SOFT_PASS_IDS
    plain = next(l for l in LESSONS if not l.get("scene") and l["id"] not in SOFT_PASS_IDS)  # обычный урок без сцены
    assert pass_mark(plain) == 70 and pass_mark(LESSONS_BY_ID[10001]) == 70
    c = make_student()
    parent.post("/parent/students/1/credit", data={"upto": "1", "action": "add"})   # урок 1 — второй в курсе
    html = c.get("/lesson/1").get_data(as_text=True)
    assert "нужно 60%" in html                            # урок 1 — сцена-история


def _partial(client, lid, n_right):
    """Сдаёт тест, где верны только первые n_right ответов; возвращает html результата."""
    from tests.helpers import attempt_id_from, correct_fields, wrong_fields
    html = client.get(f"/lesson/{lid}").get_data(as_text=True)
    form = {"attempt_id": attempt_id_from(html), "seconds": 600}
    for i, q in enumerate(LESSONS_BY_ID[lid]["test"]):
        form.update((correct_fields if i < n_right else wrong_fields)(q, i))
    return client.post(f"/lesson/{lid}/submit", data=form).get_data(as_text=True)


def test_score_between_60_and_70_passes_only_on_soft_lessons(parent, make_student):
    c = make_student()
    parent.post("/parent/students/1/credit", data={"upto": "2", "action": "add"})   # открыт «Алфавит A–I» (33)
    n = len(LESSONS_BY_ID[33]["test"])
    right = next(k for k in range(n + 1) if 60 <= 100 * k / n < 70)
    assert "fix=" not in _partial(c, 33, right)                    # нет кнопки «Исправь ошибки» (фраза бывает в подписи версии); алфавит: порог 60% — сдан
    assert db_scalar("SELECT passed FROM attempts ORDER BY id DESC LIMIT 1") == 1
    from curriculum import LESSONS, SOFT_PASS_IDS
    lid = next(l["id"] for l in LESSONS if not l.get("scene") and l["id"] not in SOFT_PASS_IDS)
    parent.post("/parent/students/1/credit", data={"upto": str(LESSONS.index(LESSONS_BY_ID[lid])), "action": "add"})
    n2 = len(LESSONS_BY_ID[lid]["test"])
    html = _partial(c, lid, next(k for k in range(n2 + 1) if 60 <= 100 * k / n2 < 70))   # обычный урок: 60–70% — мало
    assert "Нужно 70%" in html


def test_order_keeps_dependencies():
    """Порядок по ревизии методиста: урок не требует того, что объясняется позже."""
    from data.course import ISLANDS, ORDER
    pos = {lid: i for i, lid in enumerate(ORDER)}
    for chain in ([14, 15, 18, 31], [12, 26], [44, 26], [19, 20, 46], [20, 51], [22, 23, 47, 55], [25, 26, 31],
                  [25, 30], [10, 11, 38, 49], [21, 40, 43], [50, 56], [44, 54], [52, 53, 59, 60], [25, 58],
                  [24, 48], [28, 50]):
        assert [pos[x] for x in chain] == sorted(pos[x] for x in chain), chain
    assert ORDER[-1] == 60 and pos[32] < pos[52]            # «Большой финал» настоящего — до прошедшего времени
    # остров 4 расширен до 12 уроков (кухня и рецепт пиццы) — решение владельца 31.10.2026
    assert all(len(ids) <= 12 for _, ids in ISLANDS)
    assert len(ISLANDS[3][1]) == 12


def test_children_progress_stays_in_first_island():
    """Сданное детьми (Маша: 1, 2, 3, 4, 9, 10, 33, 34) — на первом острове: иначе откроется всё перед ним."""
    from data.course import ISLANDS
    assert {1, 2, 3, 4, 9, 10, 33, 34, 12} == set(ISLANDS[0][1])


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
