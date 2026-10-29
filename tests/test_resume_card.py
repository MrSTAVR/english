# -*- coding: utf-8 -*-
"""Карточка «Продолжи урок» на главной ученика."""
from curriculum import LESSONS
from tests.helpers import submit_lesson

CARD = 'next-cta-kicker">Продолжи урок'   # сама карточка (фраза бывает и в подписи версии — тексте коммита)


def test_resume_card_shows_unfinished_lesson(make_student):
    c = make_student()
    l = LESSONS[0]
    assert CARD not in c.get("/student").get_data(as_text=True)
    c.get(f"/lesson/{l['id']}")
    c.post(f"/api/lesson/{l['id']}/progress", json={"state": {"step": "step-test", "scene": {"pos": 5, "first": {"0": "1", "1": "x"}}}})
    html = c.get("/student").get_data(as_text=True)                # первый урок — сцена-история
    assert CARD in html and f"сделано ходов: 2 из {len(l['test'])}" in html and f'href="/lesson/{l["id"]}"' in html


def test_resume_card_counts_test_answers(make_student, parent):
    c = make_student()
    l = next(x for x in LESSONS if not x.get("scene"))
    parent.post("/parent/students/1/credit", data={"upto": str(LESSONS.index(l)), "action": "add"})
    c.get(f"/lesson/{l['id']}")
    c.post(f"/api/lesson/{l['id']}/progress", json={"state": {"step": "step-test", "test": {"radio": {"q0": "1", "q1": "0"}, "text": ["", ""]}}})
    assert f"отвечено 2 из {len(l['test'])}" in c.get("/student").get_data(as_text=True)


def test_resume_card_steps_and_gone_after_pass(make_student, parent):
    c = make_student()
    l = next(x for x in LESSONS if not x.get("scene"))           # у урока со сценой нет шага «Слова»
    parent.post("/parent/students/1/credit", data={"upto": str(LESSONS.index(l)), "action": "add"})
    c.get(f"/lesson/{l['id']}")
    c.post(f"/api/lesson/{l['id']}/progress", json={"state": {"step": "step-material", "words": {"i": 2, "seen": [0, 1, 2]}}})
    assert f"3 из {len(l['material'])} слов" in c.get("/student").get_data(as_text=True)
    submit_lesson(c, l["id"])
    assert CARD not in c.get("/student").get_data(as_text=True)


def test_resume_card_skips_passed_lesson(make_student):
    """В пройденный урок заходят повторить — главная кнопка всё равно ведёт вперёд."""
    c = make_student()
    l = LESSONS[0]
    submit_lesson(c, l["id"])
    c.get(f"/lesson/{l['id']}")
    c.post(f"/api/lesson/{l['id']}/progress", json={"state": {"step": "step-material", "words": {"seen": [0]}}})
    assert CARD not in c.get("/student").get_data(as_text=True)


def test_resume_card_survives_broken_state(make_student):
    """Испорченное сохранение (старый скрипт, ручной запрос) не роняет главную."""
    c = make_student()
    l = LESSONS[0]
    c.get(f"/lesson/{l['id']}")
    for st in ({"step": "step-material", "words": ["x"]}, {"step": "step-test", "test": {"radio": 5, "text": 3}},
               {"step": "step-test", "test": "x"}):
        c.post(f"/api/lesson/{l['id']}/progress", json={"state": st})
        r = c.get("/student")
        assert r.status_code == 200 and CARD in r.get_data(as_text=True)
