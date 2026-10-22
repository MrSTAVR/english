# -*- coding: utf-8 -*-
"""Ошибки в тестах уроков отправляют слова в повторение (коробка 0, повторить сегодня)."""
from datetime import date

import review
from curriculum import LESSONS_BY_ID
from tests.helpers import N, db_all, submit_lesson


def test_words_found_in_questions():
    results = [
        {"type": "choice", "q": "Как по-английски «синий»?", "correct_answer": "blue", "correct": False},
        {"type": "type_in", "q": "Переведи: Белый", "correct_answer": "white", "correct": False},
        {"type": "choice", "q": "Что значит «Yellow»?", "correct_answer": "жёлтый", "correct": True},   # верно — не берём
        {"type": "order", "q": "Составь: My cat is black", "correct_answer": "My cat is black", "correct": False},
    ]
    keys = review.words_in_mistakes(results, 12)
    assert "blue" in keys and "white" in keys and "yellow" not in keys and "cat" not in keys


def test_failed_test_sends_words_to_review(make_student):
    c = make_student()
    lesson = N(1)
    html = submit_lesson(c, lesson, wrong=True)
    rows = db_all("SELECT key, box, due, n_bad FROM word_review")
    assert rows, "ошибки не попали в повторение"
    assert all(box == 0 and due == date.today().isoformat() and bad >= 1 for _k, box, due, bad in rows)
    assert "отправлены в повторение" in html
    pool_keys = {w["key"] for w in review.all_words()}
    assert {k for k, *_ in rows} <= pool_keys


def test_perfect_test_sends_nothing(make_student):
    c = make_student()
    html = submit_lesson(c, N(1))
    assert db_all("SELECT * FROM word_review") == [] and "отправлены в повторение" not in html
