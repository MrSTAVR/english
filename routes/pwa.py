# -*- coding: utf-8 -*-
"""PWA: манифест, service worker и офлайн-страница (приложение «на экране телефона»)."""
import hashlib
import json
from pathlib import Path

from flask import Blueprint, Response, current_app, render_template

bp = Blueprint("pwa", __name__)

NO_CACHE = {"Cache-Control": "no-cache"}

MANIFEST = {
    "id": "/",
    "name": "English Fun — английский для детей",
    "short_name": "English Fun",
    "description": "Уроки английского с цыплёнком Чик-чик, садом и наградами",
    "lang": "ru",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#FFF7E8",
    "theme_color": "#FFF7E8",
    "icons": [
        {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "/static/icons/maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}


def _static_files():
    """Файлы статики, которые кладём в кэш телефона заранее (без sw.js)."""
    root = Path(current_app.static_folder)
    return sorted(p for p in root.rglob("*")
                  if p.is_file() and p.name != "sw.js" and p.suffix in
                  {".css", ".js", ".png", ".woff2", ".svg"})


def static_version(files, sw_path):
    """Короткий хеш статики: меняется при любой правке — тогда телефон обновляет кэш."""
    h = hashlib.sha1()
    for p in list(files) + [sw_path]:
        st = p.stat()
        h.update(f"{p.name}:{st.st_size}:{st.st_mtime_ns}".encode())
    return h.hexdigest()[:10]


@bp.route("/.well-known/assetlinks.json")
def assetlinks():
    """Digital Asset Links для Android-приложения (TWA): сайт доверяет приложению с этим ключом подписи."""
    import config
    return Response(json.dumps([{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {"namespace": "android_app", "package_name": config.TWA_PACKAGE,
                   "sha256_cert_fingerprints": [config.TWA_SHA256]},
    }]), mimetype="application/json")


@bp.route("/manifest.webmanifest")
def manifest():
    return Response(json.dumps(MANIFEST, ensure_ascii=False), mimetype="application/manifest+json",
                    headers=NO_CACHE)


@bp.route("/sw.js")
def service_worker():
    root = Path(current_app.static_folder)
    sw_path = root / "sw.js"
    files = _static_files()
    urls = ["/static/" + p.relative_to(root).as_posix() for p in files]
    body = (sw_path.read_text(encoding="utf-8")
            .replace("__VERSION__", static_version(files, sw_path))
            .replace("__PRECACHE__", json.dumps(urls)))
    return Response(body, mimetype="application/javascript",
                    headers={**NO_CACHE, "Service-Worker-Allowed": "/"})


@bp.route("/offline")
def offline():
    return render_template("offline.html")
