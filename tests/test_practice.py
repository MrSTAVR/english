# -*- coding: utf-8 -*-
"""Автозадания (practice.py), оценка речи и сохранение произношения."""

import config
from curriculum import ALL_LESSONS, validate_lessons
from grading import grade_question
from practice import _variants, practice_extras, speak_items, listening_extras
from stats import compute_stats
from tests.helpers import N, db_scalar


def test_variants_clean():
    assert _variants("Mother / Mom") == ["Mother", "Mom"]
    assert _variants("He is not (isn't)") == ["He is not"]
    assert _variants("Hello! My name is...") == []
    assert _variants("A") == []


def test_catalog_still_valid_and_idempotent():
    assert validate_lessons() == []
    from practice import augment
    sizes = [len(l["test"]) for l in ALL_LESSONS]
    augment(ALL_LESSONS)
    assert sizes == [len(l["test"]) for l in ALL_LESSONS]


def test_every_lesson_has_listening_and_speaking():
    for l in ALL_LESSONS:
        audio_q = [q for q in l["test"] if q.get("audio")]
        assert audio_q, l["id"]
        assert l["speak"] or l.get("letters"), l["id"]
        assert l["practice"], l["id"]
        for q in audio_q + [p for p in l["practice"] if p.get("audio")]:
            ok, _ = grade_question(q, q["answer"])
            assert ok


def listening_extras_deterministic():
    l = ALL_LESSONS[3]
    assert listening_extras(l) == listening_extras(l)
    assert practice_extras(l) == practice_extras(l)
    assert speak_items(l) == speak_items(l)


def test_listen_questions_do_not_leak_answer_in_text():
    for l in ALL_LESSONS:
        for q in l["test"]:
            if q.get("audio") and q["type"] == "choice":
                assert q["audio"].lower() not in q["q"].lower()
                assert len(set(q["options"])) == len(q["options"])


def test_scramble_is_scrambled():
    for l in ALL_LESSONS:
        for p in l["practice"]:
            if p["type"] == "scramble":
                assert sorted(p["letters"]) == sorted(p["answer"])
                assert "".join(p["letters"]) != p["answer"]


def test_words_learned_counts_unique_words(app_client=None):
    # Orange встречается и в цветах, и во фруктах — это одно слово
    allw = [w["en"].strip().lower() for l in ALL_LESSONS for w in l["material"]]
    assert len(set(allw)) < len(allw)


def test_speak_api_requires_student_and_validates(anon, make_student):
    assert anon.post("/api/speak", json={"target": "cat", "score": 3}).status_code == 403
    c = make_student()
    assert c.post("/api/speak", json={"target": "cat", "score": 9}).status_code == 400
    assert c.post("/api/speak", json={"target": "", "score": 1}).status_code == 400
    assert c.post("/api/speak", json={"target": "x" * 200, "score": 1}).status_code == 400
    assert c.post("/api/speak", json={"target": "cat", "score": "abc"}).status_code == 400
    ok = c.post("/api/speak", json={"target": "cat", "score": 3, "lesson": 1})
    assert ok.status_code == 200
    data = ok.get_json()
    assert data["words"] == 1 and data["perfect"] == 1
    assert any(a["key"] == "speak_1" for a in data["newAchievements"])


def test_speak_api_needs_csrf(flask_app, make_student):
    c = make_student()
    flask_app.config["CSRF_ENABLED"] = True
    assert c.post("/api/speak", json={"target": "cat", "score": 3}).status_code == 400


def test_speak_stats_and_parent_view(flask_app, make_student, parent):
    c = make_student()
    for t, sc in (("cat", 3), ("cat", 1), ("dog", 2), ("pen", 0)):
        c.post("/api/speak", json={"target": t, "score": sc})
    from database import get_db
    with flask_app.app_context():
        st = compute_stats(get_db())
    assert st["speak_words"] == 2 and st["speak_perfect"] == 1 and st["speak_tries"] == 4
    sid = db_scalar("SELECT id FROM students")
    assert "слов произнесено вслух" in parent.get(f"/parent/students/{sid}").get_data(as_text=True)


def test_speak_page_and_lesson_blocks(make_student):
    c = make_student()
    r = c.get("/student/speak")
    assert r.status_code == 200 and "Говорим" in r.get_data(as_text=True)
    html = c.get(f"/lesson/{N(1)}").get_data(as_text=True)
    assert 'id="speak-block"' in html and 'id="practice"' in html and "speak.js" in html


def test_speaking_can_be_disabled(make_student, monkeypatch):
    c = make_student()
    monkeypatch.setattr(config, "SPEAKING", False)
    assert c.get("/student/speak").status_code == 404
    assert c.post("/api/speak", json={"target": "cat", "score": 3}).status_code == 404
    assert "speak.js" not in c.get(f"/lesson/{N(1)}").get_data(as_text=True)


def test_russian_answer_placeholder(parent, make_student):
    c = make_student()
    parent.post("/parent/students/1/credit", data={"upto": "1", "action": "add"})   # урок 1 (фонетика) — второй в курсе
    html = c.get("/lesson/1").get_data(as_text=True)
    assert "Напиши перевод по-русски" in html
    # у русскоязычных вопросов нет кнопки «Послушать» для вписанного ответа
    from template_filters import is_russian_answer
    assert is_russian_answer({"answer": "кот"}) and not is_russian_answer({"answer": "cat"})
