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

from app import app, LESSONS_BY_ID, MAIN_COUNT  # noqa: E402

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
        from app import match_columns
        _, _, expected = match_columns(q)
        pairs = ",".join(f"{k}:{v}" for k, v in sorted(expected.items()))
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
check("блок «Дополнительные уроки» на главной", "Дополнительные уроки" in body)
check("доп. уроки не заблокированы", "Бонус-урок" in body)
# 1b. Дополнительные уроки доступны ВСЕГДА (сразу после входа, id 101..105)
from data.extra_lessons import EXTRA_LESSONS as _EXTRAS
for les_x in _EXTRAS:
    eid = les_x["id"]
    re_ = client.get(f"/lesson/{eid}")
    body_x = re_.get_data(as_text=True)
    check(f"доп. урок {eid} открывается без блокировки",
          re_.status_code == 200 and "Дополнительный урок" not in body_x[:200])
    # match в формате пар должен отдавать корректный эталон JS
    if any(q.get("type") == "match" and "left" not in q for q in les_x["exercises"] + les_x["test"]):
        check(f"доп. урок {eid}: match-эталон в формате dict",
              "&#34;0&#34;: 0" in body_x or '"0": 0' in body_x)
    # сдаём тест доп. урока идеально (включая парный match)
    attempt_id = re.search(r'name="attempt_id" value="(\d+)"', body_x).group(1)
    data = {"attempt_id": attempt_id, "seconds": 300}
    for i, q in enumerate(les_x["test"]):
        data.update(correct_fields(q, i))
    r2 = client.post(f"/lesson/{eid}/submit", data=data)
    check(f"доп. урок {eid} сдаётся на 100%", "Идеально" in r2.get_data(as_text=True))
r = client.get("/student/garden")
check("страница сада открывается без ошибки", r.status_code == 200)
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
# Ачивки показываются на главной (всплывающая плашка + сетка достижений),
# а не на странице результата теста.
home_body = client.get("/student").get_data(as_text=True)
check("ачивка Первый шаг", "Первый шаг" in home_body)

# 6. Урок 2 теперь открыт
r = client.get("/student")
body = r.get_data(as_text=True)
check("урок 2 разблокирован", "Начать урок" in body)
from app import MAIN_COUNT
check(f"трекер показывает 1/{MAIN_COUNT}", f"1/{MAIN_COUNT}" in body)

# 7. Пройдём все оставшиеся уроки идеально, чтобы проверить ачивки
from data.lessons import LESSONS as MAIN_LESSONS
for lid in [l['id'] for l in MAIN_LESSONS if l['id'] != 1]:
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

# --- проверка коробки-подарка и новых ачивок ---
import json as _json
with open("static/mascot.js", encoding="utf-8") as f:
    mjs = f.read()
check("помощник умеет вручать коробку", "celebrateAchievements" in mjs and "gift-box" in mjs)
check("конфетти при открытии", "confettiBurst" in mjs)
from app import ACHIEVEMENTS
keys = {a["key"] for a in ACHIEVEMENTS}
for k in ("five_lessons", "half_way", "streak10", "words100", "attempts5",
          "time180", "diamond", "first_try_perfect"):
    check(f"ачивка {k} в каталоге", k in keys)
check("всего ачивок >= 16", len(ACHIEVEMENTS) >= 16)

# --- сад: регрессия на баг "no such column: name" (регистрация #20) ---
client.get("/logout")
client.post("/login/student", data={"username": "masha", "password": "secret1"})
r = client.get("/student/garden")
gb = r.get_data(as_text=True)
check("страница сада открывается (200)", r.status_code == 200)
check("сад не падает на имени ученицы", "OperationalError" not in gb and "Internal Server Error" not in gb)
check("в саду есть сцена с деревьями", "garden-scene" in gb or "tree-cell" in gb)
client.get("/logout")

print("\nALL TESTS PASSED ✔")
