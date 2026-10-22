# -*- coding: utf-8 -*-
"""Telegram-бот администратора: пока только отправка резервных копий базы.

Настройки хранятся в таблице app_settings (вводятся в кабинете администратора):
tg_token — токен бота от @BotFather, tg_chat — id чата администратора,
tg_chat_name — как чат называется, tg_backups — "1"/"0", tg_last — итог последней отправки,
tg_server — адрес сервера (запоминается из кабинета) для инструкции по восстановлению.
Работает и без Flask: backup_db.py вызывает send_backup() из cron.
"""
import html
import json
import logging
import mimetypes
import os
import sqlite3
import time
import urllib.error
import urllib.request
import uuid

log = logging.getLogger(__name__)

API = "https://api.telegram.org"
TIMEOUT = 60
MAX_FILE = 50 * 1024 * 1024          # бот не может отправить файл больше 50 МБ
KEYS = ("tg_token", "tg_chat", "tg_chat_name", "tg_backups", "tg_last", "tg_server")


class TgError(Exception):
    """Ошибка Telegram или сети — текст можно показать администратору."""


# ---------------------------------------------------------------- настройки

def settings(db):
    rows = db.execute(f"SELECT key, value FROM app_settings WHERE key IN ({','.join('?' * len(KEYS))})",
                      KEYS).fetchall()
    s = {k: "" for k in KEYS}
    s.update({r[0]: r[1] or "" for r in rows})
    s["linked"] = bool(s["tg_token"] and s["tg_chat"])
    s["backups_on"] = s["tg_backups"] != "0"
    s["token_hint"] = (s["tg_token"].split(":")[0] + ":…") if s["tg_token"] else ""
    return s


def save(db, **values):
    """save(db, tg_token="…") — пустая строка или None удаляет настройку."""
    for key, value in values.items():
        assert key in KEYS, key
        if value in (None, ""):
            db.execute("DELETE FROM app_settings WHERE key=?", (key,))
        else:
            db.execute("INSERT INTO app_settings (key, value) VALUES (?, ?) "
                       "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
    db.commit()


def forget(db):
    save(db, **{k: None for k in KEYS})


# ---------------------------------------------------------------- Bot API

def _multipart(fields, file_field, path):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    fname = os.path.basename(path)
    ctype = mimetypes.guess_type(fname)[0] or "application/octet-stream"
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; filename="{fname}"\r\n'
                 f"Content-Type: {ctype}\r\n\r\n".encode())
    with open(path, "rb") as f:
        parts.append(f.read())
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def call(token, method, fields=None, file_field=None, path=None):
    """Запрос к Bot API. Возвращает result или бросает TgError."""
    if not token:
        raise TgError("не задан токен бота")
    if path:
        body, ctype = _multipart(fields or {}, file_field, path)
    else:
        body, ctype = json.dumps(fields or {}).encode(), "application/json"
    req = urllib.request.Request(f"{API}/bot{token}/{method}", data=body, headers={"Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:            # Telegram отвечает 4xx с описанием в JSON
        try:
            data = json.loads(e.read().decode())
        except ValueError:
            raise TgError(f"Telegram ответил {e.code}") from None
    except (urllib.error.URLError, OSError) as e:
        raise TgError(f"нет связи с Telegram ({getattr(e, 'reason', e)})") from None
    except ValueError:
        raise TgError("непонятный ответ Telegram") from None
    if not data.get("ok"):
        desc = data.get("description", "ошибка")
        if data.get("error_code") == 401:
            desc = "неверный токен бота"
        raise TgError(desc)
    return data["result"]


def check_token(token):
    """Возвращает имя бота (@username) или бросает TgError."""
    if ":" not in token:
        raise TgError("токен выглядит как 123456789:ABC… — скопируйте его из @BotFather целиком")
    return "@" + call(token, "getMe").get("username", "")


def find_chat(token):
    """Последний личный чат, который написал боту. → (chat_id, имя) или TgError."""
    updates = call(token, "getUpdates", {"allowed_updates": ["message"]})
    for upd in reversed(updates):
        chat = (upd.get("message") or {}).get("chat") or {}
        if chat.get("type") == "private":
            name = " ".join(x for x in (chat.get("first_name"), chat.get("last_name")) if x)
            if chat.get("username"):
                name += f" (@{chat['username']})"
            return str(chat["id"]), name.strip() or str(chat["id"])
    raise TgError("бот пока не получал сообщений — откройте бота в Telegram и нажмите «Запустить» (/start)")


def send_message(token, chat, text):
    return call(token, "sendMessage", {"chat_id": chat, "text": text})


def send_document(token, chat, path, caption="", html_caption=False):
    size = os.path.getsize(path)
    if size > MAX_FILE:
        raise TgError(f"файл {size // (1024 * 1024)} МБ — больше лимита Telegram 50 МБ")
    fields = {"chat_id": chat, "caption": caption}
    if html_caption:
        fields["parse_mode"] = "HTML"
    return call(token, "sendDocument", fields, "document", path)


BACKUPS_ON_SERVER = "/opt/english/backups"


def restore_help(path, server="", on_server=True):
    """Подпись к копии: размер и как восстановить из неё базу (HTML, в лимите подписи Telegram 1024 символа)."""
    name = html.escape(os.path.basename(path))
    host = html.escape(server or "адрес-сервера")
    kb = max(1, os.path.getsize(path) // 1024)
    lines = [f"💾 <b>Резервная копия English Fun</b> · {kb} КБ", "",
             "<b>Как восстановить базу из этой копии:</b>",
             "1. Скачайте файл на компьютер (в «Загрузки»).",
             "2. В PowerShell отправьте его на сервер:",
             f"<code>scp \"$HOME\\Downloads\\{name}\" root@{host}:/root/</code>",
             f"3. Зайдите на сервер (<code>ssh root@{host}</code>) и выполните:",
             f"<code>bash /opt/english/app/deploy/restore.sh /root/{name}</code>",
             "",
             "Копия проверяется до начала. Текущая база не удаляется — откладывается как "
             "<code>*.before-restore-…</code>, сайт перезапускается сам."]
    if on_server:
        lines += ["", "Если копия ещё есть на сервере, шаги 1–2 не нужны:",
                  f"<code>bash /opt/english/app/deploy/restore.sh {BACKUPS_ON_SERVER}/{name}</code>"]
    return "\n".join(lines)


# ---------------------------------------------------------------- бэкапы

def _stamp(db, text):
    save(db, tg_last=f"{time.strftime('%d.%m.%Y %H:%M')} — {text}")


def send_backup(db, path, force=False, on_server=True):
    """Отправляет копию базы администратору с инструкцией по восстановлению.
    True — отправлено, False — не настроено/выключено.
    force=True — отправить, даже если ежедневная отправка выключена (кнопка в кабинете);
    on_server=False — копия на сервере не сохраняется (ручная), в инструкции нет пути на сервере."""
    s = settings(db)
    if not s["linked"] or not (s["backups_on"] or force):
        return False
    try:
        send_document(s["tg_token"], s["tg_chat"], path, restore_help(path, s["tg_server"], on_server), True)
    except TgError as e:
        _stamp(db, f"❌ не отправлено: {e}")
        raise
    _stamp(db, f"✅ отправлена копия {os.path.basename(path)}")
    return True


def notify_failure(db, error):
    """Сообщить администратору, что копия не сделалась. Ошибки отправки только в журнал."""
    s = settings(db)
    if not s["linked"] or not s["backups_on"]:
        return
    try:
        send_message(s["tg_token"], s["tg_chat"], f"❌ Резервная копия English Fun не сделалась: {error}")
    except TgError as e:
        log.warning("Telegram: не удалось сообщить об ошибке копии: %s", e)


def open_db(db_path):
    """Подключение к базе для скриптов (без Flask). None, если базы или таблицы нет."""
    if not os.path.exists(db_path):
        return None
    db = sqlite3.connect(db_path, timeout=10)
    try:
        db.execute("SELECT 1 FROM app_settings LIMIT 1")
        return db
    except sqlite3.Error as e:
        log.warning("Telegram: не открыть настройки в базе: %s", e)
        db.close()
        return None
