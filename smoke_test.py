# -*- coding: utf-8 -*-
"""Полный смоук-тест приложения через Flask test client."""
import json
import re
import sys

sys.path.insert(0, ".")
import os
os.environ.setdefault("FLASK_DEBUG", "0")

# чистая база для теста
if os.path.exists("english_app.db"):
    os.remove("english_app.db")

from app import app, LESSONS_BY_ID  # noqa: E402

client = app.test_client()

def check(name, cond):
    print(("PASS" if cond else "FAIL"), "-", name)
    if not cond:
        raise SystemExit(f"TEST FAILED: {name}")

# 1. Индекс
r = client.get("/")
check("индекс открывается", r.status_code == 200 and "Я ученица".encode() in r.data or "Я ученица" in r.get_data(as_text=True))

# 2. Вход ученика
r = client.post("/login/student", data={"name": "Маша"}, follow_redirects=True)
body = r.get_data(as_text=True)
check("вход ученицы", r.status_code == 200 and "Привет, Маша" in body)
check("урок 2 заблокирован", "Закрой предыдущий урок" in body)

# 3. Урок заблокирован — нельзя открыть напрямую
r = client.get("/lesson/2", follow_redirects=True)
check("закрытый урок редиректит", "Сначала пройди предыдущий урок" in r.get_data(as_text=True))

# 4. Открыть урок 1, сдать тест с ошибками (намеренно неверные ответы)
r = client.get("/lesson/1")
body = r.get_data(as_text=True)
m = re.search(r'name="attempt_id" value="(\d+)"', body)
check("страница урока 1", r.status_code == 200 and m)
attempt_id = m.group(1)

lesson = LESSONS_BY_ID[1]
data = {"attempt_id": attempt_id, "seconds": 500}
expected_mistakes = 0
for i, q in enumerate(lesson["test"]):
    if q["type"] == "choice":
        wrong = (q["answer"] + 1) % len(q["options"])
        data[f"q{i}"] = wrong
        expected_mistakes += 1
    elif q["type"] == "order":
        data[f"q{i}_order"] = "wrong words here"
        expected_mistakes += 1
    else:
        data[f"q{i}"] = "xyz"
        expected_mistakes += 1
r = client.post("/lesson/1/submit?x=1", data=data)
# submit требует session role? submit_test не проверяет роль — ок для теста
body = r.get_data(as_text=True)
check("тест 1 провален (<70%)", "Почти получилось" in body)
check("разбор ошибок показан", "Твой ответ" in body)

# 5. Сдать урок 1 идеально
r = client.get("/lesson/1")
body = r.get_data(as_text=True)
attempt_id = re.search(r'name="attempt_id" value="(\d+)"', body).group(1)
data = {"attempt_id": attempt_id, "seconds": 600}
for i, q in enumerate(lesson["test"]):
    if q["type"] == "choice":
        data[f"q{i}"] = q["answer"]
    elif q["type"] == "order":
        data[f"q{i}_order"] = q["answer"]
    else:
        data[f"q{i}"] = q["answer"]
r = client.post("/lesson/1/submit", data=data)
body = r.get_data(as_text=True)
check("идеальный тест 100%", "Идеально! 100%" in body)
check("ачивка Первый шаг", "Первый шаг" in body)

# 6. Урок 2 теперь открыт
r = client.get("/student")
body = r.get_data(as_text=True)
check("урок 2 разблокирован", "Начать урок" in body)
check("трекер показывает 1/8", "1/8" in body)

# 7. Пройдём все оставшиеся уроки идеально, чтобы проверить ачивки
for lid in range(2, len(LESSONS_BY_ID) + 1):
    les = LESSONS_BY_ID[lid]
    r = client.get(f"/lesson/{lid}")
    body = r.get_data(as_text=True)
    attempt_id = re.search(r'name="attempt_id" value="(\d+)"', body).group(1)
    data = {"attempt_id": attempt_id, "seconds": 700}
    for i, q in enumerate(les["test"]):
        if q["type"] == "choice":
            data[f"q{i}"] = q["answer"]
        elif q["type"] == "order":
            data[f"q{i}_order"] = q["answer"]
        else:
            data[f"q{i}"] = q["answer"]
    r = client.post(f"/lesson/{lid}/submit", data=data)
    check(f"урок {lid} сдан на 100%", "Идеально" in r.get_data(as_text=True))

r = client.get("/student")
body = r.get_data(as_text=True)
check("чемпион достигнут", "Английский чемпион" in body)
check("ачивка час упорства", "Час упорства" in body)

# 8. Родитель: неправильный пароль
r = client.post("/login/parent", data={"password": "0000"}, follow_redirects=True)
check("родитель без пароля не входит", "Неверный пароль" in r.get_data(as_text=True))

# 9. Вход родителя и проверка дашборда
r = client.post("/login/parent", data={"password": "1234"}, follow_redirects=True)
body = r.get_data(as_text=True)
check("кабинет родителя открыт", "Кабинет родителя" in body)
check("время показано", "мин" in body)
# в проваленной попытке было 6 вопросов — все с ошибками
m = re.search(r'<span class="stat-num">(\d+)</span><span class="stat-label">ошибок за всё время', body)
check("ошибки посчитаны (6 из проваленной попытки)", m and int(m.group(1)) == expected_mistakes)

r = client.get("/api/mistakes")
mistakes = r.get_json()
check("API ошибок доступен родителю", isinstance(mistakes, list) and len(mistakes) == expected_mistakes)
if mistakes:
    m0 = mistakes[0]
    check("в ошибке есть вопрос/ответ/правильный ответ",
          all(k in m0 for k in ("question", "given", "correct", "date", "lesson_title")))

print("\nALL TESTS PASSED ✔")
