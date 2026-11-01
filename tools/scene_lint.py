# -*- coding: utf-8 -*-
"""Линтер сцен-историй: механические проверки до критиков.

Запуск:
    python tools/scene_lint.py 25 26 31     # строгая проверка новых сцен (код 1 при ошибках)
    python tools/scene_lint.py             # сводка по всему курсу (не ошибка: старые сцены)

Ошибки: длина, заметки, speak, вопросы и типы, ход-повторение, слова материала в тексте,
эхо ответа choice в двух репликах над вопросом, дубли вариантов.
Предупреждения: слово урока без карточки, слова из уроков, которые идут позже, повторы
фраз с соседними сценами (4 слова подряд).
"""
import collections
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import curriculum as C  # noqa: E402
from data.story import SCENES  # noqa: E402

MIN_STEPS, MAX_STEPS = 24, 34
MIN_ASKS, MAX_ASKS = 6, 8
MAX_NOTES = 6

ALLOW = set("""
a an the and or but if so because of to in on at for with from by about up down out off over under
i you he she it we they me him her us them my your his its our their this that these those
am is are was were be been do does did done have has had got get gets go goes going went
not no yes ok oh ah ow hey ha haha hmm mm wow oops achoo ouch please thanks thank sorry
here there now then today tomorrow yesterday always never very too also just only all some any
one two three four five six seven eight nine ten eleven twelve thirteen twenty thirty
first second third fourth fifth last next big small little good bad best nice new old hot cold
what where who when why how whose which
tom anna grandma mum dad grandpa zoe smiths bell rex chick mr mrs brown kate doctor
sam ben lily lady man waiter pilot baker fisherman driver
masha name friend
""".split())


def norm(text):
    return re.sub(r"[^a-z' ]+", " ", str(text).lower().replace("\u2019", "'")).replace("  ", " ").strip()


def tokens(text):
    return re.findall(r"[a-z']+", str(text).lower().replace("\u2019", "'"))


def scene_text(sc):
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
        if isinstance(ln.get("pick"), str):
            out += [str(o.get("en", "")) for o in ln.get("options", [])]
        if isinstance(ln.get("speak"), str):
            out.append(ln["speak"])
    return norm(" ".join(out))


def say_text(sc):
    out = []
    for ln in sc["lines"]:
        if "say" in ln:
            out.append(ln["en"])
        ok = ln.get("ok")
        if isinstance(ok, dict) and "say" in ok:
            out.append(ok["en"])
    return norm(" ".join(out))


def material_key(en):
    return re.sub(r"[.!?…]+$", "", en.split("/")[0]).strip().lower()


def card_shown(key, text):
    return bool(key) and re.search(r"(?<![a-z'])" + re.escape(key) + r"(?![a-z'])", text) is not None


def split_material(lid):
    """(слова пройденных уроков, слова будущих уроков: слово → id ближайшего урока)."""
    earlier, later = set(ALLOW), {}
    seen_later = False
    for l in C.LESSONS:
        if l["id"] == lid:
            seen_later = True
            continue
        for w in l.get("material", []):
            for t in tokens(w["en"]):
                if seen_later and t not in earlier and t not in later:
                    later[t] = l["id"]
                elif not seen_later:
                    earlier.add(t)
    return earlier, later


def right(q):
    return q["options"][q["answer"]] if q["type"] == "choice" else q["answer"]


STOP = set("""the and are this that like does don't doesn't is it you yes no for not have got she he her his
him them they we i'm i've it's that's what's where's who's""".split())


def content_words(text):
    return {w for w in tokens(text) if len(w) > 2 and w not in STOP}


def check(lid):
    errors, warns = [], []
    sc = SCENES.get(lid)
    if not sc:
        return [f"сцены {lid} нет"], []
    lines = sc["lines"]
    asks = [(i, ln) for i, ln in enumerate(lines) if "ask" in ln]
    qs = [ln["ask"] for _, ln in asks]
    notes = sum(1 for ln in lines if "note" in ln)
    speaks = [ln for ln in lines if "speak" in ln]

    if not MIN_STEPS <= len(lines) <= MAX_STEPS:
        errors.append(f"шагов {len(lines)}, нужно {MIN_STEPS}–{MAX_STEPS}")
    if notes > MAX_NOTES:
        errors.append(f"заметок {notes} > {MAX_NOTES}")
    if len(speaks) != 1:
        errors.append(f"speak {len(speaks)}, нужен 1")
    if not MIN_ASKS <= len(qs) <= MAX_ASKS:
        errors.append(f"вопросов {len(qs)}, нужно {MIN_ASKS}–{MAX_ASKS}")
    if not any(q.get("audio") for q in qs):
        errors.append("нет вопроса с озвучкой")
    if not any(q["type"] in ("order", "type_in") for q in qs):
        errors.append("нет order/type_in")
    if not any(ln.get("review") for _, ln in asks):
        errors.append("нет хода-повторения (review)")

    text, hero = scene_text(sc), say_text(sc)
    for w in C.LESSONS_BY_ID[lid]["material"]:
        if norm(w["en"]) not in text:
            errors.append(f"слово урока не звучит в сцене: {w['en']}")
        elif not card_shown(norm(material_key(w["en"])), hero):
            warns.append(f"нет карточки: {w['en']} (слово есть только в вариантах)")

    prev = []
    for ln in lines:
        if "ask" in ln:
            q = ln["ask"]
            hit = sorted(content_words(right(q)) & set(" ".join(prev[-2:]).split()))
            if hit:
                msg = f"эхо {hit} перед «{q['q'][:50]}»"
                (errors if q["type"] == "choice" and not ln.get("review") else warns).append(msg)
        if "say" in ln:
            prev.append(norm(ln["en"]))

    for _, ln in asks:
        q = ln["ask"]
        if q["type"] == "choice" and len(set(map(norm, q["options"]))) != len(q["options"]):
            errors.append(f"повторяющиеся варианты: «{q['q'][:40]}»")

    earlier, later = split_material(lid)
    future = collections.Counter()
    for ln in lines:
        if "say" in ln:
            for w in tokens(ln["en"]):
                if w in later:
                    future[w] = later[w]
    if future:
        warns.append("слова из будущих уроков: " + ", ".join(
            f"{w} (урок {lid_})" for w, lid_ in list(future.items())[:10]))

    return errors, warns


def cross_dupes():
    grams = {}
    for lid, sc in SCENES.items():
        words = say_text(sc).split()
        for i in range(len(words) - 3):
            grams.setdefault(" ".join(words[i:i + 4]), []).append(lid)
    bad = collections.defaultdict(set)
    for gram, lids in grams.items():
        uniq = sorted(set(lids))
        if len(uniq) > 1 and len(gram) > 12:
            for a in uniq:
                bad[a].add((gram, tuple(x for x in uniq if x != a)))
    return bad


def main():
    only = [int(x) for x in sys.argv[1:]]
    dupes = cross_dupes()
    if not only:
        bad = [lid for lid in sorted(SCENES) if check(lid)[0]]
        print(f"Сцен всего: {len(SCENES)}; строгие ошибки у {len(bad)} (старые сцены — не блокер): "
              + ", ".join(map(str, bad[:20])))
        for lid in (22, 23):
            for gram, others in dupes.get(lid, set()):
                print(f"повтор фразы {lid} с {', '.join(map(str, others))}: «{gram}»")
        return 0
    bad = 0
    for lid in only:
        errors, warns = check(lid)
        title = SCENES.get(lid, {}).get("title", "—")
        if errors:
            bad += 1
            print(f"\n[{lid}] {title}")
            for e in errors:
                print("  ОШИБКА:", e)
        else:
            print(f"[{lid}] {title}: ошибок нет")
        for w in warns:
            print("  предупреждение:", w)
        for gram, others in dupes.get(lid, set()):
            print(f"  повтор фразы с {', '.join(map(str, others))}: «{gram}»")
    print(f"\nПроверено сцен: {len(only)}, с ошибками: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
