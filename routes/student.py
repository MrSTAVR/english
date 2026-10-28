# -*- coding: utf-8 -*-
"""Режим ученика: список уроков, урок, сдача теста."""

import json
from badges import CAT_ICONS, TIERS
from achievements import (ACHIEVEMENTS, CATEGORIES, public, tier_counts,
                          update_achievements, views as achievement_views)
import config
import goals
from routes.games import dialogs_for
from curriculum import ALL_LESSONS, LESSONS, LESSONS_BY_ID, pass_mark, unlocked_lesson_ids
from data.course import ISLANDS
from data.extra_lessons import EXTRA_LESSONS
from database import get_db
from datetime import datetime
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
import activity
import castle
import weekly
import seasons
from seasons import active_season, advent_open, content
from garden import award_coins, get_garden, on_vacation, refresh_garden, tree_count_for, tree_stage
import friends
from friends import post as feed_post
from grading import grade_question, near_miss, near_dict
from mascot import build_mascot_ctx
from review import counts as review_counts, learned_pool, send_mistakes, state as review_state, word_of_day
from stats import compute_stats

from routes.common import get_student_or_none, require_role

bp = Blueprint("student", __name__)


@bp.route("/student/theory")
def theory_page():
    """Теория из всех пройденных (и зачтённых) уроков."""
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    stats = compute_stats(db, student["id"])
    lessons = [l for l in ALL_LESSONS if l["id"] in stats["completed_ids"] and l.get("theory")]
    mascot = build_mascot_ctx()
    mascot["empty"] = not lessons
    return render_template("theory.html", mascot=mascot, lessons=lessons)


@bp.route("/student/words")
def words_page():
    """Словарь ученика: все слова из пройденных (и зачтённых) уроков."""
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    stats = compute_stats(db, student["id"])
    groups = [{"lesson": l, "words": l["material"]}
              for l in ALL_LESSONS if l["id"] in stats["completed_ids"]]
    mascot = build_mascot_ctx()
    mascot["empty"] = not groups
    return render_template("words.html", mascot=mascot, groups=groups,
                           total_words=sum(len(g["words"]) for g in groups),
                           name=student["display_name"], emoji=student["emoji"])


@bp.route("/student")
def student_home():
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        flash("Аккаунт был удалён родителем. Войди заново 🙂", "error")
        return redirect(url_for("auth.index"))
    stats = compute_stats(db, student["id"])
    garden = refresh_garden(db, student["id"])
    weekly_got = weekly.claim(db, student["id"])
    if weekly_got:
        _new = update_achievements(db, compute_stats(db, student["id"]), student["id"])
        if _new:
            session["new_achievements"] = (session.get("new_achievements") or []) + [a["key"] for a in _new]
    unlocked = unlocked_lesson_ids(stats)

    def lesson_info(l):
        best = stats["best_by_lesson"].get(l["id"])
        credited = l["id"] in stats["credited_ids"]
        return {
            "lesson": l,
            "locked": l["id"] not in unlocked,
            "done": l["id"] in stats["completed_ids"],
            "credited": credited,
            "best_score": best["score_percent"] if best and not credited else None,
        }

    lessons_info = [lesson_info(l) for l in LESSONS]
    extra_info = [lesson_info(l) for l in EXTRA_LESSONS]
    extras_done = sum(1 for i in extra_info if i["done"])
    achievements = achievement_views(db, stats, student["id"])
    new_keys = session.pop("new_achievements", None) or []
    new_badge = [a for a in achievements if a["key"] in new_keys]
    ach_recent = sorted((a for a in achievements if a["earned"]),
                        key=lambda a: a["earned_at"] or "", reverse=True)[:8]
    ach_next = sorted((a for a in achievements if not a["earned"] and a["progress"]),
                      key=lambda a: -a["progress"][2])[:3]
    mascot = build_mascot_ctx()
    mascot["alreadyStarted"] = bool(stats["attempts"] or stats["completed_ids"])
    mascot["allDone"] = stats["lessons_completed"] >= len(LESSONS)
    # Следующий непройденный доступный урок (для крупной кнопки «Продолжить»)
    next_lesson = None
    for l in LESSONS:
        if l["id"] in unlocked and l["id"] not in stats["completed_ids"]:
            next_lesson = l
            break
    resume = resume_info(db, student["id"], unlocked, stats["completed_ids"])
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
    rv_pool = learned_pool(stats)
    rv_state = review_state(db, student["id"])
    rv_due, rv_new, rv_mastered = review_counts(rv_pool, rv_state)
    goal = goals.view(db, student["id"], stats, len(rv_pool))
    season, adv = active_season(), advent_open()
    return render_template("student_home.html", goal=goal, rv_pool=len(rv_pool), rv_ready=rv_due + min(rv_new, 10),
                           rv_mastered=rv_mastered, wod=word_of_day(rv_pool, rv_state, student["id"]), mascot=mascot, speaking=config.SPEAKING,
                           name=student["display_name"],
                           emoji=student["emoji"],
                           friends_on=friends.competing(student),
                           friends_news=friends.news_count(db, student["id"]) if friends.competing(student) else 0,
                           duel_calls=friends.incoming_count(db, student["id"]) if friends.competing(student) else 0,
                           lessons=lessons_info,
                           hidden_lessons_count=hidden_count,
                           extra_lessons=extra_info,
                           extras_done=extras_done,
                           total_extras=len(EXTRA_LESSONS),
                           stats=stats,
                           achievements=achievements, ach_recent=ach_recent, ach_next=ach_next,
                           total_lessons=len(LESSONS),
                           new_badge=new_badge,
                           next_lesson=next_lesson, resume=resume,
                           earned_count=earned_count,
                           garden=garden,
                           on_vacation=on_vacation(db, student["id"]),
                           season=season, season_banner=content(season).BANNER if season else "",
                           birthday_banner=content("birthday").BANNER.format(name=student["display_name"])
                           if seasons.birthday_active(student["birthday"]) else "",
                           advent=adv, advent_today_open=adv and bool(db.execute(
                               "SELECT 1 FROM advent WHERE student_id=? AND year=? AND day=?",
                               (student["id"], seasons.today().year, seasons.today().day)).fetchone()),
                           weekly=weekly.status(db, student["id"]),
                           weekly_got=weekly_got,
                           tree_stage=tree_stage(garden["streak_days"]),
                           tree_count=tree_count_for(garden["streak_days"]))


STEP_NAMES = {"step-theory": "Теория", "step-material": "Слова", "step-exercises": "Тренировка", "step-test": "Тест"}


def _resume_sub(lesson, st):
    """Подпись карточки «Продолжи урок» по сохранённому месту (st — dict из lesson_progress)."""
    step = st.get("step") if st.get("step") in STEP_NAMES else "step-theory"
    sub = "Ты на шаге «" + STEP_NAMES[step] + "»"
    if step == "step-material":
        words = st.get("words")
        seen = words.get("seen") if isinstance(words, dict) else None
        if isinstance(seen, list) and seen:
            sub += f" · {len(seen)} из {len(lesson['material'])} слов"
    elif step == "step-test":
        t = st.get("test") if isinstance(st.get("test"), dict) else {}

        def n(key, as_list):
            v = t.get(key)
            if as_list:
                return sum(1 for x in v if x and str(x).strip()) if isinstance(v, list) else 0
            return len(v) if isinstance(v, dict) else 0
        done = n("radio", False) + n("lines", False) + n("text", True) + n("match", True) + n("sort", True)
        total = len(lesson["test"])
        if done:
            done = min(done, total)
            sub = f"Ты на тесте · отвечено {done} из {total}"
            if done * 4 >= total * 3 or total - done <= 2:
                sub += " — осталось совсем чуть-чуть!"
            elif done * 2 >= total:
                sub += " — уже половина!"
    return sub


def resume_info(db, student_id, unlocked, completed=()):
    """Последний начатый и не сданный урок (сохранённое место) — для карточки «Продолжи урок» на главной.
    Сданные уроки пропускаем: туда заходят повторить, а главная кнопка должна вести вперёд."""
    rows = db.execute("SELECT lesson_id, state FROM lesson_progress WHERE student_id=? ORDER BY updated_at DESC",
                      (student_id,)).fetchall()
    for r in rows:
        lesson = LESSONS_BY_ID.get(r["lesson_id"])
        if not lesson or r["lesson_id"] not in unlocked or r["lesson_id"] in completed:
            continue
        try:
            st = json.loads(r["state"] or "{}")
        except ValueError:
            continue
        if not isinstance(st, dict):
            continue
        return {"lesson": lesson, "sub": _resume_sub(lesson, st)}
    return None


def fix_correct(db, student_id, lesson, attempt_id):
    """«Исправь ошибки»: {номер вопроса: результат} верных ответов прошлой несданной попытки этого урока —
    их не спрашиваем снова. Пусто, если попытка чужая, не та, сдана или тест с тех пор поменялся."""
    if not attempt_id:
        return {}
    a = db.execute("SELECT * FROM attempts WHERE id=? AND student_id=? AND lesson_id=?",
                   (attempt_id, student_id, lesson["id"])).fetchone()
    if not a or not a["finished_at"] or a["passed"]:
        return {}
    try:
        results = json.loads(a["details_json"] or "{}").get("results")
    except (ValueError, AttributeError):
        return {}
    test = lesson["test"]
    if not isinstance(results, list) or len(results) != len(test):
        return {}
    return {i: r for i, r in enumerate(results)
            if isinstance(r, dict) and r.get("correct") and r.get("q") == test[i]["q"]}


@bp.route("/lesson/<int:lesson_id>")
def lesson_page(lesson_id):
    err = require_role("student")
    if err:
        return err
    lesson = LESSONS_BY_ID.get(lesson_id) or abort(404)
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    stats = compute_stats(db, student["id"])
    if lesson_id not in unlocked_lesson_ids(stats):
        flash("Сначала пройди предыдущий урок! 😉", "error")
        return redirect(url_for("student.student_home"))
    # серию дня продлевает не открытие урока, а занятие (тест, игра, история…) — см. garden.study_days
    # Создаём новую попытку (начало занятия)
    started = datetime.now()
    cur = db.execute(
        "INSERT INTO attempts (student_id, lesson_id, started_at) VALUES (?, ?, ?)",
        (student["id"], lesson_id, started.isoformat(timespec="seconds")))
    db.commit()
    saved = load_progress(db, student["id"], lesson_id)
    fix_from = request.args.get("fix", type=int)
    fix_done = fix_correct(db, student["id"], lesson, fix_from)
    mascot = build_mascot_ctx()
    mascot["lessonId"] = lesson_id
    mascot["lessonTitle"] = lesson["title"]
    return render_template("lesson.html", lesson=lesson, near_words=near_dict(lesson), speaking=config.SPEAKING, need=pass_mark(lesson), total_lessons=len(LESSONS),
                           saved_state=saved,
                           lesson_dialogs=dialogs_for(db, student["id"], {lesson_id}),
                           me_emoji=student["emoji"] or "🎒", me_name=student["display_name"],
                           attempt_id=cur.lastrowid, fix_from=fix_from, fix_done=fix_done,
                           started_ts=started.timestamp() - (saved or {}).get("secs", 0),   # время урока копится
                           mascot=mascot)


PROGRESS_MAX = 20000          # байт JSON на один урок
PROGRESS_STEPS = ("step-theory", "step-material", "step-exercises", "step-test")


def load_progress(db, student_id, lesson_id):
    """Сохранённое место в уроке (или None)."""
    row = db.execute("SELECT state FROM lesson_progress WHERE student_id=? AND lesson_id=?", (student_id, lesson_id)).fetchone()
    if not row:
        return None
    try:
        state = json.loads(row["state"])
    except ValueError:
        return None
    if not isinstance(state, dict) or state.get("step") not in PROGRESS_STEPS:
        return None
    secs = state.get("secs")
    state["secs"] = min(int(secs), 4 * 3600) if isinstance(secs, (int, float)) and secs > 0 else 0
    return state


@bp.route("/api/lesson/<int:lesson_id>/progress", methods=["POST"])
def save_progress(lesson_id):
    """Запоминаем, где ученик в уроке: шаг, слово, ответы. {"reset": true} — начать заново."""
    if session.get("role") != "student" or lesson_id not in LESSONS_BY_ID:
        abort(403 if session.get("role") != "student" else 404)
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        abort(403)
    data = request.get_json(silent=True) or {}
    if data.get("reset"):
        db.execute("DELETE FROM lesson_progress WHERE student_id=? AND lesson_id=?", (student["id"], lesson_id))
        db.commit()
        return jsonify(ok=True)
    state = data.get("state")
    raw = json.dumps(state, ensure_ascii=False) if isinstance(state, dict) else ""
    if not raw or len(raw.encode()) > PROGRESS_MAX or state.get("step") not in PROGRESS_STEPS:
        abort(400)
    db.execute("INSERT OR REPLACE INTO lesson_progress (student_id, lesson_id, state, updated_at) VALUES (?, ?, ?, ?)",
               (student["id"], lesson_id, raw, datetime.now().isoformat(timespec="seconds")))
    db.commit()
    return jsonify(ok=True)


@bp.route("/lesson/<int:lesson_id>/submit", methods=["POST"])
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
        return redirect(url_for("auth.index"))
    attempt = db.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
    if not attempt or attempt["student_id"] != student["id"] or attempt["lesson_id"] != lesson_id:
        abort(400)
    if lesson_id not in unlocked_lesson_ids(compute_stats(db, student["id"])):
        abort(400)
    if attempt["finished_at"]:
        try:
            ago = (datetime.now() - datetime.fromisoformat(attempt["finished_at"])).total_seconds()
        except ValueError:
            ago = 3600
        if ago < 60:                                     # повторная отправка той же формы (двойное нажатие, «Назад»)
            flash("Этот тест уже проверен — результат сохранён.", "info")
            return redirect(url_for("student.student_home"))
        # страница урока из офлайн-кэша со старой попыткой — ответы не теряем, заводим новую попытку
        cur = db.execute("INSERT INTO attempts (student_id, lesson_id, started_at) VALUES (?, ?, ?)",
                         (student["id"], lesson_id, datetime.now().isoformat(timespec="seconds")))
        attempt_id = cur.lastrowid

    test = lesson["test"]
    results, mistakes = [], []
    correct = 0
    fixed = fix_correct(db, student["id"], lesson, request.form.get("fix_from", type=int))
    for i, q in enumerate(test):
        if i in fixed:                                   # «Исправь ошибки»: верный ответ прошлой попытки засчитан
            results.append(fixed[i])
            correct += 1
            continue
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
        almost = not ok and q["type"] == "type_in" and near_miss(q, given)   # опечатку засчитываем
        ok = ok or almost
        if q["type"] == "choice":                        # в разборе — текст выбранного варианта, а не его номер
            shown = q["options"][given] if 0 <= given < len(q["options"]) else ""
        elif q["type"] in ("match", "sort"):             # служебная запись пар — ребёнку не показываем
            shown = ""
        else:
            shown = str(given)
        if ok:
            correct += 1
        else:
            mistakes.append({"question": q["q"],
                             "given": shown or "(пусто)",
                             "correct": str(correct_disp)})
        results.append({"q": q["q"], "type": q["type"],
                        "given": shown,
                        "correct_answer": str(correct_disp),
                        "explain": q.get("explain", ""),
                        "correct": bool(ok), "almost": almost,
                        "helped": bool(ok and request.form.get(f"q{i}_help"))})   # с подсказкой — слово в повторение

    total = len(test)
    percent = round(100 * correct / total) if total else 0
    need = pass_mark(lesson)
    passed = percent >= need
    first_pass = passed and not db.execute(
        "SELECT 1 FROM attempts WHERE student_id=? AND lesson_id=? AND passed=1 AND id<>?",
        (student["id"], lesson_id, attempt_id)).fetchone()
    finished = datetime.now()
    db.execute(
        """UPDATE attempts SET finished_at=?, seconds_spent=?, score_percent=?,
           passed=?, total_q=?, correct_q=?, mistakes_json=?, details_json=? WHERE id=?""",
        (finished.isoformat(timespec="seconds"), seconds, percent, int(passed),
         total, correct, json.dumps(mistakes, ensure_ascii=False),
         json.dumps({"results": results}, ensure_ascii=False), attempt_id))
    db.commit()
    bricks_earned = 0
    if first_pass:
        feed_post(db, student["id"], "lesson", f"Урок пройден: «{lesson['title']}»")
        bricks_earned = castle.on_lesson_passed(db, student["id"], lesson)
    db.execute("DELETE FROM lesson_progress WHERE student_id=? AND lesson_id=?", (student["id"], lesson_id))   # урок сдан
    to_review = send_mistakes(db, student["id"], results, lesson_id)     # ошибки — в повторение слов

    stats = compute_stats(db, student["id"])
    _row, goal_coins, goal_done = goals.add(db, student["id"], stats, len(learned_pool(stats)),
                                            lessons=1 if passed else 0)
    stats = compute_stats(db, student["id"])             # цель дня могла дать ачивку
    new_achievements = update_achievements(db, stats, student["id"])
    if new_achievements:
        session["new_achievements"] = [a["key"] for a in new_achievements]

    if passed:
        activity.log(db, student["id"], "lesson")
    coins_earned, coins_why = award_coins(db, student["id"], percent, passed, lesson_id, attempt_id, fixed=bool(fixed))
    garden = get_garden(db, student["id"])

    mascot = build_mascot_ctx()
    mascot["percent"] = percent
    mascot["passed"] = passed
    mascot["coinsEarned"] = coins_earned
    mascot["goalDone"] = goal_done
    mascot["goalCoins"] = goal_coins
    mascot["newAchievements"] = [public(a) for a in new_achievements]
    return render_template("result.html", mascot=mascot,
                           lesson=lesson, percent=percent, passed=passed, need=need,
                           correct=correct, total=total, missing=max(0, -(-need * total // 100) - correct), attempt_id=attempt_id, fixed=bool(fixed), coins_why=coins_why,
                           seconds=seconds, results=results, to_review=to_review,
                           coins_earned=coins_earned, bricks_earned=bricks_earned,
                           coins_total=garden["coins"],
                           streak_days=garden["streak_days"],
                           tier_names={k: v["name"] for k, v in TIERS.items()},
                           new_achievements=[a for a in ACHIEVEMENTS
                                             if a["key"] in [n["key"] for n in new_achievements]])




def _stars(score):
    return 3 if score >= 90 else 2 if score >= 80 else 1


@bp.route("/student/map")
def course_map():
    """Карта курса: тропинка по всем основным урокам в порядке прохождения."""
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    stats = compute_stats(db, student["id"])
    unlocked = unlocked_lesson_ids(stats)
    nodes, current = [], None
    for pos, l in enumerate(LESSONS, 1):
        best = stats["best_by_lesson"].get(l["id"])
        done = l["id"] in stats["completed_ids"]
        credited = l["id"] in stats["credited_ids"]
        node = {"pos": pos, "lesson": l, "done": done, "locked": l["id"] not in unlocked,
                "stars": _stars(best["score_percent"]) if done and best and not credited else 0, "credited": credited}
        if current is None and not done and not node["locked"]:
            current = node
            node["current"] = True
        nodes.append(node)
    by_id = {n["lesson"]["id"]: n for n in nodes}
    parts = [{"title": title, "nodes": [by_id[i] for i in ids if i in by_id]} for title, ids in ISLANDS]   # острова — data/course.py
    for part in parts:
        part["done"] = all(n["done"] for n in part["nodes"])
    mascot = build_mascot_ctx()
    mascot["page"] = "map"
    return render_template("course_map.html", parts=parts, mascot=mascot, done=stats["lessons_completed"],
                           total=len(LESSONS), current=current)


@bp.route("/student/achievements")
def achievements_page():
    """Коллекция наград: медали по категориям, шкалы прогресса, счётчики по уровням."""
    err = require_role("student")
    if err:
        return err
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        session.clear()
        return redirect(url_for("auth.index"))
    items = achievement_views(db, compute_stats(db, student["id"]), student["id"])
    groups = [{"key": k, "name": n, "icon": CAT_ICONS.get(k, "medal"), "items": [i for i in items if i["cat"] == k]}
              for k, n, _e in CATEGORIES]
    soon = sorted((i for i in items if not i["earned"] and i["progress"] and i["progress"][2] > 0),
                  key=lambda i: -i["progress"][2])[:3]
    mascot = build_mascot_ctx()
    mascot["earned"] = sum(1 for i in items if i["earned"])
    mascot["total"] = len(items)
    return render_template("achievements.html", mascot=mascot, groups=groups,
                           earned=mascot["earned"], total=len(items),
                           tiers=tier_counts(items), soon=soon)
