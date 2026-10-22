# -*- coding: utf-8 -*-
"""SQLite: схема, подключение, миграции."""

import sqlite3
from flask import g

from config import DB_PATH


def get_db():
    if "db" not in g:
        # timeout: при нескольких процессах сервера ждём освобождения базы, а не падаем
        g.db = sqlite3.connect(DB_PATH, timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT NOT NULL UNIQUE COLLATE NOCASE,  -- логин для входа
    display_name TEXT NOT NULL,                        -- имя на странице урока
    password_hash TEXT NOT NULL,                       -- PBKDF2-хеш пароля
    emoji        TEXT DEFAULT '🎒',                    -- аватарка для ребёнка
    created_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER,                         -- за кем попытка (NULL = старые данные)
    lesson_id     INTEGER NOT NULL,
    started_at    TEXT NOT NULL,             -- ISO, когда открыли урок
    finished_at   TEXT,                      -- ISO, когда сдали тест
    seconds_spent INTEGER DEFAULT 0,         -- сколько секунд потратили
    score_percent REAL DEFAULT 0,            -- результат теста в %
    passed        INTEGER DEFAULT 0,         -- тест сдан?
    total_q       INTEGER DEFAULT 0,
    correct_q     INTEGER DEFAULT 0,
    mistakes_json TEXT DEFAULT '[]',         -- [{question, given, correct}]
    manual        INTEGER DEFAULT 0,         -- 1 = урок зачтён родителем (не настоящая попытка)
    details_json  TEXT DEFAULT '{}'          -- полные результаты по каждому вопросу
);
CREATE TABLE IF NOT EXISTS achievements (
    student_id   INTEGER NOT NULL,
    key          TEXT NOT NULL,
    earned_at    TEXT NOT NULL,
    PRIMARY KEY (student_id, key)
);
CREATE TABLE IF NOT EXISTS speaking (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id   INTEGER NOT NULL,
    lesson_id    INTEGER DEFAULT 0,
    target       TEXT NOT NULL,                 -- что просили сказать
    score        INTEGER NOT NULL,              -- 0..3 звезды
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_speaking_student ON speaking (student_id);
CREATE TABLE IF NOT EXISTS word_review (
    student_id   INTEGER NOT NULL,
    key          TEXT NOT NULL,                 -- слово (нижний регистр)
    box          INTEGER DEFAULT 0,             -- коробка Лейтнера 0..5
    due          TEXT NOT NULL,                 -- дата следующего повторения
    n_ok         INTEGER DEFAULT 0,
    n_bad        INTEGER DEFAULT 0,
    last_at      TEXT,
    PRIMARY KEY (student_id, key)
);
CREATE TABLE IF NOT EXISTS daily_goal (
    student_id   INTEGER NOT NULL,
    day          TEXT NOT NULL,
    lessons      INTEGER DEFAULT 0,
    words        INTEGER DEFAULT 0,
    done         INTEGER DEFAULT 0,
    PRIMARY KEY (student_id, day)
);
CREATE TABLE IF NOT EXISTS goal_settings (
    student_id   INTEGER PRIMARY KEY,           -- цель дня, заданная родителем
    lessons      INTEGER NOT NULL,
    words        INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS game_scores (
    student_id   INTEGER NOT NULL,
    game         TEXT NOT NULL,
    best         INTEGER DEFAULT 0,             -- лучшие звёзды 0..3
    plays        INTEGER DEFAULT 0,
    PRIMARY KEY (student_id, game)
);
CREATE TABLE IF NOT EXISTS dialog_done (
    student_id   INTEGER NOT NULL,
    key          TEXT NOT NULL,
    done_at      TEXT NOT NULL,
    PRIMARY KEY (student_id, key)
);
CREATE TABLE IF NOT EXISTS story_done (
    student_id   INTEGER NOT NULL,
    key          TEXT NOT NULL,
    mode         TEXT NOT NULL,                -- read / listen
    best         INTEGER DEFAULT 0,            -- лучший результат: верных ответов из 3
    done_at      TEXT NOT NULL,
    PRIMARY KEY (student_id, key, mode)
);
CREATE TABLE IF NOT EXISTS wardrobe_items (
    student_id   INTEGER NOT NULL,
    item_key     TEXT NOT NULL,
    PRIMARY KEY (student_id, item_key)
);
CREATE TABLE IF NOT EXISTS wardrobe_wear (
    student_id   INTEGER NOT NULL,
    slot         TEXT NOT NULL,
    item_key     TEXT NOT NULL,
    PRIMARY KEY (student_id, slot)
);
CREATE TABLE IF NOT EXISTS garden (
    student_id     INTEGER PRIMARY KEY,        -- сад принадлежит ученику
    coins          INTEGER DEFAULT 0,          -- монетки за уроки
    streak_days    INTEGER DEFAULT 0,          -- серия дней занятий
    best_streak    INTEGER DEFAULT 0,          -- рекорд серии (для дерева)
    last_study_day TEXT,                       -- ISO-дата последнего занятия
    broken         INTEGER DEFAULT 0           -- 1 = серия прервана, сад «опустел»
);
CREATE TABLE IF NOT EXISTS house_items (
    student_id INTEGER NOT NULL,
    item_key   TEXT NOT NULL,
    PRIMARY KEY (student_id, item_key)
);
CREATE TABLE IF NOT EXISTS house_place (
    student_id INTEGER NOT NULL,
    slot       TEXT NOT NULL,
    item_key   TEXT NOT NULL,
    PRIMARY KEY (student_id, slot)
);
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS activity (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    day        TEXT NOT NULL,                  -- ISO-дата
    kind       TEXT NOT NULL                   -- lesson / game / story / write / dialog
);
CREATE INDEX IF NOT EXISTS idx_activity_student_day ON activity (student_id, day);
CREATE TABLE IF NOT EXISTS weekly_done (
    student_id INTEGER NOT NULL,
    week       TEXT NOT NULL,                  -- ISO-дата понедельника
    boss_won   INTEGER DEFAULT 0,
    PRIMARY KEY (student_id, week)
);
CREATE TABLE IF NOT EXISTS boss_wins (
    student_id INTEGER NOT NULL,
    week       TEXT NOT NULL,
    PRIMARY KEY (student_id, week)
);
CREATE TABLE IF NOT EXISTS season_log (
    student_id INTEGER NOT NULL,
    season     TEXT NOT NULL,
    day        TEXT NOT NULL,
    correct    INTEGER DEFAULT 0,
    PRIMARY KEY (student_id, season, day)
);
CREATE TABLE IF NOT EXISTS advent (
    student_id INTEGER NOT NULL,
    year       INTEGER NOT NULL,
    day        INTEGER NOT NULL,                -- 1..31 декабря
    coins      INTEGER DEFAULT 0,               -- сколько монет дало окошко
    opened_at  TEXT NOT NULL,
    PRIMARY KEY (student_id, year, day)
);
CREATE TABLE IF NOT EXISTS vacations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    start_day  TEXT NOT NULL,                  -- ISO-дата начала каникул
    end_day    TEXT NOT NULL                   -- ISO-дата конца (включительно)
);
CREATE TABLE IF NOT EXISTS decorations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,               -- кому принадлежит украшение
    deco_key   TEXT NOT NULL,                  -- ключ из DECORATIONS
    slot       INTEGER NOT NULL                 -- слот на дереве (0..MAX_SLOTS-1)
);
CREATE TABLE IF NOT EXISTS login_failures (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,                       -- ip / student / parent
    ident TEXT NOT NULL,                       -- адрес или логин
    ts    REAL NOT NULL                        -- unix-время неудачной попытки
);
CREATE INDEX IF NOT EXISTS idx_login_failures ON login_failures (scope, ident, ts);
"""



RETIRED_DECORATIONS = {"rainbow": 30}   # ключ -> цена: выведены из магазина, монеты возвращаются


def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL")   # читатели не мешают писателям; остаётся в файле базы
    conn.executescript(SCHEMA)
    # Миграция старых баз: добавляем недостающие колонки/таблицы
    cols = {r[1] for r in conn.execute("PRAGMA table_info(attempts)")}
    if "student_id" not in cols:
        conn.execute("ALTER TABLE attempts ADD COLUMN student_id INTEGER")
    if "manual" not in cols:
        conn.execute("ALTER TABLE attempts ADD COLUMN manual INTEGER DEFAULT 0")
    g_cols = {r[1] for r in conn.execute("PRAGMA table_info(garden)")}
    if g_cols and "manual" not in g_cols:
        conn.execute("ALTER TABLE garden ADD COLUMN manual INTEGER DEFAULT 0")
    ach_cols = [r[1] for r in conn.execute("PRAGMA table_info(achievements)")]
    if ach_cols and "student_id" not in ach_cols:
        # старая таблица ачивок без привязки к ученику — пересоздаём
        conn.execute("DROP TABLE achievements")
        conn.executescript(SCHEMA)
    # индекс уникальности для новой таблицы ачивок уже задан PRIMARY KEY
    for key, cost in RETIRED_DECORATIONS.items():
        conn.execute(
            "UPDATE garden SET coins = coins + ? * (SELECT COUNT(*) FROM decorations d "
            "WHERE d.student_id = garden.student_id AND d.deco_key = ?)", (cost, key))
        conn.execute("DELETE FROM decorations WHERE deco_key = ?", (key,))
    conn.commit()
    conn.close()
