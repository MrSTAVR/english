# -*- coding: utf-8 -*-
"""Хеширование и проверка паролей (PBKDF2)."""

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
    except Exception:
        return False
