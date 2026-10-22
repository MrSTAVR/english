# -*- coding: utf-8 -*-
"""Логопедическая часть: логопеды и их ученики (семейные аккаунты — ими пользуются родители).

Отдельно от «English Fun»: свои таблицы (sp_*), свои страницы (routes/speech.py)."""
import re
from datetime import date, datetime

from security import hash_password

USERNAME_RE = r"[a-zA-Z0-9_.\-]{2,20}"
MIN_PASSWORD = 6


def valid_username(name):
    return bool(re.fullmatch(USERNAME_RE, name or ""))


def _now():
    return datetime.now().isoformat(timespec="seconds")


def parse_date(raw):
    try:
        return datetime.strptime((raw or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def age_text(birth, today=None):
    """«5 лет 3 мес.» по дате рождения (ISO-строка)."""
    b = parse_date(birth)
    if not b:
        return ""
    t = today or date.today()
    months = (t.year - b.year) * 12 + t.month - b.month - (t.day < b.day)
    if months < 0:
        return ""
    y, m = divmod(months, 12)
    word = "год" if y % 10 == 1 and y % 100 != 11 else "года" if 2 <= y % 10 <= 4 and not 12 <= y % 100 <= 14 else "лет"
    return f"{y} {word}" + (f" {m} мес." if m else "")


def check_account(db, username, password, table):
    """Текст ошибки или None. table — sp_logopeds или sp_clients (логин уникален в своей таблице)."""
    if not valid_username(username):
        return "Логин: только английские буквы, цифры, точка/дефис/подчёркивание, 2–20 символов."
    if len(password or "") < MIN_PASSWORD:
        return f"Пароль должен быть не короче {MIN_PASSWORD} символов."
    if db.execute(f"SELECT 1 FROM {table} WHERE username=?", (username,)).fetchone():
        return f"Логин «{username}» уже занят."
    return None


def create_logoped(db, username, name, password):
    err = check_account(db, username, password, "sp_logopeds") or (None if name.strip() else "Укажите имя логопеда.")
    if err:
        return None, err
    cur = db.execute("INSERT INTO sp_logopeds (username, name, password_hash, created_at) VALUES (?, ?, ?, ?)",
                     (username.lower(), name.strip()[:60], hash_password(password), _now()))
    db.commit()
    return cur.lastrowid, None


def clean_client_fields(form):
    """Поля карточки из формы: (dict, ошибка)."""
    child = (form.get("child_name") or "").strip()[:60]
    if not child:
        return None, "Укажите имя ребёнка."
    raw_birth = (form.get("birth_date") or "").strip()
    birth = parse_date(raw_birth)
    if raw_birth and (not birth or birth > date.today() or birth.year < 1990):
        return None, "Дата рождения некорректна."
    return {"child_name": child, "birth_date": birth.isoformat() if birth else None,
            "parent_name": (form.get("parent_name") or "").strip()[:60],
            "phone": (form.get("phone") or "").strip()[:30]}, None


def create_client(db, logoped_id, form):
    fields, err = clean_client_fields(form)
    username = (form.get("username") or "").strip().lower()
    err = err or check_account(db, username, form.get("password"), "sp_clients")
    if err:
        return None, err
    cur = db.execute("INSERT INTO sp_clients (logoped_id, child_name, birth_date, parent_name, phone, username, "
                     "password_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (logoped_id, fields["child_name"], fields["birth_date"], fields["parent_name"], fields["phone"],
                      username, hash_password(form.get("password")), _now()))
    db.commit()
    return cur.lastrowid, None


def client_of(db, logoped_id, client_id):
    """Ученик, только если он принадлежит этому логопеду."""
    return db.execute("SELECT * FROM sp_clients WHERE id=? AND logoped_id=?", (client_id, logoped_id)).fetchone()


def clients(db, logoped_id, archived=False):
    return db.execute("SELECT * FROM sp_clients WHERE logoped_id=? AND archived=? ORDER BY child_name COLLATE NOCASE",
                      (logoped_id, int(archived))).fetchall()


# ---------------------------------------------------------------- карточка и звуковая карта

SOUND_GROUPS = [
    ("Свистящие", ["С", "Сь", "З", "Зь", "Ц"]),
    ("Шипящие", ["Ш", "Ж", "Ч", "Щ"]),
    ("Сонорные", ["Л", "Ль", "Р", "Рь"]),
    ("Заднеязычные", ["К", "Кь", "Г", "Гь", "Х", "Хь"]),
    ("Другие", ["Й", "Т", "Д", "Н", "В", "Ф", "Б", "П", "М"]),
]
ALL_SOUNDS = [snd for _g, group in SOUND_GROUPS for snd in group]
# (для логопеда, для родителей)
STAGES = [
    ("нарушен", "пока не получается"),
    ("постановка", "учимся правильно произносить"),
    ("автоматизация: слоги", "тренируем в слогах"),
    ("автоматизация: слова", "тренируем в словах"),
    ("автоматизация: фразы", "тренируем во фразах"),
    ("автоматизация: связная речь", "тренируем в рассказе"),
    ("дифференциация", "учимся не путать с похожими звуками"),
    ("введён в речь", "говорим правильно! 🎉"),
]
DONE_STAGE = len(STAGES) - 1


def get_card(db, client_id):
    r = db.execute("SELECT * FROM sp_card WHERE client_id=?", (client_id,)).fetchone()
    return {"diagnosis": r["diagnosis"], "program": r["program"], "updated_at": r["updated_at"]} if r else \
        {"diagnosis": "", "program": "", "updated_at": None}


def save_card(db, client_id, diagnosis, program):
    db.execute("INSERT INTO sp_card (client_id, diagnosis, program, updated_at) VALUES (?, ?, ?, ?) "
               "ON CONFLICT(client_id) DO UPDATE SET diagnosis=excluded.diagnosis, program=excluded.program, "
               "updated_at=excluded.updated_at",
               (client_id, (diagnosis or "").strip()[:5000], (program or "").strip()[:10000], _now()))
    db.commit()


def sound_map(db, client_id):
    """Звуки в работе в порядке ALL_SOUNDS: стадия, подписи, процент пути."""
    rows = {r["sound"]: r for r in db.execute("SELECT * FROM sp_sounds WHERE client_id=?", (client_id,))}
    out = []
    for snd in ALL_SOUNDS:
        r = rows.get(snd)
        if r:
            st = max(0, min(DONE_STAGE, r["stage"]))
            out.append({"sound": snd, "stage": st, "label": STAGES[st][0], "family": STAGES[st][1],
                        "percent": round(100 * st / DONE_STAGE), "note": r["note"], "done": st == DONE_STAGE})
    return out


def set_sound(db, client_id, sound, stage, note=""):
    """Добавляет звук в работу или меняет стадию. Смена стадии пишется в историю."""
    if sound not in ALL_SOUNDS or not 0 <= stage <= DONE_STAGE:
        return False
    prev = db.execute("SELECT stage FROM sp_sounds WHERE client_id=? AND sound=?", (client_id, sound)).fetchone()
    db.execute("INSERT INTO sp_sounds (client_id, sound, stage, note, updated_at) VALUES (?, ?, ?, ?, ?) "
               "ON CONFLICT(client_id, sound) DO UPDATE SET stage=excluded.stage, note=excluded.note, "
               "updated_at=excluded.updated_at", (client_id, sound, stage, (note or "").strip()[:200], _now()))
    if not prev or prev["stage"] != stage:
        db.execute("INSERT INTO sp_sound_log (client_id, sound, stage, day) VALUES (?, ?, ?, ?)",
                   (client_id, sound, stage, date.today().isoformat()))
    db.commit()
    return True


def remove_sound(db, client_id, sound):
    db.execute("DELETE FROM sp_sounds WHERE client_id=? AND sound=?", (client_id, sound))
    db.commit()


def sound_history(db, client_id, limit=30):
    rows = db.execute("SELECT * FROM sp_sound_log WHERE client_id=? ORDER BY id DESC LIMIT ?", (client_id, limit))
    return [{"sound": r["sound"], "label": STAGES[max(0, min(DONE_STAGE, r["stage"]))][0],
             "day": datetime.strptime(r["day"], "%Y-%m-%d").strftime("%d.%m.%Y")} for r in rows]
