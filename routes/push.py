# -*- coding: utf-8 -*-
"""Web Push для ученика: ключ, подписка и отписка устройства (push.py)."""
import logging
import sqlite3

from flask import Blueprint, jsonify, request

import push
from database import get_db
from routes.common import get_student_or_none, require_role

log = logging.getLogger(__name__)
bp = Blueprint("push", __name__)


@bp.route("/api/push/key")
def push_key():
    err = require_role("student")
    if err:
        return jsonify(error="login"), 401
    try:
        return jsonify(key=push.public_key(get_db()))
    except (ImportError, ValueError, sqlite3.Error) as e:
        log.warning("push: нет ключа: %s", e)
        return jsonify(error="unavailable"), 503


@bp.route("/api/push/subscribe", methods=["POST"])
def push_subscribe():
    err = require_role("student")
    if err:
        return jsonify(error="login"), 401
    db = get_db()
    student = get_student_or_none(db)
    if not student:
        return jsonify(error="login"), 401
    ok = push.subscribe(db, student["id"], (request.get_json(silent=True) or {}).get("sub"))
    return (jsonify(ok=True), 200) if ok else (jsonify(error="bad subscription"), 400)


@bp.route("/api/push/unsubscribe", methods=["POST"])
def push_unsubscribe():
    err = require_role("student")
    if err:
        return jsonify(error="login"), 401
    endpoint = (request.get_json(silent=True) or {}).get("endpoint")
    db = get_db()
    student = get_student_or_none(db)
    if student and isinstance(endpoint, str):
        push.unsubscribe(db, student["id"], endpoint)
    return jsonify(ok=True)
