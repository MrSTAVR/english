# -*- coding: utf-8 -*-
"""Каталог уроков: списки, проверка целостности, разблокировка."""

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
    """Проходной балл: на «сухих» первых темах мягче (60%), дальше — стандартные 70%."""
    from config import PASS_MARK, PASS_MARK_SOFT
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


SCENE_MAX = 9      # ходов в сцене: +1 «Повторение» — и тест не длиннее 10 вопросов


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
        for ln in sc["lines"]:
            if "say" in ln and (ln["say"] not in CHARACTERS and ln["say"] != CHICK or not ln.get("en") or not ln.get("ru")):
                errors.append(f"{ref} — реплика без героя/en/ru: {ln}")
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
