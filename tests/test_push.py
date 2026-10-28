# -*- coding: utf-8 -*-
"""Напоминания от Чик-чика на телефон (Web Push): ключи, подписка, отправка, вечерняя рассылка."""
import base64
import os
import sqlite3
from datetime import date, datetime

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

import database
import push
import remind
from tests.helpers import N, db_scalar, submit_lesson
from tests.test_vacation import sid_of

EVENING = datetime.combine(date.today(), datetime.min.time()).replace(hour=18, minute=1)


def _conn():
    c = sqlite3.connect(database.DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _b64(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _device_sub(endpoint="https://fcm.googleapis.com/fcm/send/abc"):
    """Подписка как у настоящего браузера: открытый ключ устройства P-256 и секрет auth."""
    key = ec.generate_private_key(ec.SECP256R1())
    raw = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return {"endpoint": endpoint, "keys": {"p256dh": _b64(raw), "auth": _b64(os.urandom(16))}}


def test_keys_are_created_once_and_fit_browser(make_student):
    make_student()
    c = _conn()
    pem, pub = push.keys(c)
    assert push.keys(c) == (pem, pub)
    assert len(base64.urlsafe_b64decode(pub + "==")) == 65          # applicationServerKey для pushManager.subscribe


def test_real_encryption_and_vapid_signature(make_student, monkeypatch):
    """pywebpush шифрует и подписывает нашими ключами; сеть подменяем."""
    import requests
    make_student()
    c = _conn()
    calls = []

    class Resp:
        status_code = 201
        text = ""
        headers = {}

    monkeypatch.setattr(requests, "post", lambda url, **kw: calls.append((url, kw)) or Resp())
    pem, _ = push.keys(c)
    push._webpush(_device_sub(), '{"title": "t"}', pem)
    url, kw = calls[0]
    assert url.startswith("https://fcm.googleapis.com/") and kw["headers"]["Authorization"].startswith("vapid t=")
    assert kw["headers"]["Content-Encoding"] == "aes128gcm" and kw["data"]


def test_subscribe_and_unsubscribe_routes(make_student):
    c = make_student()
    assert c.get("/api/push/key").get_json()["key"]
    sub = _device_sub()
    assert c.post("/api/push/subscribe", json={"sub": sub}).status_code == 200
    assert c.post("/api/push/subscribe", json={"sub": sub}).status_code == 200      # повтор — та же строка
    assert db_scalar("SELECT COUNT(*) FROM push_subs") == 1
    assert c.post("/api/push/subscribe", json={"sub": {"endpoint": "http://x"}}).status_code == 400
    c.post("/api/push/unsubscribe", json={"endpoint": sub["endpoint"]})
    assert db_scalar("SELECT COUNT(*) FROM push_subs") == 0


def test_routes_need_student(anon):
    assert anon.get("/api/push/key").status_code == 401
    assert anon.post("/api/push/subscribe", json={"sub": _device_sub()}).status_code == 401


def test_gone_device_is_forgotten(make_student, monkeypatch):
    from pywebpush import WebPushException
    c = make_student()
    c.post("/api/push/subscribe", json={"sub": _device_sub()})

    class Gone:
        status_code = 410
        text = "gone"

    def fail(info, data, pem):
        raise WebPushException("gone", response=Gone())
    monkeypatch.setattr(push, "_webpush", fail)
    assert push.send(_conn(), sid_of(), "t", "b") == 0
    assert db_scalar("SELECT COUNT(*) FROM push_subs") == 0


def test_evening_push_only_if_not_studied_and_once(make_student, monkeypatch):
    c = make_student()
    c.post("/api/push/subscribe", json={"sub": _device_sub()})
    got = []
    monkeypatch.setattr(push, "_webpush", lambda info, data, pem: got.append(data))
    db = _conn()
    assert remind.run(db, now=EVENING) == 1 and len(got) == 1 and "Чик-чик ждёт тебя" in got[0]
    assert remind.run(db, now=EVENING) == 0                          # раз в день
    assert remind.run(db, now=EVENING.replace(hour=11)) == 0         # не днём


def test_no_push_when_studied_today(make_student, monkeypatch):
    c = make_student()
    submit_lesson(c, N(1))
    c.post("/api/push/subscribe", json={"sub": _device_sub()})
    got = []
    monkeypatch.setattr(push, "_webpush", lambda info, data, pem: got.append(data))
    assert remind.run(_conn(), now=EVENING) == 0 and not got


def test_home_has_push_card_and_sw_handles_push(make_student):
    c = make_student()
    html = c.get("/student").get_data(as_text=True)
    assert 'id="push-card"' in html and "push.js" in html and "#o-bell" in html
    sw = c.get("/sw.js").get_data(as_text=True)
    assert 'addEventListener("push"' in sw and 'addEventListener("notificationclick"' in sw


def test_delete_student_removes_subscriptions(parent, make_student):
    c = make_student()
    c.post("/api/push/subscribe", json={"sub": _device_sub()})
    parent.post(f"/parent/students/{sid_of()}/delete")
    assert db_scalar("SELECT COUNT(*) FROM push_subs") == 0


def test_admin_push_test_button(parent, make_student, monkeypatch):
    c = make_student()
    c.post("/api/push/subscribe", json={"sub": _device_sub()})
    got = []
    monkeypatch.setattr(push, "_webpush", lambda info, data, pem: got.append(data))
    db = _conn()
    import tg
    tg.save(db, tg_token="1:x", tg_chat="42")
    assert "уведомления от Чик-чика включены (1)" in parent.get("/parent/telegram").get_data(as_text=True)
    parent.post("/parent/telegram", data={"action": "push_test"})
    assert got and "Проверка" in got[0]
