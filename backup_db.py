#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Резервная копия базы данных: python backup_db.py [--dir ПАПКА] [--keep N]

Копия делается штатным механизмом SQLite, поэтому безопасна, пока сайт работает.
Каждая копия — файл english_app-ГГГГММДД-ЧЧММСС.db.gz; хранятся последние N штук.

Настройки по умолчанию: ENGLISH_BACKUP_DIR (папка backups/ рядом с проектом),
ENGLISH_BACKUP_KEEP (14).

Если в кабинете администратора привязан Telegram-бот, копия уходит и туда
(кроме запуска с --no-telegram — так делает update.sh перед каждым обновлением).
"""
import argparse
import glob
import gzip
import os
import shutil
import sqlite3
import sys
import tempfile
import time

import config
import tg

PREFIX = "english_app-"


def _check_readable(gz_path):
    """Проверяет, что копию можно распаковать и база в ней целая."""
    with tempfile.TemporaryDirectory() as tmp:
        plain = os.path.join(tmp, "check.db")
        with gzip.open(gz_path, "rb") as fi, open(plain, "wb") as fo:
            shutil.copyfileobj(fi, fo)
        conn = sqlite3.connect(plain)
        try:
            return conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            conn.close()


def make_backup(db_path, backup_dir, keep=14, now=None):
    """Создаёт копию, проверяет её, удаляет старые. Возвращает путь к новой копии."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"база не найдена: {db_path}")
    os.makedirs(backup_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    base = os.path.join(backup_dir, f"{PREFIX}{stamp}")
    out, n = base + ".db.gz", 1
    while os.path.exists(out):          # две копии в одну секунду
        out, n = f"{base}-{n}.db.gz", n + 1

    raw = out[:-3]
    src, dst = sqlite3.connect(db_path), sqlite3.connect(raw)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    with open(raw, "rb") as fi, gzip.open(out, "wb", compresslevel=6) as fo:
        shutil.copyfileobj(fi, fo)
    os.remove(raw)

    if not _check_readable(out):
        os.remove(out)
        raise RuntimeError("копия не прошла проверку целостности и удалена")

    old = sorted(glob.glob(os.path.join(backup_dir, PREFIX + "*.db.gz")))
    for path in old[:max(0, len(old) - keep)]:
        os.remove(path)
    return out


def default_dir():
    return os.environ.get("ENGLISH_BACKUP_DIR") or os.path.join(config.BASE_DIR, "backups")


def default_keep():
    return int(os.environ.get("ENGLISH_BACKUP_KEEP", "14"))


def main(argv=None):
    p = argparse.ArgumentParser(description="Резервная копия базы English Fun")
    p.add_argument("--dir", default=default_dir())
    p.add_argument("--keep", type=int, default=default_keep())
    p.add_argument("--no-telegram", action="store_true", help="не отправлять копию в Telegram")
    args = p.parse_args(argv)
    try:
        path = make_backup(config.DB_PATH, args.dir, args.keep)
    except (OSError, sqlite3.Error, RuntimeError) as e:   # понятная ошибка вместо трейсбека (для cron/логов)
        print(f"ОШИБКА резервной копии: {e}", file=sys.stderr)
        if not args.no_telegram:
            error = str(e)
            _telegram(lambda db: tg.notify_failure(db, error))
        return 1
    print(f"Копия создана: {path} ({os.path.getsize(path) // 1024} КБ)")
    if not args.no_telegram:
        _telegram(lambda db: tg.send_backup(db, path) and print("Копия отправлена в Telegram"))
    return 0


def _telegram(action):
    """Отправка в Telegram — дополнительная: её сбой не отменяет созданную копию."""
    db = tg.open_db(config.DB_PATH)
    if db is None:
        return
    try:
        action(db)
    except tg.TgError as e:
        print(f"Telegram: {e}", file=sys.stderr)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
