# -*- coding: utf-8 -*-
"""Проверка ответов: разбор формы и оценивание всех типов заданий."""
import re



def norm_answer(text):
    """Нормализация ответа для проверки type_in."""
    return " ".join(str(text or "").lower().replace("’", "'").split()).strip(" .!?,;:")


def _distance(a, b):
    """Сколько правок нужно, чтобы из a получить b: вставка, удаление, замена буквы
    или две соседние буквы местами (eigth → eight — одна опечатка)."""
    d = [[i + j if i * j == 0 else 0 for j in range(len(b) + 1)] for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)]


def typo_limit(expected):
    """Сколько опечаток прощаем в слове: в коротких (до 5 букв) — ни одной, дальше — одну, в длинных — две."""
    n = len(expected)
    return 0 if n < 5 else 1 if n < 10 else 2


# Служебные слова — «настоящие слова», которые легко получить опечаткой из другого (than/then, your/you…)
FUNCTION_WORDS = set("""
a an the i me my mine you your yours he him his she her hers it its we us our ours they them their theirs
this that these those there here then than where were wear when what which who whose why how
am is are was be been being do does did done don't doesn't didn't isn't aren't wasn't weren't can't
have has had having will would shall should can could may might must
to too two for four from form of off on in into at by bye buy with without about
and or but so not no now know new knew some any many much more most very well
""".split())

_WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")
_DICT = None


def _collect(obj, out):
    if isinstance(obj, str):
        out.update(_WORD_RE.findall(obj.lower().replace("’", "'")))
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _collect(v, out)


def dictionary():
    """Английские слова, которые встречаются в курсе (уроки, истории, диалоги) + служебные.
    Если ребёнок написал одно из них вместо ответа — это другое слово, а не опечатка."""
    global _DICT
    if _DICT is None:
        from curriculum import ALL_LESSONS
        from data.dialogs import DIALOGS
        from data.stories import STORIES
        words = set(FUNCTION_WORDS)
        _collect([ALL_LESSONS, DIALOGS, STORIES], words)
        _DICT = words
    return _DICT


_FORMS = ("s", "es", "ed", "d", "ing", "'s")


def _form_change(g, e):
    """True, если слова отличаются только окончанием или удвоенной буквой (sock/socks, run/runing)."""
    for a, b in ((g, e), (e, g)):
        if any(a + s == b for s in _FORMS):
            return True
        if len(b) == len(a) + 1:
            for i in range(1, len(b)):
                if b[i] == b[i - 1] and b[:i] + b[i + 1:] == a:
                    return True
    return False


def word_typo(g, e, words):
    """True, если слово g — опечатка в слове e (а не другое слово и не другая форма)."""
    return (g != e and len(e) >= 5 and g[:1] == e[:1] and g not in words
            and not _form_change(g, e) and _distance(g, e) <= typo_limit(e))


def _has_cyrillic(s):
    return any("а" <= c <= "я" or c == "ё" for c in s)


def near_answer(given, expected, words=None):
    """Ответ с маленькой опечаткой: слова те же и по порядку, опечатка — максимум в одном слове.
    Русские ответы не прощаем (там легко «засчитать» другое слово: правильный/неправильный)."""
    g, e = norm_answer(given), norm_answer(expected)
    if not g or g == e or _has_cyrillic(e):
        return False
    gw, ew = g.split(), e.split()
    if len(gw) != len(ew):
        return False
    words = dictionary() if words is None else words
    diff = [(a, b) for a, b in zip(gw, ew) if a != b]
    return len(diff) == 1 and word_typo(diff[0][0], diff[0][1], words)


def near_miss(q, given):
    """True, если ответ type_in написан с маленькой опечаткой (засчитываем, но показываем, как правильно)."""
    return any(near_answer(given, a) for a in [q["answer"]] + list(q.get("accept", [])))


def near_dict(lesson):
    """Слова словаря, похожие на ответы урока, — для той же проверки в браузере (LetterTiles.near)."""
    words = dictionary()
    answers = set()
    for q in list(lesson.get("exercises", [])) + list(lesson.get("test", [])) + list(lesson.get("practice", [])):
        if q.get("type") == "type_in":
            for a in [q.get("answer", "")] + list(q.get("accept", [])):
                answers.update(w for w in norm_answer(a).split() if len(w) >= 5)
    return sorted(w for w in words if any(w[:1] == a[:1] and abs(len(w) - len(a)) <= 2
                                          and w != a and _distance(w, a) <= 2 for a in answers))


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
