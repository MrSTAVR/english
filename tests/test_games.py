# -*- coding: utf-8 -*-
"""Игры со словами и мини-диалоги."""
from curriculum import ALL_LESSONS as LESSONS, validate_dialogs
from data.dialogs import DIALOGS
from tests.helpers import N, db_all, db_scalar, submit_lesson


def _credit(parent, n=12):
    sid = db_scalar("SELECT id FROM students WHERE username='masha'")
    parent.post(f"/parent/students/{sid}/credit", data={"upto": str(n), "action": "add"})


def test_dialogs_are_valid_and_attached_to_lessons():
    assert validate_dialogs() == []
    assert len(DIALOGS) >= 30
    for d in DIALOGS:
        lesson = next(l for l in LESSONS if l["id"] == d["lesson"])
        assert d in lesson["dialogs"]


def test_games_hub_needs_words(make_student):
    c = make_student()
    html = c.get("/student/games").get_data(as_text=True)
    assert "Пока мало слов" in html


def test_game_pages_open_after_lessons(parent, make_student):
    c = make_student()
    _credit(parent)
    hub = c.get("/student/games").get_data(as_text=True)
    for title in ("Найди пару", "Мемори", "Блиц", "Услышь", "Бег", "Диалоги"):
        assert title in hub
    for g in ("pairs", "memory", "blitz", "listen", "runner"):
        html = c.get(f"/student/games/play/{g}").get_data(as_text=True)
        assert 'id="game"' in html and "games.js" in html and "data-words" in html
    assert c.get("/student/games/play/nope").status_code == 404


def test_game_for_one_lesson_and_locked_lesson(make_student):
    c = make_student()
    assert c.get(f"/student/games?lesson={N(1)}").status_code == 200         # открытый урок
    assert c.get(f"/student/games/play/pairs?lesson={N(1)}").status_code == 200
    assert c.get(f"/student/games/play/pairs?lesson={N(30)}").status_code == 403   # закрытый
    assert 'games?lesson=' in submit_lesson(c, N(1))                          # после сданного урока — «Сыграй со словами»


def test_game_api_and_achievements(make_student):
    c = make_student()
    assert c.post("/api/game", json={"game": "pairs", "stars": 9}).status_code == 400
    assert c.post("/api/game", json={"game": "zzz", "stars": 1}).status_code == 400
    r = c.post("/api/game", json={"game": "pairs", "stars": 2}).get_json()
    assert r["plays"] == 1 and any(a["key"] == "game_1" for a in r["newAchievements"])
    c.post("/api/game", json={"game": "pairs", "stars": 1})
    assert db_all("SELECT game, best, plays FROM game_scores") == [("pairs", 2, 2)]       # лучший результат сохраняется


def test_four_perfect_games_give_champion(make_student):
    c = make_student()
    last = None
    for g in ("pairs", "memory", "blitz", "listen", "runner"):
        last = c.post("/api/game", json={"game": g, "stars": 3}).get_json()
    assert any(a["key"] == "game_p4" for a in last["newAchievements"])


def test_game_api_needs_student(anon):
    assert anon.post("/api/game", json={"game": "pairs", "stars": 1}).status_code == 403
    assert anon.post("/api/dialog", json={"key": "greet-meet"}).status_code == 403


def test_dialogs_page_and_progress(parent, make_student):
    c = make_student()
    assert "откроются после уроков" in c.get("/student/dialogs").get_data(as_text=True)
    submit_lesson(c, N(1))
    submit_lesson(c, 9)                                      # приветствия пройдены
    html = c.get("/student/dialogs").get_data(as_text=True)
    assert "greet-meet" in html and 'id="dialogs"' in html
    r = c.post("/api/dialog", json={"key": "greet-meet"}).get_json()
    assert r["done"] == 1 and any(a["key"] == "dialog_1" for a in r["newAchievements"])
    c.post("/api/dialog", json={"key": "greet-meet"})
    assert db_scalar("SELECT COUNT(*) FROM dialog_done") == 1          # повтор не дублируется
    assert c.post("/api/dialog", json={"key": "nope"}).status_code == 400


def test_lesson_page_embeds_its_dialog(make_student, parent):
    c = make_student()
    _credit(parent, 1)
    html = c.get("/lesson/9").get_data(as_text=True)                  # тренировки (и диалога в ней) в уроке больше нет
    assert "lesson-dialogs" not in html and "dialogs.js" not in html
    assert "greet-meet" in c.get("/student/dialogs").get_data(as_text=True)


def test_dialog_partners_have_portraits():
    from data.dialogs import CHARACTERS
    assert {d["partner"] for d in DIALOGS} <= set(CHARACTERS)
    assert not any(c for c in CHARACTERS.values() if len(c) != 3)
