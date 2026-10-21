# -*- coding: utf-8 -*-
"""Общие фикстуры. Тесты работают ТОЛЬКО с временной БД и не трогают english_app.db."""
import os
import tempfile

# Должно выполниться ДО `import app`: при импорте app.py вызывает init_db().
os.environ["ENGLISH_APP_DB"] = os.path.join(
    tempfile.mkdtemp(prefix="english_boot_"), "boot.db")

import pytest  # noqa: E402

import app as appmod  # noqa: E402
import config  # noqa: E402
import database  # noqa: E402


@pytest.fixture
def flask_app(tmp_path, monkeypatch):
    """Приложение со свежей пустой БД на каждый тест."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    database.init_db()
    appmod.app.config.update(TESTING=True)
    return appmod.app


@pytest.fixture
def anon(flask_app):
    return flask_app.test_client()


@pytest.fixture
def parent(flask_app):
    c = flask_app.test_client()
    r = c.post("/login/parent", data={"password": config.PARENT_PASSWORD},
               follow_redirects=True)
    assert "Кабинет родителя" in r.get_data(as_text=True)
    return c


@pytest.fixture
def make_student(flask_app, parent):
    """Фабрика: родитель создаёт аккаунт, возвращается клиент, уже вошедший как ученик."""
    def _make(username="masha", name="Маша", password="secret1", emoji="🦄"):
        r = parent.post("/parent/students/add", data={
            "display_name": name, "username": username,
            "password": password, "emoji": emoji}, follow_redirects=True)
        assert f"Аккаунт для {name} создан" in r.get_data(as_text=True)
        c = flask_app.test_client()
        r = c.post("/login/student",
                   data={"username": username, "password": password},
                   follow_redirects=True)
        assert f"Привет, {name}" in r.get_data(as_text=True)
        return c
    return _make
