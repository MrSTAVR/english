# -*- coding: utf-8 -*-
"""Кабинет администратора (роль "parent"): аккаунты учеников, статистика, API ошибок."""

import json
import logging
import sqlite3
import tempfile
import time

import backup_db
import castle
import config
import visits
import database
import friends
import goals
import speech
import remind
import tg
import updates
from achievements import ACHIEVEMENTS, update_achievements
from curriculum import ALL_LESSONS, LESSONS, LESSONS_BY_ID
from database import get_db
from datetime import datetime
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from garden import cap_streak, get_garden, tree_count_for, tree_stage
from report import MAX_WEEKS_BACK, activity_heatmap, hard_words, score_trend, week_report
from progress import credit_lessons, lesson_ids_upto, uncredit_lessons
from seasons import SEASONS, active_season, dates_text, get_dates, get_mode, in_season, is_yearly, set_dates, set_mode, set_yearly
from security import hash_password
from stats import compute_stats
from version import info as app_version

from routes.common import require_role

bp = Blueprint("parent", __name__)
log = logging.getLogger(__name__)


STUDENT_EMOJIS = ["🦄", "🐱", "🐰", "🦊", "🐼", "🐥", "🦋", "🌈", "🚀", "🎀", "🐢", "🦁"]


def _student_page():
    """Куда вернуться после действия с учеником: на его страницу (или к списку)."""
    sid = (request.view_args or {}).get("sid")
    return url_for("parent.parent_student", sid=sid) if sid else url_for("parent.parent_students")


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
    return redirect(_student_page())


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
    for table in ("wardrobe_items", "wardrobe_wear", "story_done", "game_scores", "dialog_done", "word_review", "speaking", "daily_goal", "goal_settings", "vacations", "activity", "weekly_done", "boss_wins", "season_log", "advent", "birthday_gifts", "house_items", "house_place", "lesson_progress"):
        db.execute(f"DELETE FROM {table} WHERE student_id=?", (sid,))
    friends.forget_student(db, sid)
    castle.forget_student(db, sid)
    visits.forget_student(db, sid)
    db.execute("DELETE FROM students WHERE id=?", (sid,))
    db.commit()
    flash(f"Аккаунт {student['display_name']} удалён вместе с его прогрессом.", "success")
    return redirect(url_for("parent.parent_students"))


@bp.route("/parent/students/<int:sid>/reset_password", methods=["POST"])
def reset_student_password(sid):
    err = require_role("parent")
    if err:
        return err
    password = request.form.get("password") or ""
    if len(password) < 4:
        flash("Новый пароль должен быть не короче 4 символов.", "error")
        return redirect(_student_page())
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
    if not student:
        abort(404)
    db.execute("UPDATE students SET password_hash=? WHERE id=?",
               (hash_password(password), sid))
    db.commit()
    flash(f"Пароль для {student['display_name']} обновлён 🔑", "success")
    return redirect(_student_page())


@bp.route("/parent/students/<int:sid>/garden", methods=["POST"])
def parent_update_garden(sid):
    """Настройка сада и замка ребёнка: серия дней, монетки, кирпичики."""
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
    bricks = _num("bricks")
    if streak is None and coins is None and bricks is None:
        flash("Ничего не изменено — заполни хотя бы одно поле.", "error")
        return redirect(_student_page())
    if streak is not None:
        streak = cap_streak(streak)  # серия ограничена STREAK_CAP днями
        # синхронизируем last_study_day с реальностью, чтобы refresh не сбросил серию
        if streak > 0:
            db.execute("UPDATE garden SET streak_days=?, broken=0, manual=1 WHERE student_id=?",
                       (streak, sid))
        else:
            # «прерываем» серию — как будто пропущены дни: дерево возвращается
            # к начальному размеру, сад «засыпает» (украшения и монетки остаются)
            db.execute("UPDATE garden SET streak_days=0, broken=1, manual=1 WHERE student_id=?",
                       (sid,))
        best = cap_streak(max(int(g["best_streak"]), streak or 0))
        db.execute("UPDATE garden SET best_streak=? WHERE student_id=?", (best, sid))
    if coins is not None:
        db.execute("UPDATE garden SET coins=? WHERE student_id=?", (coins, sid))
    if bricks is not None:
        castle.set_bricks(db, sid, bricks)
    db.commit()
    flash(f"Сад и замок для {student['display_name']} обновлены: серия {streak if streak is not None else g['streak_days']} дн., "
          f"монет {coins if coins is not None else g['coins']}, кирпичиков {castle.bricks(db, sid)}", "success")
    return redirect(_student_page())


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
    back = redirect(url_for("parent.parent_student", sid=sid) + "#credit")
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
        return redirect(_student_page())
    try:
        d1 = datetime.strptime(request.form.get("start_day", ""), "%Y-%m-%d").date()
        d2 = datetime.strptime(request.form.get("end_day", ""), "%Y-%m-%d").date()
    except ValueError:
        flash("Укажите даты начала и конца каникул.", "error")
        return redirect(_student_page())
    if d2 < d1 or (d2 - d1).days > 60 or d2 < today:
        flash("Даты некорректны: конец не раньше начала, не дольше 60 дней, не в прошлом.", "error")
        return redirect(_student_page())
    db.execute("INSERT INTO vacations (student_id, start_day, end_day) VALUES (?,?,?)",
               (sid, d1.isoformat(), d2.isoformat()))
    db.commit()
    flash("Каникулы сохранены: серия в эти дни не сгорит. 🏖", "ok")
    return redirect(_student_page())


@bp.route("/parent/students/<int:sid>/birthday", methods=["POST"])
def parent_birthday(sid):
    """День рождения ученика — личный праздник (пусто — убрать)."""
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    if not db.execute("SELECT 1 FROM students WHERE id=?", (sid,)).fetchone():
        abort(404)
    raw = (request.form.get("birthday") or "").strip()
    try:
        value = datetime.strptime(raw, "%Y-%m-%d").date().isoformat() if raw else None
    except ValueError:
        flash("Дата рождения некорректна.", "error")
        return redirect(_student_page())
    db.execute("UPDATE students SET birthday=? WHERE id=?", (value, sid))
    db.commit()
    flash("День рождения сохранён 🎂 — в эти дни у ученика будет праздник." if value else "День рождения убран.", "ok")
    return redirect(_student_page())


@bp.route("/parent/students/<int:sid>/competitions", methods=["POST"])
def parent_competitions(sid):
    """Участвует ли ученик в «Друзьях»: дуэли, рекорды, лента, гости."""
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    if not db.execute("SELECT 1 FROM students WHERE id=?", (sid,)).fetchone():
        abort(404)
    on = request.form.get("on") == "1"
    db.execute("UPDATE students SET competitions=? WHERE id=?", (int(on), sid))
    db.commit()
    flash("Соревнования включены." if on else "Соревнования выключены: ученик не видит друзей, а друзья — его.", "ok")
    return redirect(_student_page())


@bp.route("/parent/students/<int:sid>/avatar", methods=["POST"])
def parent_avatar(sid):
    """Аватарка ученика (эмодзи из STUDENT_EMOJIS)."""
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    if not db.execute("SELECT 1 FROM students WHERE id=?", (sid,)).fetchone():
        abort(404)
    emoji = request.form.get("emoji") or ""
    if emoji not in STUDENT_EMOJIS:
        flash("Выберите аватарку из списка.", "error")
        return redirect(_student_page())
    db.execute("UPDATE students SET emoji=? WHERE id=?", (emoji, sid))
    db.commit()
    flash("Аватарка сохранена.", "ok")
    return redirect(_student_page())


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
    return redirect(_student_page())


@bp.route("/parent/students/<int:sid>/review_hard", methods=["POST"])
def parent_review_hard(sid):
    """Трудные слова — в повторение сегодня (коробка 0)."""
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    if not db.execute("SELECT 1 FROM students WHERE id=?", (sid,)).fetchone():
        abort(404)
    keys = [w["key"] for w in hard_words(db, sid)]
    db.executemany("UPDATE word_review SET box=0, due=? WHERE student_id=? AND key=?",
                   [(datetime.now().date().isoformat(), sid, k) for k in keys])
    db.commit()
    flash(f"Слов отправлено в повторение на сегодня: {len(keys)} 🔁" if keys else "Трудных слов нет 🎉", "ok")
    return redirect(url_for("parent.parent_progress") + f"#s{sid}")


@bp.route("/parent/logopeds", methods=["POST"])
def parent_logopeds():
    """Аккаунты логопедов: action=add (логин, имя, пароль) / password (новый пароль)."""
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    action = request.form.get("action")
    if action == "add":
        _id, error = speech.create_logoped(db, (request.form.get("username") or "").strip(),
                                           request.form.get("name") or "", request.form.get("password") or "")
        flash(error or "Аккаунт логопеда создан. Вход: /logoped 👩‍⚕️", "error" if error else "ok")
    elif action == "password":
        password = request.form.get("password") or ""
        lid = request.form.get("id", type=int)
        if len(password) < speech.MIN_PASSWORD:
            flash(f"Пароль должен быть не короче {speech.MIN_PASSWORD} символов.", "error")
        elif not db.execute("SELECT 1 FROM sp_logopeds WHERE id=?", (lid,)).fetchone():
            abort(404)
        else:
            db.execute("UPDATE sp_logopeds SET password_hash=? WHERE id=?", (hash_password(password), lid))
            db.commit()
            flash("Пароль логопеда обновлён 🔑", "ok")
    else:
        abort(400)
    return redirect(url_for("parent.parent_logopeds_page"))


@bp.route("/parent/updates", methods=["POST"])
def parent_updates():
    """Обновления сайта: action=now (обновить сейчас) / auto_on / auto_off."""
    err = require_role("parent")
    if err:
        return err
    action = request.form.get("action")
    try:
        if action == "now":
            updates.request_update()
            flash("Запрос отправлен: сервер проверит GitHub и обновится в течение минуты. Обнови страницу чуть позже. 🔄", "ok")
        elif action in ("auto_on", "auto_off"):
            updates.set_auto(action == "auto_on")
            flash("Автообновление включено ✅" if action == "auto_on" else
                  "Автообновление выключено: новые версии ставятся только кнопкой.", "ok")
        else:
            abort(400)
    except OSError as e:
        flash(f"Не удалось передать команду серверу: {e}", "error")
    return redirect(url_for("parent.parent_updates_page"))


@bp.route("/parent/updates/state")
def parent_updates_state():
    """Для страницы, ждущей сервер: выполнена ли просьба «Обновить сейчас»."""
    if session.get("role") != "parent":
        abort(403)
    st = updates.status() or {}
    return jsonify(pending=updates.update_pending(), checked=st.get("checked", ""), version=app_version()["full"])


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
            return redirect(url_for("parent.parent_holidays"))
    if set_mode(db, key, request.form.get("mode", "")) and set_dates(db, key, d1, d2):
        set_yearly(db, key, bool(request.form.get("yearly")) and d1 is not None)
        flash("Настройка праздника сохранена.", "ok")
    else:
        flash("Не удалось сохранить настройку.", "error")
    return redirect(url_for("parent.parent_holidays"))


def _students(db):
    return db.execute("SELECT * FROM students ORDER BY created_at ASC").fetchall()


def _admin(template, **ctx):
    """Страница кабинета администратора (общий каркас с вкладками — templates/admin/_layout.html)."""
    return render_template(f"admin/{template}", **ctx)


def _last_activity(db, sid):
    r = db.execute("SELECT MAX(d) FROM (SELECT MAX(day) d FROM activity WHERE student_id=? "
                   "UNION SELECT MAX(substr(finished_at, 1, 10)) FROM attempts WHERE student_id=? AND COALESCE(manual, 0)=0 "
                   "UNION SELECT MAX(day) FROM daily_goal WHERE student_id=?)", (sid, sid, sid)).fetchone()[0]
    return datetime.strptime(r, "%Y-%m-%d").strftime("%d.%m.%Y") if r else None


@bp.route("/parent")
def parent_dashboard():
    """Обзор: компактная карточка на каждого ученика и короткий статус сайта."""
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    cards = []
    for st in _students(db):
        sstats = compute_stats(db, st["id"])
        garden = get_garden(db, st["id"])
        vac = db.execute("SELECT * FROM vacations WHERE student_id=? AND end_day>=? ORDER BY start_day LIMIT 1",
                         (st["id"], datetime.now().date().isoformat())).fetchone()
        cards.append({"student": st, "stats": sstats, "garden": garden, "vacation": vac,
                      "tree_stage": tree_stage(garden["streak_days"]), "goal": goals.target(db, st["id"]),
                      "week": week_report(db, st["id"]), "last": _last_activity(db, st["id"]),
                      "hard_count": len(hard_words(db, st["id"]))})
    season = active_season()
    return _admin("overview.html", tab="overview", cards=cards, total_lessons=len(LESSONS),
                  upd=updates.view(app_version()["commit"]), tg=tg.settings(db),
                  season=SEASONS.get(season) if season else None,
                  logoped_count=db.execute("SELECT COUNT(*) FROM sp_logopeds").fetchone()[0])


@bp.route("/parent/students")
def parent_students():
    """Ученики: список и новый аккаунт."""
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    rows = [{"student": st, "stats": compute_stats(db, st["id"]), "last": _last_activity(db, st["id"])}
            for st in _students(db)]
    return _admin("students.html", tab="students", rows=rows, total_lessons=len(LESSONS),
                  student_emojis=STUDENT_EMOJIS)


@bp.route("/parent/students/<int:sid>")
def parent_student(sid):
    """Настройки одного ученика: цель дня, день рождения, каникулы, сад, зачёт уроков, пароль."""
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    st = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone() or abort(404)
    sstats = compute_stats(db, sid)
    garden = get_garden(db, sid)
    vac = db.execute("SELECT * FROM vacations WHERE student_id=? AND end_day>=? ORDER BY start_day LIMIT 1",
                     (sid, datetime.now().date().isoformat())).fetchone()
    rows = [{"lesson": l, "state": ("credited" if l["id"] in sstats["credited_ids"] else
                                    "done" if l["id"] in sstats["completed_ids"] else "none")} for l in ALL_LESSONS]
    earned = db.execute("SELECT COUNT(*) FROM achievements WHERE student_id=?", (sid,)).fetchone()[0]
    return _admin("student.html", tab="students", st=st, student_emojis=STUDENT_EMOJIS, stats=sstats, garden=garden, vacation=vac,
                  tree_stage=tree_stage(garden["streak_days"]), tree_count=tree_count_for(garden["streak_days"]),
                  deco_count=db.execute("SELECT COUNT(*) FROM decorations WHERE student_id=?", (sid,)).fetchone()[0],
                  bricks=castle.bricks(db, sid),
                  goal=goals.target(db, sid), goal_limits=(goals.MAX_LESSONS, goals.MAX_WORDS), credit_rows=rows,
                  main_count=len(LESSONS), total_lessons=len(LESSONS), earned_count=earned,
                  achievements_total=len(ACHIEVEMENTS), last=_last_activity(db, sid), visits=visits.sessions(db, sid))


@bp.route("/parent/students/<int:sid>/switch", methods=["POST"])
def switch_to_student(sid):
    """Перейти в учётку ученика без пароля (для проверки нового); обратно — кнопкой «В админку»,
    пока действует вход администратора."""
    err = require_role("parent")
    if err:
        return err
    st = get_db().execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone() or abort(404)
    session["role"] = "student"
    session["student_id"] = st["id"]
    session["student_name"] = st["display_name"]
    session["admin_back"] = time.time() + config.ADMIN_BACK_MINUTES * 60   # срок кнопки «В админку»
    session["admin_last_student"] = st["id"]
    return redirect(url_for("student.student_home"))


@bp.route("/parent/progress")
def parent_progress():
    """Прогресс: неделя, 12 недель, уроки и история занятий."""
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    weeks_back = max(0, min(MAX_WEEKS_BACK, request.args.get("week", 0, type=int) or 0))
    students = _students(db)
    cards = [{"student": st, "week": week_report(db, st["id"], weeks_back), "heatmap": activity_heatmap(db, st["id"]),
              "trend": score_trend(db, st["id"]), "hard": hard_words(db, st["id"])} for st in students]
    stats = compute_stats(db)
    lesson_rows = []
    for l in ALL_LESSONS:
        la = [a for a in stats["attempts"] if a["lesson_id"] == l["id"]]
        best = max(la, key=lambda a: a["score_percent"], default=None)
        lesson_rows.append({"lesson": l, "tries": len(la), "passed": l["id"] in stats["completed_ids"],
                            "best_score": best["score_percent"] if best else None,
                            "time_spent": sum(a["seconds_spent"] or 0 for a in la)})
    return _admin("progress.html", tab="progress", cards=cards, weeks_back=weeks_back, max_weeks_back=MAX_WEEKS_BACK,
                  lessons=lesson_rows, attempts=list(reversed(stats["attempts"]))[:100],
                  names_by_id={st["id"]: st["display_name"] for st in students},
                  emojis_by_id={st["id"]: st["emoji"] for st in students},
                  lesson_titles={l["id"]: (f'{l["num"]}. ' if l.get("num") else "") + l["title"] for l in ALL_LESSONS})


@bp.route("/parent/mistakes")
def parent_mistakes():
    err = require_role("parent")
    if err:
        return err
    return _admin("mistakes.html", tab="mistakes")


@bp.route("/parent/holidays")
def parent_holidays():
    err = require_role("parent")
    if err:
        return err
    return _admin("holidays.html", tab="holidays",
                  seasons=[{"key": k, **v, "dates": dates_text(k), "mode": get_mode(k), "custom": get_dates(k),
                            "yearly": is_yearly(k), "auto_now": in_season(k)} for k, v in SEASONS.items()])


@bp.route("/parent/logopeds")
def parent_logopeds_page():
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    return _admin("logopeds.html", tab="logopeds", min_sp_password=speech.MIN_PASSWORD,
                  logopeds=db.execute("SELECT l.*, (SELECT COUNT(*) FROM sp_clients c WHERE c.logoped_id=l.id "
                                      "AND c.archived=0) AS n FROM sp_logopeds l ORDER BY l.name").fetchall())


@bp.route("/parent/updates")
def parent_updates_page():
    err = require_role("parent")
    if err:
        return err
    return _admin("updates.html", tab="updates", upd=updates.view(app_version()["commit"]))


@bp.route("/parent/telegram", methods=["GET", "POST"])
def parent_telegram():
    """Telegram-бот администратора: токен, привязка чата, отправка копий базы."""
    err = require_role("parent")
    if err:
        return err
    db = get_db()
    s = tg.settings(db)
    host = request.host.split(":")[0]
    if s["tg_token"] and host not in ("localhost", "127.0.0.1", s["tg_server"]):
        tg.save(db, tg_server=host)                    # для инструкции «как восстановить» в подписи к копии
    if request.method == "GET":
        students = db.execute("SELECT id, display_name, tg_remind FROM students ORDER BY id").fetchall()
        return _admin("telegram.html", tab="telegram", tg=tg.settings(db), students=students,
                      remind_hour=remind.REMIND_HOUR)
    action = request.form.get("action")
    try:
        if action == "token":
            token = (request.form.get("token") or "").strip()
            name = tg.check_token(token)
            tg.forget(db)
            tg.save(db, tg_token=token, tg_chat_name=name,
                    tg_server=None if host in ("localhost", "127.0.0.1") else host)
            flash(f"Бот {name} подключён ✅ Теперь откройте его в Telegram, нажмите «Запустить» и вернитесь сюда.", "ok")
        elif action == "link":
            chat, name = tg.find_chat(s["tg_token"])
            tg.send_message(s["tg_token"], chat, "✅ Готово! Сюда будут приходить резервные копии English Fun.")
            tg.save(db, tg_chat=chat, tg_chat_name=name)
            flash(f"Чат привязан: {name}. Бот отправил туда сообщение 👋", "ok")
        elif action == "test":
            tg.send_message(s["tg_token"], s["tg_chat"], "👋 Проверка связи из кабинета администратора English Fun.")
            flash("Сообщение отправлено — проверьте Telegram 📨", "ok")
        elif action == "backup":
            # сайту (systemd, ProtectSystem=strict) нельзя писать в папку копий — делаем во временной и удаляем
            with tempfile.TemporaryDirectory() as tmp:
                tg.send_backup(db, backup_db.make_backup(database.DB_PATH, tmp), force=True, on_server=False)
            flash("Копия базы отправлена в Telegram 💾", "ok")
        elif action in ("backups_on", "backups_off"):
            tg.save(db, tg_backups="1" if action == "backups_on" else "0")
            flash("Ежедневная отправка копий включена ✅" if action == "backups_on" else
                  "Ежедневная отправка копий выключена", "ok")
        elif action == "remind":                        # кому напоминать вечером (галочки по ученикам)
            on = {int(x) for x in request.form.getlist("remind") if x.isdigit()}
            for r in db.execute("SELECT id FROM students").fetchall():
                db.execute("UPDATE students SET tg_remind=? WHERE id=?", (int(r["id"] in on), r["id"]))
            db.commit()
            flash("Напоминания сохранены ✅", "ok")
        elif action == "remind_now":                    # пробное напоминание — сразу
            n = remind.run(db, force=True)
            flash(f"Отправлено напоминаний: {n} 📨" if n else "Некому напоминать — отметьте учеников", "ok")
        elif action == "forget":
            tg.forget(db)
            flash("Бот отключён. Удалите его в @BotFather (/deletebot), если он больше не нужен.", "ok")
        else:
            abort(400)
    except tg.TgError as e:
        flash(f"Не получилось: {e}", "error")
    except (OSError, sqlite3.Error, RuntimeError) as e:
        log.exception("копия базы для Telegram")
        flash(f"Копия базы не сделалась: {e}", "error")
    if request.form.get("back") == "overview":
        return redirect(url_for("parent.parent_dashboard"))
    return redirect(url_for("parent.parent_telegram"))


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
        except (ValueError, TypeError):
            log.warning("попытка %s: не читается details_json", r["id"])
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
