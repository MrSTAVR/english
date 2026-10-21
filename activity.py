# -*- coding: utf-8 -*-
"""Журнал занятий (по дням) — основа недельного челленджа."""
from datetime import datetime, timedelta


def log(db, student_id, kind, day=None):
    day = day or datetime.now().date().isoformat()
    db.execute("INSERT INTO activity (student_id, day, kind) VALUES (?,?,?)", (student_id, day, kind))
    db.commit()


def week_start(day=None):
    d = day or datetime.now().date()
    return d - timedelta(days=d.weekday())


def counts(db, student_id, week_monday):
    """{kind: сколько раз} за неделю, начинающуюся с week_monday."""
    a, b = week_monday.isoformat(), (week_monday + timedelta(days=6)).isoformat()
    rows = db.execute("SELECT kind, COUNT(*) n FROM activity WHERE student_id=? AND day>=? AND day<=? GROUP BY kind",
                      (student_id, a, b)).fetchall()
    return {r["kind"]: r["n"] for r in rows}
