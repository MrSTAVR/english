# -*- coding: utf-8 -*-
"""Сезонные события: Хэллоуин (15 октября — 3 ноября) и Новый год (15 декабря — 14 января).
Родитель может включить сезон принудительно или выключить его (настройка в кабинете родителя).
К Новому году относится адвент-календарь: окошки с 1 по 31 декабря."""
from datetime import datetime

SEASONS = {
    "halloween": {"title": "Хэллоуин", "emoji": "🎃", "dates": "с 15 октября по 3 ноября",
                  "start": (10, 15), "end": (11, 3)},
    "newyear": {"title": "Новый год", "emoji": "🎄", "dates": "с 15 декабря по 14 января",
                "start": (12, 15), "end": (1, 14)},
}
MODES = ("auto", "on", "off")


def content(key):
    """Слова, викторина и тексты сезона: модуль data/<key>.py."""
    import importlib
    return importlib.import_module(f"data.{key}")


def today():
    return datetime.now().date()


def _setting(name):
    try:
        from database import get_db
        row = get_db().execute("SELECT value FROM app_settings WHERE key=?", (name,)).fetchone()
        return row["value"] if row else None
    except Exception:
        return None


def get_dates(key="halloween"):
    """Свои даты праздника, заданные родителем: (date_from, date_to) или None (тогда — стандартные)."""
    a, b = _setting(f"season_{key}_from"), _setting(f"season_{key}_to")
    try:
        d1, d2 = datetime.strptime(a or "", "%Y-%m-%d").date(), datetime.strptime(b or "", "%Y-%m-%d").date()
    except ValueError:
        return None
    return (d1, d2) if d1 <= d2 else None


def set_dates(db, key, d1, d2):
    """Сохраняет свои даты (d1, d2 — date) или сбрасывает на стандартные (None, None)."""
    if key not in SEASONS:
        return False
    for suffix, val in (("from", d1), ("to", d2)):
        if val is None:
            db.execute("DELETE FROM app_settings WHERE key=?", (f"season_{key}_{suffix}",))
        else:
            db.execute("INSERT INTO app_settings (key, value) VALUES (?, ?) "
                       "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (f"season_{key}_{suffix}", val.isoformat()))
    db.commit()
    return True


def _in_window(d, start, end):
    """(месяц, день) — окно может переходить через Новый год (start > end)."""
    md = (d.month, d.day)
    return start <= md <= end if start <= end else (md >= start or md <= end)


def in_season(key, day=None):
    """Идёт ли сезон по календарю (свои даты родителя заменяют стандартные)."""
    d = day or today()
    custom = get_dates(key)
    if custom:
        return custom[0] <= d <= custom[1]
    return _in_window(d, SEASONS[key]["start"], SEASONS[key]["end"])


def auto_season(day=None):
    d = day or today()
    return next((k for k in SEASONS if in_season(k, d)), None)


def get_mode(key="halloween"):
    """auto / on / off — из настроек в базе (вне запроса — auto)."""
    v = _setting(f"season_{key}")
    return v if v in MODES else "auto"


def set_mode(db, key, mode):
    if key not in SEASONS or mode not in MODES:
        return False
    db.execute("INSERT INTO app_settings (key, value) VALUES (?, ?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (f"season_{key}", mode))
    db.commit()
    return True


def active_season(day=None):
    """Ключ сезона, который идёт сейчас, или None. С явной датой считает только по календарю."""
    if day is not None:
        return auto_season(day)
    modes = {k: get_mode(k) for k in SEASONS}
    on = [k for k, m in modes.items() if m == "on"]
    if on:
        return on[0]
    d = today()
    return next((k for k, m in modes.items() if m == "auto" and in_season(k, d)), None)


def advent_open(day=None):
    """Адвент-календарь: весь декабрь, если родитель не выключил Новый год."""
    d = day or today()
    return d.month == 12 and get_mode("newyear") != "off"
