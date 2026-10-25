# -*- coding: utf-8 -*-
"""Фильтры Jinja и перемешивание заданий для шаблонов."""

from garden_scene import tree_mini_svg
import json
import random

from grading import match_columns


def is_russian_answer(q):
    """True, если ответ на type_in-вопрос нужно написать по-русски (перевод)."""
    import re
    return bool(re.search("[а-яёА-ЯЁ]", str(q.get("answer", ""))))


def human_time(seconds):
    seconds = int(seconds or 0)
    if seconds < 60:
        return f"{seconds} сек"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m} мин {s} сек" if s else f"{m} мин"
    h, m = divmod(m, 60)
    return f"{h} ч {m} мин"


def shuffle_words(words):
    """Перемешиваем слова в задании 'собери предложение' (стабильно для одной страницы)."""
    w = list(words)
    rng = random.Random("|".join(w))  # одно и то же перемешивание при повторном рендере
    rng.shuffle(w)
    if w == list(words):                # чтобы не было соблазна читать по порядку
        w.reverse()
    return w


def _stable_shuffle(items, seed):
    items = list(items)
    rng = random.Random(seed)
    rng.shuffle(items)
    return items


def shuffle_match(q):
    """Для задания 'match': правый столбик перемешиваем стабильно.
    Работает с обоими форматами (left/right и пары [[l, r], ...]).
    Возвращает список [(right_idx, text)] — порядок отображения."""
    _, right, _ = match_columns(q)
    rights = list(range(len(right)))
    order = _stable_shuffle(rights, "m" + "".join(map(str, rights)) + str(len(right)))
    if order == rights:
        order = order[::-1]
    return [(i, right[i]) for i in order]


def shuffle_sort(q):
    """Для задания 'sort': карточки слов перемешиваем стабильно.
    Возвращает список [(word, cat_id)]."""
    items = []
    for raw in q["words"]:
        w, _, c = raw.partition("|")
        items.append((w, c))
    order = _stable_shuffle(list(range(len(items))), "s" + str(sorted(q["words"])))
    res = [items[i] for i in order]
    if res == items:
        res = res[::-1]
    return res


def match_cols(q):
    """Фильтр шаблона: список левой колонки match-задания (любой формат)."""
    left, _, _ = match_columns(q)
    return left


def match_answer_json(q):
    """Фильтр шаблона: эталон ответов match-задания в JSON (ключи — индексы слева)."""
    _, _, pairs = match_columns(q)
    return json.dumps({str(k): v for k, v in pairs.items()})


def match_expected_json(q):
    """Эталон пар для JS (data-pairs/data-answer) в обоих форматах: {left_idx: right_idx}."""
    _, _, expected = match_columns(q)
    return json.dumps(expected, ensure_ascii=False)


def mistakes_count(mistakes_json):
    try:
        return len(json.loads(mistakes_json or "[]"))
    except (ValueError, TypeError):
        return 0


def tree_mini(streak_days):
    """Иконка-деревце для главной ученика (по дню серии)."""
    return tree_mini_svg(streak_days)


# эмодзи и значки-символы: в интерфейсе их нет (дизайн 3.0) — остаются только картинки к словам
EMOJI_RE = __import__("re").compile(
    "[\U0001F000-\U0001FAFF☀-☄☇-✔✗-➿⬀-⯿⌀-⏿️‍⃣]")
# стрелки ← →, звёзды ★ ☆ и крестик ✕ — не цветные значки, их оставляем


def pic_html(pic):
    """Картинка к слову: эмодзи как текст или свой рисунок («@table» → static/pics/table.svg)."""
    from markupsafe import Markup, escape
    pic = str(pic or "")
    if pic.startswith("@") and pic[1:].isalpha():
        return Markup(f'<img class="pic-img" src="/static/pics/{pic[1:]}.svg" alt="">')
    return escape(pic)


def noemoji(text):
    """Убирает эмодзи из текста интерфейса (названия уроков, баннеры, сообщения)."""
    if text is None:
        return ""
    s = EMOJI_RE.sub("", str(text))
    return " ".join(s.split()).replace(" !", "!").replace(" ?", "?").replace(" .", ".").replace(" ,", ",")
