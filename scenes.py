# -*- coding: utf-8 -*-
"""Сцена-диалог вместо итогового теста (сюжет — data/story.py).

Вопросы сцены — это и есть lesson["test"] (practice.augment), поэтому сдача, «Исправь ошибки»,
монетки и повторение работают как у обычного теста. Здесь — только данные для показа в чате
(static/scene.js): реплики героев, ходы ученицы с вариантами и плитками, вопросы «Повторение»
после сцены (их задаёт Чик-чик).
"""
from data.dialogs import character
from template_filters import is_russian_answer, letter_tiles, shuffle_options, shuffle_words

CHICK = "Chick-chick"


def _who(name):
    if name == CHICK:
        return {"name": "Чик-чик", "pic": "", "chick": True, "role": "", "bg": ""}
    c = character(name)
    return {"name": name, "pic": c["pic"], "role": c["role"], "bg": c["bg"]}


def _question(i, q, done):
    d = {"t": "q", "i": i, "type": q["type"], "q": q["q"], "explain": q.get("explain", ""), "done": done}
    if q.get("audio"):
        d["audio"] = q["audio"]
    if q["type"] == "choice":
        d["options"] = shuffle_options(q)
        d["answer"] = q["answer"]
    elif q["type"] == "order":
        d["words"] = shuffle_words(q["words"])
        d["answer"] = q["answer"]
    else:
        d["answer"] = q["answer"]
        d["ru"] = is_russian_answer(q)
        if not d["ru"]:
            d["tiles"] = letter_tiles(q)
    return d


def steps(lesson, fix_done=()):
    """Шаги чата: реплики (say), слова рассказчика (note) и ходы ученицы (q, i — номер вопроса теста)."""
    scene, out, i = lesson["scene"], [], 0
    for ln in scene["lines"]:
        if "say" in ln:
            out.append({"t": "say", "who": _who(ln["say"]), "en": ln["en"], "ru": ln["ru"]})
        elif "note" in ln:
            out.append({"t": "note", "text": ln["note"]})
        else:
            out.append(_question(i, lesson["test"][i], i in fix_done))
            i += 1
    if i < len(lesson["test"]):                          # «Повторение» из прошлых уроков — от Чик-чика
        out.append({"t": "note", "text": "И ещё вопрос на повторение — из прошлых уроков."})
        for k in range(i, len(lesson["test"])):
            out.append(_question(k, lesson["test"][k], k in fix_done))
    return out
