# -*- coding: utf-8 -*-
"""app.py — веб-приложение «Английский для дочки» на Flask + SQLite.

Что внутри:
  * Режим ученика: уроки (материал -> упражнения -> итоговый тест),
    трекер успеваемости и ачивки за прохождения.
  * Режим родителя: время, потраченное на каждый урок/тест, все ошибки
    с правильными ответами, прогресс и достижения.
"""

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
CREATE TABLE IF NOT EXISTS attempts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
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
    key        TEXT PRIMARY KEY,
    earned_at  TEXT NOT NULL
);
"""


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
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


def grade_question(q, given):
    """Возвращает (is_correct, correct_display)."""
    qtype = q.get("type", "choice")
    if qtype == "choice":
        idx = given
        ok = isinstance(idx, int) and 0 <= idx < len(q["options"]) and idx == q["answer"]
        return ok, q["options"][q["answer"]]
    if qtype == "order":
        expected = norm_answer(q["answer"])
        ok = norm_answer(given) == expected
        return ok, q["answer"]
    # type_in
    accepted = [norm_answer(q["answer"])] + [norm_answer(a) for a in q.get("accept", [])]
    ok = norm_answer(given) in accepted
    return ok, q["answer"]


def compute_stats(db):
    """Общая статистика по всем попыткам — используется для ачивок и трекера."""
    rows = db.execute(
        "SELECT * FROM attempts WHERE finished_at IS NOT NULL ORDER BY finished_at ASC, id ASC"
    ).fetchall()

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


def update_achievements(db, stats):
    """Проверяет ачивки; возвращает список новых (чтобы показать поздравление)."""
    existing = {r["key"] for r in db.execute("SELECT key FROM achievements").fetchall()}
    new_earned = []
    now = datetime.now().isoformat(timespec="seconds")
    for ach in ACHIEVEMENTS:
        if ach["key"] not in existing and ach["check"](stats):
            db.execute("INSERT INTO achievements (key, earned_at) VALUES (?, ?)",
                       (ach["key"], now))
            new_earned.append(ach)
    db.commit()
    return new_earned


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
    """Перемешиваем слова в задании 'собери предложение'."""
    w = list(words)
    random.shuffle(w)
    return w


app.jinja_env.filters["shuffle_words"] = shuffle_words


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
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Напиши, как тебя зовут! 😊", "error")
        return redirect(url_for("index"))
    session["role"] = "student"
    session["student_name"] = name[:40]
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


# ---------------------------- Ученик ---------------------------------------

@app.route("/student")
def student_home():
    err = require_role("student")
    if err:
        return err
    db = get_db()
    stats = compute_stats(db)
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
    earned = {r["key"]: r["earned_at"] for r in
              db.execute("SELECT key, earned_at FROM achievements").fetchall()}
    achievements = [{**a, "earned": a["key"] in earned,
                     "earned_at": earned.get(a["key"])} for a in ACHIEVEMENTS]
    new_badge = session.pop("new_achievements", None)
    return render_template("student_home.html",
                           name=session["student_name"],
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
    stats = compute_stats(db)
    if lesson_id not in unlocked_lesson_ids(stats):
        flash("Сначала пройди предыдущий урок! 😉", "error")
        return redirect(url_for("student_home"))
    # Создаём новую попытку (начало занятия)
    started = datetime.now()
    cur = db.execute(
        "INSERT INTO attempts (lesson_id, started_at) VALUES (?, ?)",
        (lesson_id, started.isoformat(timespec="seconds")))
    db.commit()
    return render_template("lesson.html", lesson=lesson,
                           attempt_id=cur.lastrowid,
                           started_ts=started.timestamp())


@app.route("/lesson/<int:lesson_id>/submit", methods=["POST"])
def submit_test(lesson_id):
    lesson = LESSONS_BY_ID.get(lesson_id) or abort(404)
    attempt_id = request.form.get("attempt_id", type=int)
    seconds = request.form.get("seconds", type=int) or 0
    db = get_db()
    attempt = db.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
    if not attempt or attempt["finished_at"]:
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

    stats = compute_stats(db)
    new_achievements = update_achievements(db, stats)
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
    stats = compute_stats(db)
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

    earned = {r["key"]: r["earned_at"] for r in
              db.execute("SELECT key, earned_at FROM achievements").fetchall()}
    achievements = [{**a, "earned": a["key"] in earned,
                     "earned_at": earned.get(a["key"])} for a in ACHIEVEMENTS]

    return render_template("parent_dashboard.html",
                           stats=stats, lessons=lesson_rows,
                           attempts=attempts, achievements=achievements,
                           lesson_titles={l["id"]: l["title"] for l in LESSONS},
                           total_lessons=len(LESSONS))


@app.route("/api/mistakes")
def api_mistakes():
    """Все ошибки по всем попыткам — для таблицы в кабинете родителя."""
    err = require_role("parent")
    if err:
        return jsonify([])
    db = get_db()
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
