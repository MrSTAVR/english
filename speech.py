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
