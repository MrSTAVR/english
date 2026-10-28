# -*- coding: utf-8 -*-
"""Web Push: уведомления ученику от Чик-чика (Android/Chrome, а на iPhone — если сайт добавлен на экран).

Ключи VAPID создаются сами при первом обращении и хранятся в app_settings (vapid_private — PEM,
vapid_public — для браузера). Подписки устройств — таблица push_subs (одна строка на устройство).
Отправку вызывает remind.py вечером; адрес, который больше не принимает уведомления (404/410),
удаляем. Работает и без Flask.
"""
import base64
import json
import logging
import random
from datetime import datetime

log = logging.getLogger(__name__)

CLAIM_SUB = "mailto:noreply@english-fun.app"   # контакт для сервиса уведомлений (требование VAPID)
TTL = 6 * 3600                                  # не доставили за 6 часов — уже не актуально
MAX_SUBS = 5                                    # устройств на ученика


def _setting(db, key):
    row = db.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


def _put(db, key, value):
    db.execute("INSERT INTO app_settings (key, value) VALUES (?, ?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def keys(db):
    """(PEM закрытого ключа, открытый ключ base64url для браузера); создаёт при первом вызове."""
    pem, pub = _setting(db, "vapid_private"), _setting(db, "vapid_public")
    if pem and pub:
        return pem, pub
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption()).decode()
    raw = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    pub = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    _put(db, "vapid_private", pem)
    _put(db, "vapid_public", pub)
    db.commit()
    return pem, pub


def public_key(db):
    return keys(db)[1]


def subscribe(db, student_id, sub):
    """Сохранить подписку устройства (dict из PushSubscription.toJSON()). True — сохранена."""
    if not isinstance(sub, dict):
        return False
    endpoint, k = sub.get("endpoint"), sub.get("keys")
    if not isinstance(endpoint, str) or not endpoint.startswith("https://") or len(endpoint) > 1000:
        return False
    if not isinstance(k, dict) or not isinstance(k.get("p256dh"), str) or not isinstance(k.get("auth"), str):
        return False
    now = datetime.now().isoformat(timespec="seconds")
    db.execute("INSERT INTO push_subs (student_id, endpoint, p256dh, auth, created_at) VALUES (?, ?, ?, ?, ?) "
               "ON CONFLICT(endpoint) DO UPDATE SET student_id=excluded.student_id, p256dh=excluded.p256dh, "
               "auth=excluded.auth", (student_id, endpoint, k["p256dh"], k["auth"], now))
    old = db.execute("SELECT id FROM push_subs WHERE student_id=? ORDER BY id DESC LIMIT -1 OFFSET ?",
                     (student_id, MAX_SUBS)).fetchall()
    for r in old:
        db.execute("DELETE FROM push_subs WHERE id=?", (r[0],))
    db.commit()
    return True


def unsubscribe(db, student_id, endpoint):
    db.execute("DELETE FROM push_subs WHERE student_id=? AND endpoint=?", (student_id, endpoint))
    db.commit()


def count(db, student_id):
    return db.execute("SELECT COUNT(*) FROM push_subs WHERE student_id=?", (student_id,)).fetchone()[0]


def _webpush(info, data, pem):
    """Отправка одного уведомления (вынесено, чтобы в тестах подменять)."""
    from py_vapid import Vapid02
    from pywebpush import webpush
    webpush(subscription_info=info, data=data, vapid_private_key=Vapid02.from_pem(pem.encode()),
            vapid_claims={"sub": CLAIM_SUB}, ttl=TTL, timeout=15)


def send(db, student_id, title, body, url="/student"):
    """Уведомление на все устройства ученика. Возвращает, на сколько ушло."""
    from pywebpush import WebPushException
    pem, _ = keys(db)
    data = json.dumps({"title": title, "body": body, "url": url}, ensure_ascii=False)
    ok = 0
    for r in db.execute("SELECT id, endpoint, p256dh, auth FROM push_subs WHERE student_id=?", (student_id,)).fetchall():
        info = {"endpoint": r[1], "keys": {"p256dh": r[2], "auth": r[3]}}
        try:
            _webpush(info, data, pem)
            ok += 1
        except WebPushException as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (404, 410):                     # устройство отписалось — забываем
                db.execute("DELETE FROM push_subs WHERE id=?", (r[0],))
                db.commit()
            else:
                log.warning("push ученику %s: %s", student_id, e)
        except (OSError, ValueError) as e:
            log.warning("push ученику %s: %s", student_id, e)
    return ok


def nudge_text(name, streak, next_title, seed=None):
    """Вечерняя реплика Чик-чика, если сегодня ещё не занимались (каждый день разная)."""
    rng = random.Random(seed)
    lines = ["Чик-чик скучает! 5 минут английского — и он будет счастлив 🐥",
             f"{name}, Чик-чик приготовил тебе новые слова! Заглянешь? 🐥",
             "Твой сад ждёт тебя 🌱 Одно занятие — и он расцветёт!",
             "Чик-чик спрашивает: сыграем сегодня в английские игры? 🎮"]
    if streak:
        lines.append(f"Серия {streak} — не дай ей прерваться! Позанимайся сегодня 🔥")
    else:
        lines.append("Сад уснул 🌙 Одно занятие сегодня — и он проснётся!")
    if next_title:
        lines.append(f"Следующий урок: «{next_title}». Чик-чик ждёт тебя! 📚")
    return rng.choice(lines)
