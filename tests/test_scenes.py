# -*- coding: utf-8 -*-
"""Сцена истории вместо теста урока (data/story.py, scenes.py, static/scene.js)."""
import json
import re

import scenes
from curriculum import LESSONS, LESSONS_BY_ID, validate_scenes
from data.story import SCENES
from tests.helpers import N, attempt_id_from, db_scalar, submit_lesson


def _scene_data(html):
    return json.loads(re.search(r'<script type="application/json" id="scene-data">(.*?)</script>', html, re.S).group(1))


def test_scenes_are_valid():
    assert validate_scenes() == []


def test_first_island_is_story():
    assert all(l["id"] in SCENES for l in LESSONS[:9])


def _norm(text):
    """Нижний регистр, знаки препинания — в пробелы (фразы урока бывают с «!» и «?»)."""
    return re.sub(r"[^a-z' ]+", " ", text.lower()).replace("  ", " ").strip()


def _scene_text(sc):
    """Английский текст сцены: реплики героев (включая ok/no) и варианты ответов."""
    out = []
    for ln in sc["lines"]:
        if "say" in ln:
            out.append(ln["en"])
        for key in ("ok", "no"):
            val = ln.get(key)
            if isinstance(val, dict):
                for v in ([val] if "say" in val else val.values()):
                    if isinstance(v, dict) and "say" in v:
                        out.append(v["en"])
        ask = ln.get("ask")
        if isinstance(ask, dict):
            out += [str(o) for o in ask.get("options", [])]
        if isinstance(ln.get("pick"), str):                      # выбор без правильного ответа: его варианты тоже текст сцены
            out += [str(o.get("en", "")) for o in ln.get("options", [])]
        if isinstance(ln.get("speak"), str):
            out.append(ln["speak"])
    return _norm(" ".join(out))


def test_island3_starts_with_story():
    """Острова 3–4: все слова урока звучат в тексте сцены (реплики или варианты —
    иначе карточки слов не появятся), вопросов не больше десяти, есть ход-повторение."""
    assert SCENES[16]["title"] == "Первый день на ферме"
    for lid in (16, 42, 5, 18, 6, 69, 70, 19, 67, 20, 46, 51, 21, 40, 39, 63, 64, 22, 23, 47, 24, 48, 55):
        sc = SCENES[lid]
        text = _scene_text(sc)
        for w in LESSONS_BY_ID[lid]["material"]:
            assert _norm(w["en"]) in text, (lid, w["en"])
        assert 6 <= sum(1 for ln in sc["lines"] if "ask" in ln) <= 10
        assert any(ln.get("review") for ln in sc["lines"])          # «Вспомни!» в сюжете


def test_scene_questions_are_the_test():
    for lid, sc in SCENES.items():
        l = LESSONS_BY_ID[lid]
        asks = [ln["ask"] for ln in sc["lines"] if "ask" in ln]
        assert l["test"][:len(asks)] == asks
        assert len(l["test"]) <= 10
        steps = scenes.steps(l)
        assert [s["i"] for s in steps if s["t"] == "q"] == list(range(len(l["test"])))


def test_review_is_part_of_the_story():
    l = LESSONS_BY_ID[10]                                # повторение — ходы сюжета, а не случайный вопрос после сцены
    asks = [ln["ask"] for ln in SCENES[10]["lines"] if "ask" in ln]
    assert l["test"] == asks and not any("Повторение" in q["q"] for q in l["test"])
    steps = scenes.steps(l)
    rev = [s for s in steps if s["t"] == "q" and s.get("review")]
    assert rev and any(s["options"] and "Nice to meet you!" in [o[1] for o in s["options"]] for s in rev)
    assert not any(s["t"] == "note" and "повторение" in s["text"] for s in steps)


def test_review_move_needs_earlier_word(monkeypatch):
    from data import story
    bad = dict(SCENES[10], lines=SCENES[10]["lines"] + [
        story.ask(story.choice("Ответь", ["Red!", "Blue!"], 0), review=True)])      # цвета — позже урока 10
    monkeypatch.setitem(SCENES, 10, bad)
    assert any("ход-повторение «Red!»" in e for e in validate_scenes())


def test_lesson_page_shows_scene(make_student):
    c = make_student()
    html = c.get(f"/lesson/{N(1)}").get_data(as_text=True)
    assert 'id="scene-data"' in html and "scene.js" in html and "Итоговый тест" not in html
    assert LESSONS_BY_ID[N(1)]["scene"]["title"] in html and 'id="test-form"' in html
    steps = _scene_data(html)
    assert any(s["t"] == "say" for s in steps) and any(s["t"] == "q" for s in steps)


def test_scene_passes_like_test(make_student):
    c = make_student()
    submit_lesson(c, N(1))
    assert db_scalar("SELECT passed FROM attempts WHERE finished_at IS NOT NULL") == 1


def test_fix_mode_marks_done_questions(make_student):
    c = make_student()
    html = submit_lesson(c, N(1), wrong=True)
    aid = db_scalar("SELECT id FROM attempts WHERE finished_at IS NOT NULL")
    page = c.get(f"/lesson/{N(1)}?step=test&fix={aid}").get_data(as_text=True)
    assert "Исправь ошибки" in page and attempt_id_from(page)
    assert all(not s["done"] for s in _scene_data(page) if s["t"] == "q")   # всё было неверно — ничего не засчитано
    assert html


def test_type_in_keeps_synonyms():
    l = LESSONS_BY_ID[9]
    hi = next(q for q in l["test"] if q.get("answer") == "hi")
    assert "hello" in hi["accept"]


def _second_try_form(lesson, aid, right_first):
    """Первые right_first ходов верны сразу, остальные — со второй попытки (q<i>_2 / q<i>_order_2)."""
    from tests.helpers import correct_fields, wrong_fields
    data = {"attempt_id": aid, "seconds": 300}
    for i, q in enumerate(lesson["test"]):
        if i < right_first:
            data.update(correct_fields(q, i))
        else:
            data.update(wrong_fields(q, i))
            data.update({k + "_2": v for k, v in correct_fields(q, i).items()})
    return data


def test_second_try_gives_half_point(make_student):
    from tests.helpers import open_lesson
    c = make_student()
    l = LESSONS_BY_ID[N(1)]
    html = c.post(f"/lesson/{N(1)}/submit", data=_second_try_form(l, open_lesson(c, N(1)), 0)).get_data(as_text=True)
    assert db_scalar("SELECT score_percent FROM attempts WHERE finished_at IS NOT NULL") == 50
    assert db_scalar("SELECT passed FROM attempts WHERE finished_at IS NOT NULL") == 0     # нужно 60%
    assert "со второй попытки" in html


def test_half_points_can_pass(make_student):
    from tests.helpers import open_lesson
    c = make_student()
    l = LESSONS_BY_ID[N(1)]
    n = len(l["test"])
    c.post(f"/lesson/{N(1)}/submit", data=_second_try_form(l, open_lesson(c, N(1)), (n + 1) // 2))
    assert db_scalar("SELECT passed FROM attempts WHERE finished_at IS NOT NULL") == 1


def test_second_try_ignored_without_scene(make_student, parent):
    """У обычного теста второй попытки нет — поля _2 не дают баллов."""
    from tests.helpers import open_lesson
    lid = next(l["id"] for l in LESSONS if not l.get("scene"))
    c = make_student()
    parent.post("/parent/students/1/credit", data={"upto": str(LESSONS.index(LESSONS_BY_ID[lid])), "action": "add"})
    c.post(f"/lesson/{lid}/submit", data=_second_try_form(LESSONS_BY_ID[lid], open_lesson(c, lid), 0))
    assert db_scalar("SELECT score_percent FROM attempts WHERE finished_at IS NOT NULL AND lesson_id=?", (lid,)) == 0


def test_name_in_lines_latin():
    assert scenes.name_en("Маша") == "Masha" and scenes.name_en("Женя") == "Zhenya" and scenes.name_en("Kate") == "Kate"
    steps = scenes.steps(LESSONS_BY_ID[10], name="Маша")
    first = next(s for s in steps if s["t"] == "say")
    assert "Masha" in first["en"] and "Маша" in first["ru"] and "{name}" not in first["en"]


def test_name_in_audio_is_spoken():
    """Озвучка вопроса тоже подставляет имя — иначе диктор говорит «for name» (урок 20)."""
    steps = scenes.steps(LESSONS_BY_ID[20], name="Маша")
    audio = next(s for s in steps if s["t"] == "q" and s.get("audio"))
    assert "Masha" in audio["audio"] and "{name}" not in audio["audio"]


def test_new_words_shown_once():
    steps = scenes.steps(LESSONS_BY_ID[10])
    lines = [s for s in steps if s["t"] == "say"] + [s["ok"] for s in steps if s.get("ok")]
    shown = [w["en"] for s in lines for w in s["new"]]
    assert len(shown) == len(set(shown)) and "Seven" in shown
    seven = next(s for s in lines if any(w["en"] == "Seven" for w in s["new"]))   # в реакции папы после хода «на слух»
    assert "seven" in seven["hl"]


def test_reactions_pick_and_speak_reach_page():
    steps = scenes.steps(LESSONS_BY_ID[10])
    bags = next(s for s in steps if s["t"] == "q" and s.get("no") and "2" in s["no"])
    assert bags["ok"]["who"]["name"] == "Dad" and bags["no"]["2"]["en"].startswith("A tree")
    assert any(s["t"] == "pick" and s["key"] == "lucky" for s in steps)
    assert any(s["t"] == "speak" for s in steps)
    pics = next(s for s in steps if s["t"] == "q" and s.get("pics"))
    assert set(pics["pics"]) == {"0", "1", "2"} and all(pics["pics"].values())
    assert len([s for s in steps if s["t"] == "q"]) == len(LESSONS_BY_ID[10]["test"])   # pick и speak — не вопросы теста


def test_validate_catches_bad_scene(monkeypatch):
    from data import story
    bad = dict(SCENES[10], lines=SCENES[10]["lines"] + [story.say("Tom", "I like {colour}!", "Мне нравится {colour}!")])
    monkeypatch.setitem(SCENES, 10, bad)
    assert any("{colour}" in e for e in validate_scenes())


def test_lesson_steps_without_training(make_student, parent):
    c = make_student()
    html = c.get(f"/lesson/{N(1)}").get_data(as_text=True)          # сцена: теория → слова → история
    assert 'id="step-exercises"' not in html and 'id="step-material"' in html and "1/3" in html
    assert 'id="wd-data"' in html and "<span>История</span>" in html
    lid = next(l["id"] for l in LESSONS if not l.get("scene"))
    parent.post("/parent/students/1/credit", data={"upto": str(LESSONS.index(LESSONS_BY_ID[lid])), "action": "add"})
    html = c.get(f"/lesson/{lid}").get_data(as_text=True)            # обычный: теория → слова → тест
    assert 'id="step-exercises"' not in html and 'id="step-material"' in html and "1/3" in html
    assert "practice.js" not in html


def test_old_saved_training_step_resumes_at_test(make_student):
    from routes.student import _resume_sub
    l = LESSONS_BY_ID[N(1)]
    assert "История" in _resume_sub(l, {"step": "step-exercises"})
    assert "«Слова»" in _resume_sub(l, {"step": "step-material"})
    assert "сделано ходов: 2" in _resume_sub(l, {"step": "step-test", "scene": {"first": {"0": "1", "1": "x"}}})
