# -*- coding: utf-8 -*-
"""PWA: манифест, service worker, офлайн-страница, иконки, локальные шрифты."""
import json
import re
import struct
from pathlib import Path

from tools import fetch_fonts
from tests.helpers import N

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"


def png_size(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def test_manifest_is_valid_and_installable(anon):
    r = anon.get("/manifest.webmanifest")
    assert r.status_code == 200 and r.mimetype == "application/manifest+json"
    m = json.loads(r.get_data(as_text=True))
    assert m["display"] == "standalone" and m["start_url"] == "/" and m["scope"] == "/"
    assert m["name"] and m["short_name"] and m["lang"] == "ru"
    assert re.fullmatch(r"#[0-9a-fA-F]{6}", m["theme_color"])
    sizes = {(i["sizes"], i["purpose"]) for i in m["icons"]}
    assert ("192x192", "any") in sizes and ("512x512", "any") in sizes and ("512x512", "maskable") in sizes


def test_manifest_icons_exist_with_declared_size(anon):
    m = json.loads(anon.get("/manifest.webmanifest").get_data(as_text=True))
    for icon in m["icons"]:
        assert icon["src"].startswith("/static/")
        path = ROOT / icon["src"].lstrip("/")
        w, h = png_size(path)
        assert f"{w}x{h}" == icon["sizes"], icon
        assert anon.get(icon["src"]).status_code == 200
    assert png_size(STATIC / "icons" / "apple-touch-icon.png") == (180, 180)


def test_service_worker_served_from_root_and_not_cached(anon):
    r = anon.get("/sw.js")
    assert r.status_code == 200 and "javascript" in r.mimetype
    assert r.headers["Cache-Control"] == "no-cache" and r.headers["Service-Worker-Allowed"] == "/"
    body = r.get_data(as_text=True)
    assert "__VERSION__" not in body and "__PRECACHE__" not in body
    precache = json.loads(re.search(r"const PRECACHE = (\[.*?\]);", body, re.S).group(1))
    assert "/static/style.css" in precache and "/static/pwa.js" in precache
    assert not any(u.endswith("sw.js") for u in precache)
    for url in precache:
        assert anon.get(url).status_code == 200, url


def test_service_worker_version_changes_with_static(flask_app, tmp_path, monkeypatch):
    from routes import pwa
    a = tmp_path / "a.css"; a.write_text("x")
    sw = tmp_path / "sw.js"; sw.write_text("y")
    v1 = pwa.static_version([a], sw)
    a.write_text("changed content")
    assert pwa.static_version([a], sw) != v1


def test_service_worker_never_touches_forms_or_pages():
    src = (STATIC / "sw.js").read_text(encoding="utf-8")
    assert 'req.method !== "GET"' in src          # POST (формы, вход) идут напрямую
    assert 'req.mode === "navigate"' in src and "OFFLINE_URL" in src
    # HTML-страницы не кладутся в кэш: в них личные данные и CSRF-токены
    nav = src.split('req.mode === "navigate"')[1].split("return;")[0]
    assert "cache.put" not in nav


def test_offline_page_is_standalone(anon):
    r = anon.get("/offline")
    body = r.get_data(as_text=True)
    assert r.status_code == 200 and "Нет интернета" in body
    assert "/static/" not in body and "{{" not in body          # работает без сервера


def test_pages_link_manifest_and_icons(anon):
    body = anon.get("/").get_data(as_text=True)
    assert 'rel="manifest" href="/manifest.webmanifest"' in body
    assert "apple-touch-icon" in body and 'name="theme-color"' in body
    assert "viewport-fit=cover" in body and "pwa.js" in body


def test_no_external_font_servers(anon):
    body = anon.get("/").get_data(as_text=True)
    assert "googleapis" not in body and "gstatic" not in body
    assert "googleapis" not in (STATIC / "style.css").read_text(encoding="utf-8")


def test_font_css_references_existing_files():
    css = (STATIC / "fonts.css").read_text(encoding="utf-8")
    for rel in re.findall(r"url\(([^)]+\.woff2)\)", css):
        assert (STATIC / rel).is_file(), rel


SAMPLE = """
/* cyrillic-ext */
@font-face { font-family: 'Nunito'; font-style: normal; font-weight: 200 1000; font-display: swap;
  src: url(https://fonts.gstatic.com/s/nunito/v26/aaa.woff2) format('woff2'); unicode-range: U+0460-052F; }
/* cyrillic */
@font-face { font-family: 'Nunito'; font-style: normal; font-weight: 200 1000; font-display: swap;
  src: url(https://fonts.gstatic.com/s/nunito/v26/bbb.woff2) format('woff2'); unicode-range: U+0301, U+0400-045F; }
/* latin */
@font-face { font-family: 'Nunito'; font-style: normal; font-weight: 200 1000; font-display: swap;
  src: url(https://fonts.gstatic.com/s/nunito/v26/ccc.woff2) format('woff2'); unicode-range: U+0000-00FF; }
"""


def test_fetch_fonts_keeps_only_cyrillic_and_latin():
    css, files = fetch_fonts.convert(SAMPLE, lambda url: url.encode())
    assert sorted(files) == ["nunito-cyrillic-200-1000.woff2", "nunito-latin-200-1000.woff2"]
    assert "googleapis" not in css and "gstatic" not in css
    assert css.count("@font-face") == 2 and "url(fonts/nunito-cyrillic-200-1000.woff2)" in css
    assert "unicode-range: U+0301" in css


def test_mobile_assets_wired(anon):
    body = anon.get("/").get_data(as_text=True)
    assert "mobile.js" in body and (STATIC / "mobile.js").is_file()
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    assert "touch-action: none" in css and "@media (max-width: 640px)" in css


def test_lesson_uses_pointer_events_not_html5_drag(parent, make_student):
    student = make_student()
    parent.post("/parent/students/1/credit", data={"upto": "2", "action": "add"})
    html = student.get(f"/lesson/{N(3)}").get_data(as_text=True)
    assert "pointerdown" in html and "setPointerCapture" in html
    assert "addEventListener('dragstart', e => {\n      dragged" not in html
