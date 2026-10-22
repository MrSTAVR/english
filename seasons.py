# -*- coding: utf-8 -*-
"""Сезонные события: Хэллоуин, Новый год, 8 Марта, Пасха (православная, дата считается сама).
Родитель может включить сезон принудительно или выключить его, задать свои даты (можно «каждый год»).
К Новому году относится адвент-календарь: окошки с 1 по 31 декабря.
День рождения — личный праздник ученика (students.birthday), не глобальный сезон: см. birthday_*()."""
import logging
import sqlite3
from datetime import date, datetime, timedelta


def orthodox_easter(year):
    """Дата православной Пасхи (григорианский календарь, 1900–2099)."""
    a, b, c = year % 4, year % 7, year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month, day = divmod(d + e + 114, 31)
    return date(year, month, day + 1) + timedelta(days=13)


def _easter_window(year):
    e = orthodox_easter(year)
    return e - timedelta(days=6), e + timedelta(days=7)


SEASONS = {
    "halloween": {"title": "Хэллоуин", "emoji": "🎃", "dates": "с 15 октября по 3 ноября",
                  "start": (10, 15), "end": (11, 3)},
    "newyear": {"title": "Новый год", "emoji": "🎄", "dates": "с 15 декабря по 14 января",
                "start": (12, 15), "end": (1, 14)},
    "march8": {"title": "8 Марта", "emoji": "💐", "dates": "с 1 по 10 марта", "start": (3, 1), "end": (3, 10)},
    "easter": {"title": "Пасха", "emoji": "🐣", "dates": "неделя до и после православной Пасхи", "window": _easter_window},
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
    except RuntimeError:         # вне запроса (скрипты, тесты дат) — настроек нет, работаем по календарю
        return None
    except sqlite3.Error:
        logging.getLogger(__name__).exception("не удалось прочитать настройку %s", name)
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


def is_yearly(key):
    return _setting(f"season_{key}_yearly") == "1"


def set_yearly(db, key, yearly):
    db.execute("INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
               (f"season_{key}_yearly", "1" if yearly else "0"))
    db.commit()


def in_season(key, day=None):
    """Идёт ли сезон по календарю. Свои даты родителя заменяют стандартные; «каждый год» — те же числа ежегодно."""
    d = day or today()
    custom = get_dates(key)
    if custom:
        if is_yearly(key):
            return _in_window(d, (custom[0].month, custom[0].day), (custom[1].month, custom[1].day))
        return custom[0] <= d <= custom[1]
    s = SEASONS[key]
    if "window" in s:                                # дата меняется каждый год (Пасха)
        return any(a <= d <= b for a, b in (s["window"](d.year - 1), s["window"](d.year)))
    return _in_window(d, s["start"], s["end"])


def dates_text(key, year=None):
    """Стандартные даты сезона текстом (для Пасхи — на этот год)."""
    s = SEASONS[key]
    if "window" in s:
        a, b = s["window"](year or today().year)
        return f"{a:%d.%m} — {b:%d.%m.%Y} (Пасха {orthodox_easter(year or today().year):%d.%m})"
    return s["dates"]


# ---------------------------------------------------------------- день рождения ученика

BIRTHDAY_BEFORE, BIRTHDAY_AFTER = 1, 6     # праздник: за день до и неделю после
BIRTHDAY_GIFT = 25                         # монеток в подарок (раз в год)


def birthday_this_year(birthday, day=None):
    """Дата дня рождения в текущем году (29 февраля → 28-е) или None."""
    if not birthday:
        return None
    d = day or today()
    try:
        b = datetime.strptime(birthday, "%Y-%m-%d").date() if len(birthday) > 5 else \
            datetime.strptime(f"2000-{birthday}", "%Y-%m-%d").date()
    except ValueError:
        return None
    try:
        return b.replace(year=d.year)
    except ValueError:
        return date(d.year, 2, 28)


def birthday_active(birthday, day=None):
    """Идёт ли праздник дня рождения (учитываем переход через Новый год)."""
    d = day or today()
    for y in (d.year - 1, d.year, d.year + 1):
        b = birthday_this_year(birthday, date(y, 1, 1))
        if b and b - timedelta(days=BIRTHDAY_BEFORE) <= d <= b + timedelta(days=BIRTHDAY_AFTER):
            return True
    return False


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
