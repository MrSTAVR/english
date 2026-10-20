# -*- coding: utf-8 -*-
"""Проверка ответов: разбор формы и оценивание всех типов заданий."""


def norm_answer(text):
    """Нормализация ответа для проверки type_in."""
    return " ".join(str(text or "").lower().replace("’", "'").split()).strip(" .!?,;:")


def parse_pairs(raw):
    """Разбирает ответ match-задания из формы: 'leftIdx:rightIdx,leftIdx:rightIdx,...'
    Возвращает dict {int: int} (только полные пары)."""
    pairs = {}
    for part in str(raw or "").split(","):
        if ":" not in part:
            continue
        a, _, b = part.partition(":")
        try:
            pairs[int(a)] = int(b)
        except ValueError:
            continue
    return pairs


def parse_sort(raw):
    """Разбирает ответ sort-задания: 'word|catId;word|catId;...' -> list[(word, cat)]."""
    out = []
    for part in str(raw or "").split(";"):
        if "|" in part:
            w, _, c = part.partition("|")
            out.append((w.strip(), c.strip()))
    return out


def grade_question(q, given):
    """Возвращает (is_correct, correct_display)."""
    qtype = q.get("type", "choice")
    if qtype == "choice":
        # ответ приходит из формы строкой ("2") или как -1 (пусто) — приводим к int
        try:
            idx = int(given)
        except (TypeError, ValueError):
            idx = -1
        ok = 0 <= idx < len(q["options"]) and idx == q["answer"]
        return ok, q["options"][q["answer"]]
    if qtype == "order":
        expected = norm_answer(q["answer"])
        ok = norm_answer(given) == expected
        return ok, q["answer"]
    if qtype == "match":
        left, right, expected = match_columns(q)
        got = parse_pairs(given)
        ok = got == expected and len(got) == len(left)
        disp = ", ".join(f"{left[li]} ↔ {right[ri]}"
                         for li, ri in sorted(expected.items()))
        return ok, disp
    if qtype == "sort":
        expected = {}
        for item in q["words"]:
            w, _, c = item.partition("|")
            expected.setdefault(c.lower(), []).append(w.lower())
        got = {}
        for w, c in parse_sort(given):
            got.setdefault(c.lower(), []).append(w.lower())
        ok = {k: sorted(v) for k, v in got.items()} == \
             {k: sorted(v) for k, v in expected.items()}
        disp = "; ".join(f"{c}: {', '.join(w)}" for c, w in
                         ((cat["title"], [x.partition("|")[0] for x in q["words"]
                                          if x.endswith("|" + cat["id"])])
                          for cat in q["categories"]))
        return ok, disp
    # type_in
    accepted = [norm_answer(q["answer"])] + [norm_answer(a) for a in q.get("accept", [])]
    ok = norm_answer(given) in accepted
    return ok, q["answer"]


def match_columns(q):
    """Нормализует match-задание к колоночному виду (left, right, pairs{int:int}).

    Поддерживаются два формата банка уроков:
      A) колонки:  {"left": [...], "right": [...], "pairs": {0: 2, ...}}
      B) пары:     {"pairs": [["en", "ru"], ...]}  (парный формат доп. уроков)
    Возвращает (left, right, pairs_dict)."""
    raw = q.get("pairs", {})
    if isinstance(raw, dict) and q.get("left") and q.get("right"):
        left = list(q["left"])
        right = list(q["right"])
        pairs = {int(k): int(v) for k, v in raw.items()}
        return left, right, pairs
    # парный формат: [["cat", "кошка"], ...] -> левая колонка en, правая ru
    seq = list(raw)
    left = [p[0] for p in seq]
    right = [p[1] for p in seq]
    pairs = {i: i for i in range(len(seq))}
    return left, right, pairs
