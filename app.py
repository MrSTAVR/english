# -*- coding: utf-8 -*-
"""app.py — веб-приложение «Английский для дочки» на Flask + SQLite.

Что внутри:
  * Режим ученика: уроки (материал -> упражнения -> итоговый тест),
    трекер успеваемости и ачивки за прохождения.
  * Режим родителя: время, потраченное на каждый урок/тест, все ошибки
    с правильными ответами, прогресс и достижения.
"""

import hashlib
import hmac
import json
import os
import random
import sqlite3
import sys
from datetime import datetime
from markupsafe import Markup

from flask import (Flask, abort, flash, g, jsonify, redirect,
                   render_template, request, session, url_for)

from data.lessons import LESSONS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "english_app.db")

app = Flask(__name__)

# Постоянный секретный ключ, чтобы сессии не сбрасывались после перезапуска
SECRET_FILE = os.path.join(BASE_DIR, ".secret_key")
if not os.path.exists(SECRET_FILE):
    with open(SECRET_FILE, "w") as f:
        f.write(os.urandom(24).hex())
with open(SECRET_FILE) as f:
    app.secret_key = f.read().strip()

LESSONS_BY_ID = {l["id"]: l for l in LESSONS}
PASS_MARK = 70          # минимальный процент, чтобы тест считаться сданным
PARENT_PASSWORD = "1234"  # пароль для входа в режим родителя (можно поменять)


# ---------------------------------------------------------------------------
# Пароли: хешируем PBKDF2 + случайная соль (в базе хранится только хеш)
# ---------------------------------------------------------------------------

PBKDF2_ROUNDS = 120_000


def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 salt, PBKDF2_ROUNDS)
    return f"pbkdf2${salt.hex()}${digest.hex()}"


def verify_password(stored, password):
    try:
        algo, salt_hex, digest_hex = str(stored).split("$")
        if algo != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                     bytes.fromhex(salt_hex), PBKDF2_ROUNDS)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False

# ---------------------------------------------------------------------------
# База данных
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT NOT NULL UNIQUE COLLATE NOCASE,  -- логин для входа
    display_name TEXT NOT NULL,                        -- имя на странице урока
    password_hash TEXT NOT NULL,                       -- PBKDF2-хеш пароля
    emoji        TEXT DEFAULT '🎒',                    -- аватарка для ребёнка
    created_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER,                         -- за кем попытка (NULL = старые данные)
    lesson_id     INTEGER NOT NULL,
    started_at    TEXT NOT NULL,             -- ISO, когда открыли урок
    finished_at   TEXT,                      -- ISO, когда сдали тест
    seconds_spent INTEGER DEFAULT 0,         -- сколько секунд потратили
    score_percent REAL DEFAULT 0,            -- результат теста в %
    passed        INTEGER DEFAULT 0,         -- тест сдан?
    total_q       INTEGER DEFAULT 0,
    correct_q     INTEGER DEFAULT 0,
    mistakes_json TEXT DEFAULT '[]',         -- [{question, given, correct}]
    details_json  TEXT DEFAULT '{}'          -- полные результаты по каждому вопросу
);
CREATE TABLE IF NOT EXISTS achievements (
    student_id   INTEGER NOT NULL,
    key          TEXT NOT NULL,
    earned_at    TEXT NOT NULL,
    PRIMARY KEY (student_id, key)
);
CREATE TABLE IF NOT EXISTS garden (
    student_id     INTEGER PRIMARY KEY,        -- сад принадлежит ученику
    coins          INTEGER DEFAULT 0,          -- монетки за уроки
    streak_days    INTEGER DEFAULT 0,          -- серия дней занятий
    best_streak    INTEGER DEFAULT 0,          -- рекорд серии (для дерева)
    last_study_day TEXT,                       -- ISO-дата последнего занятия
    broken         INTEGER DEFAULT 0           -- 1 = серия прервана, сад «опустел»
);
CREATE TABLE IF NOT EXISTS decorations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,               -- кому принадлежит украшение
    deco_key   TEXT NOT NULL,                  -- ключ из DECORATIONS
    slot       INTEGER NOT NULL                 -- слот на дереве (0..MAX_SLOTS-1)
);
"""



def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    # Миграция старых баз: добавляем недостающие колонки/таблицы
    cols = {r[1] for r in conn.execute("PRAGMA table_info(attempts)")}
    if "student_id" not in cols:
        conn.execute("ALTER TABLE attempts ADD COLUMN student_id INTEGER")
    g_cols = {r[1] for r in conn.execute("PRAGMA table_info(garden)")}
    if g_cols and "manual" not in g_cols:
        conn.execute("ALTER TABLE garden ADD COLUMN manual INTEGER DEFAULT 0")
    ach_cols = [r[1] for r in conn.execute("PRAGMA table_info(achievements)")]
    if ach_cols and "student_id" not in ach_cols:
        # старая таблица ачивок без привязки к ученику — пересоздаём
        conn.execute("DROP TABLE achievements")
        conn.executescript(SCHEMA)
    # индекс уникальности для новой таблицы ачивок уже задан PRIMARY KEY
    conn.commit()
    conn.close()


init_db()

# ---------------------------------------------------------------------------
# Ачивки (достижения)
# Функции-проверки получают словарь stats (см. compute_stats)
# ---------------------------------------------------------------------------

ACHIEVEMENTS = [
    {"key": "first_lesson", "emoji": "🚀", "title": "Первый шаг!",
     "desc": "Пройден первый урок и сдан первый тест.",
     "check": lambda s: s["lessons_completed"] >= 1},
    {"key": "three_lessons", "emoji": "⭐", "title": "Три урока позади",
     "desc": "Успешно пройдено три урока.",
     "check": lambda s: s["lessons_completed"] >= 3},
    {"key": "all_lessons", "emoji": "🏆", "title": "Английский чемпион!",
     "desc": "Пройдены ВСЕ уроки в приложении.",
     "check": lambda s: s["lessons_completed"] >= len(LESSONS)},
    {"key": "perfect_test", "emoji": "💯", "title": "Идеальный тест",
     "desc": "Тест решён без единой ошибки.",
     "check": lambda s: s["has_perfect"]},
    {"key": "streak5", "emoji": "🔥", "title": "Огонь-машина",
     "desc": "Подряд 5 (или больше) правильных ответов в тесте.",
     "check": lambda s: s["max_streak"] >= 5},
    {"key": "clean_three", "emoji": "🧹", "title": "Чистая работа",
     "desc": "Три теста подряд без ошибок.",
     "check": lambda s: s["best_clean_run"] >= 3},
    {"key": "words50", "emoji": "📚", "title": "Книжный червь",
     "desc": "Выучено 50+ слов из пройденных уроков.",
     "check": lambda s: s["words_learned"] >= 50},
    {"key": "time60", "emoji": "⏰", "title": "Час упорства",
     "desc": "Суммарно час занятий английским.",
     "check": lambda s: s["total_minutes"] >= 60},
    {"key": "five_lessons", "emoji": "🚂", "title": "Паровозик",
     "desc": "Пройдено пять уроков — полный ход!",
     "check": lambda s: s["lessons_completed"] >= 5},
    {"key": "half_way", "emoji": "🌗", "title": "Половинка пути",
     "desc": "Пройдена половина всех уроков.",
     "check": lambda s: len(LESSONS) and s["lessons_completed"] * 2 >= len(LESSONS)},
    {"key": "streak10", "emoji": "☄️", "title": "Комета",
     "desc": "Подряд 10 правильных ответов в тесте!",
     "check": lambda s: s["max_streak"] >= 10},
    {"key": "words100", "emoji": "🦉", "title": "Мудрая сова",
     "desc": "Выучено 100+ слов из пройденных уроков.",
     "check": lambda s: s["words_learned"] >= 100},
    {"key": "attempts5", "emoji": "🔄", "title": "Упорный бобрик",
     "desc": "Пятая попытка теста — не сдаёшься, молодец!",
     "check": lambda s: len(s["attempts"]) >= 5},
    {"key": "time180", "emoji": "🧘", "title": "Три часа труда",
     "desc": "Суммарно три часа занятий английским.",
     "check": lambda s: s["total_minutes"] >= 180},
    {"key": "diamond", "emoji": "💎", "title": "Алмазная коллекция",
     "desc": "Идеальных тестов (100%) уже пять штук!",
     "check": lambda s: s["perfect_count"] >= 5},
    {"key": "first_try_perfect", "emoji": "✨", "title": "Безупречный урок",
     "desc": "Урок сдан с первой попытки и без единой ошибки.",
     "check": lambda s: s["first_try_perfect"]},
]


# ---------------------------------------------------------------------------
# Подсчёт статистики
# ---------------------------------------------------------------------------

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
        expected = {int(k): int(v) for k, v in q["pairs"].items()}
        got = parse_pairs(given)
        ok = got == expected
        disp = ", ".join(f"{q['left'][li]} ↔ {q['right'][ri]}"
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


def compute_stats(db, student_id=None):
    """Статистика по попыткам — используется для ачивок и трекера.

    student_id=None — общая статистика (кабинет родителя),
    student_id=<id> — статистика конкретного ученика.
    """
    if student_id is None:
        rows = db.execute(
            "SELECT * FROM attempts WHERE finished_at IS NOT NULL "
            "ORDER BY finished_at ASC, id ASC").fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM attempts WHERE finished_at IS NOT NULL AND student_id=? "
            "ORDER BY finished_at ASC, id ASC", (student_id,)).fetchall()

    best_by_lesson = {}   # лучший результат по каждому уроку
    max_streak = 0
    best_clean_run = 0
    current_clean_run = 0
    has_perfect = False
    perfect_count = 0
    first_try_perfect = False
    total_seconds = 0
    total_mistakes = 0
    attempts_by_lesson = {}

    for r in rows:
        total_seconds += r["seconds_spent"] or 0
        try:
            details = json.loads(r["details_json"] or "{}")
        except Exception:
            details = {}
        results = details.get("results", [])
        streak = cur = 0
        for item in results:
            if item.get("correct"):
                cur += 1
                streak = max(streak, cur)
            else:
                cur = 0
        max_streak = max(max_streak, streak)

        lid = r["lesson_id"]
        attempts_by_lesson[lid] = attempts_by_lesson.get(lid, 0) + 1
        if r["passed"]:
            if lid not in best_by_lesson or r["score_percent"] > best_by_lesson[lid]["score_percent"]:
                best_by_lesson[lid] = r
            if r["mistakes_json"] and len(json.loads(r["mistakes_json"])) == 0:
                has_perfect = True
                perfect_count += 1
                if attempts_by_lesson[lid] == 1:
                    first_try_perfect = True
                best_clean_run += 1
                current_clean_run = max(current_clean_run, best_clean_run)
            else:
                best_clean_run = 0
        else:
            best_clean_run = 0

        try:
            total_mistakes += len(json.loads(r["mistakes_json"] or "[]"))
        except Exception:
            pass

    completed_ids = sorted(best_by_lesson.keys())
    words_learned = sum(len(LESSONS_BY_ID[i]["material"]) for i in completed_ids)

    return {
        "attempts": rows,
        "best_by_lesson": best_by_lesson,
        "lessons_completed": len(completed_ids),
        "completed_ids": set(completed_ids),
        "avg_score": (sum(r["score_percent"] for r in best_by_lesson.values()) / len(best_by_lesson))
                     if best_by_lesson else 0.0,
        "total_seconds": total_seconds,
        "total_minutes": round(total_seconds / 60),
        "max_streak": max_streak,
        "best_clean_run": current_clean_run,
        "has_perfect": has_perfect,
        "perfect_count": perfect_count,
        "first_try_perfect": first_try_perfect,
        "words_learned": words_learned,
        "total_mistakes": total_mistakes,
    }


# ---------------------------------------------------------------------------
# 🌳 Сад: деревья растут от серии дней, монетки, украшения для всего сада
# ---------------------------------------------------------------------------

MAX_SLOTS = 3      # сколько украшений можно разместить в саду
STREAK_CAP = 30    # серия ограничена 30 днями: дальше сад не растёт
COIN_PASS = 5      # монеток за сданный тест
COIN_PERFECT = 5   # бонусных монеток за идеальный тест (100%)
TREES_START = 1    # стартовое число деревьев в саду
TREES_MAX = 6      # максимум деревьев
TREES_PER_DAYS = 5 # каждое новое дерево — за каждые N дней серии


def tree_count_for(streak_days):
    """Сколько деревьев в саду при данной серии дней (серия <= STREAK_CAP)."""
    return min(TREES_MAX, TREES_START + streak_days // TREES_PER_DAYS)


# category:
#   span   — растягивается на ВЕСЬ сад (гирлянда, флажки, огни, заборчик)
#   sky    — украшение неба над всем садом (солнце, радуга, звёзды, луна, облака)
#   effect — погодный/сказочный эффект на весь сад (снег, лепестки, светлячки)
#   theme  — фон сада; можно выбрать только ОДИН (покупка нового заменяет старый)
DECORATIONS = [
    {"key": "garland",   "emoji": "💡", "name": "Гирлянда",        "cost": 10, "category": "span"},
    {"key": "flags",     "emoji": "🚩", "name": "Флажки",          "cost": 12, "category": "span"},
    {"key": "lights",    "emoji": "🎊", "name": "Огни-бусы",       "cost": 16, "category": "span"},
    {"key": "fence",     "emoji": None,  "name": "Заборчик",       "cost": 8,  "category": "span"},
    {"key": "sun",       "emoji": "☀️", "name": "Солнышко",        "cost": 8,  "category": "sky"},
    {"key": "rainbow",   "emoji": "🌈", "name": "Радуга",          "cost": 30, "category": "sky"},
    {"key": "stars",     "emoji": "✨", "name": "Звёздное небо",   "cost": 15, "category": "sky"},
    {"key": "moon",      "emoji": "🌙", "name": "Луна",            "cost": 18, "category": "sky"},
    {"key": "clouds",    "emoji": "☁️", "name": "Облачка",         "cost": 10, "category": "sky"},
    {"key": "snow",      "emoji": "❄️", "name": "Снежинки",        "cost": 20, "category": "effect"},
    {"key": "petals",    "emoji": "🌸", "name": "Лепестки сакуры", "cost": 22, "category": "effect"},
    {"key": "fireflies", "emoji": "🧚", "name": "Светлячки",       "cost": 25, "category": "effect"},
    {"key": "night",     "emoji": "🌌", "name": "Ночной фон",      "cost": 28, "category": "theme"},
    {"key": "sunset",    "emoji": "🌇", "name": "Закат",           "cost": 28, "category": "theme"},
]
DECOS_BY_KEY = {d["key"]: d for d in DECORATIONS}

CATEGORY_NAMES = {
    "span": "на весь сад", "sky": "украшение неба", "effect": "эффект",
    "theme": "фон сада (можно выбрать только один)",
}

# SVG-иконки для магазина вместо emoji, которые плохо рисуются на Windows
DECO_ICONS = {
    "fence": '''<svg viewBox="0 0 48 32" xmlns="http://www.w3.org/2000/svg">'''
             '''<rect x="4" y="4" width="7" height="26" rx="3" fill="#c99a5b"/>'''
             '''<rect x="20.5" y="4" width="7" height="26" rx="3" fill="#c99a5b"/>'''
             '''<rect x="37" y="4" width="7" height="26" rx="3" fill="#c99a5b"/>'''
             '''<rect x="0" y="10" width="48" height="5" rx="2.5" fill="#a87941"/>'''
             '''<rect x="0" y="21" width="48" height="5" rx="2.5" fill="#a87941"/></svg>''',
}

# SVG-глифы стадий дерева (видны на всех платформах, в отличие от emoji)
TREE_GLYPHS = {
    "acorn": '''<g><path d="M30 26c0-8 4-12 10-12s10 4 10 12-4 16-10 16-10-8-10-16z" fill="#a56a2f"/><path d="M28 26q12-10 24 0-4 6-12 6-8 0-12-6z" fill="#6d4322"/></g>''',
    "sprout": '''<g><path d="M40 46V28" stroke="#3fae5a" stroke-width="4" stroke-linecap="round"/><path d="M40 32C32 30 28 24 28 18c8 0 13 6 12 14z" fill="#5cc46f"/><path d="M40 32c8-2 12-8 12-14-8 0-13 6-12 14z" fill="#41b257"/></g>''',
    "seedling": '''<g><path d="M40 48V22" stroke="#3fae5a" stroke-width="4" stroke-linecap="round"/><path d="M40 30C30 28 24 20 24 12c12 0 18 8 16 18z" fill="#5cc46f"/><path d="M40 30c10-2 16-10 16-18-12 0-18 8-16 18z" fill="#41b257"/><path d="M40 22c-3-5-2-10 0-14 3 4 3 9 0 14z" fill="#6fd47f"/></g>''',
    "bushy": '''<g><path d="M40 48V26" stroke="#8a5a2b" stroke-width="5" stroke-linecap="round"/><circle cx="30" cy="26" r="10" fill="#5cc46f"/><circle cx="50" cy="26" r="10" fill="#5cc46f"/><circle cx="40" cy="18" r="11" fill="#6fd47f"/></g>''',
    "young": '''<g><path d="M40 48V24" stroke="#8a5a2b" stroke-width="5" stroke-linecap="round"/><path d="M40 32l-8-6M40 28l8-6" stroke="#8a5a2b" stroke-width="3" stroke-linecap="round"/><circle cx="40" cy="16" r="13" fill="#5cc46f"/><circle cx="30" cy="22" r="8" fill="#41b257"/><circle cx="50" cy="22" r="8" fill="#6fd47f"/></g>''',
    "tree": '''<g><path d="M40 48V22" stroke="#8a5a2b" stroke-width="6" stroke-linecap="round"/><path d="M40 30l-10-8M40 26l10-8" stroke="#8a5a2b" stroke-width="4" stroke-linecap="round"/><circle cx="40" cy="15" r="14" fill="#41b257"/><circle cx="27" cy="22" r="9" fill="#5cc46f"/><circle cx="53" cy="22" r="9" fill="#3fae5a"/></g>''',
    "lush": '''<g><path d="M40 48V20" stroke="#7a4d22" stroke-width="7" stroke-linecap="round"/><path d="M40 30l-12-9M40 24l12-9" stroke="#7a4d22" stroke-width="4" stroke-linecap="round"/><circle cx="40" cy="14" r="15" fill="#3fae5a"/><circle cx="25" cy="20" r="10" fill="#5cc46f"/><circle cx="55" cy="20" r="10" fill="#41b257"/><circle cx="40" cy="24" r="10" fill="#6fd47f"/></g>''',
    "blooming": '''<g><path d="M40 48V20" stroke="#7a4d22" stroke-width="7" stroke-linecap="round"/><path d="M40 30l-12-9M40 24l12-9" stroke="#7a4d22" stroke-width="4" stroke-linecap="round"/><circle cx="40" cy="14" r="15" fill="#41b257"/><circle cx="25" cy="20" r="10" fill="#5cc46f"/><circle cx="55" cy="20" r="10" fill="#3fae5a"/><circle cx="34" cy="10" r="3" fill="#ff8fb3"/><circle cx="47" cy="15" r="3" fill="#ffd166"/><circle cx="40" cy="22" r="3" fill="#ff8fb3"/></g>''',
    "big": '''<g><path d="M40 48V18" stroke="#6d4322" stroke-width="8" stroke-linecap="round"/><path d="M40 30l-14-10M40 24l14-10M40 36l10 6" stroke="#6d4322" stroke-width="4" stroke-linecap="round"/><circle cx="40" cy="12" r="16" fill="#3fae5a"/><circle cx="22" cy="20" r="11" fill="#5cc46f"/><circle cx="58" cy="20" r="11" fill="#41b257"/><circle cx="40" cy="24" r="10" fill="#6fd47f"/></g>''',
    "huge": '''<g><path d="M40 48V16" stroke="#6d4322" stroke-width="9" stroke-linecap="round"/><path d="M40 28l-16-10M40 22l16-10M40 36l12 6M40 36l-12 6" stroke="#6d4322" stroke-width="4" stroke-linecap="round"/><circle cx="40" cy="10" r="17" fill="#3fae5a"/><circle cx="20" cy="18" r="12" fill="#5cc46f"/><circle cx="60" cy="18" r="12" fill="#41b257"/><circle cx="40" cy="22" r="11" fill="#6fd47f"/><circle cx="30" cy="8" r="3" fill="#ffd166"/><circle cx="50" cy="12" r="3" fill="#ff8fb3"/></g>''',
    "legendary": '''<g><path d="M40 48V14" stroke="#5a3a1e" stroke-width="10" stroke-linecap="round"/><path d="M40 26l-18-10M40 20l18-10M40 36l14 6M40 36l-14 6" stroke="#5a3a1e" stroke-width="4" stroke-linecap="round"/><circle cx="40" cy="8" r="18" fill="#2f9e44"/><circle cx="18" cy="16" r="13" fill="#5cc46f"/><circle cx="62" cy="16" r="13" fill="#41b257"/><circle cx="40" cy="20" r="12" fill="#6fd47f"/><path d="M33 -2l3 5 3-5 3 5 3-5v7h-12z" fill="#ffd166" transform="translate(2,6)"/><circle cx="28" cy="6" r="2.5" fill="#fff3bf"/><circle cx="52" cy="10" r="2.5" fill="#fff3bf"/></g>''',
}

# 31 стадия: по одной на каждый день серии (0..30).
# Правила «заметных изменений»:
#   • новое дерево появляется каждые TREES_PER_DAYS дней серии;
#   • в оставшиеся дни у ВСЕХ деревьев меняется форма кроны (глиф) и/или
#     заметно подрастает ствол (размер +7% в день);
#   • глифы чередуются так, что соседние дни никогда не выглядят одинаково.
_STAGE_GLYPHS = ["acorn", "sprout", "seedling", "bushy", "young", "tree",
                 "lush", "blooming", "big", "huge", "legendary"]

def _stage_glyph(day):
    """Глиф дерева для дня серии: от жёлудя до легендарного дерева.

    Каждый новый глиф — это видимое изменение формы кроны. Чтобы форма
    менялась буквально каждый день, к основному «взрослому» глифу дня
    добавляется ежедневная деталь (цветки/плоды/сияние), см. DAY_ACCENTS.
    """
    idx = round(day / STREAK_CAP * (len(_STAGE_GLYPHS) - 1))
    return _STAGE_GLYPHS[idx]


# Ежедневные детали кроны — гарантируют, что день ко дню дерево выглядит иначе.
# Цикл из 7 деталей: в любой день серии хотя бы одна деталь активна.
DAY_ACCENTS = [
    (" blossoms", "#ff8fb3"),   # розовые цветки
    ("fruits", "#ffd166"),      # золотые плоды
    ("berries", "#e4572e"),     # ягодки
    ("sparkles", "#fff3bf"),    # искорки
    ("leaves-gold", "#f4a259"), # золотая листва
    ("snow-dust", "#e0f7ff"),   # снежная пыль
    ("glow", "#b7f7c7"),        # зелёное сияние
]

def day_accent(day):
    """Деталь дня None на нулевом дне и в день появления нового дерева."""
    if day <= 0 or day % TREES_PER_DAYS == 0:
        return None
    return DAY_ACCENTS[day % len(DAY_ACCENTS)]


def tree_glyphs_for(streak, count):
    """Форма кроны для каждого дерева сада.

    Главное дерево (i=0) показывает «общую» стадию сада; соседние деревья
    отстают на несколько дней — визуально сад выглядит живым и разным,
    а не рядом одинаковых копий.
    """
    return [_stage_glyph(max(0, streak - i * 2)) for i in range(count)]

TREE_STAGES = []
for _d in range(STREAK_CAP + 1):
    new_tree = _d > 0 and _d % TREES_PER_DAYS == 0
    if _d == 0:
        _name, _msg = "Жёлудь", "Всё большое начинается с маленького зёрнышка!"
    elif _d == 1:
        _name, _msg = "Росток", "Первый день занятий — росток проклюнулся! 🌱"
    elif new_tree:
        _n = tree_count_for(_d)
        _name, _msg = f"Новое дерево!", f"В саду появилось дерево — теперь их {_n}! 🎉"
    elif _d == STREAK_CAP:
        _name, _msg = "Легендарный сад", "ТРИДЦАТЬ дней подряд! Ты — легенда! 👑"
    else:
        acc = day_accent(_d)
        _name = f"День {_d}"
        _msg = (f"Деревья меняют форму: {acc[0].strip()}! Ещё +7% роста 🌿"
                if acc else f"Сад стал выше и крепче — ещё на чуть-чуть! 🌿")
    TREE_STAGES.append({
        "min": _d,
        "size": round(0.5 + _d * 0.035, 3),   # 0.5 → ~1.55 за 30 дней (+7%/день)
        "glyph": _stage_glyph(_d),
        "accent": day_accent(_d),
        "new_tree": bool(new_tree),
        "emoji": "🌳",
        "name": _name,
        "msg": _msg,
    })
# emoji стадии подбираем по глифу
_EMOJI_BY_GLYPH = {"acorn": "🌰", "sprout": "🌱", "seedling": "🌿", "bushy": "🪴",
                   "young": "🌳", "tree": "🌳", "lush": "🌳", "blooming": "🌸",
                   "big": "🌳", "huge": "🌳", "legendary": "👑"}
for _s in TREE_STAGES:
    _s["emoji"] = _EMOJI_BY_GLYPH[_s["glyph"]]


def get_garden(db, student_id):
    """Строка сада (создаётся при первом обращении)."""
    row = db.execute("SELECT * FROM garden WHERE student_id=?",
                     (student_id,)).fetchone()
    if not row:
        db.execute("INSERT INTO garden (student_id) VALUES (?)", (student_id,))
        db.commit()
        row = db.execute("SELECT * FROM garden WHERE student_id=?",
                         (student_id,)).fetchone()
    return row


def tree_stage(streak_days):
    stage = TREE_STAGES[0]
    for s in TREE_STAGES:
        if streak_days >= s["min"]:
            stage = s
    return stage


def cap_streak(days):
    """Серия не может превышать STREAK_CAP дней."""
    return max(0, min(int(days), STREAK_CAP))


def compute_streak_from_history(db, student_id):
    """Реальная серия дней по датам попыток (для синхронизации после ручных правок)."""
    from datetime import timedelta
    rows = db.execute(
        "SELECT DISTINCT substr(started_at, 1, 10) AS d FROM attempts "
        "WHERE student_id=?", (student_id,)).fetchall()
    days = sorted({r["d"] for r in rows if r["d"]}, reverse=True)
    if not days:
        return 0, None
    today = datetime.now().date()
    last = datetime.strptime(days[0], "%Y-%m-%d").date()
    if (today - last).days > 1:      # последний заход был позавчера или раньше
        return 0, days[0]
    streak, expected = 1, last - timedelta(days=1)
    for d in days[1:]:
        if datetime.strptime(d, "%Y-%m-%d").date() == expected:
            streak += 1
            expected -= timedelta(days=1)
        else:
            break
    return streak, days[0]


def refresh_garden(db, student_id):
    """Синхронизирует сад с реальностью.

    Правила:
      • если сегодня/вчера были занятия — streak = реальная серия по истории;
      • если между последним занятием и сегодняшним днём пропущен хотя бы
        один день — серия считается прерванной: дерево возвращается к
        начальному размеру (жёлудь), украшения пропадают (монетки остаются);
      • родитель может вручную выставить streak/coins для теста — эти значения
        живут, пока ребёнок реально занимается (история попыток их подтверждает).
    """
    g = get_garden(db, student_id)
    hist_streak, last_day = compute_streak_from_history(db, student_id)
    stored = int(g["streak_days"])

    if hist_streak > 0:
        # есть свежие занятия: берём максимум из реального и «ручного» значения
        streak = cap_streak(max(hist_streak, stored))
        broken = 0
    elif stored > 0 and last_day is None:
        # истории нет, но родитель выставил серию вручную — доверяем (не выше 30)
        streak, broken = cap_streak(stored), 0
    else:
        streak = 0
        broken = 1 if stored > 0 or bool(g["broken"]) else 0
        if broken:
            db.execute("DELETE FROM decorations WHERE student_id=?", (student_id,))

    best = cap_streak(max(int(g["best_streak"]), streak))
    db.execute("UPDATE garden SET streak_days=?, best_streak=?, broken=?, "
               "last_study_day=? WHERE student_id=?",
               (streak, best, broken, last_day, student_id))
    db.commit()
    return get_garden(db, student_id)


def award_coins(db, student_id, percent, passed):
    """Начисляет монетки за тест. Возвращает число полученных монет."""
    earned = 0
    if passed:
        earned += COIN_PASS
    if percent >= 100:
        earned += COIN_PERFECT
    if earned:
        g = get_garden(db, student_id)
        db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?",
                   (earned, student_id))
        db.commit()
    return earned


def touch_streak(db, student_id):
    """Вызывается при открытии урока: продлевает/обнуляет серию дней."""
    g = get_garden(db, student_id)
    today = datetime.now().date().isoformat()
    last = g["last_study_day"]
    if last == today:
        return g
    from datetime import timedelta
    if last:
        delta = (datetime.now().date() -
                 datetime.strptime(last, "%Y-%m-%d").date()).days
        streak = g["streak_days"] + 1 if delta == 1 else 1
    else:
        # истории занятий ещё нет (или сад правили вручную) — просто фиксируем день
        streak = max(int(g["streak_days"]), 1)
    streak = cap_streak(streak)
    broken = 0                       # начала заниматься — сад «оживает»
    best = cap_streak(max(int(g["best_streak"]), streak))
    db.execute("UPDATE garden SET streak_days=?, best_streak=?, broken=?, "
               "last_study_day=? WHERE student_id=?",
               (streak, best, broken, today, student_id))
    db.commit()
    return get_garden(db, student_id)


def garden_view(db, student_id):
    """Всё нужное для рендера страницы сада."""
    g = get_garden(db, student_id)
    streak = cap_streak(g["streak_days"])
    stage = tree_stage(streak)
    next_stage = next((s for s in TREE_STAGES if s["min"] > streak), None)
    owned = db.execute(
        "SELECT deco_key, slot FROM decorations WHERE student_id=? ORDER BY slot",
        (student_id,)).fetchall()
    active = {r["slot"]: r["deco_key"] for r in owned}
    # группируем активные украшения по категориям — каждое действует на ВЕСЬ сад
    by_cat = {}
    for slot, key in active.items():
        d = DECOS_BY_KEY.get(key)
        if not d:
            continue
        item = {"key": key, "slot": slot, "name": d["name"],
                "emoji": d["emoji"], "cost": d["cost"]}
        by_cat.setdefault(d["category"], []).append(item)
    theme = by_cat.get("theme", [None])[0]  # фон: единственный активный (см. garden_buy)
    counts = {}
    for r in owned:
        counts[r["deco_key"]] = counts.get(r["deco_key"], 0) + 1
    tcount = tree_count_for(streak)
    trees = [{"i": i, "coin_bonus": (i + 1) * 2} for i in range(tcount)]
    return {
        "garden": g,
        "stage": stage,
        "next_stage": next_stage,
        "active": active,
        "by_cat": by_cat,
        "theme": theme,
        "cat_names": CATEGORY_NAMES,
        "tree_glyphs": tree_glyphs_for(streak, tcount),
        "owned_counts": counts,
        "decorations": DECORATIONS,
        "max_slots": MAX_SLOTS,
        "streak_cap": STREAK_CAP,
        "coin_pass": COIN_PASS,
        "coin_perfect": COIN_PERFECT,
        "tree_count": tcount,
        "trees": trees,
        "per_tree": TREES_PER_DAYS,
        "to_next_tree": (tcount - TREES_START + 1) * TREES_PER_DAYS - streak
                        if tcount < TREES_MAX else 0,
    }


def update_achievements(db, stats, student_id):
    """Проверяет ачивки ученика; возвращает список новых (чтобы показать поздравление)."""
    existing = {r["key"] for r in db.execute(
        "SELECT key FROM achievements WHERE student_id=?", (student_id,)).fetchall()}
    new_earned = []
    now = datetime.now().isoformat(timespec="seconds")
    for ach in ACHIEVEMENTS:
        if ach["key"] not in existing and ach["check"](stats):
            db.execute("INSERT INTO achievements (student_id, key, earned_at) VALUES (?, ?, ?)",
                       (student_id, ach["key"], now))
            new_earned.append(ach)
    db.commit()
    return new_earned


def get_student_or_none(db):
    """Текущий ученик из сессии (или None)."""
    sid = session.get("student_id")
    if not sid:
        return None
    return db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()


def human_time(seconds):
    seconds = int(seconds or 0)
    if seconds < 60:
        return f"{seconds} сек"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m} мин {s} сек" if s else f"{m} мин"
    h, m = divmod(m, 60)
    return f"{h} ч {m} мин"


app.jinja_env.filters["human_time"] = human_time


def shuffle_words(words):
    """Перемешиваем слова в задании 'собери предложение' (стабильно для одной страницы)."""
    w = list(words)
    rng = random.Random(hash(tuple(w)))  # одно и то же перемешивание при повторном рендере
    rng.shuffle(w)
    if w == list(words):                # чтобы не было соблазна читать по порядку
        w.reverse()
    return w


app.jinja_env.filters["shuffle_words"] = shuffle_words


def _stable_shuffle(items, seed):
    items = list(items)
    rng = random.Random(seed)
    rng.shuffle(items)
    return items


def shuffle_match(q):
    """Для задания 'match': правый столбик перемешиваем стабильно.
    Возвращает список [(right_idx, text)] — порядок отображения."""
    rights = list(range(len(q["right"])))
    order = _stable_shuffle(rights, "m" + "".join(map(str, rights)) + str(len(q["left"])))
    if order == rights:
        order = order[::-1]
    return [(i, q["right"][i]) for i in order]


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


app.jinja_env.filters["shuffle_match"] = shuffle_match
app.jinja_env.filters["shuffle_sort"] = shuffle_sort


def validate_lessons():
    """Проверка целостности банка уроков: индексы ответов, полнота слов для 'order'."""
    errors = []
    for l in LESSONS:
        for section in ("exercises", "test"):
            for q in l.get(section, []):
                t = q.get("type", "choice")
                ref = f"урок {l['id']} ({section}): {q.get('q', '?')[:40]}"
                if t == "choice":
                    a = q.get("answer")
                    if not isinstance(a, int) or not 0 <= a < len(q.get("options", [])):
                        errors.append(f"{ref} — некорректный индекс answer={a!r}")
                elif t == "order":
                    # сравнение по «кушкам» слов (без учёта пунктуации), чтобы
                    # многословные фишки банков ("in the bedroom") тоже сходились
                    def _keys(s):
                        return sorted(w.lower().strip(" .!?,;:") for w in s.split())
                    need = _keys(q["answer"])
                    bank = []
                    for w in q.get("words", []):
                        bank.extend(_keys(w))
                    if need != sorted(bank):
                        errors.append(f"{ref} — слова в банке не совпадают с ответом")
                elif t == "match":
                    left, right, pairs = q.get("left", []), q.get("right", []), q.get("pairs", {})
                    if len(left) != len(right) or not left:
                        errors.append(f"{ref} — разная длина колонок в match")
                    norm = {}
                    for k, v in pairs.items():
                        ki, vi = int(k), int(v)
                        if not 0 <= ki < len(left) or not 0 <= vi < len(right):
                            errors.append(f"{ref} — выход индекса пары за пределы {ki}:{vi}")
                        norm[ki] = vi
                    if len(norm) != len(left) or sorted(norm.values()) != list(range(len(right))):
                        errors.append(f"{ref} — пары должны быть полным взаимно-однозначным соответствием")
                elif t == "sort":
                    cats = {c["id"] for c in q.get("categories", [])}
                    if not cats or not q.get("words"):
                        errors.append(f"{ref} — sort без категорий или слов")
                    for item in q.get("words", []):
                        _, _, c = item.partition("|")
                        if c not in cats:
                            errors.append(f"{ref} — слово '{item}' ссылается на неизвестную категорию '{c}'")
                elif t != "type_in":
                    errors.append(f"{ref} — неизвестный тип задания {t!r}")
        # теория: если есть — проверяем структуру
        th = l.get("theory")
        if th is not None:
            if not isinstance(th, dict) or not th.get("blocks"):
                errors.append(f"урок {l['id']} — theory без блоков 'blocks'")
            else:
                for b in th["blocks"]:
                    if not isinstance(b, dict) or not b.get("title") or not b.get("text"):
                        errors.append(f"урок {l['id']} — блок теории без title/text")
    return errors


def mistakes_count(mistakes_json):
    try:
        return len(json.loads(mistakes_json or "[]"))
    except Exception:
        return 0


app.jinja_env.filters["mistakes_count"] = mistakes_count


def tree_glyph_svg(glyph_key, accent=None):
    """SVG-стадия дерева (надёжнее emoji: не зависит от шрифта системы).

    accent — ежедневная деталь кроны (name, color): guarantees, что дерево
    выглядит иначе почти каждый день серии.
    """
    inner = TREE_GLYPHS.get(glyph_key) or TREE_GLYPHS["sprout"]
    if accent:
        name, color = accent
        extra = {
            " blossoms": f'<circle cx="30" cy="14" r="2.6" fill="{color}"/>'
                         f'<circle cx="48" cy="10" r="2.6" fill="{color}"/>'
                         f'<circle cx="40" cy="20" r="2.2" fill="{color}"/>',
            "fruits":    f'<circle cx="27" cy="18" r="2.8" fill="{color}"/>'
                         f'<circle cx="52" cy="14" r="2.8" fill="{color}"/>',
            "berries":   f'<circle cx="34" cy="8" r="2.2" fill="{color}"/>'
                         f'<circle cx="46" cy="18" r="2.2" fill="{color}"/>'
                         f'<circle cx="24" cy="22" r="2" fill="{color}"/>',
            "sparkles":  f'<path d="M22 6l1.5 3 3 1.5-3 1.5-1.5 3-1.5-3-3-1.5 3-1.5z" fill="{color}"/>'
                         f'<path d="M56 10l1.2 2.4 2.4 1.2-2.4 1.2-1.2 2.4-1.2-2.4-2.4-1.2 2.4-1.2z" fill="{color}"/>',
            "leaves-gold": f'<path d="M20 26c4-6 10-6 14-2-4 6-12 6-14 2z" fill="{color}" opacity=".85"/>'
                           f'<path d="M58 22c-4-4-10-3-13 1 4 4 11 3 13-1z" fill="{color}" opacity=".85"/>',
            "snow-dust": f'<circle cx="26" cy="10" r="1.8" fill="{color}"/>'
                         f'<circle cx="40" cy="6" r="1.8" fill="{color}"/>'
                         f'<circle cx="54" cy="12" r="1.8" fill="{color}"/>',
            "glow":      f'<circle cx="40" cy="16" r="20" fill="{color}" opacity=".28"/>',
        }.get(name, "")
        inner += extra
    return Markup(
        '<svg class="tree-svg" viewBox="0 0 80 52" xmlns="http://www.w3.org/2000/svg">'
        f'{inner}</svg>'
    )


@app.template_filter("tree_glyph")
def tree_glyph(glyph_key, accent=None):
    return tree_glyph_svg(glyph_key, accent)


@app.template_filter("deco_icon")
def deco_icon(deco):
    """Иконка украшения для магазина: SVG там, где emoji плохо рисуется."""
    key = deco["key"] if isinstance(deco, dict) else deco
    svg = DECO_ICONS.get(key)
    if svg:
        return Markup(f'<span class="shop-icon">{svg}</span>')
    e = deco.get("emoji") if isinstance(deco, dict) else None
    return Markup(f'<span class="shop-emoji">{e}</span>') if e else Markup(
        '<span class="shop-icon shop-icon-dot"></span>')

# ---------------------------------------------------------------------------
# Доступность уроков: следующий открыт, если предыдущий сдан
# ---------------------------------------------------------------------------

def unlocked_lesson_ids(stats):
    unlocked = set()
    for l in LESSONS:
        prev = l["id"] - 1
        if prev == 0 or prev in stats["completed_ids"]:
            unlocked.add(l["id"])
    return unlocked


# ---------------------------------------------------------------------------
# Анимированный помощник «Чик-чик» — настройки для шаблона base.html
# ---------------------------------------------------------------------------

MASCOT_NAME = "Чик-чик"        # имя помощника (можно поменять)
MASCOT_ENABLED = True          # False — полностью отключить помощника


def build_mascot_ctx():
    """Собирает базовые настройки помощника для текущей страницы."""
    role = session.get("role")
    page = "anon" if not role else ("parent" if role == "parent" else "student")
    endpoint = request.endpoint or ""
    mascot = {"enabled": MASCOT_ENABLED, "name": MASCOT_NAME, "page": page}
    if page != "student":
        return mascot
    if endpoint == "index":
        mascot["page"] = "index"
    elif endpoint == "student_home":
        mascot["page"] = "home"
    elif endpoint == "lesson_page":
        mascot["page"] = "lesson"
    elif endpoint == "submit_test":
        mascot["page"] = "result"
    elif endpoint == "garden_page":
        mascot["page"] = "garden"
    return mascot


@app.context_processor
def inject_mascot():
    """Добавляет переменную `mascot` во все шаблоны: кто на какой странице,
    чтобы JS-помощник знал, что говорить и когда."""
    return {"mascot": build_mascot_ctx()}


# ---------------------------------------------------------------------------
# Маршруты
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    if session.get("role") == "student":
        return redirect(url_for("student_home"))
    return render_template("index.html")


@app.route("/login/student", methods=["POST"])
def login_student():
    """Вход ученика по логину и паролю (аккаунты создаёт родитель)."""
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE username=?",
                         (username,)).fetchone()
    if not student or not verify_password(student["password_hash"], password):
        flash("Такого аккаунта нет или пароль неверный. Попроси родителей проверить в кабинете 👀", "error")
        return redirect(url_for("index"))
    session["role"] = "student"
    session["student_id"] = student["id"]
    session["student_name"] = student["display_name"]
    return redirect(url_for("student_home"))


@app.route("/login/parent", methods=["POST"])
def login_parent():
    pwd = request.form.get("password") or ""
    if pwd != PARENT_PASSWORD:
        flash("Неверный пароль. Подсказка: спроси у родителей 😉", "error")
        return redirect(url_for("index"))
    session["role"] = "parent"
    return redirect(url_for("parent_dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


def require_role(role):
    if session.get("role") != role:
        return redirect(url_for("index"))
    return None


# ------------------------- Управление аккаунтами (родитель) -----------------

STUDENT_EMOJIS = ["🦄", "🐱", "🐰", "🦊", "🐼", "🐥", "🦋", "🌈", "🚀", "🎀", "🐢", "🦁"]


def valid_username(name):
    import re
    return bool(re.fullmatch(r"[a-zA-Z0-9_.\-]{2,20}", name or ""))


@app.route("/parent/students/add", methods=["POST"])
def add_student():
    err = require_role("parent")
    if err:
        return err
    username = (request.form.get("username") or "").strip().lower()
    display_name = (request.form.get("display_name") or "").strip()[:40]
    password = request.form.get("password") or ""
    emoji = request.form.get("emoji") or "🎒"
    if emoji not in STUDENT_EMOJIS:
        emoji = "🎒"
    db = get_db()
    if not valid_username(username):
        flash("Логин: только английские буквы, цифры, точка/дефис/подчёркивание, 2–20 символов.", "error")
    elif not display_name:
        flash("Нужно указать имя ученика.", "error")
    elif len(password) < 4:
        flash("Пароль должен быть не короче 4 символов.", "error")
    elif db.execute("SELECT id FROM students WHERE username=?", (username,)).fetchone():
        flash(f"Логин «{username}» уже занят.", "error")
    else:
        db.execute(
            "INSERT INTO students (username, display_name, password_hash, emoji, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, display_name, hash_password(password), emoji,
             datetime.now().isoformat(timespec="seconds")))
        db.commit()
        flash(f"Аккаунт для {display_name} создан! 🎉", "success")
    return redirect(url_for("parent_dashboard") + "#students")


@app.route("/parent/students/<int:sid>/delete", methods=["POST"])
def delete_student(sid):
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
    if not student:
        abort(404)
    db.execute("DELETE FROM attempts WHERE student_id=?", (sid,))
    db.execute("DELETE FROM achievements WHERE student_id=?", (sid,))
    db.execute("DELETE FROM students WHERE id=?", (sid,))
    db.commit()
    flash(f"Аккаунт {student['display_name']} удалён вместе с его прогрессом.", "success")
    return redirect(url_for("parent_dashboard") + "#students")


@app.route("/parent/students/<int:sid>/reset_password", methods=["POST"])
def reset_student_password(sid):
    err = require_role("parent")
    if err:
        return err
    password = request.form.get("password") or ""
    if len(password) < 4:
        flash("Новый пароль должен быть не короче 4 символов.", "error")
        return redirect(url_for("parent_dashboard") + "#students")
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
    if not student:
        abort(404)
    db.execute("UPDATE students SET password_hash=? WHERE id=?",
               (hash_password(password), sid))
    db.commit()
    flash(f"Пароль для {student['display_name']} обновлён 🔑", "success")
    return redirect(url_for("parent_dashboard") + "#students")


@app.route("/parent/students/<int:sid>/garden", methods=["POST"])
def parent_update_garden(sid):
    """Тестовая настройка сада ребёнка: серия дней и монетки."""
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
    if not student:
        abort(404)
    g = get_garden(db, sid)

    def _num(name, default=None):
        raw = request.form.get(name)
        if raw is None or raw.strip() == "":
            return default
        try:
            return max(0, min(9999, int(raw)))
        except ValueError:
            return default

    streak = _num("streak_days")
    coins = _num("coins")
    if streak is None and coins is None:
        flash("Ничего не изменено — заполни хотя бы одно поле.", "error")
        return redirect(url_for("parent_dashboard") + "#students")
    if streak is not None:
        streak = cap_streak(streak)  # серия ограничена STREAK_CAP днями
        # синхронизируем last_study_day с реальностью, чтобы refresh не сбросил серию
        if streak > 0:
            db.execute("UPDATE garden SET streak_days=?, broken=0, manual=1 WHERE student_id=?",
                       (streak, sid))
        else:
            # «прерываем» серию — как будто пропущен день: дерево возвращается
            # к начальному размеру, украшения снимаются (монетки остаются)
            db.execute("UPDATE garden SET streak_days=0, broken=1, manual=1 WHERE student_id=?",
                       (sid,))
            db.execute("DELETE FROM decorations WHERE student_id=?", (sid,))
        best = cap_streak(max(int(g["best_streak"]), streak or 0))
        db.execute("UPDATE garden SET best_streak=? WHERE student_id=?", (best, sid))
    if coins is not None:
        db.execute("UPDATE garden SET coins=? WHERE student_id=?", (coins, sid))
    db.commit()
    flash(f"Сад для {student['display_name']} обновлён: серия {streak if streak is not None else g['streak_days']} дн., "
          f"монет {coins if coins is not None else g['coins']} 🌳", "success")
    return redirect(url_for("parent_dashboard") + "#students")


# ---------------------------- Ученик ---------------------------------------

@app.route("/student")
def student_home():
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        flash("Аккаунт был удалён родителем. Войди заново 🙂", "error")
        return redirect(url_for("index"))
    stats = compute_stats(db, student["id"])
    garden = refresh_garden(db, student["id"])
    unlocked = unlocked_lesson_ids(stats)
    lessons_info = []
    for l in LESSONS:
        best = stats["best_by_lesson"].get(l["id"])
        lessons_info.append({
            "lesson": l,
            "locked": l["id"] not in unlocked,
            "done": l["id"] in stats["completed_ids"],
            "best_score": best["score_percent"] if best else None,
        })
    earned = {r["key"]: r["earned_at"] for r in db.execute(
        "SELECT key, earned_at FROM achievements WHERE student_id=?",
        (student["id"],)).fetchall()}
    achievements = [{**a, "earned": a["key"] in earned,
                     "earned_at": earned.get(a["key"])} for a in ACHIEVEMENTS]
    new_badge = session.pop("new_achievements", None)
    mascot = build_mascot_ctx()
    mascot["alreadyStarted"] = bool(stats["attempts"])
    mascot["allDone"] = len(stats["completed_ids"]) == len(LESSONS)
    # Следующий непройденный доступный урок (для крупной кнопки «Продолжить»)
    next_lesson = None
    for l in LESSONS:
        if l["id"] in unlocked and l["id"] not in stats["completed_ids"]:
            next_lesson = l
            break
    earned_count = sum(1 for a in achievements if a["earned"])
    return render_template("student_home.html", mascot=mascot,
                           name=student["display_name"],
                           emoji=student["emoji"],
                           lessons=lessons_info,
                           stats=stats,
                           achievements=achievements,
                           total_lessons=len(LESSONS),
                           new_badge=new_badge,
                           next_lesson=next_lesson,
                           earned_count=earned_count,
                           garden=garden,
                           tree_stage=tree_stage(garden["streak_days"]),
                           tree_count=tree_count_for(garden["streak_days"]))


@app.route("/lesson/<int:lesson_id>")
def lesson_page(lesson_id):
    err = require_role("student")
    if err:
        return err
    lesson = LESSONS_BY_ID.get(lesson_id) or abort(404)
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("index"))
    stats = compute_stats(db, student["id"])
    if lesson_id not in unlocked_lesson_ids(stats):
        flash("Сначала пройди предыдущий урок! 😉", "error")
        return redirect(url_for("student_home"))
    touch_streak(db, student["id"])   # занялись сегодня — серия дня продлевается
    # Создаём новую попытку (начало занятия)
    started = datetime.now()
    cur = db.execute(
        "INSERT INTO attempts (student_id, lesson_id, started_at) VALUES (?, ?, ?)",
        (student["id"], lesson_id, started.isoformat(timespec="seconds")))
    db.commit()
    mascot = build_mascot_ctx()
    mascot["lessonId"] = lesson_id
    mascot["lessonTitle"] = lesson["title"]
    return render_template("lesson.html", lesson=lesson,
                           attempt_id=cur.lastrowid,
                           started_ts=started.timestamp(),
                           mascot=mascot)


@app.route("/lesson/<int:lesson_id>/submit", methods=["POST"])
def submit_test(lesson_id):
    err = require_role("student")
    if err:
        return err
    lesson = LESSONS_BY_ID.get(lesson_id) or abort(404)
    attempt_id = request.form.get("attempt_id", type=int)
    seconds = request.form.get("seconds", type=int) or 0
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("index"))
    attempt = db.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
    if not attempt or attempt["finished_at"] or attempt["student_id"] != student["id"]:
        abort(400)

    test = lesson["test"]
    results, mistakes = [], []
    correct = 0
    for i, q in enumerate(test):
        if q["type"] == "choice":
            raw = request.form.get(f"q{i}")
            given = int(raw) if raw is not None and raw.isdigit() else -1
        elif q["type"] == "order":
            raw = request.form.get(f"q{i}_order", "")
            given = raw
        elif q["type"] in ("match", "sort"):
            # скрытые поля заполняет drag&drop-скрипт перед отправкой
            given = request.form.get(f"q{i}_{q['type']}", "")
        else:
            given = request.form.get(f"q{i}", "")
        ok, correct_disp = grade_question(q, given)
        if ok:
            correct += 1
        else:
            mistakes.append({"question": q["q"],
                             "given": str(given if given != -1 else "(пусто)"),
                             "correct": str(correct_disp)})
        results.append({"q": q["q"], "type": q["type"],
                        "given": str(given if given != -1 else ""),
                        "correct_answer": str(correct_disp),
                        "explain": q.get("explain", ""),
                        "correct": bool(ok)})

    total = len(test)
    percent = round(100 * correct / total) if total else 0
    passed = percent >= PASS_MARK
    finished = datetime.now()
    db.execute(
        """UPDATE attempts SET finished_at=?, seconds_spent=?, score_percent=?,
           passed=?, total_q=?, correct_q=?, mistakes_json=?, details_json=? WHERE id=?""",
        (finished.isoformat(timespec="seconds"), seconds, percent, int(passed),
         total, correct, json.dumps(mistakes, ensure_ascii=False),
         json.dumps({"results": results}, ensure_ascii=False), attempt_id))
    db.commit()

    stats = compute_stats(db, student["id"])
    new_achievements = update_achievements(db, stats, student["id"])
    if new_achievements:
        session["new_achievements"] = [a["key"] for a in new_achievements]

    coins_earned = award_coins(db, student["id"], percent, passed)
    garden = get_garden(db, student["id"])

    mascot = build_mascot_ctx()
    mascot["percent"] = percent
    mascot["passed"] = passed
    mascot["coinsEarned"] = coins_earned
    mascot["newAchievements"] = [
        {"key": a["key"], "emoji": a["emoji"], "title": a["title"], "desc": a["desc"]}
        for a in new_achievements]
    return render_template("result.html", mascot=mascot,
                           lesson=lesson, percent=percent, passed=passed,
                           correct=correct, total=total,
                           seconds=seconds, results=results,
                           coins_earned=coins_earned,
                           coins_total=garden["coins"],
                           streak_days=garden["streak_days"],
                           new_achievements=[a for a in ACHIEVEMENTS
                                             if a["key"] in [n["key"] for n in new_achievements]])


# ---------------------------- Сад-дерево -----------------------------------

@app.route("/student/garden")
def garden_page():
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("index"))
    refresh_garden(db, student["id"])
    view = garden_view(db, student["id"])
    mascot = build_mascot_ctx()
    mascot["page"] = "garden"
    mascot["streak"] = view["garden"]["streak_days"]
    flash_msg = session.pop("garden_flash", None)
    return render_template("garden.html", mascot=mascot, name=student["display_name"],
                           deco_by_key=DECOS_BY_KEY,
                           deco_emojis={k: d["emoji"] for k, d in DECOS_BY_KEY.items()},
                           flash_msg=flash_msg, **view)


@app.route("/student/garden/buy", methods=["POST"])
def garden_buy():
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("index"))
    key = request.form.get("deco_key")
    deco = DECOS_BY_KEY.get(key) or abort(400)
    g = get_garden(db, student["id"])
    used = {r["slot"] for r in db.execute(
        "SELECT slot FROM decorations WHERE student_id=?", (student["id"],)).fetchall()}
    free_slots = [s for s in range(MAX_SLOTS) if s not in used]
    if bool(g["broken"]) or g["streak_days"] <= 0:
        session["garden_flash"] = "Серия прервана — сначала позанимайся сегодня, чтобы сад ожил! 🍂"
    elif not free_slots:
        session["garden_flash"] = f"В саду уже максимум украшений ({MAX_SLOTS}). Сними одно 😉"
    elif g["coins"] < deco["cost"]:
        session["garden_flash"] = (f"Не хватает монеток: нужно {deco['cost']}, "
                                   f"а у тебя {g['coins']}. Пройди ещё пару тестов!")
    else:
        # фон сада — только один: покупка нового заменяет старый (стоимость возвращается)
        replacing = None
        if deco["category"] == "theme":
            for r in db.execute(
                    "SELECT deco_key, slot FROM decorations WHERE student_id=?",
                    (student["id"],)).fetchall():
                od = DECOS_BY_KEY.get(r["deco_key"])
                if od and od["category"] == "theme" and r["deco_key"] != key:
                    replacing = r
                    break
        if replacing:
            od = DECOS_BY_KEY[replacing["deco_key"]]
            db.execute("DELETE FROM decorations WHERE student_id=? AND slot=?",
                       (student["id"], replacing["slot"]))
            db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?",
                       (od["cost"], student["id"]))
            db.execute("UPDATE garden SET coins=coins-? WHERE student_id=?",
                       (deco["cost"], student["id"]))
            db.execute("INSERT INTO decorations (student_id, deco_key, slot) VALUES (?, ?, ?)",
                       (student["id"], key, replacing["slot"]))
            db.commit()
            session["garden_flash"] = (f"{deco['emoji']} «{deco['name']}» заменил фон "
                                       f"«{od['name']}» (его цена вернулась монетками). "
                                       f"Фон в саду может быть только один!")
        else:
            free_slots = [s for s in range(MAX_SLOTS) if s not in used]
            if not free_slots:
                session["garden_flash"] = f"В саду уже максимум украшений ({MAX_SLOTS}). Сними одно 😉"
                return redirect(url_for("garden_page"))
            db.execute("UPDATE garden SET coins=coins-? WHERE student_id=?",
                       (deco["cost"], student["id"]))
            db.execute("INSERT INTO decorations (student_id, deco_key, slot) VALUES (?, ?, ?)",
                       (student["id"], key, free_slots[0]))
            db.commit()
            session["garden_flash"] = f"{deco['emoji'] or '🎨'} «{deco['name']}» украсило весь сад!"
    return redirect(url_for("garden_page"))


@app.route("/student/garden/remove/<int:slot>", methods=["POST"])
def garden_remove(slot):
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("index"))
    row = db.execute("SELECT * FROM decorations WHERE student_id=? AND slot=?",
                     (student["id"], slot)).fetchone()
    if row:
        db.execute("DELETE FROM decorations WHERE id=?", (row["id"],))
        # возвращаем половину стоимости — сняли украшение с дерева
        deco = DECOS_BY_KEY.get(row["deco_key"], {"cost": 0, "name": "", "emoji": ""})
        refund = deco["cost"] // 2
        db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?",
                   (refund, student["id"]))
        db.commit()
        session["garden_flash"] = (f"{deco['emoji']} «{deco['name']}» снято из сада, "
                                   f"вернулось {refund} монеток")
    return redirect(url_for("garden_page"))


# ---------------------------- Родитель -------------------------------------

@app.route("/parent")
def parent_dashboard():
    err = require_role("parent")
    if err:
        return err
    db = get_db()

    # Аккаунты учеников + их персональная статистика
    students = db.execute(
        "SELECT * FROM students ORDER BY created_at ASC").fetchall()
    student_cards = []
    for st in students:
        sstats = compute_stats(db, st["id"])
        earned = {r["key"] for r in db.execute(
            "SELECT key FROM achievements WHERE student_id=?", (st["id"],)).fetchall()}
        sgarden = get_garden(db, st["id"])
        student_cards.append({"student": st, "stats": sstats,
                              "earned_count": len(earned),
                              "garden": sgarden,
                              "tree_stage": tree_stage(sgarden["streak_days"]),
                              "tree_count": tree_count_for(sgarden["streak_days"]),
                              "deco_count": db.execute(
                                  "SELECT COUNT(*) c FROM decorations WHERE student_id=?",
                                  (st["id"],)).fetchone()["c"]})

    stats = compute_stats(db)  # общая сводка по всем детям
    attempts = list(reversed(stats["attempts"]))  # свежие сверху

    # Сводка по урокам
    lesson_rows = []
    for l in LESSONS:
        la = [a for a in stats["attempts"] if a["lesson_id"] == l["id"]]
        best = max(la, key=lambda a: a["score_percent"], default=None)
        time_spent = sum(a["seconds_spent"] or 0 for a in la)
        lesson_rows.append({
            "lesson": l,
            "tries": len(la),
            "passed": l["id"] in stats["completed_ids"],
            "best_score": best["score_percent"] if best else None,
            "time_spent": time_spent,
        })

    earned = {}
    for r in db.execute(
            "SELECT a.student_id, a.key, a.earned_at, s.display_name, s.emoji "
            "FROM achievements a JOIN students s ON s.id = a.student_id").fetchall():
        earned[(r["student_id"], r["key"])] = r
    achievements = [{**a, "earned": any(k[1] == a["key"] for k in earned),
                     "who": ", ".join(f"{v['emoji']} {v['display_name']}"
                                      for k, v in earned.items() if k[1] == a["key"]),
                     "earned_at": next((v["earned_at"] for k, v in earned.items()
                                        if k[1] == a["key"]), None)}
                    for a in ACHIEVEMENTS]

    names_by_id = {st["id"]: st["display_name"] for st in students}
    emojis_by_id = {st["id"]: st["emoji"] for st in students}

    return render_template("parent_dashboard.html",
                           stats=stats, lessons=lesson_rows,
                           attempts=attempts, achievements=achievements,
                           students=students, student_cards=student_cards,
                           names_by_id=names_by_id, emojis_by_id=emojis_by_id,
                           student_emojis=STUDENT_EMOJIS,
                           lesson_titles={l["id"]: l["title"] for l in LESSONS},
                           total_lessons=len(LESSONS))


@app.route("/api/mistakes")
def api_mistakes():
    """Все ошибки по всем попыткам — для таблицы в кабинете родителя."""
    err = require_role("parent")
    if err:
        return jsonify([])
    db = get_db()
    names = {r["id"]: r["display_name"] for r in
             db.execute("SELECT id, display_name FROM students").fetchall()}
    rows = db.execute(
        "SELECT * FROM attempts WHERE finished_at IS NOT NULL ORDER BY finished_at DESC").fetchall()
    out = []
    for r in rows:
        lesson = LESSONS_BY_ID.get(r["lesson_id"], {})
        try:
            details = json.loads(r["details_json"] or "{}")
        except Exception:
            details = {}
        for res in details.get("results", []):
            if not res["correct"]:
                out.append({
                    "date": (r["finished_at"] or "")[:16].replace("T", " "),
                    "student": names.get(r["student_id"], "—"),
                    "lesson_title": lesson.get("title", f"Урок {r['lesson_id']}"),
                    "question": res["q"],
                    "given": res["given"] or "(пусто)",
                    "correct": res["correct_answer"],
                    "explain": res.get("explain", ""),
                })
    return jsonify(out)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Порт можно менять: python3 app.py 8080  (или PORT=8080 python3 app.py)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 5000))
    print(f"==> Приложение запущено: http://localhost:{port}")
    print("    Режим ученика: вход по имени. Кабинет родителя: пароль 1234")
    app.run(host="0.0.0.0", port=port, debug=False)
