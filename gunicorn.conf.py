# -*- coding: utf-8 -*-
"""Настройки gunicorn для Linux-сервера: gunicorn -c gunicorn.conf.py wsgi:app"""
import os

bind = os.environ.get("ENGLISH_BIND", "127.0.0.1:8000")   # наружу смотрит только прокси (Caddy/nginx)
workers = int(os.environ.get("ENGLISH_WORKERS", "2"))
threads = 4
worker_class = "gthread"
timeout = 30
graceful_timeout = 20
keepalive = 5
preload_app = True        # приложение и миграции базы стартуют один раз, до запуска воркеров
accesslog = "-"
errorlog = "-"
