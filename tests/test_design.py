# -*- coding: utf-8 -*-
"""Дизайн 3.0: файл стилей подключён, логопедическая часть в своём стиле, шрифты локальные, у Чик-чика один клюв."""
import re
from pathlib import Path

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
    c = make_student()
    body = c.get("/student").get_data(as_text=True)
    assert 'class="has-tabbar"' in body and 'class="tabbar"' in body
    for label in ("Главная", "Карта", "Сад", "Домик", "Награды"):
        assert f"<span>{label}</span>" in body
    assert 'class="tab on" aria-current="page"' in body
    garden = c.get("/student/garden").get_data(as_text=True)
    assert 'href="/student/garden" class="tab on"' in garden
    lesson = c.get("/lesson/1").get_data(as_text=True)          # в уроке нижнего меню нет
    assert 'class="has-tabbar"' not in lesson


def test_lesson_test_has_progress_bar(make_student):
    c = make_student()
    html = c.get("/lesson/1").get_data(as_text=True)
    assert 'id="test-progress"' in html and "function unansweredQuestions()" in html
    assert html.count("unansweredQuestions()") >= 3          # и полоска, и проверка перед отправкой


def test_house_has_tabs(make_student):
    html = make_student().get("/student/house").get_data(as_text=True)
    assert 'id="hs-tabs"' in html and 'data-slot="wall"' in html and 'data-slot="floor"' in html
