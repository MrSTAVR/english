# -*- coding: utf-8 -*-
"""Защита приложения, открытого в интернете: заголовки и работа за прокси."""

from flask import request

import config


def init_hardening(app):
    """Подключает заголовки безопасности и (по настройке) доверие к обратному прокси."""
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=config.COOKIE_SECURE,
        PERMANENT_SESSION_LIFETIME=config.SESSION_DAYS * 24 * 3600,
        MAX_CONTENT_LENGTH=256 * 1024,      # формы маленькие: большие запросы отбрасываем
    )

    if config.BEHIND_PROXY:
        from werkzeug.middleware.proxy_fix import ProxyFix
        # доверяем ровно одному прокси перед нами (Caddy/nginx на этом же сервере)
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    @app.after_request
    def _security_headers(resp):
        h = resp.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")                      # нельзя встроить в чужой сайт
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "camera=(), geolocation=(), payment=()")
        h.setdefault("X-Robots-Tag", "noindex, nofollow")            # детский сайт не для поисковиков
        if config.IS_PRODUCTION and request.is_secure:
            h.setdefault("Strict-Transport-Security", "max-age=15552000")   # 180 дней
        return resp
