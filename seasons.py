# -*- coding: utf-8 -*-
"""Сезонные события. Пока только Хэллоуин (15 октября — 3 ноября); остальные сезоны — в планах."""
from datetime import date, datetime


def today():
    return datetime.now().date()


def active_season(day=None):
    """Ключ сезона на указанный день или None."""
    d = day or today()
    if (d.month == 10 and d.day >= 15) or (d.month == 11 and d.day <= 3):
        return "halloween"
    return None
