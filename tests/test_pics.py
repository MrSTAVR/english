# -*- coding: utf-8 -*-
"""Свои рисунки к словам без подходящего эмодзи (static/pics)."""
from pathlib import Path

from data.emoji import DRAWN, emoji_for
from template_filters import pic_html

PICS = Path(__file__).resolve().parent.parent / "static" / "pics"


def test_drawn_pictures_exist_and_are_used():
    for w in DRAWN:
        assert (PICS / f"{w}.svg").is_file(), w
        assert emoji_for(w) == "@" + w
    assert emoji_for("Table") == "@table" and emoji_for("chair") == "🪑"


def test_pic_filter():
    assert pic_html("@table") == '<img class="pic-img" src="/static/pics/table.svg" alt="">'
    assert pic_html("🍕") == "🍕" and pic_html("") == ""
    assert "<" not in str(pic_html("<b>"))


def test_lesson_word_has_drawn_picture(parent, make_student):
    c = make_student()
    from curriculum import LESSONS_BY_ID
    lid = next(i for i, l in LESSONS_BY_ID.items() if any(w["en"].lower() == "table" for w in l["material"]))
    parent.post("/parent/students/1/credit", data={"upto": "60", "action": "add"})
    html = c.get(f"/lesson/{lid}").get_data(as_text=True)
    assert '"pic": "@table"' in html or '"pic":"@table"' in html
    assert "window.picHtml" in html
