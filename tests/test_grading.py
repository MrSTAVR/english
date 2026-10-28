# -*- coding: utf-8 -*-
"""Юнит-тесты оценивания — страховка перед выносом в grading.py."""
from grading import grade_question, norm_answer


def test_norm_answer():
    assert norm_answer("  Hello,   World! ") == "hello world"          # знаки внутри фразы не важны
    assert norm_answer("don’t") == norm_answer("do not") == "do not"              # сокращение = полная форма
    assert norm_answer("He's not my brother") == "he is not my brother" and norm_answer("Tom's dog") == "tom's dog"
    assert norm_answer(None) == ""


def test_choice():
    q = {"type": "choice", "options": ["a", "b", "c"], "answer": 1}
    assert grade_question(q, "1") == (True, "b")
    assert grade_question(q, 1)[0] is True
    assert grade_question(q, "0")[0] is False
    assert grade_question(q, -1)[0] is False
    assert grade_question(q, "junk")[0] is False


def test_type_in_with_accept():
    q = {"type": "type_in", "answer": "кот", "accept": ["кошка"]}
    assert grade_question(q, " Кот. ")[0] is True
    assert grade_question(q, "кошка")[0] is True
    assert grade_question(q, "пёс")[0] is False


def test_order_ignores_case_and_edge_punctuation():
    q = {"type": "order", "answer": "My name is Alex"}
    assert grade_question(q, "my name is alex.")[0] is True
    assert grade_question(q, "name my is Alex")[0] is False


def test_match_column_format():
    q = {"type": "match", "left": ["a", "b"], "right": ["B", "A"], "pairs": {0: 1, 1: 0}}
    assert grade_question(q, "0:1,1:0")[0] is True
    assert grade_question(q, "0:0,1:1")[0] is False
    assert grade_question(q, "0:1")[0] is False   # неполный ответ


def test_match_pairs_format():
    q = {"type": "match", "pairs": [["cat", "кошка"], ["dog", "собака"]]}
    assert grade_question(q, "0:0,1:1")[0] is True
    assert grade_question(q, "0:1,1:0")[0] is False


def test_sort():
    q = {"type": "sort",
         "categories": [{"id": "a", "title": "A"}, {"id": "b", "title": "B"}],
         "words": ["x|a", "y|b", "z|a"]}
    assert grade_question(q, "x|a;y|b;z|a")[0] is True
    assert grade_question(q, "z|a;x|a;y|b")[0] is True     # порядок не важен
    assert grade_question(q, "x|b;y|a;z|a")[0] is False


def test_backtick_is_apostrophe():
    assert norm_answer("masha`s cat") == norm_answer("Masha's cat") == "masha's cat"


def test_extra_article_is_ok_only_when_answer_has_none():
    """Урок про a/an учит «an egg» — лишний артикль в ответе без артикля не ошибка, но и не наоборот."""
    assert grade_question({"type": "type_in", "answer": "egg"}, "an egg")[0]
    assert grade_question({"type": "type_in", "answer": "bread"}, "some bread")[0]
    assert not grade_question({"type": "type_in", "answer": "an apple"}, "apple")[0]
    assert not grade_question({"type": "type_in", "answer": "egg"}, "an")[0]
