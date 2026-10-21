# -*- coding: utf-8 -*-
"""Автоматические задания из слов урока: «послушай», диктант, буквы, перевод,
а также список фраз для тренировки произношения.

Всё детерминировано (зерно = номер урока): вопросы не «прыгают» между
открытиями страницы, а проверка на сервере видит тот же тест.
"""

import random
import re

_BAD_FOR_DICTATION = ("/", ",", "...", "(", "?", "[", "…")


def _variants(en):
    """Допустимые варианты произнесения: 'Mother / Mom' -> ['Mother','Mom']."""
    if "..." in en or "…" in en:
        return []
    s = re.sub(r"\(.*?\)", "", en).strip()
    out = []
    for part in s.split("/"):
        part = " ".join(part.split()).strip()
        if len(re.sub(r"[^A-Za-z]", "", part)) >= 2:
            out.append(part)
    return out


def speak_items(lesson, limit=6):
    """Что ребёнок может произнести: [{'en','accept','ru'}, ...]."""
    items = []
    for w in lesson.get("material", []):
        v = _variants(w["en"])
        if not v:
            continue
        items.append({"en": v[0], "accept": v, "ru": w["ru"]})
    rng = random.Random(lesson["id"] * 31 + 5)
    if len(items) > limit:
        items = sorted(rng.sample(items, limit), key=lambda x: [i["en"] for i in items].index(x["en"]))
    return items


def _dictation_ok(w):
    v = _variants(w["en"])
    if not v or any(b in w["en"] for b in _BAD_FOR_DICTATION):
        return None
    if "[" in w["ru"] or len(v[0].split()) > 3:
        return None
    return v[0]


def _choices(rng, lesson, target, key):
    """3 неправильных варианта из слов того же урока (по полю key)."""
    pool = []
    for w in lesson["material"]:
        if w is target:
            continue
        val = w[key]
        if val != target[key] and val not in pool:
            pool.append(val)
    if len(pool) < 3:
        return None
    opts = rng.sample(pool, 3) + [target[key]]
    rng.shuffle(opts)
    return opts


def _listen_choice(rng, lesson, w):
    en = _dictation_ok(w) or (_variants(w["en"]) or [None])[0]
    if not en:
        return None
    opts = _choices(rng, lesson, w, "ru")
    if not opts:
        return None
    return {"type": "choice", "q": "🔊 Послушай и выбери перевод", "audio": en,
            "options": opts, "answer": opts.index(w["ru"]),
            "explain": f"{en} — {w['ru']}"}


def _dictation(w):
    en = _dictation_ok(w)
    if not en:
        return None
    return {"type": "type_in", "q": "🔊 Послушай и напиши по-английски", "audio": en,
            "answer": en, "explain": f"{en} — {w['ru']}"}


def _letter_extras(lesson, rng, n_listen, n_dict):
    """Уроки алфавита: услышал название буквы → выбери/напиши букву."""
    letters = [w["en"].strip() for w in lesson["material"] if w.get("letter")]
    if len(letters) < 4:
        return []
    out = []
    pool = letters[:]
    rng.shuffle(pool)
    for t in pool[:n_listen]:
        others = [x for x in letters if x != t]
        opts = rng.sample(others, 3) + [t]
        rng.shuffle(opts)
        out.append({"type": "choice", "q": "🔊 Послушай и выбери букву", "audio": t,
                    "options": opts, "answer": opts.index(t), "explain": f"Это буква {t}."})
    for t in pool[n_listen:n_listen + n_dict]:
        out.append({"type": "type_in", "q": "🔊 Послушай и напиши эту букву", "audio": t,
                    "answer": t, "explain": f"Это буква {t}."})
    return out


def listening_extras(lesson):
    """Два вопроса для итогового теста: на слух (выбор) и диктант."""
    if lesson.get("letters"):
        return _letter_extras(lesson, random.Random(lesson["id"] * 17 + 3), 1, 1)
    rng = random.Random(lesson["id"] * 17 + 3)
    mat = lesson.get("material", [])
    cand = mat[:]
    rng.shuffle(cand)
    out = []
    for w in cand:
        q = _listen_choice(rng, lesson, w)
        if q:
            out.append(q)
            break
    for w in cand:
        if out and out[0].get("audio") == (_dictation_ok(w) or ""):
            continue
        q = _dictation(w)
        if q:
            out.append(q)
            break
    return out


def practice_extras(lesson):
    """«Ещё потренируемся»: 8 заданий, не влияют на оценку."""
    rng = random.Random(lesson["id"] * 13 + 11)
    if lesson.get("letters"):
        return _letter_extras(lesson, rng, 3, 3)
    cand = lesson.get("material", [])[:]
    rng.shuffle(cand)
    out = []
    used = set()

    def take(fn, n):
        got = 0
        for w in cand:
            if got >= n:
                break
            if (fn.__name__, w["en"]) in used:
                continue
            q = fn(w)
            if q:
                used.add((fn.__name__, w["en"]))
                out.append(q)
                got += 1

    def listen(w):
        return _listen_choice(rng, lesson, w)

    def dictate(w):
        return _dictation(w)

    def scramble(w):
        en = w["en"].strip()
        if re.fullmatch(r"[A-Za-z]{4,9}", en):
            letters = list(en.lower())
            for _ in range(10):
                rng.shuffle(letters)
                if "".join(letters) != en.lower():
                    break
            return {"type": "scramble", "q": f"Собери слово: {w['ru']}", "letters": letters,
                    "answer": en.lower(), "explain": f"{en} — {w['ru']}"}
        return None

    def translate(w):
        v = _variants(w["en"])
        if not v or "[" in w["ru"]:
            return None
        pool = []
        for o in lesson["material"]:
            ov = _variants(o["en"])
            if ov and ov[0] != v[0] and ov[0] not in pool:
                pool.append(ov[0])
        if len(pool) < 3:
            return None
        opts = rng.sample(pool, 3) + [v[0]]
        rng.shuffle(opts)
        return {"type": "choice", "q": f"Как по-английски: «{w['ru']}»?",
                "options": opts, "answer": opts.index(v[0]), "explain": f"{w['ru']} — {v[0]}"}

    take(listen, 2)
    take(dictate, 2)
    take(scramble, 2)
    take(translate, 2)
    return out


def pool_from(lessons):
    """Уникальные слова уроков (для повторения): key, en, accept, ru (без скобок), hint, lesson."""
    seen, out = set(), []
    for l in lessons:
        for w in l.get("material", []):
            if w.get("letter") or "[" in w["ru"]:
                continue
            v = _variants(w["en"])
            if not v:
                continue
            key = v[0].lower()
            if key in seen:
                continue
            seen.add(key)
            ru = re.sub(r"\s*\(.*?\)", "", w["ru"]).strip() or w["ru"]    # без пояснений в скобках
            out.append({"key": key, "en": v[0], "accept": v, "ru": ru, "hint": w.get("hint", ""), "pic": w.get("pic", ""),
                        "lesson": l["id"]})
    return out


def review_extras(lesson, earlier_lessons, n=2):
    """Вопросы «🔁 Повторение» из прошлых уроков для итогового теста (детерминированно)."""
    pool = pool_from(earlier_lessons)
    if len(pool) < 6:
        return []
    rng = random.Random(lesson["id"] * 101 + 7)
    out = []
    for i, w in enumerate(rng.sample(pool, n)):
        field_q, field_a = ("ru", "en") if i % 2 == 0 else ("en", "ru")
        size = len(w[field_a].split())
        cand = [x[field_a] for x in pool if x["key"] != w["key"] and x[field_a] != w[field_a]
                and abs(len(x[field_a].split()) - size) <= 1]
        cand = list(dict.fromkeys(cand))
        if len(cand) < 3:
            continue
        opts = rng.sample(cand, 3) + [w[field_a]]
        rng.shuffle(opts)
        q = (f"🔁 Повторение. Как по-английски: «{w['ru']}»?" if field_a == "en"
             else f"🔁 Повторение. Что значит «{w['en']}»?")
        out.append({"type": "choice", "q": q, "options": opts, "answer": opts.index(w[field_a]),
                    "explain": f"{w['en']} — {w['ru']}"})
    return out


def augment(lessons):
    """Один раз дополняет уроки: +2 вопроса в тест, +задания тренировки."""
    for l in lessons:
        if l.get("_augmented"):
            continue
        l["test"] = list(l["test"]) + listening_extras(l)
        l["practice"] = practice_extras(l)
        l["speak"] = speak_items(l)
        l["_augmented"] = True


def add_review_questions(course):
    """В тест каждого урока — по 2 вопроса из ранее пройденных (по порядку курса)."""
    for i, l in enumerate(course):
        if i and not l.get("_review_added"):
            l["test"] = list(l["test"]) + review_extras(l, course[:i])
            l["_review_added"] = True
