# -*- coding: utf-8 -*-
"""Telegram-бот администратора: подключение, привязка чата, отправка копий базы."""
import io
import json
import sqlite3
import urllib.error

import pytest

import backup_db
import database
import tg

TOKEN = "123456:ABCdef"


class FakeTelegram:
    """Подменяет urlopen: запоминает запросы и отвечает как Bot API."""

    def __init__(self, monkeypatch):
        self.calls, self.updates, self.down = [], [], False
        monkeypatch.setattr(tg.urllib.request, "urlopen", self.urlopen)

    def urlopen(self, req, timeout=None):
        if self.down:
            raise urllib.error.URLError("timed out")
        method = req.full_url.rsplit("/", 1)[1]
        token = req.full_url.split("/bot", 1)[1].split("/")[0]
        self.calls.append((method, req.data))
        if token != TOKEN:
            body = json.dumps({"ok": False, "error_code": 401, "description": "Unauthorized"}).encode()
            raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(body))
        result = {"getMe": {"username": "masha_admin_bot"}, "getUpdates": self.updates}.get(method, {"message_id": 1})
        return io.BytesIO(json.dumps({"ok": True, "result": result}).encode())

    def methods(self):
        return [m for m, _ in self.calls]


@pytest.fixture
def fake(monkeypatch, tmp_path):
    return FakeTelegram(monkeypatch)


def _db():
    return sqlite3.connect(database.DB_PATH)


def _start(fake, chat_id=777):
    fake.updates = [{"update_id": 1, "message": {"chat": {"id": chat_id, "type": "private",
                                                          "first_name": "Папа", "username": "stavr"}}}]


def _link(parent, fake):
    parent.post("/parent/telegram", data={"action": "token", "token": TOKEN})
    _start(fake)
    return parent.post("/parent/telegram", data={"action": "link"}, follow_redirects=True)


def test_page_needs_admin(anon):
    assert anon.get("/parent/telegram").status_code in (302, 403)
    assert anon.post("/parent/telegram", data={"action": "forget"}).status_code in (302, 403)


def test_connect_and_link(parent, fake):
    assert "Шаг 1" in parent.get("/parent/telegram").get_data(as_text=True)
    html = parent.post("/parent/telegram", data={"action": "token", "token": "bad:token"},
                       follow_redirects=True).get_data(as_text=True)
    assert "неверный токен бота" in html and "Шаг 1" in html
    html = parent.post("/parent/telegram", data={"action": "token", "token": TOKEN},
                       follow_redirects=True).get_data(as_text=True)
    assert "@masha_admin_bot" in html and "Шаг 2" in html and TOKEN not in html
    html = parent.post("/parent/telegram", data={"action": "link"}, follow_redirects=True).get_data(as_text=True)
    assert "пока не получал сообщений" in html                      # /start ещё не нажали
    html = _link(parent, fake).get_data(as_text=True)
    assert "Чат привязан: Папа (@stavr)" in html and "Отправить копию сейчас" in html
    assert fake.methods()[-1] == "sendMessage"
    db = _db()
    s = tg.settings(db)
    assert s["tg_chat"] == "777" and s["linked"] and s["backups_on"]


def test_send_backup_now_and_toggle(parent, fake):
    _link(parent, fake)
    html = parent.post("/parent/telegram", data={"action": "backup"}, follow_redirects=True).get_data(as_text=True)
    assert "Копия базы отправлена" in html and "✅ отправлена копия english_app-" in html
    method, body = fake.calls[-1]
    assert method == "sendDocument" and b'name="chat_id"\r\n\r\n777' in body and b".db.gz" in body
    parent.post("/parent/telegram", data={"action": "backups_off"})
    assert "Ежедневная копия: выключена" in parent.get("/parent/telegram").get_data(as_text=True)
    fake.down = True
    html = parent.post("/parent/telegram", data={"action": "backup"}, follow_redirects=True).get_data(as_text=True)
    assert "нет связи с Telegram" in html and "❌ не отправлено" in html


def test_forget(parent, fake):
    _link(parent, fake)
    parent.post("/parent/telegram", data={"action": "forget"})
    assert tg.settings(_db())["tg_token"] == ""
    assert "Шаг 1" in parent.get("/parent/telegram").get_data(as_text=True)


def test_nightly_backup_script(parent, fake, tmp_path, monkeypatch):
    monkeypatch.setattr(backup_db.config, "DB_PATH", database.DB_PATH)
    assert backup_db.main(["--dir", str(tmp_path)]) == 0            # бот не подключён — просто копия
    assert fake.calls == []
    _link(parent, fake)
    n = len(fake.calls)
    assert backup_db.main(["--dir", str(tmp_path), "--no-telegram"]) == 0
    assert len(fake.calls) == n                                     # update.sh не шлёт копии
    assert backup_db.main(["--dir", str(tmp_path)]) == 0
    assert fake.methods()[-1] == "sendDocument"
    fake.down = True
    assert backup_db.main(["--dir", str(tmp_path)]) == 0            # копия есть, Telegram недоступен — не ошибка
    assert "❌" in tg.settings(_db())["tg_last"]
    fake.down = False
    parent.post("/parent/telegram", data={"action": "backups_off"})
    n = len(fake.calls)
    assert backup_db.main(["--dir", str(tmp_path)]) == 0
    assert len(fake.calls) == n


def test_backup_failure_is_reported(parent, fake, tmp_path, monkeypatch):
    _link(parent, fake)
    monkeypatch.setattr(backup_db.config, "DB_PATH", database.DB_PATH)
    monkeypatch.setattr(backup_db, "make_backup", lambda *a: (_ for _ in ()).throw(OSError("диск полон")))
    assert backup_db.main(["--dir", str(tmp_path)]) == 1
    method, body = fake.calls[-1]
    assert method == "sendMessage" and "диск полон" in json.loads(body)["text"]


def test_big_file_refused(tmp_path, monkeypatch):
    f = tmp_path / "big.db.gz"
    f.write_bytes(b"x" * 10)
    monkeypatch.setattr(tg, "MAX_FILE", 5)
    with pytest.raises(tg.TgError, match="50 МБ"):
        tg.send_document(TOKEN, "1", str(f))


def test_update_script_skips_telegram():
    assert "backup_db.py\" --no-telegram" in open("deploy/update.sh", encoding="utf-8").read()


def test_backup_button_on_overview(parent, fake):
    html = parent.get("/parent").get_data(as_text=True)
    assert "Подключить Telegram" in html and "Бэкап в Telegram" not in html
    _link(parent, fake)
    assert "Бэкап в Telegram" in parent.get("/parent").get_data(as_text=True)
    r = parent.post("/parent/telegram", data={"action": "backup", "back": "overview"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/parent")
    assert fake.methods()[-1] == "sendDocument"
    assert "Копия базы отправлена" in parent.get("/parent").get_data(as_text=True)


def test_manual_backup_works_without_backup_dir_access(parent, fake, tmp_path, monkeypatch):
    """На сервере сайт не может писать в /opt/english/backups — ручная копия делается во временной папке."""
    locked = tmp_path / "backups"
    locked.write_text("это файл, а не папка")                      # писать сюда нельзя
    monkeypatch.setenv("ENGLISH_BACKUP_DIR", str(locked))
    _link(parent, fake)
    html = parent.post("/parent/telegram", data={"action": "backup"}, follow_redirects=True).get_data(as_text=True)
    assert "Копия базы отправлена" in html and fake.methods()[-1] == "sendDocument"
    assert locked.read_text() == "это файл, а не папка"
