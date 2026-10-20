# -*- coding: utf-8 -*-
"""Сад: серия дней, деревья, монетки, украшения."""

from datetime import datetime


MAX_SLOTS = 5      # сколько украшений можно разместить в саду одновременно
STREAK_CAP = 30    # серия ограничена 30 днями: дальше сад не растёт
COIN_PASS = 5      # монеток за сданный тест
COIN_PERFECT = 5   # бонусных монеток за идеальный тест (100%)
TREES_START = 1    # стартовое число деревьев в саду
TREES_MAX = 6      # максимум деревьев
# день серии -> сколько деревьев (каждое новое дерево — заметное событие)
TREES_EVERY = {5: 2, 10: 3, 15: 4, 22: 5, 28: 6}


def tree_count_for(streak_days):
    """Сколько деревьев в саду при данной серии дней (серия <= STREAK_CAP)."""
    count = TREES_START
    for day, n in sorted(TREES_EVERY.items()):
        if streak_days >= day:
            count = n
    return count


# category:
#   span   — растягивается на ВЕСЬ сад (гирлянда, флажки, забор, огни-бусы)
#   sky    — украшение неба над всем садом (солнце, радуга, звёзды, луна, облака)
#   effect — погодный/сказочный эффект на весь сад (снег, лепестки, светлячки)
#   theme  — фон сада (ночь, закат, рассвет) — активен только ОДИН фон за раз
DECORATIONS = [
    {"key": "garland",   "emoji": "💡", "name": "Гирлянда",        "cost": 10, "category": "span"},
    {"key": "flags",     "emoji": "🚩", "name": "Флажки",          "cost": 12, "category": "span"},
    {"key": "lights",    "emoji": "🎊", "name": "Огни-бусы",       "cost": 16, "category": "span"},
    {"key": "fence",     "emoji": "🪵", "name": "Заборчик",        "cost": 8,  "category": "span"},
    {"key": "sun",       "emoji": "☀️", "name": "Солнышко",        "cost": 8,  "category": "sky"},
    {"key": "rainbow",   "emoji": "🌈", "name": "Радуга",          "cost": 30, "category": "sky"},
    {"key": "stars",     "emoji": "✨", "name": "Звёздное небо",   "cost": 15, "category": "sky"},
    {"key": "moon",      "emoji": "🌙", "name": "Луна",            "cost": 18, "category": "sky"},
    {"key": "clouds",    "emoji": "☁️", "name": "Облачка",         "cost": 10, "category": "sky"},
    {"key": "snow",      "emoji": "❄️", "name": "Снежинки",        "cost": 20, "category": "effect"},
    {"key": "petals",    "emoji": "🌸", "name": "Лепестки сакуры", "cost": 22, "category": "effect"},
    {"key": "fireflies", "emoji": "🧚", "name": "Светлячки",       "cost": 25, "category": "effect"},
    {"key": "night",     "emoji": "🌌", "name": "Ночной фон",      "cost": 28, "category": "theme"},
    {"key": "sunset",    "emoji": "🌇", "name": "Закат",           "cost": 28, "category": "theme"},
    {"key": "dawn",      "emoji": "🌅", "name": "Рассвет",         "cost": 28, "category": "theme"},
]
DECOS_BY_KEY = {d["key"]: d for d in DECORATIONS}

CATEGORY_NAMES = {
    "span": "на весь сад", "sky": "украшение неба", "effect": "эффект",
    "theme": "фон сада",
}

# SVG-глифы стадий дерева (видны на всех платформах, в отличие от emoji)
TREE_GLYPHS = {
    "acorn": '''<g><path d="M30 26c0-8 4-12 10-12s10 4 10 12-4 16-10 16-10-8-10-16z" fill="#a56a2f"/><path d="M28 26q12-10 24 0-4 6-12 6-8 0-12-6z" fill="#6d4322"/></g>''',
    "sprout": '''<g><path d="M40 46V28" stroke="#3fae5a" stroke-width="4" stroke-linecap="round"/><path d="M40 32C32 30 28 24 28 18c8 0 13 6 12 14z" fill="#5cc46f"/><path d="M40 32c8-2 12-8 12-14-8 0-13 6-12 14z" fill="#41b257"/></g>''',
    "seedling": '''<g><path d="M40 48V22" stroke="#3fae5a" stroke-width="4" stroke-linecap="round"/><path d="M40 30C30 28 24 20 24 12c12 0 18 8 16 18z" fill="#5cc46f"/><path d="M40 30c10-2 16-10 16-18-12 0-18 8-16 18z" fill="#41b257"/><path d="M40 22c-3-5-2-10 0-14 3 4 3 9 0 14z" fill="#6fd47f"/></g>''',
    "twoleaf": '''<g><path d="M40 48V20" stroke="#3fae5a" stroke-width="4" stroke-linecap="round"/><path d="M40 30C28 28 20 20 20 10c12 0 22 8 20 20z" fill="#5cc46f"/><path d="M40 30c12-2 20-10 20-20-12 0-22 8-20 20z" fill="#41b257"/><circle cx="40" cy="14" r="4" fill="#6fd47f"/></g>''',
    "bushy": '''<g><path d="M40 48V26" stroke="#8a5a2b" stroke-width="5" stroke-linecap="round"/><circle cx="30" cy="26" r="10" fill="#5cc46f"/><circle cx="50" cy="26" r="10" fill="#5cc46f"/><circle cx="40" cy="18" r="11" fill="#6fd47f"/></g>''',
    "tripod": '''<g><path d="M40 48V24" stroke="#8a5a2b" stroke-width="5" stroke-linecap="round"/><path d="M40 34l-10 8M40 34l10 8" stroke="#8a5a2b" stroke-width="3" stroke-linecap="round"/><circle cx="40" cy="18" r="12" fill="#5cc46f"/><circle cx="29" cy="26" r="8" fill="#41b257"/><circle cx="51" cy="26" r="8" fill="#6fd47f"/></g>''',
    "young": '''<g><path d="M40 48V24" stroke="#8a5a2b" stroke-width="5" stroke-linecap="round"/><path d="M40 32l-8-6M40 28l8-6" stroke="#8a5a2b" stroke-width="3" stroke-linecap="round"/><circle cx="40" cy="16" r="13" fill="#5cc46f"/><circle cx="30" cy="22" r="8" fill="#41b257"/><circle cx="50" cy="22" r="8" fill="#6fd47f"/></g>''',
    "oval": '''<g><path d="M40 48V22" stroke="#8a5a2b" stroke-width="6" stroke-linecap="round"/><ellipse cx="40" cy="16" rx="18" ry="13" fill="#41b257"/><circle cx="30" cy="14" r="7" fill="#5cc46f"/><circle cx="50" cy="18" r="7" fill="#3fae5a"/></g>''',
    "tree": '''<g><path d="M40 48V22" stroke="#8a5a2b" stroke-width="6" stroke-linecap="round"/><path d="M40 30l-10-8M40 26l10-8" stroke="#8a5a2b" stroke-width="4" stroke-linecap="round"/><circle cx="40" cy="15" r="14" fill="#41b257"/><circle cx="27" cy="22" r="9" fill="#5cc46f"/><circle cx="53" cy="22" r="9" fill="#3fae5a"/></g>''',
    "tiered": '''<g><path d="M40 48V20" stroke="#7a4d22" stroke-width="6" stroke-linecap="round"/><path d="M40 34l-12-6M40 28l12-6" stroke="#7a4d22" stroke-width="3" stroke-linecap="round"/><ellipse cx="40" cy="26" rx="20" ry="7" fill="#3fae5a"/><ellipse cx="40" cy="17" rx="15" ry="6" fill="#5cc46f"/><ellipse cx="40" cy="9" rx="10" ry="5" fill="#6fd47f"/></g>''',
    "lush": '''<g><path d="M40 48V20" stroke="#7a4d22" stroke-width="7" stroke-linecap="round"/><path d="M40 30l-12-9M40 24l12-9" stroke="#7a4d22" stroke-width="4" stroke-linecap="round"/><circle cx="40" cy="14" r="15" fill="#3fae5a"/><circle cx="25" cy="20" r="10" fill="#5cc46f"/><circle cx="55" cy="20" r="10" fill="#41b257"/><circle cx="40" cy="24" r="10" fill="#6fd47f"/></g>''',
    "blooming": '''<g><path d="M40 48V20" stroke="#7a4d22" stroke-width="7" stroke-linecap="round"/><path d="M40 30l-12-9M40 24l12-9" stroke="#7a4d22" stroke-width="4" stroke-linecap="round"/><circle cx="40" cy="14" r="15" fill="#41b257"/><circle cx="25" cy="20" r="10" fill="#5cc46f"/><circle cx="55" cy="20" r="10" fill="#3fae5a"/><circle cx="34" cy="10" r="3" fill="#ff8fb3"/><circle cx="47" cy="15" r="3" fill="#ffd166"/><circle cx="40" cy="22" r="3" fill="#ff8fb3"/></g>''',
    "big": '''<g><path d="M40 48V18" stroke="#6d4322" stroke-width="8" stroke-linecap="round"/><path d="M40 30l-14-10M40 24l14-10M40 36l10 6" stroke="#6d4322" stroke-width="4" stroke-linecap="round"/><circle cx="40" cy="12" r="16" fill="#3fae5a"/><circle cx="22" cy="20" r="11" fill="#5cc46f"/><circle cx="58" cy="20" r="11" fill="#41b257"/><circle cx="40" cy="24" r="10" fill="#6fd47f"/></g>''',
    "fruity": '''<g><path d="M40 48V18" stroke="#6d4322" stroke-width="8" stroke-linecap="round"/><path d="M40 30l-14-10M40 24l14-10" stroke="#6d4322" stroke-width="4" stroke-linecap="round"/><circle cx="40" cy="12" r="16" fill="#3fae5a"/><circle cx="22" cy="20" r="11" fill="#5cc46f"/><circle cx="58" cy="20" r="11" fill="#41b257"/><circle cx="32" cy="14" r="3" fill="#ff6b6b"/><circle cx="48" cy="10" r="3" fill="#ff6b6b"/><circle cx="42" cy="22" r="3" fill="#ff6b6b"/></g>''',
    "huge": '''<g><path d="M40 48V16" stroke="#6d4322" stroke-width="9" stroke-linecap="round"/><path d="M40 28l-16-10M40 22l16-10M40 36l12 6M40 36l-12 6" stroke="#6d4322" stroke-width="4" stroke-linecap="round"/><circle cx="40" cy="10" r="17" fill="#3fae5a"/><circle cx="20" cy="18" r="12" fill="#5cc46f"/><circle cx="60" cy="18" r="12" fill="#41b257"/><circle cx="40" cy="22" r="11" fill="#6fd47f"/><circle cx="30" cy="8" r="3" fill="#ffd166"/><circle cx="50" cy="12" r="3" fill="#ff8fb3"/></g>''',
    "legendary": '''<g><path d="M40 48V14" stroke="#5a3a1e" stroke-width="10" stroke-linecap="round"/><path d="M40 26l-18-10M40 20l18-10M40 36l14 6M40 36l-14 6" stroke="#5a3a1e" stroke-width="4" stroke-linecap="round"/><circle cx="40" cy="8" r="18" fill="#2f9e44"/><circle cx="18" cy="16" r="13" fill="#5cc46f"/><circle cx="62" cy="16" r="13" fill="#41b257"/><circle cx="40" cy="20" r="12" fill="#6fd47f"/><path d="M33 -2l3 5 3-5 3 5 3-5v7h-12z" fill="#ffd166" transform="translate(2,6)"/><circle cx="28" cy="6" r="2.5" fill="#fff3bf"/><circle cx="52" cy="10" r="2.5" fill="#fff3bf"/></g>''',
}

# 31 стадия — по одной на каждый день серии (0..30).
# Каждый день ЗНАЧИТЕЛЬНЫЕ изменения: размер деревьев растёт скачками ~10%
# (к финалу сад занимает больше половины окна), форма кроны меняется каждые
# 2 дня, а в особые дни появляется новое дерево или открывается новый этап.
_STAGE_GLYPHS = ["acorn", "sprout", "seedling", "twoleaf", "bushy", "tripod",
                 "young", "oval", "tree", "tiered", "lush", "blooming",
                 "big", "fruity", "huge", "legendary"]

def _stage_glyph(day):
    """Форма кроны для дня серии: новая форма каждые 2 дня, к 30-му — легендарная."""
    idx = min(len(_STAGE_GLYPHS) - 1, day // 2)
    return _STAGE_GLYPHS[idx]

def _stage_size(day):
    """Множитель размера дерева: каждый день +~8% (экспоненциально).
    0.5 → ~5.0 к 30-му дню: финальные деревья занимают больше половины сцены."""
    return round(0.5 * (1.08 ** day), 3)      # 0.5 → 5.03

TREE_STAGES = []
for _d in range(STREAK_CAP + 1):
    _trees = tree_count_for(_d)
    _prev_trees = tree_count_for(_d - 1) if _d else 1
    if _d == 0:
        _name, _msg = "Жёлудь", "Всё большое начинается с маленького зёрнышка!"
    elif _d == 1:
        _name, _msg = "Росток", "Первый день занятий — из жёлудя вырос росток! 🌱"
    elif _trees > _prev_trees:
        _name, _msg = f"Новое дерево! День {_d}", \
            f"В саду выросло ещё одно дерево — теперь их {_trees}! 🎉"
    elif _d == 7:
        _name, _msg = "Крепкое деревце", "Неделя подряд! Деревья стали выше тебя в два раза 💪"
    elif _d == 14:
        _name, _msg = "Цветущий сад", "Две недели! Кроны распушились и зацвели 🌸"
    elif _d == 21:
        _name, _msg = "Сад-гигант", "Три недели! Деревья смотрят тебе прямо в небо 🌍"
    elif _d == STREAK_CAP:
        _name, _msg = "Легендарный сад", "ТРИДЦАТЬ дней подряд! Целый лес под окном — ты легенда! 👑"
    elif _d % 2 == 0:
        _name, _msg = f"День {_d}", "Сегодня у деревьев изменилась форма кроны — посмотри, какая стала пышнее! ✨"
    else:
        _name, _msg = f"День {_d}", f"Деревья подросли ещё на шаг — прирост сегодня целых 10%! 📏"
    TREE_STAGES.append({
        "min": _d,
        "size": _stage_size(_d),
        "glyph": _stage_glyph(_d),
        "emoji": "🌳",
        "name": _name,
        "msg": _msg,
    })
# emoji стадии подбираем по глифу
_EMOJI_BY_GLYPH = {"acorn": "🌰", "sprout": "🌱", "seedling": "🌿", "twoleaf": "🌿",
                   "bushy": "🪴", "tripod": "🪴", "young": "🌳", "oval": "🌳",
                   "tree": "🌳", "tiered": "🌲", "lush": "🌳", "blooming": "🌸",
                   "big": "🌳", "fruity": "🍎", "huge": "🌳", "legendary": "👑"}
for _s in TREE_STAGES:
    _s["emoji"] = _EMOJI_BY_GLYPH[_s["glyph"]]

_GLYPH_VARIANTS = {"sprout": "seedling", "seedling": "twoleaf", "twoleaf": "bushy",
                   "bushy": "tripod", "tripod": "young", "young": "oval", "oval": "tree",
                   "tree": "tiered", "tiered": "lush", "lush": "blooming",
                   "blooming": "big", "big": "fruity", "fruity": "huge",
                   "huge": "legendary"}


def variant_glyph(glyph_key, name):
    """Небольшая вариация формы кроны для конкретного дерева (по хешу имени),
    чтобы соседние деревья в саду не выглядели клонами. Детерминированно."""
    h = sum(ord(c) for c in (name or ""))
    shift = h % 3           # 0 — базовая форма, 1/2 — чуть другая
    g = glyph_key
    for _ in range(shift):
        g = _GLYPH_VARIANTS.get(g, g)
    return g


def get_garden(db, student_id):
    """Строка сада (создаётся при первом обращении)."""
    row = db.execute("SELECT * FROM garden WHERE student_id=?",
                     (student_id,)).fetchone()
    if not row:
        db.execute("INSERT INTO garden (student_id) VALUES (?)", (student_id,))
        db.commit()
        row = db.execute("SELECT * FROM garden WHERE student_id=?",
                         (student_id,)).fetchone()
    return row


def tree_stage(streak_days):
    stage = TREE_STAGES[0]
    for s in TREE_STAGES:
        if streak_days >= s["min"]:
            stage = s
    return stage


def cap_streak(days):
    """Серия не может превышать STREAK_CAP дней."""
    return max(0, min(int(days), STREAK_CAP))


def compute_streak_from_history(db, student_id):
    """Реальная серия дней по датам попыток (для синхронизации после ручных правок)."""
    from datetime import timedelta
    rows = db.execute(
        "SELECT DISTINCT substr(started_at, 1, 10) AS d FROM attempts "
        "WHERE student_id=?", (student_id,)).fetchall()
    days = sorted({r["d"] for r in rows if r["d"]}, reverse=True)
    if not days:
        return 0, None
    today = datetime.now().date()
    last = datetime.strptime(days[0], "%Y-%m-%d").date()
    if (today - last).days > 1:      # последний заход был позавчера или раньше
        return 0, days[0]
    streak, expected = 1, last - timedelta(days=1)
    for d in days[1:]:
        if datetime.strptime(d, "%Y-%m-%d").date() == expected:
            streak += 1
            expected -= timedelta(days=1)
        else:
            break
    return streak, days[0]


def refresh_garden(db, student_id):
    """Синхронизирует сад с реальностью.

    Правила:
      • если сегодня/вчера были занятия — streak = реальная серия по истории;
      • если между последним занятием и сегодняшним днём пропущен хотя бы
        один день — серия считается прерванной: дерево возвращается к
        начальному размеру (жёлудь), украшения пропадают (монетки остаются);
      • родитель может вручную выставить streak/coins для теста — эти значения
        живут, пока ребёнок реально занимается (история попыток их подтверждает).
    """
    g = get_garden(db, student_id)
    hist_streak, last_day = compute_streak_from_history(db, student_id)
    stored = int(g["streak_days"])

    if hist_streak > 0:
        # есть свежие занятия: берём максимум из реального и «ручного» значения
        streak = cap_streak(max(hist_streak, stored))
        broken = 0
    elif stored > 0 and last_day is None:
        # истории нет, но родитель выставил серию вручную — доверяем (не выше 30)
        streak, broken = cap_streak(stored), 0
    else:
        streak = 0
        broken = 1 if stored > 0 or bool(g["broken"]) else 0
        if broken:
            db.execute("DELETE FROM decorations WHERE student_id=?", (student_id,))

    best = cap_streak(max(int(g["best_streak"]), streak))
    db.execute("UPDATE garden SET streak_days=?, best_streak=?, broken=?, "
               "last_study_day=? WHERE student_id=?",
               (streak, best, broken, last_day, student_id))
    db.commit()
    return get_garden(db, student_id)


def award_coins(db, student_id, percent, passed):
    """Начисляет монетки за тест. Возвращает число полученных монет."""
    earned = 0
    if passed:
        earned += COIN_PASS
    if percent >= 100:
        earned += COIN_PERFECT
    if earned:
        g = get_garden(db, student_id)
        db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?",
                   (earned, student_id))
        db.commit()
    return earned


def touch_streak(db, student_id):
    """Вызывается при открытии урока: продлевает/обнуляет серию дней."""
    g = get_garden(db, student_id)
    today = datetime.now().date().isoformat()
    last = g["last_study_day"]
    if last == today:
        return g
    from datetime import timedelta
    if last:
        delta = (datetime.now().date() -
                 datetime.strptime(last, "%Y-%m-%d").date()).days
        streak = g["streak_days"] + 1 if delta == 1 else 1
    else:
        # истории занятий ещё нет (или сад правили вручную) — просто фиксируем день
        streak = max(int(g["streak_days"]), 1)
    streak = cap_streak(streak)
    broken = 0                       # начала заниматься — сад «оживает»
    best = cap_streak(max(int(g["best_streak"]), streak))
    db.execute("UPDATE garden SET streak_days=?, best_streak=?, broken=?, "
               "last_study_day=? WHERE student_id=?",
               (streak, best, broken, today, student_id))
    db.commit()
    return get_garden(db, student_id)


def garden_view(db, student_id):
    """Всё нужное для рендера страницы сада."""
    g = get_garden(db, student_id)
    streak = cap_streak(g["streak_days"])
    stage = tree_stage(streak)
    next_stage = next((s for s in TREE_STAGES if s["min"] > streak), None)
    owned = db.execute(
        "SELECT deco_key, slot FROM decorations WHERE student_id=? ORDER BY slot",
        (student_id,)).fetchall()
    active = {r["slot"]: r["deco_key"] for r in owned}
    # группируем активные украшения по категориям — каждое действует на ВЕСЬ сад
    by_cat = {}
    for slot, key in sorted(active.items()):
        d = DECOS_BY_KEY.get(key)
        if not d:
            continue
        item = {"key": key, "slot": slot, "name": d["name"],
                "emoji": d["emoji"], "cost": d["cost"]}
        by_cat.setdefault(d["category"], []).append(item)
    # фон сада: активен только ПОСЛЕДНИЙ купленный тематический фон
    theme = (by_cat.get("theme") or [None])[-1]
    counts = {}
    for r in owned:
        counts[r["deco_key"]] = counts.get(r["deco_key"], 0) + 1
    tcount = tree_count_for(streak)
    student_row = db.execute("SELECT display_name FROM students WHERE id=?",
                             (student_id,)).fetchone()
    sname = student_row["display_name"] if student_row else str(student_id)
    trees = []
    for i in range(tcount):
        glyph = stage["glyph"]
        trees.append({"i": i, "coin_bonus": (i + 1) * 2,
                      "glyph": variant_glyph(glyph, f"{sname}-{i}"),
                      "scale": round(stage["size"] * (1 - 0.07 * (i % 3)), 3)})
    # сколько дней до следующего дерева
    to_next = 0
    if tcount < TREES_MAX:
        nxt_day = min((d for d, n in sorted(TREES_EVERY.items()) if n > tcount),
                      default=None)
        if nxt_day is not None:
            to_next = max(0, nxt_day - streak)
    return {
        "garden": dict(zip(g.keys(), g)),
        "stage": stage,
        "next_stage": next_stage,
        "active": active,
        "by_cat": by_cat,
        "theme": theme,
        "cat_names": CATEGORY_NAMES,
        "owned_counts": counts,
        "decorations": DECORATIONS,
        "max_slots": MAX_SLOTS,
        "streak_cap": STREAK_CAP,
        "coin_pass": COIN_PASS,
        "coin_perfect": COIN_PERFECT,
        "tree_count": tcount,
        "trees": trees,
        "trees_every": TREES_EVERY,
        "to_next_tree": to_next,
    }
