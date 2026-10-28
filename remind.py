#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Вечернее напоминание администратору в Telegram: python remind.py [--force]

Запускается таймером english-remind.timer в REMIND_HOUR (18:00 по времени сервера — Москва).
Для каждого ученика с включённым напоминанием (students.tg_remind, переключатель в кабинете
на вкладке Telegram): не занимался сегодня — «ещё не занималась» + серия и следующий урок;
занимался — короткая сводка дня. Каждому ученику — одно сообщение в день (app_settings
tg_remind_<id> = дата). На каникулах не напоминаем. Позже LATEST_HOUR не шлём (сервер мог лежать).
"""
import argparse
import logging
import sqlite3
import sys
from datetime import datetime

import config
import tg

log = logging.getLogger(__name__)

REMIND_HOUR = 18
LATEST_HOUR = 22


def _plural(n, one, few, many):
    n10, n100 = n % 10, n % 100
    return one if n10 == 1 and n100 != 11 else few if 2 <= n10 <= 4 and not 12 <= n100 <= 14 else many


def _next_lesson(stats):
    from curriculum import LESSONS, unlocked_lesson_ids
    unlocked = unlocked_lesson_ids(stats)
    return next((l for l in LESSONS if l["id"] in unlocked and l["id"] not in stats["completed_ids"]), None)


def _title(lesson):
    from template_filters import noemoji
    return noemoji(lesson["title"]).strip()


def build_message(db, student, today=None):
    """Текст напоминания (HTML для Telegram) или None, если напоминать не нужно (каникулы)."""
    import html
    import garden
    from stats import compute_stats
    today = today or datetime.now().date()
    sid, name = student["id"], html.escape(student["display_name"])
    if garden.on_vacation(db, sid, today):
        return None
    day = today.isoformat()
    streak, last = garden.compute_streak_from_history(db, sid)
    studied = today in garden.study_days(db, sid)
    stats = compute_stats(db, sid)
    nxt = _next_lesson(stats)
    lines = []
    if studied:
        passed = db.execute("SELECT lesson_id, MAX(score_percent) p FROM attempts WHERE student_id=? AND passed=1 "
                            "AND substr(finished_at, 1, 10)=? AND manual=0 GROUP BY lesson_id", (sid, day)).fetchall()
        kinds = {r[0]: r[1] for r in db.execute("SELECT kind, COUNT(*) FROM activity WHERE student_id=? AND day=? "
                                                "GROUP BY kind", (sid, day)).fetchall()}
        goal = db.execute("SELECT words, done FROM daily_goal WHERE student_id=? AND day=?", (sid, day)).fetchone()
        from curriculum import LESSONS_BY_ID
        lines.append(f"✅ <b>{name}</b> сегодня занималась.")
        for lid, p in passed:
            if lid in LESSONS_BY_ID:
                lines.append(f"• урок «{html.escape(_title(LESSONS_BY_ID[lid]))}» сдан — {round(p or 0)}%")
        if kinds.get("game"):
            lines.append(f"• игр: {kinds['game']}")
        if kinds.get("story"):
            lines.append(f"• историй: {kinds['story']}")
        if goal and goal[0]:
            lines.append(f"• слов в повторении: {goal[0]}" + (" — цель дня выполнена" if goal[1] else ""))
        lines.append(f"Серия: {streak} {_plural(streak, 'день', 'дня', 'дней')}.")
    else:
        lines.append(f"🔔 <b>{name}</b> сегодня ещё не занималась.")
        if streak:
            lines.append(f"Серия: {streak} {_plural(streak, 'день', 'дня', 'дней')} — "
                         "если позанимается сегодня, серия продолжится.")
        else:
            lines.append("Серия прервалась, сад уснул — одно занятие сегодня его разбудит.")
        if last:
            lines.append(f"Последнее занятие: {datetime.strptime(last, '%Y-%m-%d').strftime('%d.%m')}.")
    if nxt:
        from curriculum import LESSONS
        lines.append(f"Следующий урок: «{html.escape(_title(nxt))}» ({nxt['num']} из {len(LESSONS)}).")
    return "\n".join(lines)


def run(db, now=None, force=False):
    """Разослать напоминания. Возвращает число отправленных сообщений."""
    now = now or datetime.now()
    s = tg.settings(db)
    if not s["linked"]:
        return 0
    if not force and not REMIND_HOUR <= now.hour < LATEST_HOUR:
        return 0
    day = now.date().isoformat()
    sent = 0
    for st in db.execute("SELECT id, display_name FROM students WHERE tg_remind=1 ORDER BY id").fetchall():
        key = f"tg_remind_{st['id']}"
        row = db.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
        if not force and row and row[0] == day:
            continue
        text = build_message(db, st, now.date())
        if text is None:
            continue
        try:
            tg.call(s["tg_token"], "sendMessage", {"chat_id": s["tg_chat"], "text": text, "parse_mode": "HTML"})
        except tg.TgError as e:
            log.warning("напоминание ученику %s не отправлено: %s", st["id"], e)
            continue
        db.execute("INSERT INTO app_settings (key, value) VALUES (?, ?) "
                   "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, day))
        db.commit()
        sent += 1
    return sent


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true", help="отправить сейчас, даже если уже отправляли сегодня")
    args = ap.parse_args()
    db = tg.open_db(config.DB_PATH)
    if db is None:
        log.info("базы нет — нечего напоминать")
        return 0
    db.row_factory = sqlite3.Row
    try:
        n = run(db, force=args.force)
    finally:
        db.close()
    log.info("напоминаний отправлено: %s", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
