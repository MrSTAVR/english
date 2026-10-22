#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Резервная копия базы данных: python backup_db.py [--dir ПАПКА] [--keep N]

Копия делается штатным механизмом SQLite, поэтому безопасна, пока сайт работает.
Каждая копия — файл english_app-ГГГГММДД-ЧЧММСС.db.gz; хранятся последние N штук.

Настройки по умолчанию: ENGLISH_BACKUP_DIR (папка backups/ рядом с проектом),
ENGLISH_BACKUP_KEEP (14).
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


def main(argv=None):
    p = argparse.ArgumentParser(description="Резервная копия базы English Fun")
    p.add_argument("--dir", default=os.environ.get("ENGLISH_BACKUP_DIR") or os.path.join(config.BASE_DIR, "backups"))
    p.add_argument("--keep", type=int, default=int(os.environ.get("ENGLISH_BACKUP_KEEP", "14")))
    args = p.parse_args(argv)
    try:
        path = make_backup(config.DB_PATH, args.dir, args.keep)
    except (OSError, sqlite3.Error, RuntimeError) as e:   # понятная ошибка вместо трейсбека (для cron/логов)
        print(f"ОШИБКА резервной копии: {e}", file=sys.stderr)
        return 1
    print(f"Копия создана: {path} ({os.path.getsize(path) // 1024} КБ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
