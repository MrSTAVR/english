# -*- coding: utf-8 -*-
"""Версия приложения из git: v1.<число коммитов> · <хеш> · <дата коммита>.

Считается один раз при запуске (после обновления сервис перезапускается). Без git — «dev»."""
import os
import subprocess
from functools import lru_cache

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAJOR = 1


def _git(*args):
    # safe.directory: на сервере код принадлежит root, а сайт работает от другого пользователя
    out = subprocess.run(["git", "-c", f"safe.directory={BASE_DIR}", "-C", BASE_DIR, *args],
                         capture_output=True, text=True, timeout=5,
                         encoding="utf-8", errors="replace")   # git отдаёт UTF-8; в Windows по умолчанию cp1251
    if out.returncode:
        raise OSError(out.stderr.strip())
    return out.stdout.strip()


@lru_cache(maxsize=1)
def info():
    """{"version": "v1.42", "commit": "abc1234", "date": "22.10.2026", "subject": "...", "full": "v1.42 · abc1234 · 22.10.2026"}"""
    try:
        count = _git("rev-list", "--count", "HEAD")
        commit, date = _git("log", "-1", "--format=%h%x1f%cd", "--date=format:%d.%m.%Y").split("\x1f")
        subject = _git("log", "-1", "--no-merges", "--format=%s")   # у merge-коммита заголовок неинформативный
    except (OSError, ValueError, subprocess.SubprocessError):
        return {"version": "dev", "commit": "", "date": "", "subject": "", "full": "dev"}
    ver = f"v{MAJOR}.{count}"
    return {"version": ver, "commit": commit, "date": date, "subject": subject, "full": f"{ver} · {commit} · {date}"}
