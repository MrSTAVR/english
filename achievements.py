# -*- coding: utf-8 -*-
"""Каталог ачивок (уровни: bronze/silver/gold/legend), выдача и прогресс."""

from datetime import datetime

from badges import TIERS, TIER_ORDER, badge_svg
from curriculum import MAIN_COUNT
from data.dialogs import DIALOGS

CATEGORIES = [
    ("lessons", "Уроки", "📚"),
    ("tests", "Тесты", "📝"),
    ("answers", "Ответы подряд", "🔥"),
    ("words", "Слова", "🔤"),
    ("time", "Время занятий", "⏰"),
    ("grit", "Упорство", "💪"),
    ("speak", "Произношение", "🎤"),
    ("review", "Повторение", "🔁"),
    ("goals", "Цели дня", "🎯"),
    ("games", "Игры и диалоги", "🎮"),
    ("garden", "Сад", "🌳"),
    ("special", "Особые", "🎁"),
]
CAT_NAMES = {k: (n, e) for k, n, e in CATEGORIES}

HALF = (MAIN_COUNT + 1) // 2


def _m(key, emoji, title, desc, tier, cat, metric=None, goal=None, check=None):
    """metric+goal — числовая ачивка (с шкалой прогресса); check — особое условие."""
    return {"key": key, "emoji": emoji, "title": title, "desc": desc, "tier": tier, "cat": cat,
            "metric": metric, "goal": goal, "check": check}


ACHIEVEMENTS = [
    # --- Уроки ---
    _m("first_lesson", "🚀", "Первый шаг!", "Пройден первый урок.", "bronze", "lessons", "lessons_completed", 1),
    _m("three_lessons", "⭐", "Три урока позади", "Успешно пройдено три урока.", "bronze", "lessons", "lessons_completed", 3),
    _m("five_lessons", "🚂", "Паровозик", "Пять уроков — полный ход!", "bronze", "lessons", "lessons_completed", 5),
    _m("ten_lessons", "🎯", "Десятка", "Десять уроков пройдено — прямо в цель.", "silver", "lessons", "lessons_completed", 10),
    _m("half_way", "🌗", "Половинка пути", "Пройдена половина всех уроков.", "silver", "lessons", "lessons_completed", HALF),
    _m("twenty_lessons", "🏔️", "Вершина близко", "Двадцать уроков — уже видно финиш!", "gold", "lessons", "lessons_completed", 20),
    _m("all_lessons", "🏆", "Английский чемпион!", "Пройдены ВСЕ уроки основного курса.", "legend", "lessons", "lessons_completed", MAIN_COUNT),
    # --- Тесты ---
    _m("perfect_test", "💯", "Идеальный тест", "Тест решён без единой ошибки.", "bronze", "tests", "perfect_count", 1),
    _m("first_try_perfect", "✨", "Безупречный урок", "Урок сдан с первой попытки и без ошибок.", "silver", "tests",
       check=lambda s: s["first_try_perfect"]),
    _m("clean_three", "🧹", "Чистая работа", "Три идеальных теста подряд.", "silver", "tests", "best_clean_run", 3),
    _m("diamond", "💎", "Алмазная коллекция", "Пять идеальных тестов.", "silver", "tests", "perfect_count", 5),
    _m("avg90", "🎓", "Отличница", "Средний балл от 90% после пяти уроков.", "gold", "tests",
       check=lambda s: s["lessons_completed"] >= 5 and s["avg_score"] >= 90),
    _m("perfect10", "👑", "Король идеала", "Десять идеальных тестов.", "gold", "tests", "perfect_count", 10),
    _m("perfect25", "🌟", "Совершенство", "Двадцать пять идеальных тестов!", "legend", "tests", "perfect_count", 25),
    # --- Произношение ---
    _m("speak_1", "🎤", "Первое слово вслух", "Сказал(а) слово в микрофон — и его поняли!", "bronze", "speak", "speak_words", 1),
    _m("speak_20", "🗣️", "Болтушка", "Двадцать слов произнесено вслух.", "silver", "speak", "speak_words", 20),
    _m("speak_60", "🎙️", "Оратор", "Шестьдесят слов произнесено вслух.", "gold", "speak", "speak_words", 60),
    _m("speak_p10", "🔔", "Чистый звук", "Десять слов — с тремя звёздами за произношение.", "silver", "speak", "speak_perfect", 10),
    _m("speak_p40", "🦜", "Как носитель!", "Сорок слов — с тремя звёздами. Почти как англичанка!", "legend", "speak", "speak_perfect", 40),
    # --- Повторение ---
    _m("rev_20", "🔁", "Повторяшка", "Двадцать верных ответов в повторении слов.", "bronze", "review", "review_correct", 20),
    _m("rev_100", "🧩", "Крепкая память", "Сто верных ответов в повторении.", "silver", "review", "review_correct", 100),
    _m("rev_300", "🐘", "Слоновья память", "Триста верных ответов в повторении!", "gold", "review", "review_correct", 300),
    _m("rev_m25", "🏅", "Слова-старожилы", "25 слов выучены надолго (повторены много раз).", "gold", "review", "review_mastered", 25),
    _m("rev_m100", "🧠", "Мастер слов", "100 слов выучены надолго!", "legend", "review", "review_mastered", 100),
    # --- Цели дня ---
    _m("goal_1", "🎯", "Цель дня!", "Выполнена первая цель дня: урок и повторение слов.", "bronze", "goals", "goal_days", 1),
    _m("goal_5", "📆", "Пять целей", "Цель дня выполнена 5 раз.", "silver", "goals", "goal_days", 5),
    _m("goal_20", "🏹", "Меткий стрелок", "Цель дня выполнена 20 раз!", "gold", "goals", "goal_days", 20),
    # --- Игры и диалоги ---
    _m("game_1", "🎮", "Первая игра", "Сыграна первая игра со словами.", "bronze", "games", "games_played", 1),
    _m("game_10", "🕹️", "Игроман", "Десять сыгранных игр.", "silver", "games", "games_played", 10),
    _m("game_50", "🎲", "Король игр", "Пятьдесят сыгранных игр!", "gold", "games", "games_played", 50),
    _m("game_p4", "🏆", "Чемпион игр", "Три звезды во всех пяти играх.", "legend", "games", "games_perfect", 5),
    _m("dialog_1", "💬", "Первый разговор", "Пройден первый диалог.", "bronze", "games", "dialogs_done", 1),
    _m("dialog_8", "🗨️", "Собеседница", "Пройдено 8 диалогов.", "silver", "games", "dialogs_done", 8),
    _m("dialog_15", "🎤", "Мастер общения", "Пройдены все диалоги!", "gold", "games", "dialogs_done", len(DIALOGS)),
    # --- Ответы подряд ---
    _m("streak5", "🔥", "Огонь-машина", "Пять правильных ответов подряд.", "bronze", "answers", "max_streak", 5),
    _m("streak10", "☄️", "Комета", "Десять правильных ответов подряд!", "silver", "answers", "max_streak", 10),
    # --- Слова ---
    _m("words25", "🌱", "Первые слова", "Выучено 25 слов.", "bronze", "words", "words_learned", 25),
    _m("words50", "📚", "Книжный червь", "Выучено 50 слов.", "bronze", "words", "words_learned", 50),
    _m("words100", "🦉", "Мудрая сова", "Выучено 100 слов.", "silver", "words", "words_learned", 100),
    _m("words200", "🧠", "Живой словарь", "Выучено 200 слов!", "gold", "words", "words_learned", 200),
    # --- Время ---
    _m("time30", "🏃", "Разминка", "Полчаса занятий английским.", "bronze", "time", "total_minutes", 30),
    _m("time60", "⏰", "Час упорства", "Суммарно час занятий.", "silver", "time", "total_minutes", 60),
    _m("time180", "🧘", "Три часа труда", "Суммарно три часа занятий.", "gold", "time", "total_minutes", 180),
    _m("time600", "⛰️", "Марафонец", "Десять часов занятий — вот это выдержка!", "legend", "time", "total_minutes", 600),
    # --- Упорство ---
    _m("attempts5", "🔄", "Упорный бобрик", "Пять попыток тестов — не сдаёшься!", "bronze", "grit", "n_attempts", 5),
    _m("attempts20", "🛡️", "Железная воля", "Двадцать попыток тестов.", "silver", "grit", "n_attempts", 20),
    _m("comeback", "🧗", "Работа над ошибками", "Не сдала урок, попробовала снова — и получилось!", "silver", "grit",
       check=lambda s: s["comeback"]),
    # --- Сад ---
    _m("garden_3", "🌿", "Росток", "Три дня занятий подряд.", "bronze", "garden", "garden_best", 3),
    _m("garden_7", "🌳", "Неделя в саду", "Семь дней подряд — сад зеленеет!", "silver", "garden", "garden_best", 7),
    _m("garden_14", "🦋", "Две недели", "Четырнадцать дней подряд — в саду бабочки!", "gold", "garden", "garden_best", 14),
    _m("garden_30", "🌈", "Хозяйка сада", "Тридцать дней подряд — сад в полном цвету!", "legend", "garden", "garden_best", 30),
    # --- Особые ---
    _m("early_bird", "🌅", "Ранняя пташка", "Тест сдан до девяти утра.", "bronze", "special", check=lambda s: s["early_bird"]),
    _m("evening", "🌙", "Вечерняя звезда", "Тест сдан после восьми вечера.", "bronze", "special", check=lambda s: s["evening"]),
    _m("extra_done", "🎁", "Бонус-игрок", "Пройден дополнительный урок.", "bronze", "special", "extras_completed", 1),
]

BY_KEY = {a["key"]: a for a in ACHIEVEMENTS}


def metrics(db, stats, student_id):
    """Статистика + то, чего нет в compute_stats (число попыток, рекорд серии сада)."""
    s = dict(stats)
    s["n_attempts"] = len(stats["attempts"])
    row = db.execute("SELECT best_streak, streak_days FROM garden WHERE student_id=?",
                     (student_id,)).fetchone()
    s["garden_best"] = max(row["best_streak"] or 0, row["streak_days"] or 0) if row else 0
    return s


def _done(a, s):
    if a["check"]:
        return bool(a["check"](s))
    return s[a["metric"]] >= a["goal"]


def progress(a, s):
    """(текущее, цель, процент) для числовой ачивки; None — для особых."""
    if not a["metric"]:
        return None
    cur = min(int(s[a["metric"]]), a["goal"])
    return cur, a["goal"], round(100 * cur / a["goal"])


def update_achievements(db, stats, student_id):
    """Проверяет ачивки ученика; возвращает список новых (чтобы показать поздравление)."""
    s = metrics(db, stats, student_id)
    existing = {r["key"] for r in db.execute(
        "SELECT key FROM achievements WHERE student_id=?", (student_id,)).fetchall()}
    new_earned = []
    now = datetime.now().isoformat(timespec="seconds")
    for ach in ACHIEVEMENTS:
        if ach["key"] not in existing and _done(ach, s):
            db.execute("INSERT INTO achievements (student_id, key, earned_at) VALUES (?, ?, ?)",
                       (student_id, ach["key"], now))
            new_earned.append(ach)
    db.commit()
    return new_earned


def views(db, stats, student_id):
    """Весь каталог для страниц ученика: статус, дата, прогресс."""
    s = metrics(db, stats, student_id)
    earned = {r["key"]: r["earned_at"] for r in db.execute(
        "SELECT key, earned_at FROM achievements WHERE student_id=?", (student_id,)).fetchall()}
    out = []
    for a in ACHIEVEMENTS:
        item = {k: v for k, v in a.items() if k != "check"}
        item["earned"] = a["key"] in earned
        item["earned_at"] = earned.get(a["key"])
        p = progress(a, s)
        item["progress"] = p
        item["tier_name"] = TIERS[a["tier"]]["name"]
        out.append(item)
    return out


def tier_counts(items):
    """{'bronze': (получено, всего), ...} для шапки коллекции."""
    return {t: (sum(1 for i in items if i["tier"] == t and i["earned"]),
                sum(1 for i in items if i["tier"] == t)) for t in TIER_ORDER}


def public(a):
    """Данные об ачивке для JS-церемонии (с готовой SVG-медалью)."""
    return {"key": a["key"], "emoji": a["emoji"], "title": a["title"], "desc": a["desc"],
            "tier": a["tier"], "tierName": TIERS[a["tier"]]["name"],
            "svg": badge_svg(a["emoji"], a["tier"])}
