# -*- coding: utf-8 -*-
"""Хеширование и проверка паролей (PBKDF2)."""

from config import BASE_DIR, PARENT_PASSWORD
import hashlib
import hmac
import os


PBKDF2_ROUNDS = 120_000


def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 salt, PBKDF2_ROUNDS)
    return f"pbkdf2${salt.hex()}${digest.hex()}"


def verify_password(stored, password):
    try:
        algo, salt_hex, digest_hex = str(stored).split("$")
        if algo != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                     bytes.fromhex(salt_hex), PBKDF2_ROUNDS)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError, AttributeError):   # испорченный или пустой хеш — пароль не подходит
        return False


def check_parent_password(password):
    """Сравнение пароля родителя за постоянное время."""
    return hmac.compare_digest(str(password).encode("utf-8"),
                               PARENT_PASSWORD.encode("utf-8"))


def load_secret_key(path=None):
    """Ключ подписи сессий: из ENGLISH_SECRET_KEY или из файла .secret_key.

    Файл создаётся при первом запуске с доступом только для владельца (0600).
    Один и тот же ключ нужен всем процессам сервера и сохраняет вход после перезапуска.
    """
    env_key = os.environ.get("ENGLISH_SECRET_KEY")
    if env_key:
        return env_key
    path = path or os.path.join(BASE_DIR, ".secret_key")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, "w") as f:
            f.write(os.urandom(24).hex())
    with open(path) as f:
        return f.read().strip()
