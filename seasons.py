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


def auto_season(day=None):
    d = day or today()
    if (d.month == 10 and d.day >= 15) or (d.month == 11 and d.day <= 3):
        return "halloween"
    return None


def get_mode(key="halloween"):
    """auto / on / off — из настроек в базе (вне запроса — auto)."""
    try:
        from database import get_db
        row = get_db().execute("SELECT value FROM app_settings WHERE key=?", (f"season_{key}",)).fetchone()
        return row["value"] if row and row["value"] in MODES else "auto"
    except Exception:
        return "auto"


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
