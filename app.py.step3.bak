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
import sys
from datetime import datetime

from flask import (Flask, abort, flash, g, jsonify, redirect,
                   render_template, request, session, url_for)

from achievements import (  # noqa: F401
    ACHIEVEMENTS,
    update_achievements,
)
# --- Модули, вынесенные из app.py (шаг 2 рефакторинга) ---
from config import (  # noqa: F401
    BASE_DIR,
    DB_PATH,
    PASS_MARK,
    PARENT_PASSWORD,
)
from curriculum import (  # noqa: F401
    ALL_LESSONS,
    MAIN_COUNT,
    LESSONS_BY_ID,
    validate_lessons,
    unlocked_lesson_ids,
)
from data.extra_lessons import EXTRA_LESSONS
from data.lessons import LESSONS
from database import (  # noqa: F401
    get_db,
    SCHEMA,
    init_db,
)
from garden import (  # noqa: F401
    MAX_SLOTS,
    STREAK_CAP,
    COIN_PASS,
    COIN_PERFECT,
    TREES_START,
    TREES_MAX,
    TREES_EVERY,
    tree_count_for,
    DECORATIONS,
    DECOS_BY_KEY,
    CATEGORY_NAMES,
    TREE_GLYPHS,
    TREE_STAGES,
    variant_glyph,
    get_garden,
    tree_stage,
    cap_streak,
    compute_streak_from_history,
    refresh_garden,
    award_coins,
    touch_streak,
    garden_view,
)
from grading import (  # noqa: F401
    norm_answer,
    parse_pairs,
    parse_sort,
    grade_question,
    match_columns,
)
from mascot import (  # noqa: F401
    MASCOT_NAME,
    MASCOT_ENABLED,
    build_mascot_ctx,
)
from security import (  # noqa: F401
    PBKDF2_ROUNDS,
    hash_password,
    verify_password,
)
from stats import (  # noqa: F401
    compute_stats,
)
from template_filters import (  # noqa: F401
    human_time,
    shuffle_words,
    shuffle_match,
    shuffle_sort,
    match_cols,
    match_answer_json,
    match_expected_json,
    mistakes_count,
    tree_glyph,
)

app = Flask(__name__)

# Постоянный секретный ключ, чтобы сессии не сбрасывались после перезапуска
SECRET_FILE = os.path.join(BASE_DIR, ".secret_key")
if not os.path.exists(SECRET_FILE):
    with open(SECRET_FILE, "w") as f:
        f.write(os.urandom(24).hex())
with open(SECRET_FILE) as f:
    app.secret_key = f.read().strip()


# ---------------------------------------------------------------------------
# Пароли: хешируем PBKDF2 + случайная соль (в базе хранится только хеш)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# База данных
# ---------------------------------------------------------------------------


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


init_db()

# ---------------------------------------------------------------------------
# Ачивки (достижения)
# Функции-проверки получают словарь stats (см. compute_stats)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Подсчёт статистики
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 🌳 Сад: деревья растут от серии дней, монетки, украшения для всего сада
# ---------------------------------------------------------------------------


def get_student_or_none(db):
    """Текущий ученик из сессии (или None)."""
    sid = session.get("student_id")
    if not sid:
        return None
    return db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()


app.jinja_env.filters["human_time"] = human_time


app.jinja_env.filters["shuffle_words"] = shuffle_words


app.jinja_env.filters["match_cols"] = match_cols
app.jinja_env.filters["match_answer"] = match_answer_json
app.jinja_env.filters["shuffle_match"] = shuffle_match


app.jinja_env.filters["match_expected"] = match_expected_json
app.jinja_env.filters["shuffle_sort"] = shuffle_sort


app.jinja_env.filters["mistakes_count"] = mistakes_count


app.template_filter("tree_glyph")(tree_glyph)

# ---------------------------------------------------------------------------
# Доступность уроков: следующий открыт, если предыдущий сдан
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Анимированный помощник «Чик-чик» — настройки для шаблона base.html
# ---------------------------------------------------------------------------


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

    def lesson_info(l):
        best = stats["best_by_lesson"].get(l["id"])
        return {
            "lesson": l,
            "locked": l["id"] not in unlocked,
            "done": l["id"] in stats["completed_ids"],
            "best_score": best["score_percent"] if best else None,
        }

    lessons_info = [lesson_info(l) for l in LESSONS]
    extra_info = [lesson_info(l) for l in EXTRA_LESSONS]
    extras_done = sum(1 for i in extra_info if i["done"])
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
    # Компактный вид блока «Мои уроки»: последний пройденный, следующий
    # доступный и первый закрытый. Остальные — за кнопкой «показать все».
    last_done_id = None
    for info in reversed(lessons_info):
        if info["done"]:
            last_done_id = info["lesson"]["id"]
            break
    next_id = next_lesson["id"] if next_lesson else None
    first_locked_id = None
    for info in lessons_info:
        if info["locked"]:
            first_locked_id = info["lesson"]["id"]
            break
    highlight_ids = {i for i in (last_done_id, next_id, first_locked_id) if i}
    for info in lessons_info:
        info["highlight"] = info["lesson"]["id"] in highlight_ids
    hidden_count = sum(1 for info in lessons_info if not info["highlight"])
    earned_count = sum(1 for a in achievements if a["earned"])
    return render_template("student_home.html", mascot=mascot,
                           name=student["display_name"],
                           emoji=student["emoji"],
                           lessons=lessons_info,
                           hidden_lessons_count=hidden_count,
                           extra_lessons=extra_info,
                           extras_done=extras_done,
                           total_extras=len(EXTRA_LESSONS),
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
    elif deco["category"] == "theme":
        # фон может быть только ОДИН: старый снимается, деньги возвращаются
        theme_keys = {d["key"] for d in DECORATIONS if d["category"] == "theme"}
        old_theme = [r for r in db.execute(
            "SELECT id, slot, deco_key FROM decorations WHERE student_id=?",
            (student["id"],)).fetchall() if r["deco_key"] in theme_keys]
        refund = sum(DECOS_BY_KEY.get(r["deco_key"], {"cost": 0})["cost"] // 2
                     for r in old_theme)
        for r in old_theme:
            db.execute("DELETE FROM decorations WHERE id=?", (r["id"],))
        used2 = {r["slot"] for r in db.execute(
            "SELECT slot FROM decorations WHERE student_id=?", (student["id"],)).fetchall()}
        free2 = [s for s in range(MAX_SLOTS) if s not in used2]
        if not free2:
            # все слоты заняты не-фонами — снимаем самый первый слот под фон
            db.execute("DELETE FROM decorations WHERE student_id=? AND slot=0",
                       (student["id"],))
            free2 = [0]
        db.execute("UPDATE garden SET coins=coins-?+? WHERE student_id=?",
                   (deco["cost"], refund, student["id"]))
        db.execute("INSERT INTO decorations (student_id, deco_key, slot) VALUES (?, ?, ?)",
                   (student["id"], key, free2[0]))
        db.commit()
        note = f" (старый фон снят, вернулось {refund} монеток)" if refund else ""
        session["garden_flash"] = f"{deco['emoji']} Новый фон сада «{deco['name']}»!{note}"
    else:
        db.execute("UPDATE garden SET coins=coins-? WHERE student_id=?",
                   (deco["cost"], student["id"]))
        db.execute("INSERT INTO decorations (student_id, deco_key, slot) VALUES (?, ?, ?)",
                   (student["id"], key, free_slots[0]))
        db.commit()
        session["garden_flash"] = f"{deco['emoji']} «{deco['name']}» украсило весь сад!"
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

    # Сводка по урокам (основные + дополнительные)
    lesson_rows = []
    for l in ALL_LESSONS:
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
                           lesson_titles={l["id"]: l["title"] for l in ALL_LESSONS},
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
