# -*- coding: utf-8 -*-
"""Сезонные события. Пока только Хэллоуин (по умолчанию 15 октября — 3 ноября); остальные сезоны — в планах.
Родитель может включить сезон принудительно или выключить его (настройка в кабинете родителя)."""
from datetime import datetime

SEASONS = {
    "halloween": {"title": "Хэллоуин", "emoji": "🎃", "dates": "с 15 октября по 3 ноября"},
}
MODES = ("auto", "on", "off")


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


def auto_season(day=None):
    d = day or today()
    custom = get_dates("halloween")
    if custom:
        return "halloween" if custom[0] <= d <= custom[1] else None
    if (d.month == 10 and d.day >= 15) or (d.month == 11 and d.day <= 3):
        return "halloween"
    return None


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
    mode = get_mode("halloween")
    if mode == "off":
        return None
    if mode == "on":
        return "halloween"
    return auto_season()
