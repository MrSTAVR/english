# -*- coding: utf-8 -*-
"""Сад: серия дней, ежедневные находки, монетки, украшения.

Рисованием занимается garden_scene.py; здесь — правила и данные для страницы.
"""

from datetime import datetime

from garden_scene import FIND_BY_DAY, FINDS, render_scene


MAX_SLOTS = 5      # сколько украшений можно разместить в саду одновременно
STREAK_CAP = 30    # серия ограничена 30 днями: дальше сад не растёт
COIN_PASS = 5      # монеток за урок, сданный впервые
COIN_PERFECT = 5   # бонус за первые 100% в уроке (не после «Исправь ошибки»)
COIN_RETRY = 2     # пересдача: только если побит свой лучший результат, раз в день на урок
COIN_EFFORT = 2    # «за старание»: тест не сдан, но набрано EFFORT_MIN% — раз в день
EFFORT_MIN = 40
TREES_START = 1    # стартовое число деревьев в саду
TREES_MAX = 6      # максимум деревьев
# день серии -> сколько деревьев (должно совпадать с garden_scene.EXTRA_TREES)
TREES_EVERY = {5: 2, 10: 3, 15: 4, 22: 5, 28: 6}
THUMB_DAY = 12     # на каком дне рисуются превью украшений в магазине


def tree_count_for(streak_days):
    """Сколько деревьев в саду при данной серии дней (серия <= STREAK_CAP)."""
    count = TREES_START
    for day, n in sorted(TREES_EVERY.items()):
        if streak_days >= day:
            count = n
    return count


# category:
#   span   — растягивается на ВЕСЬ сад (гирлянда, флажки, фонарики, заборчик)
#   sky    — украшение неба (солнышко, луна, звёзды, облака, самолётик)
#   effect — погодный/сказочный эффект на весь сад (снег, лепестки, светлячки)
#   theme  — фон сада (ночь, закат, рассвет) — активен только ОДИН фон за раз
DECORATIONS = [
    {"key": "garland",   "emoji": "💡", "name": "Гирлянда",             "cost": 10, "category": "span"},
    {"key": "flags",     "emoji": "🚩", "name": "Флажки",               "cost": 12, "category": "span"},
    {"key": "lights",    "emoji": "🏮", "name": "Фонарики",             "cost": 16, "category": "span"},
    {"key": "fence",     "emoji": "🌷", "name": "Цветочный заборчик",   "cost": 8,  "category": "span"},
    {"key": "sun",       "emoji": "☀️", "name": "Улыбчивое солнышко",   "cost": 8,  "category": "sky"},
    {"key": "moon",      "emoji": "🌙", "name": "Сонная луна",          "cost": 18, "category": "sky"},
    {"key": "stars",     "emoji": "✨", "name": "Звёздное небо",        "cost": 15, "category": "sky"},
    {"key": "clouds",    "emoji": "☁️", "name": "Пушистые облака",      "cost": 10, "category": "sky"},
    {"key": "plane",     "emoji": "✈️", "name": "Самолётик с флажком",  "cost": 24, "category": "sky"},
    {"key": "snow",      "emoji": "❄️", "name": "Снежинки",             "cost": 20, "category": "effect"},
    {"key": "petals",    "emoji": "🌸", "name": "Лепестки сакуры",      "cost": 22, "category": "effect"},
    {"key": "fireflies", "emoji": "🧚", "name": "Светлячки",            "cost": 25, "category": "effect"},
    {"key": "night",     "emoji": "🌌", "name": "Ночной фон",           "cost": 28, "category": "theme"},
    {"key": "sunset",    "emoji": "🌇", "name": "Закат",                "cost": 28, "category": "theme"},
    {"key": "dawn",      "emoji": "🌅", "name": "Рассвет",              "cost": 28, "category": "theme"},
]
DECOS_BY_KEY = {d["key"]: d for d in DECORATIONS}

CATEGORY_NAMES = {
    "span": "на весь сад", "sky": "украшение неба", "effect": "эффект",
    "theme": "фон сада",
}


def _stage_emoji(day):
    if day <= 0:
        return "🌰"
    if day <= 2:
        return "🌱"
    if day <= 7:
        return "🌿"
    if day <= 19:
        return "🌳"
    if day <= 29:
        return "🍎"
    return "👑"


# 31 стадия — по одной на каждый день серии (0..30): название = ежедневная находка
TREE_STAGES = [{"min": 0, "name": "Жёлудь", "emoji": "🌰",
                "msg": "Всё большое начинается с маленького зёрнышка! Позанимайся сегодня — и он прорастёт."}]
for _f in FINDS:
    TREE_STAGES.append({
        "min": _f["day"],
        "name": _f["title"],
        "emoji": _stage_emoji(_f["day"]),
        "msg": ("ТРИДЦАТЬ дней подряд! Целый сад под окном — ты легенда! 👑" if _f["day"] >= STREAK_CAP
                else f"Сегодня в саду новое: {_f['title'].lower()}. Завтра появится что-то ещё!"),
    })


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


def vacation_days(db, student_id):
    """Множество дат (date) каникул ученика: эти дни не считаются пропуском."""
    from datetime import timedelta
    out = set()
    for r in db.execute("SELECT start_day, end_day FROM vacations WHERE student_id=?",
                        (student_id,)).fetchall():
        try:
            d = datetime.strptime(r["start_day"], "%Y-%m-%d").date()
            e = datetime.strptime(r["end_day"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        n = 0
        while d <= e and n < 400:
            out.add(d)
            d += timedelta(days=1)
            n += 1
    return out


def on_vacation(db, student_id, day=None):
    """Сегодня (или указанный день) у ученика каникулы?"""
    return (day or datetime.now().date()) in vacation_days(db, student_id)


def missed_days(last, today, vac):
    """Сколько дней между last и today (не включая) пропущено — каникулы не в счёт."""
    from datetime import timedelta
    n, d = 0, last + timedelta(days=1)
    while d < today:
        if d not in vac:
            n += 1
        d += timedelta(days=1)
    return n


FREEZE_EVERY = 7   # один пропущенный день серию не рвёт («запасной день»), но не чаще раза в 7 дней


def study_days(db, student_id):
    """Дни, когда ученик реально занимался: прошёл тест урока (даже не сдал), играл, читал историю,
    говорил в диалоге (журнал activity), повторял слова или выполнял цель (daily_goal).
    Просто открыть урок — не занятие."""
    rows = db.execute(
        "SELECT substr(started_at, 1, 10) AS d FROM attempts WHERE student_id=? AND finished_at IS NOT NULL "
        "UNION SELECT day FROM activity WHERE student_id=? "
        "UNION SELECT day FROM daily_goal WHERE student_id=? AND (lessons > 0 OR words > 0)",
        (student_id, student_id, student_id)).fetchall()
    out = set()
    for r in rows:
        try:
            out.add(datetime.strptime((r[0] or "")[:10], "%Y-%m-%d").date())
        except ValueError:
            continue
    return out


def compute_streak_from_history(db, student_id):
    """Серия дней по реальным занятиям. Дни каникул серию не прерывают и в неё не засчитываются;
    один пропущенный день серию тоже не рвёт, если «запасной день» не тратился последние FREEZE_EVERY дней.
    Возвращает (серия, последний день занятий 'YYYY-MM-DD' или None)."""
    from datetime import timedelta
    studied = study_days(db, student_id)
    if not studied:
        return 0, None
    vac = vacation_days(db, student_id)
    today = datetime.now().date()
    one = timedelta(days=1)
    d = today if today in studied else today - one
    streak, last_freeze = 0, None
    for _ in range(400):
        if d in studied:
            streak += 1
        elif d in vac:
            pass
        elif ((last_freeze is None or (last_freeze - d).days >= FREEZE_EVERY)
              and (d - one in studied or d - one in vac) and d != today):
            last_freeze = d                              # одиночный пропуск — «запасной день»
        else:
            break
        d -= one
    return streak, max(studied).isoformat()


def refresh_garden(db, student_id):
    """Синхронизирует сад с реальностью.

    Правила:
      • если сегодня/вчера были занятия — streak = реальная серия по истории;
      • если между последним занятием и сегодняшним днём пропущено больше, чем прощает
        «запасной день», — серия прервана: дерево возвращается к жёлудю, сад «засыпает»
        (серый), но украшения остаются — купленное не отнимаем;
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

    best = cap_streak(max(int(g["best_streak"]), streak))
    db.execute("UPDATE garden SET streak_days=?, best_streak=?, broken=?, "
               "last_study_day=? WHERE student_id=?",
               (streak, best, broken, last_day, student_id))
    db.commit()
    return get_garden(db, student_id)


def award_coins(db, student_id, percent, passed, lesson_id=None, attempt_id=None, fixed=False):
    """Начисляет монетки за тест урока (попытка attempt_id уже записана). Возвращает (монет, за что).
    Первая сдача — COIN_PASS (+COIN_PERFECT за первые 100%); пересдача — COIN_RETRY, только за новый
    лучший результат и раз в день на урок; не сдан, но старался (≥ EFFORT_MIN%) — COIN_EFFORT раз в день.
    Так пересдавать лёгкий урок ради монеток невыгодно, а честная попытка не остаётся пустой."""
    today = datetime.now().date().isoformat()
    others = db.execute(
        "SELECT score_percent, passed, substr(finished_at, 1, 10) AS day, lesson_id FROM attempts "
        "WHERE student_id=? AND id<>? AND finished_at IS NOT NULL AND manual=0", (student_id, attempt_id or 0)).fetchall()
    mine = [r for r in others if r["lesson_id"] == lesson_id]
    earned, why = 0, ""
    if passed and not any(r["passed"] for r in mine):
        earned, why = COIN_PASS, "first"
        if percent >= 100 and not fixed:
            earned += COIN_PERFECT
    elif passed:
        best = max((r["score_percent"] or 0) for r in mine)
        if percent > best and not any(r["passed"] and r["day"] == today for r in mine):
            earned, why = COIN_RETRY, "retry"
    elif percent >= EFFORT_MIN and not any(not r["passed"] and r["day"] == today and (r["score_percent"] or 0) >= EFFORT_MIN
                                           for r in others):
        earned, why = COIN_EFFORT, "effort"
    if earned:
        get_garden(db, student_id)                  # создаёт строку сада, если её ещё нет
        db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?",
                   (earned, student_id))
        db.commit()
    return earned, why


def touch_streak(db, student_id):
    """Вызывается при открытии урока: продлевает/обнуляет серию дней."""
    g = get_garden(db, student_id)
    today = datetime.now().date().isoformat()
    last = g["last_study_day"]
    if last == today:
        return g
    if last:
        missed = missed_days(datetime.strptime(last, "%Y-%m-%d").date(),
                             datetime.now().date(), vacation_days(db, student_id))
        streak = g["streak_days"] + 1 if missed == 0 else 1
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
    broken = bool(g["broken"])
    day = 0 if broken else streak          # прерванная серия: дерево снова жёлудь, сад «уснул»
    stage = tree_stage(day)
    next_stage = next((s for s in TREE_STAGES if s["min"] > day), None)
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
    tcount = tree_count_for(day)
    # сколько дней до следующего дерева
    to_next = 0
    if tcount < TREES_MAX:
        nxt_day = min((d for d, n in sorted(TREES_EVERY.items()) if n > tcount),
                      default=None)
        if nxt_day is not None:
            to_next = max(0, nxt_day - day)
    active_keys = [key for _, key in sorted(active.items()) if key in DECOS_BY_KEY]
    album = [{"day": x["day"], "title": x["title"],
              "state": "today" if x["day"] == day else ("done" if x["day"] < day else "locked")}
             for x in FINDS]
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
        "trees_every": TREES_EVERY,
        "to_next_tree": to_next,
        # --- новая сцена ---
        "scene_day": day,
        "scene": render_scene(day, active_keys),
        "thumbs": {d["key"]: render_scene(THUMB_DAY, [d["key"]], thumb=True) for d in DECORATIONS},
        "album": album,
        "album_done": sum(1 for a in album if a["state"] != "locked"),
        "find_today": FIND_BY_DAY.get(day),
    }
