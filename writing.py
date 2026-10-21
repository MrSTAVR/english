# -*- coding: utf-8 -*-
"""Письмо: предложения для «Собери предложение» и «Мини-диктанта».

Источники: истории и фразы из слов пройденных уроков. Берём только то, что ребёнок уже учил."""
import re

from curriculum import ALL_LESSONS
from data.stories import STORIES

MIN_SENTENCES = 4
BUILD_ROUND = 6
DICT_ROUND = 5


def norm(text):
    """Для сравнения: нижний регистр, одинаковые апострофы, без знаков препинания."""
    t = str(text).lower().replace("’", "'").replace("`", "'")
    t = re.sub(r"[^a-z0-9' ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _clean_ru(ru):
    return re.sub(r"\s*\([^)]*\)", "", ru).strip()


def sentences_for(completed_ids):
    """Предложения из пройденного: [{en, ru, pic, src}]. Без повторов."""
    out, seen = [], set()

    def add(en, ru, pic, src):
        words = en.split()
        key = norm(en)
        if not (3 <= len(words) <= 9) or key in seen or "..." in en or "/" in en:
            return
        seen.add(key)
        out.append({"en": en.strip(), "ru": _clean_ru(ru), "pic": pic, "src": src})

    for s in STORIES:
        if s["lesson"] in completed_ids:
            for sen in s["sentences"]:
                add(sen["en"], sen["ru"], s["emoji"], s["key"])
    for l in ALL_LESSONS:
        if l["id"] in completed_ids:
            for m in l["material"]:
                if not m.get("letter"):
                    add(m["en"], m["ru"], l.get("emoji", "✍️"), f"lesson-{l['id']}")
    return out
