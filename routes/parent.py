# -*- coding: utf-8 -*-
"""Кабинет администратора (роль "parent"): аккаунты учеников, статистика, API ошибок."""

import json
import goals
from achievements import ACHIEVEMENTS, update_achievements
from curriculum import ALL_LESSONS, LESSONS, LESSONS_BY_ID
from database import get_db
from datetime import datetime
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from garden import cap_streak, get_garden, tree_count_for, tree_stage
from report import MAX_WEEKS_BACK, week_report
from progress import credit_lessons, lesson_ids_upto, uncredit_lessons
from seasons import SEASONS, get_dates, get_mode, in_season, set_dates, set_mode
from security import hash_password
from stats import compute_stats

from routes.common import require_role

bp = Blueprint("parent", __name__)


STUDENT_EMOJIS = ["🦄", "🐱", "🐰", "🦊", "🐼", "🐥", "🦋", "🌈", "🚀", "🎀", "🐢", "🦁"]


def valid_username(name):
    import re
    return bool(re.fullmatch(r"[a-zA-Z0-9_.\-]{2,20}", name or ""))


@bp.route("/parent/students/add", methods=["POST"])
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
    return redirect(url_for("parent.parent_dashboard") + "#students")


@bp.route("/parent/students/<int:sid>/delete", methods=["POST"])
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
    db.execute("DELETE FROM decorations WHERE student_id=?", (sid,))
    db.execute("DELETE FROM garden WHERE student_id=?", (sid,))
    for table in ("wardrobe_items", "wardrobe_wear", "story_done", "game_scores", "dialog_done", "word_review", "speaking", "daily_goal", "goal_settings", "vacations", "activity", "weekly_done", "boss_wins", "season_log", "advent", "house_items", "house_place"):
        db.execute(f"DELETE FROM {table} WHERE student_id=?", (sid,))
    db.execute("DELETE FROM students WHERE id=?", (sid,))
    db.commit()
    flash(f"Аккаунт {student['display_name']} удалён вместе с его прогрессом.", "success")
    return redirect(url_for("parent.parent_dashboard") + "#students")


@bp.route("/parent/students/<int:sid>/reset_password", methods=["POST"])
def reset_student_password(sid):
    err = require_role("parent")
    if err:
        return err
    password = request.form.get("password") or ""
    if len(password) < 4:
        flash("Новый пароль должен быть не короче 4 символов.", "error")
        return redirect(url_for("parent.parent_dashboard") + "#students")
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
    if not student:
        abort(404)
    db.execute("UPDATE students SET password_hash=? WHERE id=?",
               (hash_password(password), sid))
    db.commit()
    flash(f"Пароль для {student['display_name']} обновлён 🔑", "success")
    return redirect(url_for("parent.parent_dashboard") + "#students")


@bp.route("/parent/students/<int:sid>/garden", methods=["POST"])
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
        return redirect(url_for("parent.parent_dashboard") + "#students")
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
    return redirect(url_for("parent.parent_dashboard") + "#students")


@bp.route("/parent/students/<int:sid>/credit", methods=["POST"])
def credit_student_lessons(sid):
    """Зачесть (или снять зачёт с) уроков: перенос прогресса без повторного прохождения."""
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
    if not student:
        abort(404)
    back = redirect(url_for("parent.parent_dashboard") + "#credit")
    ids = set()
    for raw in request.form.getlist("lessons"):
        if raw.isdigit():
            ids.add(int(raw))
    upto = request.form.get("upto", "").strip()
    if upto.isdigit():
        ids |= lesson_ids_upto(int(upto))
    ids &= set(LESSONS_BY_ID)
    if not ids:
        flash("Выбери уроки или укажи номер, до которого всё пройдено.", "error")
        return back

    if request.form.get("action") == "remove":
        removed = uncredit_lessons(db, sid, ids)
        flash(f"Зачёт снят с уроков: {len(removed)}." if removed else
              "Снимать нечего: у выбранных уроков нет зачёта родителя.", "success" if removed else "error")
        return back

    added = credit_lessons(db, sid, ids)
    if not added:
        flash("Все выбранные уроки уже пройдены.", "error")
        return back
    new = update_achievements(db, compute_stats(db, sid), sid)
    msg = f"{student['display_name']}: зачтено уроков — {len(added)} ✅ Следующие уроки открыты."
    if new:
        msg += " Ачивки: " + ", ".join(f"{a['emoji']} {a['title']}" for a in new)
    flash(msg, "success")
    return back


@bp.route("/parent/students/<int:sid>/vacation", methods=["POST"])
def parent_vacation(sid):
    """Каникулы: в эти дни серия не сгорает. action=add (с датами) или cancel."""
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    if not db.execute("SELECT 1 FROM students WHERE id=?", (sid,)).fetchone():
        abort(404)
    today = datetime.now().date()
    if request.form.get("action") == "cancel":
        db.execute("DELETE FROM vacations WHERE student_id=? AND end_day>=?",
                   (sid, today.isoformat()))
        db.commit()
        flash("Каникулы отменены.", "ok")
        return redirect(url_for("parent.parent_dashboard") + "#students")
    try:
        d1 = datetime.strptime(request.form.get("start_day", ""), "%Y-%m-%d").date()
        d2 = datetime.strptime(request.form.get("end_day", ""), "%Y-%m-%d").date()
    except ValueError:
        flash("Укажите даты начала и конца каникул.", "error")
        return redirect(url_for("parent.parent_dashboard") + "#students")
    if d2 < d1 or (d2 - d1).days > 60 or d2 < today:
        flash("Даты некорректны: конец не раньше начала, не дольше 60 дней, не в прошлом.", "error")
        return redirect(url_for("parent.parent_dashboard") + "#students")
    db.execute("INSERT INTO vacations (student_id, start_day, end_day) VALUES (?,?,?)",
               (sid, d1.isoformat(), d2.isoformat()))
    db.commit()
    flash("Каникулы сохранены: серия в эти дни не сгорит. 🏖", "ok")
    return redirect(url_for("parent.parent_dashboard") + "#students")


@bp.route("/parent/students/<int:sid>/goal", methods=["POST"])
def parent_goal(sid):
    """Цель дня ученика: сколько уроков и слов повторения."""
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    if not db.execute("SELECT 1 FROM students WHERE id=?", (sid,)).fetchone():
        abort(404)
    try:
        lessons, words = int(request.form.get("lessons", "")), int(request.form.get("words", ""))
    except ValueError:
        lessons = words = -1
    if goals.set_target(db, sid, lessons, words):
        flash(f"Цель дня сохранена: уроков — {lessons}, слов — {words}. 🎯", "ok")
    else:
        flash(f"Цель: уроков от 0 до {goals.MAX_LESSONS}, слов от 0 до {goals.MAX_WORDS}, "
              "и хотя бы что-то одно больше нуля.", "error")
    return redirect(url_for("parent.parent_dashboard") + "#students")


@bp.route("/parent/season", methods=["POST"])
def parent_season():
    """Праздничный сезон: авто (по датам) / всегда включён / выключен."""
    err = require_role("parent")
    if err:
        return err
    key = request.form.get("season", "")
    db = get_db()
    raw1, raw2 = request.form.get("date_from", "").strip(), request.form.get("date_to", "").strip()
    d1 = d2 = None
    if raw1 or raw2:
        try:
            d1, d2 = datetime.strptime(raw1, "%Y-%m-%d").date(), datetime.strptime(raw2, "%Y-%m-%d").date()
        except ValueError:
            d1 = None
        if d1 is None or d2 < d1:
            flash("Укажите обе даты праздника, конец — не раньше начала (или очистите обе, чтобы вернуть стандартные).", "error")
            return redirect(url_for("parent.parent_dashboard") + "#seasons")
    if set_mode(db, key, request.form.get("mode", "")) and set_dates(db, key, d1, d2):
        flash("Настройка праздника сохранена.", "ok")
    else:
        flash("Не удалось сохранить настройку.", "error")
    return redirect(url_for("parent.parent_dashboard") + "#seasons")


@bp.route("/parent")
def parent_dashboard():
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    weeks_back = request.args.get("week", 0, type=int)
    weeks_back = max(0, min(MAX_WEEKS_BACK, weeks_back or 0))

    # Аккаунты учеников + их персональная статистика
    students = db.execute(
        "SELECT * FROM students ORDER BY created_at ASC").fetchall()
    student_cards = []
    for st in students:
        sstats = compute_stats(db, st["id"])
        earned = {r["key"] for r in db.execute(
            "SELECT key FROM achievements WHERE student_id=?", (st["id"],)).fetchall()}
        sgarden = get_garden(db, st["id"])
        vac = db.execute("SELECT * FROM vacations WHERE student_id=? AND end_day>=? "
                         "ORDER BY start_day LIMIT 1",
                         (st["id"], datetime.now().date().isoformat())).fetchone()
        student_cards.append({"student": st, "stats": sstats, "vacation": vac,
                              "goal": goals.target(db, st["id"]),
                              "week": week_report(db, st["id"], weeks_back),
                              "earned_count": len(earned),
                              "garden": sgarden,
                              "tree_stage": tree_stage(sgarden["streak_days"]),
                              "tree_count": tree_count_for(sgarden["streak_days"]),
                              "deco_count": db.execute(
                                  "SELECT COUNT(*) c FROM decorations WHERE student_id=?",
                                  (st["id"],)).fetchone()["c"]})

    # Зачёт уроков: состояние каждого урока для каждого ученика
    credit_cards = []
    for card in student_cards:
        sst = card["stats"]
        rows = [{"lesson": l,
                 "state": ("credited" if l["id"] in sst["credited_ids"] else
                           "done" if l["id"] in sst["completed_ids"] else "none")}
                for l in ALL_LESSONS]
        credit_cards.append({"student": card["student"], "rows": rows})

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
    achievements = [{**{k: v for k, v in a.items() if k != "check"},
                     "earned": any(k[1] == a["key"] for k in earned),
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
                           credit_cards=credit_cards, main_count=len(LESSONS),
                           names_by_id=names_by_id, emojis_by_id=emojis_by_id,
                           student_emojis=STUDENT_EMOJIS, weeks_back=weeks_back,
                           max_weeks_back=MAX_WEEKS_BACK,
                           goal_limits=(goals.MAX_LESSONS, goals.MAX_WORDS),
                           seasons=[{"key": k, **v, "mode": get_mode(k), "custom": get_dates(k), "auto_now": in_season(k)}
                                    for k, v in SEASONS.items()],
                           lesson_titles={l["id"]: (f'{l["num"]}. ' if l.get("num") else "") + l["title"] for l in ALL_LESSONS},
                           total_lessons=len(LESSONS))


@bp.route("/api/mistakes")
def api_mistakes():
    """Все ошибки по всем попыткам — для таблицы в кабинете администратора."""
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
