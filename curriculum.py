# -*- coding: utf-8 -*-
"""Каталог уроков: списки, проверка целостности, разблокировка."""

from data.extra_lessons import EXTRA_LESSONS
from data.lessons import LESSONS

from grading import match_columns


# Все уроки: основные (с последовательной разблокировкой) + дополнительные
# (всегда открыты, id >= 101, флаг is_extra).
ALL_LESSONS = LESSONS + EXTRA_LESSONS
MAIN_COUNT = len(LESSONS)


LESSONS_BY_ID = {l["id"]: l for l in ALL_LESSONS}


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


def unlocked_lesson_ids(stats):
    unlocked = set()
    for l in ALL_LESSONS:
        if l.get("is_extra"):
            unlocked.add(l["id"])
            continue
        prev = l["id"] - 1
        if prev == 0 or prev in stats["completed_ids"]:
            unlocked.add(l["id"])
    return unlocked
