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
"""


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    # Миграция старых баз: добавляем недостающие колонки/таблицы
    cols = {r[1] for r in conn.execute("PRAGMA table_info(attempts)")}
    if "student_id" not in cols:
        conn.execute("ALTER TABLE attempts ADD COLUMN student_id INTEGER")
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
    total_seconds = 0
    total_mistakes = 0

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

        if r["passed"]:
            lid = r["lesson_id"]
            if lid not in best_by_lesson or r["score_percent"] > best_by_lesson[lid]["score_percent"]:
                best_by_lesson[lid] = r
            if r["mistakes_json"] and len(json.loads(r["mistakes_json"])) == 0:
                has_perfect = True
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
        "words_learned": words_learned,
        "total_mistakes": total_mistakes,
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
                    need = [w.lower().strip(" .!?,;:") for w in q["answer"].split()]
                    bank = sorted(w.lower().strip(" .!?,;:") for w in q.get("words", []))
                    if sorted(need) != bank:
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
# Маршруты
# ---------------------------------------------------------------------------

@app.route("/")
def index():
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
    return render_template("student_home.html",
                           name=student["display_name"],
                           emoji=student["emoji"],
                           lessons=lessons_info,
                           stats=stats,
                           achievements=achievements,
                           total_lessons=len(LESSONS),
                           new_badge=new_badge)


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
    # Создаём новую попытку (начало занятия)
    started = datetime.now()
    cur = db.execute(
        "INSERT INTO attempts (student_id, lesson_id, started_at) VALUES (?, ?, ?)",
        (student["id"], lesson_id, started.isoformat(timespec="seconds")))
    db.commit()
    return render_template("lesson.html", lesson=lesson,
                           attempt_id=cur.lastrowid,
                           started_ts=started.timestamp())


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

    return render_template("result.html",
                           lesson=lesson, percent=percent, passed=passed,
                           correct=correct, total=total,
                           seconds=seconds, results=results,
                           new_achievements=[a for a in ACHIEVEMENTS
                                             if a["key"] in [n["key"] for n in new_achievements]])


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
        student_cards.append({"student": st, "stats": sstats,
                              "earned_count": len(earned)})

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
