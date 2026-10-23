# -*- coding: utf-8 -*-
"""«Друзья»: рекорды, дуэли, лента с реакциями, гости, переключатель соревнований."""
import re

from tests.helpers import db_scalar


def _sid(username):
    return db_scalar("SELECT id FROM students WHERE username=?", (username,))


def _two(make_student, parent, lessons="10"):
    masha = make_student("masha", "Маша", emoji="🦄")
    anya = make_student("anya", "Аня", emoji="🐼")
    for u in ("masha", "anya"):
        parent.post(f"/parent/students/{_sid(u)}/credit", data={"upto": lessons, "action": "add"})
    return masha, anya


def _game(c, game, score, stars=2, duel=None):
    body = {"game": game, "stars": stars, "score": score}
    if duel:
        body["duel"] = duel
    r = c.post("/api/game", json=body)
    assert r.status_code == 200
    return r.get_json()


def _coins(username):
    return db_scalar("SELECT coins FROM garden WHERE student_id=?", (_sid(username),)) or 0


def test_records_personal_and_among_friends(make_student, parent):
    masha, anya = _two(make_student, parent)
    assert "Новый личный рекорд" in _game(masha, "blitz", 10)["message"]
    assert _game(masha, "blitz", 8)["message"] == ""                  # хуже своего — не рекорд
    assert "среди друзей" in _game(anya, "blitz", 12)["message"]
    assert _game(masha, "pairs", 30)["message"] == "Новый личный рекорд!"      # у друзей рекорда ещё нет
    _game(anya, "pairs", 25)
    html = masha.get("/student/games").get_data(as_text=True)
    assert "Твой рекорд: 10 слов" in html and "Рекорд друзей: Аня — 12 слов" in html
    page = masha.get("/student/friends").get_data(as_text=True)
    assert "Рекорды в играх" in page and "25 секунд" in page
    assert "Новый рекорд среди друзей: «Блиц 60 секунд» — 12 слов" in page   # лента
    assert _game(masha, "blitz", 9999)["message"] == ""                 # мусор не сохраняется


def test_duel_flow_and_coins(make_student, parent):
    masha, anya = _two(make_student, parent)
    before_m, before_a = _coins("masha"), _coins("anya")
    r = masha.post("/student/friends/duel", data={"friend": _sid("anya"), "game": "blitz"})
    assert r.status_code == 302 and "duel=" in r.headers["Location"]
    duel = int(re.search(r"duel=(\d+)", r.headers["Location"]).group(1))
    page = masha.get(r.headers["Location"]).get_data(as_text=True)
    assert "Соперник — Аня" in page
    # Аня пока не видит вызова — Маша ещё не сыграла
    assert "Тебя вызвали на дуэль" not in anya.get("/student").get_data(as_text=True)
    assert "очередь соперника — Аня" in _game(masha, "blitz", 15, duel=duel)["message"]
    assert "Тебя вызвали на дуэль" in anya.get("/student").get_data(as_text=True)
    # второй раз сыграть свою часть нельзя
    assert masha.get(f"/student/games/play/blitz?duel={duel}").status_code == 302
    msg = _game(anya, "blitz", 11, duel=duel)["message"]
    assert "В этот раз победа у соперника" in msg
    assert _coins("masha") - before_m == 5 and _coins("anya") - before_a == 2
    page = masha.get("/student/friends").get_data(as_text=True)
    assert "Победа!" in page and "Дуэль «Блиц 60 секунд»: Маша — 15, Аня — 11, победа — Маша!" in page
    words = db_scalar("SELECT words FROM duels WHERE id=?", (duel,))
    assert words.count('"') // 2 == 20


def test_duel_rules(make_student, parent):
    masha, anya = _two(make_student, parent)
    lonely = make_student("kate", "Катя", emoji="🐱")          # без уроков — общих слов нет
    r = masha.post("/student/friends/duel", data={"friend": _sid("kate"), "game": "pairs"}, follow_redirects=True)
    assert "мало слов" in r.get_data(as_text=True)
    masha.post("/student/friends/duel", data={"friend": _sid("anya"), "game": "pairs"})
    r = masha.post("/student/friends/duel", data={"friend": _sid("anya"), "game": "memory"}, follow_redirects=True)
    assert "ещё не закончена" in r.get_data(as_text=True)
    r = masha.post("/student/friends/duel", data={"friend": _sid("anya"), "game": "runner"}, follow_redirects=True)
    assert "Такой игры" in r.get_data(as_text=True)
    assert lonely.get("/student/friends").status_code == 200


def test_pairs_duel_lower_is_better_and_draw(make_student, parent):
    masha, anya = _two(make_student, parent)
    r = masha.post("/student/friends/duel", data={"friend": _sid("anya"), "game": "pairs"})
    duel = int(re.search(r"duel=(\d+)", r.headers["Location"]).group(1))
    _game(masha, "pairs", 20, duel=duel)
    assert "Победа! Ты молодец" in _game(anya, "pairs", 18, duel=duel)["message"]
    r = anya.post("/student/friends/duel", data={"friend": _sid("masha"), "game": "memory"})
    duel = int(re.search(r"duel=(\d+)", r.headers["Location"]).group(1))
    _game(anya, "memory", 9, duel=duel)
    assert "Ничья" in _game(masha, "memory", 9, duel=duel)["message"]


def test_feed_reactions_and_news(make_student, parent):
    masha, anya = _two(make_student, parent)
    feed_id = db_scalar("SELECT id FROM feed WHERE student_id=? ORDER BY id DESC", (_sid("anya"),))
    anya.get("/student/friends")                                    # всё прочитано
    masha.post("/student/friends/react", data={"feed": feed_id, "kind": "bravo"})
    assert "Молодец! Маша" in anya.get("/student/friends").get_data(as_text=True)
    # своим новостям реакцию поставить нельзя
    own = db_scalar("SELECT id FROM feed WHERE student_id=? ORDER BY id DESC", (_sid("masha"),))
    assert masha.post("/student/friends/react", data={"feed": own, "kind": "wow"}).status_code == 400
    # повторное нажатие убирает реакцию
    masha.post("/student/friends/react", data={"feed": feed_id, "kind": "bravo"})
    assert db_scalar("SELECT COUNT(*) FROM feed_reactions") == 0
    masha.post("/student/friends/react", data={"feed": feed_id, "kind": "catch"})
    home = anya.get("/student").get_data(as_text=True)
    assert '<b>Друзья</b><small>дуэли и рекорды</small></span><span class="tile-badge">1</span>' in home


def test_visit_garden_and_house_with_like(make_student, parent):
    masha, anya = _two(make_student, parent)
    aid = _sid("anya")
    assert "garden-stage" in masha.get(f"/student/friends/{aid}/garden").get_data(as_text=True)
    page = masha.get(f"/student/friends/{aid}/house").get_data(as_text=True)
    assert "cs-castle" in page and "castle.js" in page
    masha.post(f"/student/friends/{aid}/house/like")
    assert "Нравится: Маша" in masha.get(f"/student/friends/{aid}/house").get_data(as_text=True)
    assert masha.get(f"/student/friends/{aid}/kitchen").status_code == 404
    assert masha.get(f"/student/friends/{_sid('masha')}/garden").status_code == 404   # к себе «в гости» нельзя


def test_competitions_switch(make_student, parent):
    masha, anya = _two(make_student, parent)
    aid = _sid("anya")
    assert "Соревнования" in parent.get(f"/parent/students/{aid}").get_data(as_text=True)
    parent.post(f"/parent/students/{aid}/competitions", data={"on": "0"})
    page = masha.get("/student/friends").get_data(as_text=True)
    assert "Пока здесь только ты" in page and "Аня" not in page
    assert masha.get(f"/student/friends/{aid}/garden").status_code == 404
    assert anya.get("/student/friends").status_code == 302
    assert "дуэли и рекорды" not in anya.get("/student").get_data(as_text=True)
    parent.post(f"/parent/students/{aid}/competitions", data={"on": "1"})
    assert "Аня" in masha.get("/student/friends").get_data(as_text=True)


def test_delete_student_cleans_friends(make_student, parent):
    masha, anya = _two(make_student, parent)
    aid = _sid("anya")
    _game(anya, "blitz", 7)
    r = masha.post("/student/friends/duel", data={"friend": aid, "game": "blitz"})
    masha.post(f"/student/friends/{aid}/garden/like")
    parent.post(f"/parent/students/{aid}/delete")
    assert db_scalar("SELECT COUNT(*) FROM students WHERE id=?", (aid,)) == 0
    for t, col in (("feed", "student_id"), ("game_records", "student_id"), ("duels", "to_id"), ("likes", "owner_id")):
        assert db_scalar(f"SELECT COUNT(*) FROM {t} WHERE {col}=?", (aid,)) == 0
    assert r.status_code == 302
