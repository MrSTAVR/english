# -*- coding: utf-8 -*-
import re
import sqlite3

import app as appmod
from app import match_columns


def dbmod():
    """Модуль, чей DB_PATH реально использует get_db(): database.py после шага 2,
    app.py до него. Так тесты работают и до, и после разбиения."""
    try:
        import database
        return database
    except ImportError:
        return appmod


def attempt_id_from(html):
    m = re.search(r'name="attempt_id" value="(\d+)"', html)
    assert m, "attempt_id не найден на странице урока"
    return m.group(1)


def correct_fields(q, i):
    """Поля формы с ПРАВИЛЬНЫМ ответом на вопрос q (любой тип)."""
    t = q["type"]
    if t == "choice":
        return {f"q{i}": q["answer"]}
    if t == "order":
        return {f"q{i}_order": q["answer"]}
    if t == "match":
        _, _, expected = match_columns(q)
        return {f"q{i}_match": ",".join(f"{k}:{v}" for k, v in sorted(expected.items()))}
    if t == "sort":
        return {f"q{i}_sort": ";".join(q["words"])}
    return {f"q{i}": q["answer"]}


def wrong_fields(q, i):
    """Заведомо НЕправильный ответ."""
    t = q["type"]
    if t == "choice":
        return {f"q{i}": (q["answer"] + 1) % len(q["options"])}
    if t == "order":
        return {f"q{i}_order": "zzz"}
    if t == "match":
        left, _, _ = match_columns(q)
        return {f"q{i}_match": ",".join(f"{li}:0" for li in range(len(left)))}
    if t == "sort":
        first = q["categories"][0]["id"]
        return {f"q{i}_sort": ";".join(f"{w.partition('|')[0]}|{first}" for w in q["words"])}
    return {f"q{i}": "xyz"}


def build_form(lesson, attempt_id, seconds=600, wrong=False):
    data = {"attempt_id": attempt_id, "seconds": seconds}
    for i, q in enumerate(lesson["test"]):
        data.update((wrong_fields if wrong else correct_fields)(q, i))
    return data


def open_lesson(client, lesson_id):
    r = client.get(f"/lesson/{lesson_id}")
    assert r.status_code == 200
    return attempt_id_from(r.get_data(as_text=True))


def submit_lesson(client, lesson_id, wrong=False, seconds=600):
    """Открывает урок, сдаёт тест, возвращает HTML страницы результата."""
    lesson = appmod.LESSONS_BY_ID[lesson_id]
    aid = open_lesson(client, lesson_id)
    r = client.post(f"/lesson/{lesson_id}/submit",
                    data=build_form(lesson, aid, seconds, wrong))
    return r.get_data(as_text=True)


def db_all(sql, args=()):
    conn = sqlite3.connect(dbmod().DB_PATH)
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def db_scalar(sql, args=()):
    rows = db_all(sql, args)
    return rows[0][0] if rows else None
