# -*- coding: utf-8 -*-
"""Каталог ачивок и их выдача."""

from datetime import datetime

from curriculum import MAIN_COUNT


ACHIEVEMENTS = [
    {"key": "first_lesson", "emoji": "🚀", "title": "Первый шаг!",
     "desc": "Пройден первый урок и сдан первый тест.",
     "check": lambda s: s["lessons_completed"] >= 1},
    {"key": "three_lessons", "emoji": "⭐", "title": "Три урока позади",
     "desc": "Успешно пройдено три урока.",
     "check": lambda s: s["lessons_completed"] >= 3},
    {"key": "all_lessons", "emoji": "🏆", "title": "Английский чемпион!",
     "desc": "Пройдены ВСЕ уроки в приложении.",
     "check": lambda s: s["lessons_completed"] >= MAIN_COUNT},
    {"key": "perfect_test", "emoji": "💯", "title": "Идеальный тест",
     "desc": "Тест решён без единой ошибки.",
     "check": lambda s: s["has_perfect"]},
    {"key": "streak5", "emoji": "🔥", "title": "Огонь-машина",
     "desc": "Подряд 5 (или больше) правильных ответов в тесте.",
     "check": lambda s: s["max_streak"] >= 5},
    {"key": "clean_three", "emoji": "🧹", "title": "Чистая работа",
     "desc": "Три теста подряд без ошибок.",
     "check": lambda s: s["best_clean_run"] >= 3},
    {"key": "words50", "emoji": "📚", "title": "Книжный червь",
     "desc": "Выучено 50+ слов из пройденных уроков.",
     "check": lambda s: s["words_learned"] >= 50},
    {"key": "time60", "emoji": "⏰", "title": "Час упорства",
     "desc": "Суммарно час занятий английским.",
     "check": lambda s: s["total_minutes"] >= 60},
    {"key": "five_lessons", "emoji": "🚂", "title": "Паровозик",
     "desc": "Пройдено пять уроков — полный ход!",
     "check": lambda s: s["lessons_completed"] >= 5},
    {"key": "half_way", "emoji": "🌗", "title": "Половинка пути",
     "desc": "Пройдена половина всех уроков.",
     "check": lambda s: MAIN_COUNT and s["lessons_completed"] * 2 >= MAIN_COUNT},
    {"key": "streak10", "emoji": "☄️", "title": "Комета",
     "desc": "Подряд 10 правильных ответов в тесте!",
     "check": lambda s: s["max_streak"] >= 10},
    {"key": "words100", "emoji": "🦉", "title": "Мудрая сова",
     "desc": "Выучено 100+ слов из пройденных уроков.",
     "check": lambda s: s["words_learned"] >= 100},
    {"key": "attempts5", "emoji": "🔄", "title": "Упорный бобрик",
     "desc": "Пятая попытка теста — не сдаёшься, молодец!",
     "check": lambda s: len(s["attempts"]) >= 5},
    {"key": "time180", "emoji": "🧘", "title": "Три часа труда",
     "desc": "Суммарно три часа занятий английским.",
     "check": lambda s: s["total_minutes"] >= 180},
    {"key": "diamond", "emoji": "💎", "title": "Алмазная коллекция",
     "desc": "Идеальных тестов (100%) уже пять штук!",
     "check": lambda s: s["perfect_count"] >= 5},
    {"key": "first_try_perfect", "emoji": "✨", "title": "Безупречный урок",
     "desc": "Урок сдан с первой попытки и без единой ошибки.",
     "check": lambda s: s["first_try_perfect"]},
]


def update_achievements(db, stats, student_id):
    """Проверяет ачивки ученика; возвращает список новых (чтобы показать поздравление)."""
    existing = {r["key"] for r in db.execute(
        "SELECT key FROM achievements WHERE student_id=?", (student_id,)).fetchall()}
    new_earned = []
    now = datetime.now().isoformat(timespec="seconds")
    for ach in ACHIEVEMENTS:
        if ach["key"] not in existing and ach["check"](stats):
            db.execute("INSERT INTO achievements (student_id, key, earned_at) VALUES (?, ?, ?)",
                       (student_id, ach["key"], now))
            new_earned.append(ach)
    db.commit()
    return new_earned
