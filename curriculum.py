# -*- coding: utf-8 -*-
"""Каталог уроков: списки, проверка целостности, разблокировка."""

import re

from data.extra_lessons import EXTRA_LESSONS
from data.course import ORDER
from data.dialogs import DIALOGS
from data.emoji import emoji_for
from data.later_lessons import LATER_LESSONS
from data.lessons import LESSONS as _OLD_LESSONS
from data.more_lessons import MORE_LESSONS
from data.new_lessons import NEW_LESSONS
from data.story import SCENES
from data.topic_lessons import TOPIC_LESSONS

from grading import match_columns
from practice import add_review_questions, augment


# Все уроки: основные (с последовательной разблокировкой) + дополнительные
# (всегда открыты, id >= 101, флаг is_extra).
_main_by_id = {l["id"]: l for l in _OLD_LESSONS + NEW_LESSONS + MORE_LESSONS + LATER_LESSONS + TOPIC_LESSONS}
assert sorted(ORDER) == sorted(_main_by_id), "data/course.py: порядок не совпадает с набором уроков"
LESSONS = [_main_by_id[i] for i in ORDER]       # основной курс в порядке прохождения
for _n, _l in enumerate(LESSONS, 1):
    _l["num"] = _n                                # номер в курсе (id остаётся ключом прогресса)
ALL_LESSONS = LESSONS + EXTRA_LESSONS
MAIN_COUNT = len(LESSONS)


for _l in ALL_LESSONS:
    for _w in _l["material"]:
        _w.setdefault("pic", emoji_for(_w["en"]))     # картинка-эмодзи ("" — если нет)
for _l in ALL_LESSONS:
    _l["dialogs"] = [d for d in DIALOGS if d["lesson"] == _l["id"]]
    if _l["id"] in SCENES:
        _l["scene"] = SCENES[_l["id"]]               # тест урока — сцена истории (data/story.py)
augment(ALL_LESSONS)
add_review_questions(LESSONS)

LESSONS_BY_ID = {l["id"]: l for l in ALL_LESSONS}


SOFT_PASS_IDS = set(range(1, 9)) | {33, 34, 35}     # фонетика и алфавит — самые сухие уроки


def pass_mark(lesson):
    """Проходной балл: на «сухих» первых темах мягче (60%), дальше — стандартные 70%.
    У сцены-истории — PASS_MARK_SCENE: ход со второй попытки там приносит полбалла."""
    from config import PASS_MARK, PASS_MARK_SCENE, PASS_MARK_SOFT
    if lesson.get("scene"):
        return PASS_MARK_SCENE
    return PASS_MARK_SOFT if lesson["id"] in SOFT_PASS_IDS else PASS_MARK


def validate_lessons():
    """Проверка целостности банка уроков: индексы ответов, полнота слов для 'order'."""
    errors = []
    for l in ALL_LESSONS:
        for section in ("exercises", "test"):
            for q in l.get(section, []):
                t = q.get("type", "choice")
                ref = f"урок {l['id']} ({section}): {q.get('q', '?')[:40]}"
                if t == "choice":
                    a = q.get("answer")
                    if not isinstance(a, int) or not 0 <= a < len(q.get("options", [])):
                        errors.append(f"{ref} — некорректный индекс answer={a!r}")
                elif t == "order":
                    # сравнение по «кушкам» слов (без учёта пунктуации), чтобы
                    # многословные фишки банков ("in the bedroom") тоже сходились
                    def _keys(s):
                        return sorted(w.lower().strip(" .!?,;:") for w in s.split())
                    need = _keys(q["answer"])
                    bank = []
                    for w in q.get("words", []):
                        bank.extend(_keys(w))
                    if need != sorted(bank):
                        errors.append(f"{ref} — слова в банке не совпадают с ответом")
                elif t == "match":
                    left, right, norm = match_columns(q)
                    if not left or len(left) != len(right):
                        errors.append(f"{ref} — пустые или разной длины столбцы в match")
                    for ki, vi in norm.items():
                        if not 0 <= ki < len(left) or not 0 <= vi < len(right):
                            errors.append(f"{ref} — выход индекса пары за пределы {ki}:{vi}")
                    if len(norm) != len(left) or sorted(norm.values()) != list(range(len(right))):
                        errors.append(f"{ref} — пары должны быть полным взаимно-однозначным соответствием")
                elif t == "sort":
                    cats = {c["id"] for c in q.get("categories", [])}
                    if not cats or not q.get("words"):
                        errors.append(f"{ref} — sort без категорий или слов")
                    for item in q.get("words", []):
                        _, _, c = item.partition("|")
                        if c not in cats:
                            errors.append(f"{ref} — слово '{item}' ссылается на неизвестную категорию '{c}'")
                elif t != "type_in":
                    errors.append(f"{ref} — неизвестный тип задания {t!r}")
        # теория: если есть — проверяем структуру
        th = l.get("theory")
        if th is not None:
            if not isinstance(th, dict) or not th.get("blocks"):
                errors.append(f"урок {l['id']} — theory без блоков 'blocks'")
            else:
                for b in th["blocks"]:
                    if not isinstance(b, dict) or not b.get("title") or not b.get("text"):
                        errors.append(f"урок {l['id']} — блок теории без title/text")
    return errors


SCENE_MAX = 10     # ходов в сцене (вместе с ходами-повторениями review=True) — тест не длиннее 10 вопросов


def _phrase(text):
    return " ".join(re.sub(r"[^a-z' ]+", " ", str(text).lower().replace("’", "'")).split())


def _right_answer(q):
    return q["options"][q["answer"]] if q["type"] == "choice" else q["answer"]


def _earlier_phrases(lid):
    """Слова и фразы из материала уроков, которые идут в курсе раньше урока lid."""
    out = set()
    for l in LESSONS:
        if l["id"] == lid:
            break
        out.update(_phrase(v) for w in l.get("material", []) for v in w["en"].split("/"))
    return out


def validate_scenes():
    from data.dialogs import CHARACTERS
    from scenes import CHICK
    errors = []
    for lid, sc in SCENES.items():
        ref = f"сцена урока {lid}"
        if lid not in LESSONS_BY_ID:
            errors.append(f"{ref} — нет такого урока")
            continue
        if not sc.get("title") or not sc.get("intro") or not sc.get("outro"):
            errors.append(f"{ref} — нужны title, intro и outro")
        asks = [ln["ask"] for ln in sc["lines"] if "ask" in ln]
        if not 5 <= len(asks) <= SCENE_MAX:
            errors.append(f"{ref} — ходов ученицы {len(asks)}, нужно 5–{SCENE_MAX}")
        for q in asks:
            if q["type"] not in ("choice", "type_in", "order"):
                errors.append(f"{ref} — в сцене не бывает заданий {q['type']!r}")
        known = _earlier_phrases(lid)
        for ln in sc["lines"]:
            if ln.get("review") and _phrase(_right_answer(ln["ask"])) not in known:
                errors.append(f"{ref} — ход-повторение «{_right_answer(ln['ask'])}»: нет в материале прошлых уроков курса")
        def bad_say(ln):
            return not isinstance(ln, dict) or ln.get("say") not in CHARACTERS and ln.get("say") != CHICK                 or not ln.get("en") or not ln.get("ru")
        picks = set()
        for ln in sc["lines"]:
            if "say" in ln and bad_say(ln):
                errors.append(f"{ref} — реплика без героя/en/ru: {ln}")
            if "pick" in ln:
                picks.add(ln["pick"])
                if not 2 <= len(ln["options"]) <= 4:
                    errors.append(f"{ref} — в выборе {ln['pick']!r} нужно 2–4 варианта")
            if "ask" in ln:
                q = ln["ask"]
                if ln.get("ok") and bad_say(ln["ok"]):
                    errors.append(f"{ref} — реакция ok без героя/en/ru: {q['q']}")
                no = ln.get("no")
                for k, r in ((no.items() if "say" not in no else [("*", no)]) if no else []):
                    if bad_say(r) or k != "*" and (q["type"] != "choice" or not 0 <= k < len(q["options"]) or k == q["answer"]):
                        errors.append(f"{ref} — неверная реакция no ({k}): {q['q']}")
                if q.get("pics") and q["type"] != "choice":
                    errors.append(f"{ref} — картинки бывают только у «выбери»: {q['q']}")
        for ln in sc["lines"]:                           # {ключ} в репликах — только после выбора с этим ключом
            for m in re.findall(r"\{(\w+)\}", ln.get("en", "") + ln.get("ru", "")):
                if m != "name" and m not in picks:
                    errors.append(f"{ref} — нет выбора для {{{m}}}")
    return errors


def validate_dialogs():
    errors, keys = [], set()
    for d in DIALOGS:
        if d["key"] in keys:
            errors.append(f"диалог {d['key']} — повторяющийся ключ")
        keys.add(d["key"])
        if d["lesson"] not in LESSONS_BY_ID:
            errors.append(f"диалог {d['key']} — нет урока {d['lesson']}")
        if not any("options" in ln for ln in d["lines"]) or "options" in d["lines"][0]:
            errors.append(f"диалог {d['key']} — должен начинаться с реплики партнёра и иметь ответы ученика")
        for ln in d["lines"]:
            if "options" in ln:
                if not 2 <= len(ln["options"]) <= 4 or not 0 <= ln["answer"] < len(ln["options"]):
                    errors.append(f"диалог {d['key']} — неверные варианты ответа")
                if len(set(ln["options"])) != len(ln["options"]):
                    errors.append(f"диалог {d['key']} — повторяющиеся варианты")
            elif not ln.get("en") or not ln.get("ru"):
                errors.append(f"диалог {d['key']} — реплика без en/ru")
    return errors


def unlocked_lesson_ids(stats):
    unlocked = {l["id"] for l in EXTRA_LESSONS}      # дополнительные открыты всегда
    done = stats["completed_ids"]
    prev = None
    for i, l in enumerate(LESSONS):
        # открыт, если пройден предыдущий; уроки, которые уже пройдены или стоят
        # раньше пройденных (порядок курса мог измениться), остаются открытыми
        if prev is None or prev["id"] in done or any(x["id"] in done for x in LESSONS[i:]):
            unlocked.add(l["id"])
        prev = l
    return unlocked
