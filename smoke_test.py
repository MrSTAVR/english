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

def correct_fields(q, i):
    """Возвращает dict полей формы с ПРАВИЛЬНЫМ ответом на вопрос q."""
    t = q["type"]
    if t == "choice":
        return {f"q{i}": q["answer"]}
    if t == "order":
        return {f"q{i}_order": q["answer"]}
    if t == "match":
        pairs = ",".join(f"{k}:{v}" for k, v in sorted(
            (int(a), int(b)) for a, b in q["pairs"].items()))
        return {f"q{i}_match": pairs}
    if t == "sort":
        s = ";".join(x.partition("|")[0] + "|" + x.partition("|")[2] for x in q["words"])
        return {f"q{i}_sort": s}
    return {f"q{i}": q["answer"]}


# 1. Индекс
r = client.get("/")
check("индекс открывается", r.status_code == 200 and "Я ученик" in r.get_data(as_text=True))

# 1b. Анимированный помощник Чик-чик подключён на всех страницах
body = r.get_data(as_text=True)
check("настройки помощника на индексе",
      'MASCOT_SETTINGS' in body and '"page": "anon"' in body)
check("скрипт помощника подключён", "mascot.js" in body)
check("стили помощника", ".mascot-balloon" in open("static/style.css").read())
import os as _os
check("файл mascot.js существует", _os.path.exists("static/mascot.js"))

# 2. Родитель создаёт аккаунт ученицы, вход по логину/паролю
r = client.post("/login/parent", data={"password": "1234"}, follow_redirects=True)
check("вход родителя", "Кабинет родителя" in r.get_data(as_text=True))
r = client.post("/parent/students/add", data={
    "display_name": "Маша", "username": "masha", "password": "secret1", "emoji": "🦄"},
    follow_redirects=True)
check("аккаунт создан", "Аккаунт для Маша создан" in r.get_data(as_text=True))
client.get("/logout")

r = client.post("/login/student", data={"username": "masha", "password": "secret1"},
                follow_redirects=True)
body = r.get_data(as_text=True)
check("вход ученицы", r.status_code == 200 and "Привет, Маша" in body)
check("урок 2 заблокирован", "Закрой предыдущий урок" in body)
check("помощник на главной ученицы (home)", '"page": "home"' in body)

# 2b. Помощник знает контекст урока и результата
r = client.get("/lesson/1")
lb = r.get_data(as_text=True)
check("помощник на странице урока",
      '"page": "lesson"' in lb and '"lessonTitle"' in lb)

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
r = client.post("/lesson/1/submit?x=1", data=data)  # сессия ученицы уже установлена
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
    data.update(correct_fields(q, i))
r = client.post("/lesson/1/submit", data=data)
body = r.get_data(as_text=True)
check("идеальный тест 100%", "Идеально! 100%" in body)
check("помощник на странице результата", '"page": "result"' in body and '"percent": 100' in body)
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
        data.update(correct_fields(q, i))
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
