# -*- coding: utf-8 -*-
"""Вечернее напоминание администратору в Telegram (remind.py)."""
import sqlite3
from datetime import date, datetime

import database
import remind
import tg
from tests.helpers import N, submit_lesson
from tests.test_vacation import sid_of


class FakeBot:
    def __init__(self):
        self.sent = []

    def __call__(self, token, method, fields=None, **kw):
        self.sent.append(fields["text"])
        return {}


def _conn():
    c = sqlite3.connect(database.DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _setup(monkeypatch, remind_on=True):
    bot = FakeBot()
    monkeypatch.setattr(tg, "call", bot)
    c = _conn()
    tg.save(c, tg_token="1:x", tg_chat="42")
    c.execute("UPDATE students SET tg_remind=?", (int(remind_on),))
    c.commit()
    return bot, c


EVENING = datetime.combine(date.today(), datetime.min.time()).replace(hour=18, minute=5)


def test_not_studied_today_gets_reminder_once(make_student, monkeypatch):
    make_student()
    bot, c = _setup(monkeypatch)
    assert remind.run(c, now=EVENING) == 1
    assert "ещё не занималась" in bot.sent[0] and "Следующий урок" in bot.sent[0]
    assert remind.run(c, now=EVENING) == 0                       # второй раз за день — нет


def test_studied_today_gets_summary(make_student, monkeypatch):
    s = make_student()
    submit_lesson(s, N(1))
    bot, c = _setup(monkeypatch)
    remind.run(c, now=EVENING)
    assert "сегодня занималась" in bot.sent[0] and "сдан" in bot.sent[0]


def test_only_marked_students_and_evening_and_no_vacation(make_student, monkeypatch):
    make_student()
    bot, c = _setup(monkeypatch, remind_on=False)
    assert remind.run(c, now=EVENING) == 0                       # напоминание не включено
    c.execute("UPDATE students SET tg_remind=1"); c.commit()
    assert remind.run(c, now=EVENING.replace(hour=12)) == 0      # днём не пишем
    assert remind.run(c, now=EVENING.replace(hour=23)) == 0      # поздно — сервер лежал, не будим
    t = date.today().isoformat()
    c.execute("INSERT INTO vacations (student_id, start_day, end_day) VALUES (?, ?, ?)", (sid_of(), t, t)); c.commit()
    assert remind.run(c, now=EVENING) == 0                       # каникулы
    assert not bot.sent


def test_admin_toggles_reminders(parent, make_student, monkeypatch):
    make_student()
    bot = FakeBot()
    monkeypatch.setattr(tg, "call", bot)
    c = _conn(); tg.save(c, tg_token="1:x", tg_chat="42")
    html = parent.get("/parent/telegram").get_data(as_text=True)
    assert "Вечернее напоминание" in html and 'name="remind"' in html
    parent.post("/parent/telegram", data={"action": "remind", "remind": str(sid_of())})
    assert _conn().execute("SELECT tg_remind FROM students").fetchone()[0] == 1
    parent.post("/parent/telegram", data={"action": "remind_now"})
    assert bot.sent and "Маша" in bot.sent[0]


def test_remind_units_are_installed_by_autoupdate():
    from pathlib import Path
    d = Path(__file__).resolve().parent.parent / "deploy"
    timer = (d / "english-remind.timer").read_text(encoding="utf-8")
    svc = (d / "english-remind.service").read_text(encoding="utf-8")
    assert "OnCalendar=*-*-* 18:00:00" in timer and "Persistent=true" in timer
    assert "User=english" in svc and "remind.py" in svc and b"\r" not in (d / "english-remind.service").read_bytes()
    setup = (d / "setup-autoupdate.sh").read_text(encoding="utf-8")
    assert "english-remind.timer" in setup and "english-remind.service" in setup
