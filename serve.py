# -*- coding: utf-8 -*-
"""Боевой сервер Waitress (работает и на Windows): python serve.py

Настройки через переменные окружения:
  ENGLISH_HOST  адрес (по умолчанию 127.0.0.1 — только этот компьютер;
                0.0.0.0 — открыть для домашней сети)
  PORT          порт (по умолчанию 8000)
"""
import os

from waitress import serve

from app import app

if __name__ == "__main__":
    host = os.environ.get("ENGLISH_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"==> English Fun: http://{host}:{port}  (Ctrl+C — остановить)")
    serve(app, host=host, port=port, threads=4, ident="english")
