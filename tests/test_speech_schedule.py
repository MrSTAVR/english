# -*- coding: utf-8 -*-
"""Расписание логопеда: разовые и повторяющиеся занятия, пересечения, статусы, выходные, вид семьи."""
from datetime import date, datetime, timedelta

import pytest

import speech_schedule as sched
from tests.helpers import db_all, db_scalar
from tests.test_speech import add_child, logoped  # noqa: F401  (фикстура)
from tests.test_vacation import conn

NOW = datetime(2026, 10, 21, 10, 0)          # среда


@pytest.fixture(autouse=True)
def fixed_now(monkeypatch):
    monkeypatch.setattr(sched, "now", lambda: NOW)


@pytest.fixture
def kids(logoped):  # noqa: F811
    add_child(logoped)
    add_child(logoped, child_name="Соня", username="sonya")
    return {r[1]: r[0] for r in db_all("SELECT id, child_name FROM sp_clients")}


def add(c, cid, day, time, **extra):
    return c.post("/logoped/sessions/add", data={"client_id": cid, "day": day, "time": time, "minutes": 45, **extra},
                  follow_redirects=True).get_data(as_text=True)


def test_one_off_and_conflicts(logoped, kids):  # noqa: F811
    assert "Занятие назначено" in add(logoped, kids["Петя"], "2026-10-22", "16:00")
    assert "Время занято: 16:00 — Петя" in add(logoped, kids["Соня"], "2026-10-22", "16:30")
    assert "Занятие назначено" in add(logoped, kids["Соня"], "2026-10-22", "16:45")      # встык — можно
    assert "Укажите дату и время" in add(logoped, kids["Соня"], "", "16:00")
    assert db_scalar("SELECT COUNT(*) FROM sp_sessions") == 2
    html = logoped.get("/logoped/schedule").get_data(as_text=True)
    assert "16:00–16:45" in html and "16:45–17:30" in html and "сегодня" in html


def test_series_days_off_stop_and_no_resurrection(logoped, kids):  # noqa: F811
    c = conn()
    sched.add_days_off(c, 1, date(2026, 11, 3), date(2026, 11, 3))          # вторник — выходной
    html = add(logoped, kids["Петя"], "2026-10-27", "17:00", repeat="1")
    assert "каждую неделю" in html
    starts = [r[0] for r in db_all("SELECT start FROM sp_sessions ORDER BY start")]
    assert starts[0] == "2026-10-27 17:00" and "2026-11-03 17:00" not in starts
    assert len(starts) == 7 and all(datetime.strptime(s, sched.FMT).weekday() == 1 for s in starts)
    # пересечение с серией не даёт создать вторую серию
    assert "Время занято" in add(logoped, kids["Соня"], "2026-11-10", "17:15", repeat="1")
    # удалённое занятие из серии не появляется снова при пересчёте
    sid = db_scalar("SELECT id FROM sp_sessions WHERE start='2026-11-10 17:00'")
    logoped.post(f"/logoped/sessions/{sid}", data={"action": "delete"})
    sched.extend_series(c, 1, date(2027, 1, 31))
    assert db_scalar("SELECT COUNT(*) FROM sp_sessions WHERE start='2026-11-10 17:00'") == 0
    assert db_scalar("SELECT COUNT(*) FROM sp_sessions") > 7                   # продлилась вперёд
    series_id = db_scalar("SELECT id FROM sp_series")
    assert "каждый вторник в 17:00" in logoped.get(f"/logoped/clients/{kids['Петя']}").get_data(as_text=True)
    logoped.post(f"/logoped/series/{series_id}/stop")
    assert db_scalar("SELECT COUNT(*) FROM sp_sessions WHERE start>'2026-10-22'") == 0


def test_series_with_end_day(logoped, kids):  # noqa: F811
    add(logoped, kids["Петя"], "2026-10-23", "10:00", repeat="1", until="2026-11-06")
    assert [r[0][:10] for r in db_all("SELECT start FROM sp_sessions ORDER BY start")] == \
        ["2026-10-23", "2026-10-30", "2026-11-06"]


def test_status_note_move_delete(logoped, kids):  # noqa: F811
    add(logoped, kids["Петя"], "2026-10-20", "16:00")
    add(logoped, kids["Соня"], "2026-10-22", "12:00")
    sid = db_scalar("SELECT id FROM sp_sessions WHERE client_id=?", (kids["Петя"],))
    assert "отметить ›" in logoped.get("/logoped/schedule").get_data(as_text=True)     # прошло, не отмечено
    logoped.post(f"/logoped/sessions/{sid}", data={"action": "done", "note": "Р в слогах"})
    assert db_all("SELECT status, note FROM sp_sessions WHERE id=?", (sid,)) == [("done", "Р в слогах")]
    r = logoped.post(f"/logoped/sessions/{sid}", data={"action": "move", "day": "2026-10-22", "time": "12:30",
                                                      "minutes": 45}, follow_redirects=True)
    assert "Время занято: 12:00 — Соня" in r.get_data(as_text=True)
    logoped.post(f"/logoped/sessions/{sid}", data={"action": "move", "day": "2026-10-23", "time": "09:00", "minutes": 30})
    assert db_all("SELECT start, minutes, status FROM sp_sessions WHERE id=?", (sid,)) == [("2026-10-23 09:00", 30, "planned")]
    assert logoped.post(f"/logoped/sessions/{sid}", data={"action": "hack"}).status_code == 400
    logoped.post(f"/logoped/sessions/{sid}", data={"action": "delete"})
    assert db_scalar("SELECT COUNT(*) FROM sp_sessions WHERE id=?", (sid,)) == 0


def test_days_off_warning_and_delete(logoped, kids):  # noqa: F811
    add(logoped, kids["Петя"], "2026-10-28", "16:00")
    r = logoped.post("/logoped/days-off", data={"start_day": "2026-10-28", "end_day": "2026-10-30", "note": "отпуск"},
                     follow_redirects=True).get_data(as_text=True)
    assert "уже запланировано занятий: 1" in r and "28.10.2026 — 30.10.2026" in r
    assert "выходной" in logoped.get("/logoped/schedule?week=1").get_data(as_text=True)
    oid = db_scalar("SELECT id FROM sp_days_off")
    logoped.post("/logoped/days-off", data={"action": "delete", "id": oid})
    assert db_scalar("SELECT COUNT(*) FROM sp_days_off") == 0


def test_family_sees_own_sessions_without_notes(logoped, kids, flask_app):  # noqa: F811
    add(logoped, kids["Петя"], "2026-10-23", "16:00")
    add(logoped, kids["Соня"], "2026-10-23", "17:00")
    add(logoped, kids["Петя"], "2026-10-19", "16:00")
    old = db_scalar("SELECT id FROM sp_sessions WHERE start='2026-10-19 16:00'")
    logoped.post(f"/logoped/sessions/{old}", data={"action": "done", "note": "секретная заметка"})
    fam = flask_app.test_client()
    fam.post("/family", data={"username": "petya", "password": "pass123"})
    html = fam.get("/family/home").get_data(as_text=True)
    assert "пт, 23 октября" in html and "16:00–16:45" in html and "17:00" not in html
    assert "проведено" in html and "секретная заметка" not in html


def test_other_logoped_and_archived(logoped, kids, parent, flask_app):  # noqa: F811
    add(logoped, kids["Петя"], "2026-10-23", "16:00")
    sid = db_scalar("SELECT id FROM sp_sessions")
    parent.post("/parent/logopeds", data={"action": "add", "name": "Другой", "username": "other", "password": "secret12"})
    other = flask_app.test_client()
    other.post("/logoped", data={"username": "other", "password": "secret12"})
    assert other.get(f"/logoped/sessions/{sid}").status_code == 404
    assert "Выберите ученика" in add(other, kids["Петя"], "2026-10-24", "10:00")
    assert db_scalar("SELECT COUNT(*) FROM sp_series") == 0
    logoped.post(f"/logoped/clients/{kids['Соня']}/edit", data={"action": "archive"})
    assert "Выберите ученика" in add(logoped, kids["Соня"], "2026-10-24", "10:00")


def test_week_navigation(logoped, kids):  # noqa: F811
    add(logoped, kids["Петя"], "2026-11-04", "11:00")
    assert "11:00–11:45" not in logoped.get("/logoped/schedule").get_data(as_text=True)
    html = logoped.get("/logoped/schedule?week=2").get_data(as_text=True)
    assert "11:00–11:45" in html and "2 ноября — 8 ноября" in html
    assert "Сегодня занятий нет" in logoped.get("/logoped/home").get_data(as_text=True)


# ---------------------------------------------------------------- шаг 4: окна, самозапись, отмена

def family(flask_app, username="petya"):
    fam = flask_app.test_client()
    fam.post("/family", data={"username": username, "password": "pass123"})
    return fam


def slots(c, day, times, **extra):
    return c.post("/logoped/slots", data={"action": "add", "day": day, "times": times, "minutes": 45, **extra},
                  follow_redirects=True).get_data(as_text=True)


def test_parse_times():
    assert [t.strftime("%H:%M") for t in sched.parse_times("16:30, 15:00;15:45 bad 15:00")] == ["15:00", "15:45", "16:30"]


def test_add_slots_skips_busy_and_repeats(logoped, kids):  # noqa: F811
    add(logoped, kids["Петя"], "2026-10-23", "15:00")
    assert "Окон добавлено: 2. Пропущено" in slots(logoped, "2026-10-23", "15:00, 15:45, 16:30")
    assert "Окон добавлено: 0" in slots(logoped, "2026-10-23", "16:30")          # такое окно уже есть
    assert "Окон добавлено: 3" in slots(logoped, "2026-10-26", "10:00", weeks="3")
    assert "Укажите дату" in slots(logoped, "2026-10-26", "абв")
    html = logoped.get("/logoped/schedule").get_data(as_text=True)
    assert "15:45–16:30" in html and "свободно" in html
    oid = db_scalar("SELECT id FROM sp_slots WHERE start='2026-10-23 16:30'")
    logoped.post("/logoped/slots", data={"action": "delete", "id": oid})
    assert db_scalar("SELECT COUNT(*) FROM sp_slots WHERE start LIKE '2026-10-23%'") == 1


def test_family_books_slot_24h_rule_and_logoped_sees_event(logoped, kids, flask_app):  # noqa: F811
    slots(logoped, "2026-10-22", "09:00, 10:30")      # 22.10 09:00 — меньше суток от NOW (21.10 10:00)
    slots(logoped, "2026-10-23", "15:00")
    fam = family(flask_app)
    assert "Записаться на свободное время" in fam.get("/family/home").get_data(as_text=True)
    page = fam.get("/family/book").get_data(as_text=True)
    assert "10:30–11:15" in page and "09:00" not in page and "15:00–15:45" in page
    early = db_scalar("SELECT id FROM sp_slots WHERE start='2026-10-22 09:00'")
    r = fam.post("/family/book", data={"slot_id": early}, follow_redirects=True).get_data(as_text=True)
    assert "меньше суток" in r and db_scalar("SELECT COUNT(*) FROM sp_sessions") == 0
    slot = db_scalar("SELECT id FROM sp_slots WHERE start='2026-10-23 15:00'")
    r = fam.post("/family/book", data={"slot_id": slot}, follow_redirects=True).get_data(as_text=True)
    assert "Вы записаны" in r and "пт, 23 октября" in r
    assert db_all("SELECT client_id, start, source FROM sp_sessions") == [(kids["Петя"], "2026-10-23 15:00", "family")]
    # второй раз на то же время (и другая семья) — нельзя
    other = family(flask_app, "sonya")
    assert "15:00–15:45" not in other.get("/family/book").get_data(as_text=True)
    r = other.post("/family/book", data={"slot_id": slot}, follow_redirects=True).get_data(as_text=True)
    assert "уже занято" in r and db_scalar("SELECT COUNT(*) FROM sp_sessions") == 1
    home = logoped.get("/logoped/home").get_data(as_text=True)
    assert "Новое от родителей (1)" in home and "Записались" in home and "Петя" in home
    logoped.post("/logoped/events/seen")
    assert "Новое от родителей" not in logoped.get("/logoped/home").get_data(as_text=True)


def test_family_cancel_rules(logoped, kids, flask_app):  # noqa: F811
    slots(logoped, "2026-10-24", "11:00")                       # окно; занятие поверх него — окно занято
    add(logoped, kids["Петя"], "2026-10-22", "09:30")          # меньше суток
    add(logoped, kids["Петя"], "2026-10-24", "11:00")          # больше суток
    add(logoped, kids["Соня"], "2026-10-25", "11:00")          # чужое занятие
    near, far, alien = [r[0] for r in db_all("SELECT id FROM sp_sessions ORDER BY start")]
    fam = family(flask_app)
    html = fam.get("/family/home").get_data(as_text=True)
    assert "меньше суток — отмена через логопеда" in html and html.count(">Отменить<") == 1
    assert "меньше суток" in fam.post(f"/family/sessions/{near}/cancel", follow_redirects=True).get_data(as_text=True)
    assert "не найдено" in fam.post(f"/family/sessions/{alien}/cancel", follow_redirects=True).get_data(as_text=True)
    assert "11:00–11:45" not in fam.get("/family/book").get_data(as_text=True)
    fam.post(f"/family/sessions/{far}/cancel")
    assert db_all("SELECT status, cancelled_by FROM sp_sessions WHERE id=?", (far,)) == [("cancelled", "family")]
    assert "11:00–11:45" in fam.get("/family/book").get_data(as_text=True)          # окно снова свободно
    assert "Отменили" in logoped.get("/logoped/home").get_data(as_text=True)
    assert "отменили родители" in logoped.get(f"/logoped/sessions/{far}").get_data(as_text=True)
    assert db_all("SELECT status FROM sp_sessions WHERE id IN (?, ?)", (near, alien)) == [("planned",), ("planned",)]


def test_logoped_cancel_marks_who(logoped, kids):  # noqa: F811
    add(logoped, kids["Петя"], "2026-10-24", "11:00")
    sid = db_scalar("SELECT id FROM sp_sessions")
    logoped.post(f"/logoped/sessions/{sid}", data={"action": "cancelled"})
    assert db_all("SELECT cancelled_by FROM sp_sessions") == [("logoped",)]
    assert db_scalar("SELECT COUNT(*) FROM sp_events") == 0


def test_slots_hidden_on_days_off_and_from_other_logoped(logoped, kids, parent, flask_app):  # noqa: F811
    slots(logoped, "2026-10-28", "12:00")
    sched.add_days_off(conn(), 1, date(2026, 10, 28), date(2026, 10, 28))
    assert "12:00" not in family(flask_app).get("/family/book").get_data(as_text=True)
    parent.post("/parent/logopeds", data={"action": "add", "name": "Другой", "username": "other", "password": "secret12"})
    other = flask_app.test_client()
    other.post("/logoped", data={"username": "other", "password": "secret12"})
    oid = db_scalar("SELECT id FROM sp_slots")
    other.post("/logoped/slots", data={"action": "delete", "id": oid})
    assert db_scalar("SELECT COUNT(*) FROM sp_slots") == 1


def test_migration_adds_cancelled_by(tmp_path, monkeypatch):
    import sqlite3
    import database
    path = tmp_path / "old.db"
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE sp_sessions (id INTEGER PRIMARY KEY, logoped_id INTEGER, client_id INTEGER, start TEXT, "
              "minutes INTEGER, status TEXT, series_id INTEGER, source TEXT, note TEXT, created_at TEXT)")
    c.commit(); c.close()
    monkeypatch.setattr(database, "DB_PATH", str(path))
    database.init_db()
    cols = {r[1] for r in sqlite3.connect(path).execute("PRAGMA table_info(sp_sessions)")}
    assert "cancelled_by" in cols
