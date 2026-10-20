# -*- coding: utf-8 -*-
"""SQLite: схема, подключение, миграции."""

import sqlite3
from flask import g

from config import DB_PATH


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
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
    details_json  TEXT DEFAULT '{}'          -- полные результаты по каждому вопросу
);
CREATE TABLE IF NOT EXISTS achievements (
    student_id   INTEGER NOT NULL,
    key          TEXT NOT NULL,
    earned_at    TEXT NOT NULL,
    PRIMARY KEY (student_id, key)
);
CREATE TABLE IF NOT EXISTS garden (
    student_id     INTEGER PRIMARY KEY,        -- сад принадлежит ученику
    coins          INTEGER DEFAULT 0,          -- монетки за уроки
    streak_days    INTEGER DEFAULT 0,          -- серия дней занятий
    best_streak    INTEGER DEFAULT 0,          -- рекорд серии (для дерева)
    last_study_day TEXT,                       -- ISO-дата последнего занятия
    broken         INTEGER DEFAULT 0           -- 1 = серия прервана, сад «опустел»
);
CREATE TABLE IF NOT EXISTS decorations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,               -- кому принадлежит украшение
    deco_key   TEXT NOT NULL,                  -- ключ из DECORATIONS
    slot       INTEGER NOT NULL                 -- слот на дереве (0..MAX_SLOTS-1)
);
"""



def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    # Миграция старых баз: добавляем недостающие колонки/таблицы
    cols = {r[1] for r in conn.execute("PRAGMA table_info(attempts)")}
    if "student_id" not in cols:
        conn.execute("ALTER TABLE attempts ADD COLUMN student_id INTEGER")
    g_cols = {r[1] for r in conn.execute("PRAGMA table_info(garden)")}
    if g_cols and "manual" not in g_cols:
        conn.execute("ALTER TABLE garden ADD COLUMN manual INTEGER DEFAULT 0")
    ach_cols = [r[1] for r in conn.execute("PRAGMA table_info(achievements)")]
    if ach_cols and "student_id" not in ach_cols:
        # старая таблица ачивок без привязки к ученику — пересоздаём
        conn.execute("DROP TABLE achievements")
        conn.executescript(SCHEMA)
    # индекс уникальности для новой таблицы ачивок уже задан PRIMARY KEY
    conn.commit()
    conn.close()
