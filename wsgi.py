# -*- coding: utf-8 -*-
"""Точка входа для боевых серверов: gunicorn -c gunicorn.conf.py wsgi:app"""
from app import app

application = app   # для серверов, которые ищут имя `application`
