# -*- coding: utf-8 -*-
"""Blueprint-ы приложения."""

from routes.auth import bp as auth_bp
from routes.student import bp as student_bp
from routes.garden import bp as garden_bp
from routes.parent import bp as parent_bp
from routes.system import bp as system_bp
from routes.pwa import bp as pwa_bp
from routes.speak import bp as speak_bp
from routes.review import bp as review_bp


def register_blueprints(app):
    for bp in (auth_bp, student_bp, garden_bp, parent_bp, system_bp, pwa_bp, speak_bp, review_bp):
        app.register_blueprint(bp)
