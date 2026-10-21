# -*- coding: utf-8 -*-
"""Конфигурация: пути и константы приложения."""

import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Путь к БД можно переопределить (так тесты не трогают настоящую базу)
DB_PATH = os.environ.get("ENGLISH_APP_DB") or os.path.join(BASE_DIR, "english_app.db")


PASS_MARK = 70          # минимальный процент, чтобы тест считаться сданным
PARENT_PASSWORD = os.environ.get("ENGLISH_PARENT_PASSWORD", "1234")  # пароль родителя; смените через переменную окружения
