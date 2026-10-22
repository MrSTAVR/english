# -*- coding: utf-8 -*-
"""Настройки анимированного помощника для base.html."""

import logging
import sqlite3

from flask import request, session

log = logging.getLogger(__name__)


MASCOT_NAME = "Чик-чик"        # имя помощника (можно поменять)
MASCOT_ENABLED = True          # False — полностью отключить помощника


def build_mascot_ctx():
    """Собирает базовые настройки помощника для текущей страницы."""
    role = session.get("role")
    page = "anon" if not role else ("parent" if role == "parent" else "student")
    endpoint = request.endpoint or ""
    mascot = {"enabled": MASCOT_ENABLED, "name": MASCOT_NAME, "page": page}
    if page == "parent":
        mascot["enabled"] = False      # в кабинете родителя помощник не нужен
    if page != "student":
        return mascot
    mascot["student"] = session.get("student_name") or ""
    sid = session.get("student_id")
    if sid:
        try:
            from database import get_db
            from wardrobe import outfit
            mascot["outfit"] = outfit(get_db(), sid)
        except sqlite3.Error:    # наряд — украшение, страница не должна падать из-за него
            log.exception("не удалось прочитать наряд ученика %s", sid)
            mascot["outfit"] = {}
    if endpoint == "auth.index":
        mascot["page"] = "index"
    elif endpoint == "student.student_home":
        mascot["page"] = "home"
    elif endpoint == "student.lesson_page":
        mascot["page"] = "lesson"
    elif endpoint == "student.submit_test":
        mascot["page"] = "result"
    elif endpoint in ("writing.writing_hub", "writing.writing_play"):
        mascot["page"] = "writing"
    elif endpoint in ("stories.stories_page", "stories.story_page"):
        mascot["page"] = "stories"
    elif endpoint == "wardrobe.wardrobe_page":
        mascot["page"] = "wardrobe"
    elif endpoint == "garden.garden_page":
        mascot["page"] = "garden"
    elif endpoint == "student.words_page":
        mascot["page"] = "words"
    elif endpoint == "student.achievements_page":
        mascot["page"] = "achievements"
    elif endpoint in ("games.games_hub", "games.game_play"):
        mascot["page"] = "games"
    elif endpoint == "games.dialogs_page":
        mascot["page"] = "dialogs"
    elif endpoint == "review.review_page":
        mascot["page"] = "review"
    elif endpoint == "speak.speak_page":
        mascot["page"] = "speak"
    elif endpoint == "student.theory_page":
        mascot["page"] = "theory"
    return mascot
