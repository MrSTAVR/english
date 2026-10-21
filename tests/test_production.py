# -*- coding: utf-8 -*-
"""Подготовка к публикации в интернете (шаг 1): защита входа, cookie, заголовки,
проверки боевого режима, резервные копии."""
import gzip
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import backup_db
import config
import database
import ratelimit
import security
from tests.helpers import db_all, db_scalar

ROOT = Path(__file__).resolve().parent.parent
STRONG = "Str0ng-pass-phrase"


def run_app(code, tmp_path, **env):
    """Запускает фрагмент кода в отдельном процессе с заданным окружением."""
    full = {**os.environ, "ENGLISH_APP_DB": str(tmp_path / "sub.db"),
            "ENGLISH_SECRET_KEY": "k" * 32, **env}
    for name in ("ENGLISH_ENV", "ENGLISH_PARENT_PASSWORD", "ENGLISH_BEHIND_PROXY",
                 "ENGLISH_COOKIE_SECURE"):
        if name not in env:
            full.pop(name, None)
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=full,
                          capture_output=True, text=True)


# ---------------------------------------------------------------- заголовки и служебные страницы

def test_security_headers_on_every_page(anon):
    h = anon.get("/").headers
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "DENY"
    assert "noindex" in h["X-Robots-Tag"]
    assert "Referrer-Policy" in h and "Permissions-Policy" in h
    assert "Strict-Transport-Security" not in h        # в разработке HSTS не нужен


def test_hsts_only_in_production_over_https(flask_app, anon, monkeypatch):
    monkeypatch.setattr(config, "IS_PRODUCTION", True)
    assert "Strict-Transport-Security" in anon.get("/", base_url="https://example.com").headers
    assert "Strict-Transport-Security" not in anon.get("/").headers


def test_healthz_and_robots(anon):
    r = anon.get("/healthz")
    assert r.status_code == 200 and r.get_data(as_text=True) == "ok"
    assert r.headers["Cache-Control"] == "no-store"
    assert "Disallow: /" in anon.get("/robots.txt").get_data(as_text=True)


def test_friendly_404_page(anon):
    r = anon.get("/нет-такой-страницы")
    assert r.status_code == 404
    assert "Тут ничего нет" in r.get_data(as_text=True)


def test_friendly_csrf_error_page(flask_app, anon, monkeypatch):
    monkeypatch.setitem(flask_app.config, "CSRF_ENABLED", True)
    r = anon.post("/login/parent", data={"password": "x"})
    body = r.get_data(as_text=True)
    assert r.status_code == 400 and "Форма устарела" in body and "На главную" in body


def test_oversized_request_rejected(anon):
    r = anon.post("/login/student", data={"username": "x" * 300_000, "password": "y"})
    assert r.status_code == 413


# ---------------------------------------------------------------- cookie

def test_student_cookie_is_httponly_samesite_and_persistent(flask_app, anon, make_student):
    make_student()
    r = anon.post("/login/student", data={"username": "masha", "password": "secret1"})
    cookie = r.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert "Expires=" in cookie                          # постоянная сессия (permanent)
    assert "Secure" not in cookie


def test_secure_cookie_flag_when_enabled(flask_app, anon, parent, make_student, monkeypatch):
    make_student()
    monkeypatch.setitem(flask_app.config, "SESSION_COOKIE_SECURE", True)
    r = anon.post("/login/student", data={"username": "masha", "password": "secret1"},
                  base_url="https://example.com")
    assert "Secure" in r.headers["Set-Cookie"]


# ---------------------------------------------------------------- ограничение попыток входа

def student_login(client, username, password):
    return client.post("/login/student", data={"username": username, "password": password},
                       follow_redirects=True).get_data(as_text=True)


def test_account_locked_after_too_many_failures(anon, make_student):
    make_student("masha", "Маша", "secret1")
    for _ in range(config.LOGIN_LIMITS["student"]):
        assert "Такого аккаунта нет" in student_login(anon, "masha", "wrong")
    body = student_login(anon, "masha", "secret1")               # пароль уже верный
    assert "Слишком много неудачных попыток" in body and "Привет, Маша" not in body


def test_lock_does_not_affect_other_accounts(anon, make_student):
    make_student("masha", "Маша", "secret1")
    make_student("petya", "Петя", "secret2")
    for _ in range(config.LOGIN_LIMITS["student"]):
        student_login(anon, "masha", "wrong")
    assert "Привет, Петя" in student_login(anon, "petya", "secret2")


def test_ip_locked_when_guessing_many_usernames(anon, make_student):
    make_student("masha", "Маша", "secret1")
    for i in range(config.LOGIN_LIMITS["ip"]):
        student_login(anon, f"guess{i}", "wrong")
    body = student_login(anon, "masha", "secret1")
    assert "Слишком много неудачных попыток" in body


def test_parent_password_guessing_is_locked(anon, monkeypatch):
    monkeypatch.setitem(config.LOGIN_LIMITS, "ip", 1000)         # проверяем именно лимит кабинета
    for _ in range(config.LOGIN_LIMITS["parent"]):
        r = anon.post("/login/parent", data={"password": "wrong"}, follow_redirects=True)
        assert "Неверный пароль" in r.get_data(as_text=True)
    r = anon.post("/login/parent", data={"password": config.PARENT_PASSWORD}, follow_redirects=True)
    body = r.get_data(as_text=True)
    assert "Слишком много неудачных попыток" in body and "Кабинет родителя" not in body


def test_successful_login_resets_account_counter(flask_app, anon, make_student):
    make_student("masha", "Маша", "secret1")
    for _ in range(3):
        student_login(anon, "masha", "wrong")
    assert db_scalar("SELECT COUNT(*) FROM login_failures WHERE scope='student'") == 3
    assert "Привет, Маша" in student_login(anon, "masha", "secret1")
    assert db_scalar("SELECT COUNT(*) FROM login_failures WHERE scope='student'") == 0


def test_lock_expires_after_window(flask_app):
    with flask_app.app_context():
        db = database.get_db()
        keys = [("ip", "1.2.3.4"), ("student", "masha")]
        for _ in range(config.LOGIN_LIMITS["student"]):
            ratelimit.record_failure(db, keys, now=1000)
        assert 0 < ratelimit.blocked_for(db, keys, now=1001) <= config.LOGIN_WINDOW_SEC
        assert ratelimit.blocked_for(db, keys, now=1000 + config.LOGIN_WINDOW_SEC + 2) == 0


def test_old_failures_are_pruned(flask_app):
    with flask_app.app_context():
        db = database.get_db()
        ratelimit.record_failure(db, [("ip", "9.9.9.9")], now=1)
        ratelimit.record_failure(db, [("ip", "8.8.8.8")], now=1 + ratelimit.KEEP_SECONDS + 5)
        assert db.execute("SELECT COUNT(*) FROM login_failures").fetchone()[0] == 1


# ---------------------------------------------------------------- срок входа родителя

def test_parent_login_expires(parent):
    assert parent.get("/parent").status_code == 200
    with parent.session_transaction() as s:
        s["parent_until"] = 0                          # «прошло 12 часов»
    r = parent.get("/parent")
    assert r.status_code == 302
    body = parent.get(r.headers["Location"]).get_data(as_text=True)
    assert "Вход родителя закончился" in body
    assert parent.get("/parent").status_code == 302    # и снова доступа нет


def test_parent_login_has_future_expiry(parent):
    with parent.session_transaction() as s:
        assert s["parent_until"] > __import__("time").time() + 3600


# ---------------------------------------------------------------- проверки боевого режима

def test_production_problems(monkeypatch):
    monkeypatch.setattr(config, "COOKIE_SECURE", True)
    monkeypatch.setenv("ENGLISH_PARENT_PASSWORD", STRONG)
    monkeypatch.setattr(config, "PARENT_PASSWORD", STRONG)
    assert config.production_problems() == []

    monkeypatch.setattr(config, "PARENT_PASSWORD", "1234")
    assert any("слишком простой" in p for p in config.production_problems())
    monkeypatch.setattr(config, "PARENT_PASSWORD", "short")
    assert any("короче" in p for p in config.production_problems())
    monkeypatch.delenv("ENGLISH_PARENT_PASSWORD")
    assert any("не задан" in p for p in config.production_problems())

    monkeypatch.setenv("ENGLISH_PARENT_PASSWORD", STRONG)
    monkeypatch.setattr(config, "PARENT_PASSWORD", STRONG)
    monkeypatch.setattr(config, "COOKIE_SECURE", False)
    assert any("COOKIE_SECURE" in p for p in config.production_problems())


def test_app_refuses_to_start_in_production_with_default_password(tmp_path):
    r = run_app("import app", tmp_path, ENGLISH_ENV="production")
    assert r.returncode != 0
    assert "Небезопасная настройка" in r.stderr and "ENGLISH_PARENT_PASSWORD" in r.stderr


def test_app_refuses_weak_password_in_production(tmp_path):
    r = run_app("import app", tmp_path, ENGLISH_ENV="production", ENGLISH_PARENT_PASSWORD="1234")
    assert r.returncode != 0 and "слишком простой" in r.stderr


def test_app_starts_in_production_with_strong_password(tmp_path):
    code = ("import app; c = app.app.config; "
            "print(c['SESSION_COOKIE_SECURE'], c['SESSION_COOKIE_HTTPONLY'], app.app.testing)")
    r = run_app(code, tmp_path, ENGLISH_ENV="production", ENGLISH_PARENT_PASSWORD=STRONG)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["True", "True", "False"]


# ---------------------------------------------------------------- работа за прокси

PROXY_CHECK = """
import app, database
from app import app as flask_app
flask_app.config["CSRF_ENABLED"] = False
c = flask_app.test_client()
c.post("/login/student", data={"username": "ghost", "password": "x"},
       headers={"X-Forwarded-For": "203.0.113.9", "X-Forwarded-Proto": "https"})
import sqlite3
rows = sqlite3.connect(database.DB_PATH).execute(
    "SELECT ident FROM login_failures WHERE scope='ip'").fetchall()
https = "Strict-Transport-Security" in c.get("/", headers={"X-Forwarded-Proto": "https"}).headers
print(rows[0][0], https)
"""


def test_forwarded_headers_trusted_only_behind_proxy(tmp_path):
    common = dict(ENGLISH_ENV="production", ENGLISH_PARENT_PASSWORD=STRONG)
    behind = run_app(PROXY_CHECK, tmp_path, ENGLISH_BEHIND_PROXY="1", **common)
    assert behind.returncode == 0, behind.stderr
    assert behind.stdout.split() == ["203.0.113.9", "True"]

    # без настройки заголовки подделать нельзя: лимиты считаются по настоящему адресу
    direct = run_app(PROXY_CHECK, tmp_path, **common)
    assert direct.returncode == 0, direct.stderr
    assert direct.stdout.split() == ["127.0.0.1", "False"]


# ---------------------------------------------------------------- ключ сессий, база

def test_secret_key_from_env_and_file(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGLISH_SECRET_KEY", "from-env")
    assert security.load_secret_key(str(tmp_path / "key")) == "from-env"
    assert not (tmp_path / "key").exists()

    monkeypatch.delenv("ENGLISH_SECRET_KEY")
    path = tmp_path / "key"
    first = security.load_secret_key(str(path))
    assert len(first) == 48 and security.load_secret_key(str(path)) == first   # стабилен
    if os.name != "nt":
        assert (path.stat().st_mode & 0o777) == 0o600


def test_database_uses_wal(flask_app):
    assert db_all("PRAGMA journal_mode")[0][0].lower() == "wal"


# ---------------------------------------------------------------- резервные копии

def make_db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE t (n INTEGER)")
    conn.executemany("INSERT INTO t VALUES (?)", [(1,), (2,), (3,)])
    conn.commit()
    conn.close()


def test_backup_is_valid_and_complete(tmp_path):
    make_db(tmp_path / "src.db")
    out = backup_db.make_backup(str(tmp_path / "src.db"), str(tmp_path / "b"), keep=5)
    assert out.endswith(".db.gz")
    restored = tmp_path / "restored.db"
    restored.write_bytes(gzip.decompress(Path(out).read_bytes()))
    assert sqlite3.connect(restored).execute("SELECT SUM(n) FROM t").fetchone()[0] == 6


def test_backup_keeps_only_latest(tmp_path):
    make_db(tmp_path / "src.db")
    for i in range(5):
        backup_db.make_backup(str(tmp_path / "src.db"), str(tmp_path / "b"), keep=3, now=1_700_000_000 + i * 60)
    names = sorted(p.name for p in (tmp_path / "b").iterdir())
    assert len(names) == 3
    assert names[0].startswith("english_app-2023") and names == sorted(names)


def test_two_backups_in_the_same_second_do_not_overwrite(tmp_path):
    make_db(tmp_path / "src.db")
    a = backup_db.make_backup(str(tmp_path / "src.db"), str(tmp_path / "b"), now=1_700_000_000)
    b = backup_db.make_backup(str(tmp_path / "src.db"), str(tmp_path / "b"), now=1_700_000_000)
    assert a != b and Path(a).exists() and Path(b).exists()


def test_backup_cli_reports_missing_database(tmp_path, monkeypatch, capsys=None):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "nope.db"))
    assert backup_db.main(["--dir", str(tmp_path / "b")]) == 1
