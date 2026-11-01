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
from routes.games import bp as games_bp
from routes.wardrobe import bp as wardrobe_bp
from routes.stories import bp as stories_bp
from routes.writing import bp as writing_bp
from routes.season import bp as season_bp
from routes.house import bp as house_bp
from routes.speech import bp as speech_bp
from routes.friends import bp as friends_bp
from routes.castle import bp as castle_bp
from routes.farm import bp as farm_bp
from routes.pizza import bp as pizza_bp
from routes.push import bp as push_bp


def register_blueprints(app):
    for bp in (auth_bp, student_bp, garden_bp, parent_bp, system_bp, pwa_bp, speak_bp, review_bp, games_bp, wardrobe_bp, stories_bp, writing_bp, season_bp, house_bp, speech_bp, friends_bp, castle_bp, farm_bp, pizza_bp, push_bp):
        app.register_blueprint(bp)
