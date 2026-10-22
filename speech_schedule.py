# -*- coding: utf-8 -*-
"""Расписание логопеда: разовые и повторяющиеся очные занятия, статусы, выходные.

Время — местное (config.TIMEZONE), хранится строкой 'YYYY-MM-DD HH:MM'.
Повторяющиеся занятия (sp_series) разворачиваются в обычные строки sp_sessions на HORIZON_WEEKS
вперёд; generated_until не даёт «воскресить» удалённое или перенесённое занятие."""
import logging
from datetime import date, datetime, timedelta
from functools import lru_cache

import config

DEFAULT_MINUTES = 45
HORIZON_WEEKS = 8
FMT = "%Y-%m-%d %H:%M"
STATUSES = {"planned": "запланировано", "done": "проведено", "cancelled": "отменено", "noshow": "не пришли"}
BUSY = ("planned", "done")              # такие занятия занимают время
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
EVERY = ["каждый понедельник", "каждый вторник", "каждую среду", "каждый четверг", "каждую пятницу",
         "каждую субботу", "каждое воскресенье"]
WEEKDAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября",
          "ноября", "декабря"]


def now():
    """Текущее местное время логопеда (без tzinfo)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(config.TIMEZONE)).replace(tzinfo=None, second=0, microsecond=0)
    except (ImportError, KeyError, ValueError):   # нет базы часовых поясов (Windows без tzdata) или неверный пояс
        _warn_tz()
        return datetime.now().replace(second=0, microsecond=0)


@lru_cache(maxsize=1)
def _warn_tz():
    logging.getLogger(__name__).warning("часовой пояс %s недоступен — время расписания берётся с сервера", config.TIMEZONE)


def today():
    return now().date()


def parse_start(day_raw, time_raw):
    try:
        return datetime.strptime(f"{(day_raw or '').strip()} {(time_raw or '').strip()}", FMT)
    except ValueError:
        return None


def day_text(d):
    """«вт, 28 октября»."""
    return f"{WEEKDAYS_SHORT[d.weekday()].lower()}, {d.day} {MONTHS[d.month - 1]}"


def _days_off(db, logoped_id):
    out = set()
    for r in db.execute("SELECT start_day, end_day FROM sp_days_off WHERE logoped_id=?", (logoped_id,)):
        d, end = date.fromisoformat(r["start_day"]), date.fromisoformat(r["end_day"])
        while d <= end:
            out.add(d)
            d += timedelta(days=1)
    return out


def conflicts(db, logoped_id, start, minutes, exclude_id=None):
    """Занятия логопеда, пересекающиеся с [start, start+minutes)."""
    end = start + timedelta(minutes=minutes)
    rows = db.execute("SELECT s.*, c.child_name FROM sp_sessions s JOIN sp_clients c ON c.id=s.client_id "
                      "WHERE s.logoped_id=? AND s.status IN ('planned','done') AND s.start>=? AND s.start<? "
                      "AND s.id IS NOT ?",
                      (logoped_id, (start - timedelta(hours=6)).strftime(FMT), end.strftime(FMT), exclude_id))
    out = []
    for r in rows:
        s0 = datetime.strptime(r["start"], FMT)
        if s0 < end and start < s0 + timedelta(minutes=r["minutes"]):
            out.append(r)
    return out


def _conflict_text(rows):
    r = rows[0]
    return f"Время занято: {r['start'][11:]} — {r['child_name']}."


def add_session(db, logoped_id, client_id, start, minutes=DEFAULT_MINUTES, source="logoped", series_id=None):
    """(id, ошибка)."""
    if not 15 <= minutes <= 180:
        return None, "Длительность — от 15 до 180 минут."
    busy = conflicts(db, logoped_id, start, minutes)
    if busy:
        return None, _conflict_text(busy)
    cur = db.execute("INSERT INTO sp_sessions (logoped_id, client_id, start, minutes, series_id, source, created_at) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)", (logoped_id, client_id, start.strftime(FMT), minutes, series_id,
                                                      source, now().isoformat(timespec="seconds")))
    db.commit()
    return cur.lastrowid, None


def add_series(db, logoped_id, client_id, first, minutes=DEFAULT_MINUTES, end_day=None):
    """Каждую неделю в тот же день и час, начиная с first (datetime). (id, ошибка)."""
    if not 15 <= minutes <= 180:
        return None, "Длительность — от 15 до 180 минут."
    if end_day and end_day < first.date():
        return None, "Дата окончания раньше первого занятия."
    off = _days_off(db, logoped_id)
    d, last = first.date(), min(end_day or date.max, today() + timedelta(weeks=HORIZON_WEEKS))
    while d <= last:                                 # проверяем пересечения заранее, до создания
        if d not in off:
            busy = conflicts(db, logoped_id, datetime.combine(d, first.time()), minutes)
            if busy:
                return None, f"{day_text(d).capitalize()}: {_conflict_text(busy)}"
        d += timedelta(weeks=1)
    cur = db.execute("INSERT INTO sp_series (logoped_id, client_id, weekday, time, minutes, start_day, end_day, "
                     "generated_until, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (logoped_id, client_id, first.weekday(), first.strftime("%H:%M"), minutes,
                      first.date().isoformat(), end_day.isoformat() if end_day else None,
                      (first.date() - timedelta(days=1)).isoformat(), now().isoformat(timespec="seconds")))
    db.commit()
    extend_series(db, logoped_id)
    return cur.lastrowid, None


def extend_series(db, logoped_id, until=None):
    """Создаёт занятия повторяющихся серий до until (по умолчанию — HORIZON_WEEKS вперёд)."""
    until = until or today() + timedelta(weeks=HORIZON_WEEKS)
    off = None
    for s in db.execute("SELECT * FROM sp_series WHERE logoped_id=?", (logoped_id,)).fetchall():
        last = min(until, date.fromisoformat(s["end_day"]) if s["end_day"] else until)
        d = max(date.fromisoformat(s["generated_until"]) + timedelta(days=1), date.fromisoformat(s["start_day"]))
        if d > last:
            continue
        off = off if off is not None else _days_off(db, logoped_id)
        d += timedelta(days=(s["weekday"] - d.weekday()) % 7)
        t = datetime.strptime(s["time"], "%H:%M").time()
        while d <= last:
            start = datetime.combine(d, t)
            if d not in off and not conflicts(db, logoped_id, start, s["minutes"]):
                db.execute("INSERT INTO sp_sessions (logoped_id, client_id, start, minutes, series_id, created_at) "
                           "VALUES (?, ?, ?, ?, ?, ?)", (logoped_id, s["client_id"], start.strftime(FMT),
                                                         s["minutes"], s["id"], now().isoformat(timespec="seconds")))
            d += timedelta(weeks=1)
        db.execute("UPDATE sp_series SET generated_until=? WHERE id=?", (last.isoformat(), s["id"]))
    db.commit()


def stop_series(db, logoped_id, series_id):
    """Серия заканчивается сегодня: будущие запланированные занятия из неё удаляются."""
    t = today()
    db.execute("UPDATE sp_series SET end_day=? WHERE id=? AND logoped_id=?", (t.isoformat(), series_id, logoped_id))
    db.execute("DELETE FROM sp_sessions WHERE series_id=? AND logoped_id=? AND status='planned' AND start>?",
               (series_id, logoped_id, (t + timedelta(days=1)).strftime(FMT)))
    db.commit()


def series_of(db, client_id):
    rows = db.execute("SELECT * FROM sp_series WHERE client_id=? AND (end_day IS NULL OR end_day>=?) ORDER BY weekday, time",
                      (client_id, today().isoformat())).fetchall()
    return [{"id": r["id"], "text": f"{EVERY[r['weekday']]} в {r['time']}"
             + (f" до {date.fromisoformat(r['end_day']).strftime('%d.%m.%Y')}" if r["end_day"] else ""),
             "minutes": r["minutes"]} for r in rows]


def get_session(db, logoped_id, session_id):
    return db.execute("SELECT s.*, c.child_name FROM sp_sessions s JOIN sp_clients c ON c.id=s.client_id "
                      "WHERE s.id=? AND s.logoped_id=?", (session_id, logoped_id)).fetchone()


def set_status(db, session_id, status, note=None):
    if status not in STATUSES:
        return False
    if status == "cancelled":
        db.execute("UPDATE sp_sessions SET cancelled_by='logoped' WHERE id=? AND status!='cancelled'", (session_id,))
    if note is None:
        db.execute("UPDATE sp_sessions SET status=? WHERE id=?", (status, session_id))
    else:
        db.execute("UPDATE sp_sessions SET status=?, note=? WHERE id=?", (status, note.strip()[:500], session_id))
    db.commit()
    return True


def move_session(db, logoped_id, session_id, start, minutes):
    busy = conflicts(db, logoped_id, start, minutes, exclude_id=session_id)
    if busy:
        return _conflict_text(busy)
    if not 15 <= minutes <= 180:
        return "Длительность — от 15 до 180 минут."
    db.execute("UPDATE sp_sessions SET start=?, minutes=?, status='planned' WHERE id=?",
               (start.strftime(FMT), minutes, session_id))
    db.commit()
    return None


def decorate(r):
    start = datetime.strptime(r["start"], FMT)
    return {**dict(r), "dt": start, "time": r["start"][11:], "end": (start + timedelta(minutes=r["minutes"])).strftime("%H:%M"),
            "status_text": STATUSES.get(r["status"], r["status"]), "past": start < now()}


def week(db, logoped_id, monday):
    """7 дней недели: занятия, выходные, сегодня."""
    extend_series(db, logoped_id, max(monday + timedelta(days=6), today() + timedelta(weeks=HORIZON_WEEKS)))
    rows = db.execute("SELECT s.*, c.child_name FROM sp_sessions s JOIN sp_clients c ON c.id=s.client_id "
                      "WHERE s.logoped_id=? AND s.start>=? AND s.start<? ORDER BY s.start",
                      (logoped_id, monday.strftime(FMT), (monday + timedelta(days=7)).strftime(FMT))).fetchall()
    off, t = _days_off(db, logoped_id), today()
    slots = free_slots(db, logoped_id, max(datetime.combine(monday, datetime.min.time()), now()),
                       datetime.combine(monday + timedelta(days=7), datetime.min.time()))
    days = []
    for i in range(7):
        d = monday + timedelta(days=i)
        days.append({"date": d, "title": f"{WEEKDAYS_SHORT[i]}, {d.day} {MONTHS[d.month - 1]}", "today": d == t,
                     "off": d in off, "sessions": [decorate(r) for r in rows if r["start"][:10] == d.isoformat()],
                     "slots": [x for x in slots if x["start"][:10] == d.isoformat()]})
    return days


def for_day(db, logoped_id, d):
    extend_series(db, logoped_id)
    rows = db.execute("SELECT s.*, c.child_name FROM sp_sessions s JOIN sp_clients c ON c.id=s.client_id "
                      "WHERE s.logoped_id=? AND s.start LIKE ? ORDER BY s.start", (logoped_id, d.isoformat() + "%"))
    return [decorate(r) for r in rows]


def client_sessions(db, client_id, logoped_id, upcoming=True, limit=10):
    extend_series(db, logoped_id)
    cut = now().strftime(FMT)
    sql = ("SELECT s.*, c.child_name FROM sp_sessions s JOIN sp_clients c ON c.id=s.client_id WHERE s.client_id=? AND "
           + ("s.start>=? ORDER BY s.start" if upcoming else "s.start<? ORDER BY s.start DESC") + " LIMIT ?")
    out = []
    for r in db.execute(sql, (client_id, cut, limit)):
        x = decorate(r)
        x["day"] = day_text(x["dt"].date())
        out.append(x)
    return out


def days_off(db, logoped_id):
    rows = db.execute("SELECT * FROM sp_days_off WHERE logoped_id=? AND end_day>=? ORDER BY start_day",
                      (logoped_id, today().isoformat())).fetchall()
    return [{"id": r["id"], "note": r["note"], "text": date.fromisoformat(r["start_day"]).strftime("%d.%m.%Y")
             + ("" if r["start_day"] == r["end_day"] else " — " + date.fromisoformat(r["end_day"]).strftime("%d.%m.%Y"))}
            for r in rows]


def add_days_off(db, logoped_id, d1, d2, note=""):
    """(ok, сообщение). Предупреждает о запланированных занятиях в эти дни (сами они не отменяются)."""
    if d2 < d1 or (d2 - d1).days > 120:
        return False, "Даты некорректны: конец не раньше начала, не дольше 120 дней."
    db.execute("INSERT INTO sp_days_off (logoped_id, start_day, end_day, note) VALUES (?, ?, ?, ?)",
               (logoped_id, d1.isoformat(), d2.isoformat(), (note or "").strip()[:100]))
    db.commit()
    n = db.execute("SELECT COUNT(*) FROM sp_sessions WHERE logoped_id=? AND status='planned' AND start>=? AND start<?",
                   (logoped_id, d1.strftime(FMT), (d2 + timedelta(days=1)).strftime(FMT))).fetchone()[0]
    return True, ("Выходные сохранены." + (f" ⚠️ В эти дни уже запланировано занятий: {n} — отмените или перенесите их."
                                            if n else ""))


# ---------------------------------------------------------------- свободные окна и самозапись

BOOK_BEFORE = timedelta(hours=24)       # записаться и отменить можно не позже чем за сутки
BOOK_AHEAD_WEEKS = 4                    # насколько вперёд родители видят окна


def _overlaps(a_start, a_min, b_start, b_min):
    return a_start < b_start + timedelta(minutes=b_min) and b_start < a_start + timedelta(minutes=a_min)


def add_slots(db, logoped_id, day, times, minutes=DEFAULT_MINUTES, weeks=1):
    """Окна на день (и столько же недель вперёд). Возвращает (создано, пропущено)."""
    if not 15 <= minutes <= 180:
        return 0, 0
    off, created, skipped = _days_off(db, logoped_id), 0, 0
    for w in range(max(1, min(12, weeks))):
        d = day + timedelta(weeks=w)
        for t in times:
            start = datetime.combine(d, t)
            busy = d in off or start < now() or conflicts(db, logoped_id, start, minutes) or any(
                _overlaps(start, minutes, datetime.strptime(r["start"], FMT), r["minutes"])
                for r in db.execute("SELECT start, minutes FROM sp_slots WHERE logoped_id=? AND start LIKE ?",
                                    (logoped_id, d.isoformat() + "%")))
            if busy:
                skipped += 1
                continue
            db.execute("INSERT INTO sp_slots (logoped_id, start, minutes, created_at) VALUES (?, ?, ?, ?)",
                       (logoped_id, start.strftime(FMT), minutes, now().isoformat(timespec="seconds")))
            created += 1
    db.commit()
    return created, skipped


def parse_times(raw):
    """«15:00, 15:45 16:30» → [time, …] (неверные пропускаются)."""
    out = []
    for part in (raw or "").replace(";", ",").replace(" ", ",").split(","):
        try:
            out.append(datetime.strptime(part.strip(), "%H:%M").time())
        except ValueError:
            continue
    return sorted(set(out))


def free_slots(db, logoped_id, start_from, until):
    """Окна без занятий поверх них, не в выходные, в промежутке [start_from, until)."""
    off = _days_off(db, logoped_id)
    busy = [(datetime.strptime(r["start"], FMT), r["minutes"]) for r in db.execute(
        "SELECT start, minutes FROM sp_sessions WHERE logoped_id=? AND status IN ('planned','done') AND start>=? AND start<?",
        (logoped_id, (start_from - timedelta(hours=6)).strftime(FMT), until.strftime(FMT)))]
    out = []
    for r in db.execute("SELECT * FROM sp_slots WHERE logoped_id=? AND start>=? AND start<? ORDER BY start",
                        (logoped_id, start_from.strftime(FMT), until.strftime(FMT))):
        st = datetime.strptime(r["start"], FMT)
        if st.date() in off or any(_overlaps(st, r["minutes"], b, m) for b, m in busy):
            continue
        out.append({**dict(r), "dt": st, "time": r["start"][11:],
                    "end": (st + timedelta(minutes=r["minutes"])).strftime("%H:%M"), "day": day_text(st.date())})
    return out


def bookable(db, logoped_id):
    """Окна, на которые семья может записаться сейчас."""
    t = now()
    return free_slots(db, logoped_id, t + BOOK_BEFORE, t + timedelta(weeks=BOOK_AHEAD_WEEKS))


def log_event(db, logoped_id, client_id, kind, start):
    db.execute("INSERT INTO sp_events (logoped_id, client_id, kind, start, created_at) VALUES (?, ?, ?, ?, ?)",
               (logoped_id, client_id, kind, start, now().isoformat(timespec="seconds")))


def book_slot(db, client, slot_id):
    """Семья записывается на окно. (id занятия, ошибка)."""
    slot = next((s for s in bookable(db, client["logoped_id"]) if s["id"] == slot_id), None)
    if not slot:
        return None, "Это время уже занято или до него меньше суток — выберите другое."
    sid, error = add_session(db, client["logoped_id"], client["id"], slot["dt"], slot["minutes"], source="family")
    if error:
        return None, "Это время уже занято — выберите другое."
    log_event(db, client["logoped_id"], client["id"], "booked", slot["start"])
    db.commit()
    return sid, None


def can_family_cancel(session):
    return session["status"] == "planned" and datetime.strptime(session["start"], FMT) - now() >= BOOK_BEFORE


def family_cancel(db, client, session_id):
    """Отмена семьёй не позже чем за сутки. Возвращает текст ошибки или None."""
    s = db.execute("SELECT * FROM sp_sessions WHERE id=? AND client_id=?", (session_id, client["id"])).fetchone()
    if not s or s["status"] != "planned":
        return "Занятие не найдено."
    if not can_family_cancel(s):
        return "До занятия меньше суток — отменить можно только через логопеда."
    db.execute("UPDATE sp_sessions SET status='cancelled', cancelled_by='family' WHERE id=?", (session_id,))
    log_event(db, client["logoped_id"], client["id"], "cancelled", s["start"])
    db.commit()
    return None


def unseen_events(db, logoped_id):
    rows = db.execute("SELECT e.*, c.child_name FROM sp_events e JOIN sp_clients c ON c.id=e.client_id "
                      "WHERE e.logoped_id=? AND e.seen=0 ORDER BY e.id DESC", (logoped_id,)).fetchall()
    return [{**dict(r), "when": f"{day_text(datetime.strptime(r['start'], FMT).date())}, {r['start'][11:]}"} for r in rows]


def mark_seen(db, logoped_id):
    db.execute("UPDATE sp_events SET seen=1 WHERE logoped_id=?", (logoped_id,))
    db.commit()
