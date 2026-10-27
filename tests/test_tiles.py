# -*- coding: utf-8 -*-
"""Буквы-плитки и прощение опечаток в заданиях «напиши по-английски»."""
import re

from curriculum import LESSONS, LESSONS_BY_ID
from grading import near_answer, near_miss
from template_filters import TILES_UPTO, letter_tiles
from tests.helpers import build_form, open_lesson


def test_near_miss():
    q = {"answer": "eight"}
    assert near_miss(q, "eigth") and near_miss(q, "Eght")
    assert not near_miss(q, "eight") and not near_miss(q, "Frcfhe") and not near_miss(q, "")
    assert not near_miss({"answer": "one"}, "onw")                      # короткие слова — без поблажек
    assert near_miss({"answer": "good morning"}, "Good mornign")
    assert near_miss({"answer": "Hi", "accept": ["hello!"]}, "hellp")
    assert not near_miss({"answer": "Hi", "accept": ["hello"]}, "helo")   # пропущена удвоенная буква — так и учим писать


def test_near_miss_is_not_grammar_or_other_word():
    """Опечатка — не другое слово, не другая форма и не грамматика урока."""
    for given, expected in [("he like bananas", "he likes bananas"), ("they swims well", "they swim well"),
                            ("sock", "socks"), ("watches", "watched"), ("childrens", "children"),
                            ("runing", "running"), ("then", "than"), ("fourty", "forty"), ("wrote", "write"),
                            ("grandfather", "grandmother"), ("nife", "knife"), ("she is not my brother", "he is not my brother"),
                            ("правильный", "неправильный"), ("ручка", "ручки"), ("my name is marya", "my name is masha")]:
        assert not near_answer(given, expected), (given, expected)
    for given, expected in [("eigth", "eight"), ("sevex", "seven"), ("goodbey", "goodbye"), ("purpel", "purple")]:
        assert near_answer(given, expected), (given, expected)


def test_letter_tiles_word_and_phrase():
    t = letter_tiles({"answer": "Four"})
    assert len(t["t"]) == 6 and set("four") <= set(t["t"])
    assert t["m"] == "f___" and not t["w"]
    p = letter_tiles({"answer": "Nice to meet you!"})
    assert sorted(p["t"]) == sorted(["nice", "to", "meet", "you"]) and p["w"] and p["m"] == "n___ t_ m___ y__"


def _english_typein_lesson(early, part="test"):
    for l in LESSONS:
        if (l["num"] <= TILES_UPTO) == early and any(q["type"] == "type_in" and not re.search("[а-яё]", str(q["answer"]), re.I) for q in l[part]):
            return l


def test_lesson_page_has_tiles(parent, make_student):
    c = make_student()
    parent.post("/parent/students/1/credit", data={"upto": "60", "action": "add"})
    early, late = _english_typein_lesson(True, "exercises"), _english_typein_lesson(False)
    html = c.get(f"/lesson/{early['id']}").get_data(as_text=True)
    train, test = html.split('id="test-form"', 1)
    assert 'class="lt" data-lt=' in train and 'data-open="1"' in train and "tiles.js" in html   # тренировка: плитки сразу
    assert 'data-open="1"' not in test.split("</form>")[0]                                      # тест: только по кнопке
    html = c.get(f"/lesson/{late['id']}").get_data(as_text=True)
    assert 'class="lt" data-lt=' in html and 'data-open="1"' not in html


def test_typo_counts_and_is_shown(parent, make_student):
    c = make_student()
    parent.post("/parent/students/1/credit", data={"upto": "60", "action": "add"})
    lesson = LESSONS_BY_ID[10]                      # «Цифры от 1 до 10»
    aid = open_lesson(c, lesson["id"])
    form = build_form(lesson, aid, 300, False)
    k, q = next((i, q) for i, q in enumerate(lesson["test"]) if q["type"] == "type_in" and q["answer"] == "eight")
    form[f"q{k}"] = "eigth"   # одна опечатка — соседние буквы местами
    body = c.post(f"/lesson/{lesson['id']}/submit", data=form).get_data(as_text=True)
    assert "Засчитано! Только пишется так" in body and "100%" in body


def test_tiles_are_stable_between_visits():
    q = {"q": "Напиши число 1 словом:", "answer": "one"}
    assert letter_tiles(q) == letter_tiles(dict(q))
