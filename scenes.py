# -*- coding: utf-8 -*-
"""Сцена-диалог вместо итогового теста (сюжет — data/story.py).

Вопросы сцены — это и есть lesson["test"] (practice.augment), поэтому сдача, «Исправь ошибки»,
монетки и повторение работают как у обычного теста. Здесь — только данные для показа в чате
(static/scene.js): реплики героев (с новыми словами урока — карточки под репликой), реакции героев
на ответ, ходы ученицы с вариантами и плитками, выбор без правильного ответа (pick), «скажи вслух»
(speak). Повторение прошлых уроков — обычные ходы сцены с review=True (метка «Вспомни!»).
"""
import re

from data.dialogs import character
from template_filters import is_russian_answer, letter_tiles, shuffle_options, shuffle_words

CHICK = "Chick-chick"

_TRANSLIT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                     ["a", "b", "v", "g", "d", "e", "yo", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s",
                      "t", "u", "f", "kh", "ts", "ch", "sh", "shch", "", "y", "", "e", "yu", "ya"]))


def name_en(name):
    """Имя ученицы латиницей — для английских реплик и озвучки («Маша» → «Masha»)."""
    out = []
    for ch in name or "":
        low = ch.lower()
        if low in _TRANSLIT:
            t = _TRANSLIT[low]
            out.append(t.capitalize() if ch != low else t)
        else:
            out.append(ch)
    return "".join(out).strip() or "friend"


def _who(name):
    if name == CHICK:
        return {"name": "Чик-чик", "pic": "", "chick": True, "role": "", "bg": ""}
    c = character(name)
    return {"name": name, "pic": c["pic"], "role": c["role"], "bg": c["bg"]}


def _key(en):
    """Слово/фраза урока для поиска в реплике: без многоточий и знаков в конце, строчными."""
    return re.sub(r"[.!?…]+$", "", en.split("/")[0]).strip().lower()


def _found(key, text):
    return bool(key) and re.search(r"(?<![a-z'])" + re.escape(key) + r"(?![a-z'])", text.lower()) is not None


class _Words:
    """Слова урока: первое появление в реплике — карточка под репликой, потом — просто выделение."""

    def __init__(self, lesson):
        self.items = [(w, _key(w["en"])) for w in lesson.get("material", []) if _key(w["en"])]
        self.shown = set()

    def mark(self, en):
        new, hl = [], []
        for w, k in self.items:
            if _found(k, en):
                hl.append(k)
                if k not in self.shown:
                    self.shown.add(k)
                    new.append({"en": w["en"], "ru": w["ru"], "pic": w.get("pic", "")})
        return new, hl

    def pic(self, word):
        k = _key(word)
        for w, wk in self.items:
            if wk == k and w.get("pic"):
                return w["pic"]
        from data.emoji import emoji_for
        return emoji_for(word)


def _line(ln, me_en, me_ru):
    if not ln:
        return None
    return {"who": _who(ln["say"]), "en": ln["en"].replace("{name}", me_en), "ru": ln["ru"].replace("{name}", me_ru)}


def _question(i, q, done, ask=None, words=None, me=("", "")):
    d = {"t": "q", "i": i, "type": q["type"], "q": q["q"], "explain": q.get("explain", ""), "done": done}
    if q.get("audio"):
        d["audio"] = q["audio"]
    if q["type"] == "choice":
        d["options"] = shuffle_options(q)
        d["answer"] = q["answer"]
        if q.get("pics") and words:
            d["pics"] = {str(k): words.pic(o) for k, o in enumerate(q["options"])}
    elif q["type"] == "order":
        d["words"] = shuffle_words(q["words"])
        d["answer"] = q["answer"]
    else:
        d["answer"] = q["answer"]
        d["ru"] = is_russian_answer(q)
        if not d["ru"]:
            d["tiles"] = letter_tiles(q)
    if ask:
        if ask.get("review"):
            d["review"] = True
        if ask.get("ok"):
            d["ok"] = _line(ask["ok"], *me)
            d["ok"]["new"], d["ok"]["hl"] = words.mark(d["ok"]["en"])
        no = ask.get("no")
        if isinstance(no, dict) and "say" not in no:     # своя реакция на конкретный неверный вариант
            d["no"] = {str(k): _line(v, *me) for k, v in no.items()}
        elif no:
            d["no"] = {"*": _line(no, *me)}
    return d


def steps(lesson, fix_done=(), name=""):
    """Шаги чата: реплики (say), слова рассказчика (note), ходы ученицы (q, i — номер вопроса теста),
    выбор без правильного ответа (pick) и «скажи вслух» (speak). name — имя ученицы для {name}."""
    scene, out, i = lesson["scene"], [], 0
    me = (name_en(name), name or "")
    words = _Words(lesson)
    for ln in scene["lines"]:
        if "say" in ln:
            st = _line(ln, *me)
            st["t"] = "say"
            st["new"], st["hl"] = words.mark(st["en"])
            out.append(st)
        elif "note" in ln:
            out.append({"t": "note", "text": ln["note"].replace("{name}", me[1])})
        elif "pick" in ln:
            out.append({"t": "pick", "key": ln["pick"], "q": ln["q"], "options": ln["options"]})
        elif "speak" in ln:
            out.append({"t": "speak", "en": ln["speak"].replace("{name}", me[0]), "ru": ln["ru"].replace("{name}", me[1])})
        else:
            out.append(_question(i, lesson["test"][i], i in fix_done, ln, words, me))
            i += 1
    return out
