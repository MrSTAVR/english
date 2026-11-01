# -*- coding: utf-8 -*-
"""Дизайн 3.0: файл стилей подключён, логопедическая часть в своём стиле, шрифты локальные, у Чик-чика один клюв."""
import pytest
from curriculum import LESSONS
from tests.helpers import N
import re
from pathlib import Path

from tests.test_speech import logoped  # noqa: F401  (фикстура)

STATIC = Path(__file__).resolve().parent.parent / "static"


def test_design_css_is_last_and_versioned(anon):
    body = anon.get("/").get_data(as_text=True)
    links = re.findall(r'href="/static/([\w.]+\.css)\?v=\d+"', body)
    assert links[-1] == "design.css"
    assert 'class="area-speech"' not in body


def test_speech_area_has_own_style(anon):
    assert 'class="area-speech"' in anon.get("/logoped").get_data(as_text=True)
    css = (STATIC / "design.css").read_text(encoding="utf-8")
    assert "body.area-speech" in css and "Manrope" in css
    assert 'html[data-theme="dark"] body.area-speech' in css


def test_fonts_are_local():
    css = (STATIC / "fonts.css").read_text(encoding="utf-8")
    assert "'Manrope'" in css and "'Nunito'" in css and "gstatic" not in css
    for rel in re.findall(r"url\(([^)]+\.woff2)\)", css):
        assert (STATIC / rel).is_file(), rel


def test_chick_has_one_beak():
    css = (STATIC / "mascot.css").read_text(encoding="utf-8")
    assert re.search(r"\.chick \.c-beak-low \{ display: none; \}", css)
    assert "is-talking .c-beak {" in css
    assert 'class="c-beak"' in (STATIC / "chick.js").read_text(encoding="utf-8")


def test_manifest_colors(anon):
    data = anon.get("/manifest.webmanifest").get_json()
    assert data["theme_color"] == "#FFF7E8"


def test_student_tabbar(make_student):
    c = make_student(farm=True)
    body = c.get("/student").get_data(as_text=True)
    assert 'class="has-tabbar"' in body and 'class="tabbar"' in body
    for label in ("Главная", "Карта", "Ферма", "Игры", "Награды"):
        assert f"<span>{label}</span>" in body
    assert 'class="tab on" aria-current="page"' in body
    garden = c.get("/student/garden").get_data(as_text=True)
    assert 'href="/student/farm" class="tab on"' in garden            # сад — уголок фермы
    lesson = c.get(f"/lesson/{N(1)}").get_data(as_text=True)          # в уроке нижнего меню нет
    assert 'class="has-tabbar"' not in lesson


def test_lesson_test_has_progress_bar(parent, make_student):
    c = make_student()
    parent.post("/parent/students/1/credit", data={"upto": "100", "action": "add"})
    lesson = next((x for x in LESSONS if not x.get("scene")), None)  # у уроков-сцен своя форма
    if lesson is None:
        pytest.skip("весь курс уже со сценой")
    lid = lesson["id"]
    html = c.get(f"/lesson/{lid}").get_data(as_text=True)
    assert 'id="test-progress"' in html and "function unansweredQuestions()" in html
    assert html.count("unansweredQuestions()") >= 3          # и полоска, и проверка перед отправкой


def test_castle_moved_to_farm(make_student):
    c = make_student(farm=True)
    assert c.get("/student/castle").headers["Location"].endswith("/student/farm")      # замок закрыт — ферма
    html = c.get("/student/farm").get_data(as_text=True)
    assert 'href="/student/farm" class="tab on"' in html and "Замок" not in html.split("<main")[0]



def test_logoped_menu(logoped):
    html = logoped.get("/logoped/home").get_data(as_text=True)
    assert "area-speech has-tabbar sp-logoped" in html and 'id="clients"' in html
    for label in ("Сегодня", "Расписание", "Ученики"):
        assert f"<span>{label}</span>" in html
    assert "Чик-чик" not in html and "English Fun" not in html


def test_no_color_emoji_in_interface(make_student, parent):
    import html as H
    from template_filters import EMOJI_RE, noemoji
    assert noemoji("Гласные и согласные 🔤") == "Гласные и согласные" and noemoji("Ура! 🎉 Молодец") == "Ура! Молодец"
    c = make_student()
    for client, url in ((c, "/student"), (c, "/student/map"), (c, "/student/games"), (parent, "/parent"), (parent, "/parent/progress")):
        body = client.get(url).get_data(as_text=True)
        body = re.sub(r"<script.*?</script>|<style.*?</style>|<span class=\"welcome-emoji\"[^>]*>.*?</span>", "", body, flags=re.S)
        text = H.unescape(re.sub(r"<[^>]+>", " ", body))
        assert not EMOJI_RE.findall(text), (url, set(EMOJI_RE.findall(text)))


def test_listen_buttons_have_outline_icon():
    html = open("templates/student_home.html", encoding="utf-8").read()
    m = re.search(r'<button[^>]*class="wod-say[^"]*"[^>]*>(.*?)</button>', html, re.S)
    assert m and 'href="#o-sound"' in m.group(1)
    assert "#o-sound" in open("static/dialogs.js", encoding="utf-8").read()
    css = open("static/design.css", encoding="utf-8").read()
    assert ".wod-say.say-btn" in css and "#FFFFFF" in css


def test_student_avatar_on_home(make_student, parent):
    import database
    c = make_student()
    html = c.get("/student").get_data(as_text=True)
    assert '<span class="welcome-emoji" aria-hidden="true">🦄</span>' in html
    assert 'class="logo"><span>English Fun</span>' in html
    import sqlite3
    con = sqlite3.connect(database.DB_PATH)
    sid = con.execute("SELECT id FROM students WHERE username='masha'").fetchone()[0]
    con.close()
    assert "Аватарка" in parent.get(f"/parent/students/{sid}").get_data(as_text=True)
    r = parent.post(f"/parent/students/{sid}/avatar", data={"emoji": "🐼"}, follow_redirects=True)
    assert "Аватарка сохранена" in r.get_data(as_text=True)
    assert "🐼</span>" in c.get("/student").get_data(as_text=True)
    r = parent.post(f"/parent/students/{sid}/avatar", data={"emoji": "💣"}, follow_redirects=True)
    assert "Выберите аватарку" in r.get_data(as_text=True)
