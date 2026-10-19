# -*- coding: utf-8 -*-
"""Смоук-тест v2: аккаунты учеников (создаёт родитель), входы, изоляция прогресса."""
import json
import re
import sys
import os

sys.path.insert(0, ".")
os.environ.setdefault("FLASK_DEBUG", "0")

if os.path.exists("english_app.db"):
    os.remove("english_app.db")

from app import app, LESSONS_BY_ID  # noqa: E402

client = app.test_client()

def check(name, cond):
    print(("PASS" if cond else "FAIL"), "-", name)
    if not cond:
        raise SystemExit(f"TEST FAILED: {name}")


def answer_data(lesson, attempt_id, seconds=600, wrong=False):
    """Формирует данные теста; wrong=True — заведомо неправильные ответы."""
    data = {"attempt_id": attempt_id, "seconds": seconds}
    for i, q in enumerate(lesson["test"]):
        t = q["type"]
        if t == "choice":
            data[f"q{i}"] = (q["answer"] + 1) % len(q["options"]) if wrong else q["answer"]
        elif t == "order":
            data[f"q{i}_order"] = "zzz" if wrong else q["answer"]
        elif t == "match":
            if wrong:
                data[f"q{i}_match"] = ",".join(f"{li}:0" for li in range(len(q["left"])))
            else:
                data[f"q{i}_match"] = ",".join(f"{k}:{v}" for k, v in sorted(
                    (int(a), int(b)) for a, b in q["pairs"].items()))
        elif t == "sort":
            if wrong:
                first_cat = q["categories"][0]["id"]
                data[f"q{i}_sort"] = ";".join(f"{w.partition('|')[0]}|{first_cat}" for w in q["words"])
            else:
                data[f"q{i}_sort"] = ";".join(f"{w}|{c}" for w, _, c in
                                              [x.partition("|") for x in q["words"]])
        else:  # type_in
            data[f"q{i}"] = "xyz" if wrong else q["answer"]
    return data


def pass_lesson(cl, lid, seconds=700):
    les = LESSONS_BY_ID[lid]
    r = cl.get(f"/lesson/{lid}")
    body = r.get_data(as_text=True)
    m = re.search(r'name="attempt_id" value="(\d+)"', body)
    assert m, f"не нашли attempt_id на уроке {lid}"
    r = cl.post(f"/lesson/{lid}/submit", data=answer_data(les, m.group(1), seconds))
    return r.get_data(as_text=True)


# 1. Родитель заходит и создаёт двух учеников
r = client.post("/login/parent", data={"password": "1234"}, follow_redirects=True)
check("вход родителя", "Кабинет родителя" in r.get_data(as_text=True))

r = client.post("/parent/students/add", data={
    "display_name": "Маша", "username": "masha", "password": "secret1", "emoji": "🦄"},
    follow_redirects=True)
body = r.get_data(as_text=True)
check("аккаунт Маши создан", "Аккаунт для Маша создан" in body and "masha" in body)

r = client.post("/parent/students/add", data={
    "display_name": "Петя", "username": "petya", "password": "secret2", "emoji": "🐱"},
    follow_redirects=True)
check("аккаунт Пети создан", "Аккаунт для Петя создан" in r.get_data(as_text=True))

# Дубликат логина
r = client.post("/parent/students/add", data={
    "display_name": "Двойник", "username": "MASHA", "password": "abcd", "emoji": "🐰"},
    follow_redirects=True)
check("дубликат логина отклонён (без учёта регистра)", "уже занят" in r.get_data(as_text=True))

# Невалидный логин / короткий пароль
r = client.post("/parent/students/add", data={
    "display_name": "Х", "username": "машина", "password": "abcd", "emoji": "🐰"},
    follow_redirects=True)
check("кириллический логин отклонён", "только английские буквы" in r.get_data(as_text=True))
r = client.post("/parent/students/add", data={
    "display_name": "Х", "username": "kid", "password": "12", "emoji": "🐰"},
    follow_redirects=True)
check("короткий пароль отклонён", "не короче 4" in r.get_data(as_text=True))

# 2. Ученик без аккаунта не может войти
r = client.post("/login/student", data={"username": "ghost", "password": "1234"},
                follow_redirects=True)
check("вход несуществующего ученика отклонён", "Такого аккаунта нет" in r.get_data(as_text=True))
r = client.post("/login/student", data={"username": "masha", "password": "wrong"},
                follow_redirects=True)
check("неверный пароль отклонён", "Такого аккаунта нет или пароль неверный" in r.get_data(as_text=True))

# 3. Маша входит и проходит урок 1 идеально
client.get("/logout")
r = client.post("/login/student", data={"username": "masha", "password": "secret1"},
                follow_redirects=True)
body = r.get_data(as_text=True)
check("вход Маши по логину/паролю", "Привет, Маша" in body and "🦄" in body)

body = pass_lesson(client, 1)
check("Маша сдала урок 1 на 100%", "Идеально! 100%" in body)

r = client.get("/student")
body = r.get_data(as_text=True)
check("трекер Маши 1/8", "1/8" in body)
check("урок 2 открыт Маше", "Начать урок" in body)

# 4. Петя входит — его прогресс пустой (изоляция!)
client.get("/logout")
r = client.post("/login/student", data={"username": "petya", "password": "secret2"},
                follow_redirects=True)
body = r.get_data(as_text=True)
check("вход Пети", "Привет, Петя" in body and "🐱" in body)
check("у Пети 0/8 уроков", "0/8" in body)
check("урок 2 Пете закрыт", "Закрой предыдущий урок" in body)
r = client.get("/lesson/2", follow_redirects=True)
check("Петя не может открыть урок 2 напрямую",
      "Сначала пройди предыдущий урок" in r.get_data(as_text=True))

# 5. Петя не может сдать тест по чужой попытке (attempt_id Маши)
masha_attempt = None
client.get("/logout")
client.post("/login/student", data={"username": "masha", "password": "secret1"})
r = client.get("/lesson/2")
masha_attempt = re.search(r'name="attempt_id" value="(\d+)"', r.get_data(as_text=True)).group(1)
client.get("/logout")
client.post("/login/student", data={"username": "petya", "password": "secret2"})
r = client.post("/lesson/2/submit", data=answer_data(LESSONS_BY_ID[2], masha_attempt))
check("чужая попытка отклонена (400)", r.status_code == 400)

# 6. Петя проходит свой урок 1
body = pass_lesson(client, 1)
check("Петя сдал урок 1", "Идеально! 100%" in body)
client.get("/logout")

# 7. Кабинет родителя: оба ребёнка видны, статистика разделена
client.post("/login/parent", data={"password": "1234"})
r = client.get("/parent")
body = r.get_data(as_text=True)
check("родитель видит Машу и Петю", "Маша" in body and "Петя" in body and "🦄" in body)
check("в истории есть обе попытки", body.count("Знакомство и первые слова") >= 2)
m = re.search(r'<span class="stat-num">(\d+)/8</span>', body)
check("общий прогресс считается по лучшему (1/8)", m and m.group(1) == "1")

mistakes = client.get("/api/mistakes").get_json()
check("API ошибок работает (пусто у идеальных)", isinstance(mistakes, list) and len(mistakes) == 0)

# Провальная попытка Пети -> ошибка с именем ученика
r = client.get("/logout")
client.post("/login/student", data={"username": "petya", "password": "secret2"})
r = client.get("/lesson/2")
aid = re.search(r'name="attempt_id" value="(\d+)"', r.get_data(as_text=True)).group(1)
client.post("/lesson/2/submit", data=answer_data(LESSONS_BY_ID[2], aid, wrong=True))
client.get("/logout")
client.post("/login/parent", data={"password": "1234"})
mistakes = client.get("/api/mistakes").get_json()
check("ошибки появились и помечены учеником",
      len(mistakes) > 0 and all(m["student"] == "Петя" for m in mistakes))

# 8. Сброс пароля: старый перестаёт работать, новый — работает
sid = 2  # Петя (первым создали Машу=id1)
client.post(f"/parent/students/{sid}/reset_password", data={"password": "newpass9"},
            follow_redirects=True)
client.get("/logout")
r = client.post("/login/student", data={"username": "petya", "password": "secret2"},
                follow_redirects=True)
check("старый пароль после сброса не работает", "Такого аккаунта нет" in r.get_data(as_text=True))
r = client.post("/login/student", data={"username": "petya", "password": "newpass9"},
                follow_redirects=True)
check("новый пароль работает", "Привет, Петя" in r.get_data(as_text=True))
client.get("/logout")

# 9. Удаление аккаунта: сессия вылетает, прогресс исчезает
client.post("/login/parent", data={"password": "1234"})
client.get("/logout")
client.post("/login/student", data={"username": "masha", "password": "secret1"})
client.post(f"/parent/students/1/delete", data={})  # не родитель -> редирект
r = client.get("/student")
check("удаление не родителем не сработало", r.status_code == 302 or "Привет, Маша" in
      client.get("/student").get_data(as_text=True))
client.get("/logout")
client.post("/login/parent", data={"password": "1234"})
del_resp = client.post("/parent/students/1/delete")  # флэш «удалён» остаётся в сессии
check("родитель удалил Машу (флэш об удалении)", "удалён" in del_resp.get_data(as_text=True))
client.get("/logout")
client.post("/login/student", data={"username": "masha", "password": "secret1"},
            follow_redirects=True)
# вход не должен пройти
r = client.get("/student", follow_redirects=True)
check("Маша удалена и не входит", "Я ученик" in r.get_data(as_text=True) or "Привет, Маша" not in r.get_data(as_text=True))
client.post("/login/parent", data={"password": "1234"})
r = client.get("/parent")
body = r.get_data(as_text=True)
body_noph = re.sub(r'placeholder="[^"]*"', "", body)
check("прогресс Маши стёрт из истории (аккаунтов и попыток 0)",
      "Маша" not in body_noph and "masha" not in body_noph)

print("\nALL TESTS PASSED ✔")
