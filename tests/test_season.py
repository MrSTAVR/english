# -*- coding: utf-8 -*-
"""Недельный челлендж, босс недели, Хэллоуин."""
from datetime import date

import activity
import seasons
import weekly
import wardrobe
from tests.helpers import db_scalar, submit_lesson
from tests.test_vacation import conn, sid_of


def fill(sid, **kinds):
    c = conn()
    for k, n in kinds.items():
        for _ in range(n):
            activity.log(c, sid, k)
    return c


def finish_week(sid):
    c = conn()
    for t in weekly.status(c, sid)["tasks"]:
        for _ in range(t["need"]):
            activity.log(c, sid, t["kind"])
    return c


def test_season_dates():
    assert seasons.active_season(date(2026, 10, 14)) is None
    assert seasons.active_season(date(2026, 10, 15)) == "halloween"
    assert seasons.active_season(date(2026, 11, 3)) == "halloween"
    assert seasons.active_season(date(2026, 11, 4)) is None


def test_tasks_stable_per_week_and_three():
    w = date(2026, 10, 19)
    assert weekly.pick_tasks(w) == weekly.pick_tasks(w)
    t = weekly.pick_tasks(w)
    assert len(t) == 3 and t[0] == "lesson" and t[1] == "game"


def test_challenge_claims_once(make_student):
    make_student(); sid = sid_of(); c = conn()
    assert not weekly.status(c, sid)["complete"]
    assert weekly.claim(c, sid) == 0
    finish_week(sid)
    assert weekly.status(c, sid)["complete"]
    assert weekly.claim(c, sid) == weekly.WEEKLY_COINS
    assert weekly.claim(c, sid) == 0
    assert db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) == weekly.WEEKLY_COINS


def test_activity_logged_by_api(make_student):
    c = make_student(); sid = sid_of()
    c.post("/api/game", json={"game": "pairs", "stars": 2})
    assert db_scalar("SELECT COUNT(*) FROM activity WHERE kind='game' AND student_id=?", (sid,)) == 1
    c.post("/api/dialog", json={"key": __import__("data.dialogs", fromlist=["x"]).DIALOGS[0]["key"]})
    assert db_scalar("SELECT COUNT(*) FROM activity WHERE kind='dialog'") == 1


def test_lesson_pass_logged(make_student):
    c = make_student(); sid = sid_of()
    submit_lesson(c, __import__("curriculum").LESSONS[0]["id"])
    assert db_scalar("SELECT COUNT(*) FROM activity WHERE kind='lesson' AND student_id=?", (sid,)) == 1


def test_boss_locked_until_challenge(make_student):
    c = make_student(); sid = sid_of()
    assert c.get("/student/boss").status_code == 302
    assert c.post("/api/boss", json={"win": True}).get_json()["coins"] == 0
    assert "Босс прячется" in c.get("/student/weekly").get_data(as_text=True)


def test_boss_win_rewards_once_per_week(make_student):
    c = make_student(); sid = sid_of()
    finish_week(sid)
    page = c.get("/student/weekly")        # выдаёт награду челленджа
    assert page.status_code == 200
    r = c.post("/api/boss", json={"win": True}).get_json()
    assert r["coins"] == weekly.BOSS_COINS and "Шлем рыцаря" in r["items"]
    assert "hat-knight" in wardrobe.owned_keys(conn(), sid)
    r2 = c.post("/api/boss", json={"win": True}).get_json()
    assert r2["coins"] == 0 and r2["items"] == []
    assert db_scalar("SELECT COUNT(*) FROM boss_wins WHERE student_id=?", (sid,)) == 1


def test_boss_page_needs_words(make_student):
    c = make_student(); sid = sid_of()
    finish_week(sid)
    c.get("/student/weekly")
    assert c.get("/student/boss").status_code == 302     # слов ещё нет
    from curriculum import LESSONS
    for l in LESSONS[:3]:
        submit_lesson(c, l["id"])
    r = c.get("/student/boss")
    assert r.status_code == 200 and "data-words" in r.get_data(as_text=True)


def test_boss_items_not_buyable(make_student):
    c = make_student(); sid = sid_of()
    cn = conn()
    cn.execute("UPDATE garden SET coins=500 WHERE student_id=?", (sid,)); cn.commit()
    ok, _ = wardrobe.buy(cn, sid, "hat-knight")
    assert not ok


def test_halloween_items_only_in_season(make_student, monkeypatch):
    c = make_student(); sid = sid_of()
    cn = conn()
    cn.execute("UPDATE garden SET coins=500 WHERE student_id=?", (sid,)); cn.commit()
    monkeypatch.setattr(seasons, "today", lambda: date(2026, 6, 1))
    assert not wardrobe.buy(cn, sid, "hat-witch")[0]
    assert "Шляпа ведьмы" not in c.get("/student/wardrobe").get_data(as_text=True)
    assert c.get("/student/halloween").status_code == 302
    monkeypatch.setattr(seasons, "today", lambda: date(2026, 10, 25))
    assert "Шляпа ведьмы" in c.get("/student/wardrobe").get_data(as_text=True)
    assert wardrobe.buy(cn, sid, "hat-witch")[0]
    monkeypatch.setattr(seasons, "today", lambda: date(2026, 6, 1))
    assert "Шляпа ведьмы" in c.get("/student/wardrobe").get_data(as_text=True)   # купленное остаётся


def test_halloween_quiz_coins_once_a_day(make_student, monkeypatch):
    c = make_student(); sid = sid_of()
    monkeypatch.setattr(seasons, "today", lambda: date(2026, 10, 25))
    assert c.get("/student/halloween").status_code == 200
    assert c.post("/api/halloween", json={"correct": 3}).get_json()["coins"] == 0
    assert c.post("/api/halloween", json={"correct": 7}).get_json()["coins"] == 3
    assert c.post("/api/halloween", json={"correct": 8}).get_json()["coins"] == 0
    assert c.post("/api/halloween", json={"correct": 99}).status_code == 400
    assert db_scalar("SELECT coins FROM garden WHERE student_id=?", (sid,)) == 3


def test_home_shows_teasers(make_student, monkeypatch):
    c = make_student()
    monkeypatch.setattr(seasons, "today", lambda: date(2026, 10, 25))
    body = c.get("/student").get_data(as_text=True)
    assert "Недельный челлендж" in body and "Хэллоуин!" in body


def test_sw_knows_new_pages(anon):
    body = anon.get("/sw.js").get_data(as_text=True)
    assert "weekly|boss|halloween" in body


def test_parent_controls_halloween(parent, make_student, monkeypatch):
    c = make_student()
    monkeypatch.setattr(seasons, "today", lambda: date(2026, 6, 1))
    assert "Праздничные события" in parent.get("/parent").get_data(as_text=True)
    assert c.get("/student/halloween").status_code == 302            # по датам — не сезон
    parent.post("/parent/season", data={"season": "halloween", "mode": "on"})
    assert c.get("/student/halloween").status_code == 200            # включён вручную
    monkeypatch.setattr(seasons, "today", lambda: date(2026, 10, 25))
    parent.post("/parent/season", data={"season": "halloween", "mode": "off"})
    assert c.get("/student/halloween").status_code == 302            # выключен даже в сезон
    assert "Хэллоуин!" not in c.get("/student").get_data(as_text=True)
    parent.post("/parent/season", data={"season": "halloween", "mode": "auto"})
    assert c.get("/student/halloween").status_code == 200
    parent.post("/parent/season", data={"season": "bogus", "mode": "on"})
    assert seasons.get_mode("halloween") in ("auto", "on", "off")


def test_season_setting_requires_parent(make_student):
    c = make_student()
    c.post("/parent/season", data={"season": "halloween", "mode": "off"})
    assert db_scalar("SELECT COUNT(*) FROM app_settings") == 0


def test_parent_sets_custom_dates(parent, make_student, monkeypatch):
    c = make_student()
    monkeypatch.setattr(seasons, "today", lambda: date(2026, 12, 20))
    assert c.get("/student/halloween").status_code == 302
    parent.post("/parent/season", data={"season": "halloween", "mode": "auto",
                                        "date_from": "2026-12-15", "date_to": "2026-12-25"})
    assert db_scalar("SELECT value FROM app_settings WHERE key='season_halloween_from'") == "2026-12-15"
    assert c.get("/student/halloween").status_code == 200
    monkeypatch.setattr(seasons, "today", lambda: date(2026, 10, 25))   # стандартные даты больше не работают
    assert c.get("/student/halloween").status_code == 302
    assert "15.12.2026" in parent.get("/parent").get_data(as_text=True)
    parent.post("/parent/season", data={"season": "halloween", "mode": "auto", "date_from": "", "date_to": ""})
    assert db_scalar("SELECT COUNT(*) FROM app_settings WHERE key LIKE '%_from'") == 0 and c.get("/student/halloween").status_code == 200


def test_custom_dates_validation(parent, make_student):
    make_student()
    for a, b in (("2026-12-25", "2026-12-15"), ("2026-12-15", ""), ("bad", "bad")):
        parent.post("/parent/season", data={"season": "halloween", "mode": "auto", "date_from": a, "date_to": b})
    assert db_scalar("SELECT COUNT(*) FROM app_settings WHERE key LIKE '%_from'") == 0
