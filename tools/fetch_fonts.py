# -*- coding: utf-8 -*-
"""Скачивает шрифт Nunito с Google Fonts в проект, чтобы сайт не зависел от внешних серверов
(и работал офлайн в PWA). Запускается один раз: python tools/fetch_fonts.py
Создаёт static/fonts/*.woff2 и static/fonts.css (только кириллица и латиница)."""
import re
import urllib.request
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"
CSS_URL = "https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;800;900&display=swap"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
WANT = ("cyrillic", "latin")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def convert(css, fetch):
    """Разбирает CSS Google Fonts. Возвращает (новый css, {имя файла: байты})."""
    blocks = re.findall(r"/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{.*?\})", css, flags=re.S)
    result, files, done = [], {}, {}
    for subset, block in blocks:
        if subset not in WANT:
            continue
        url = re.search(r"url\((https://[^)]+)\)", block).group(1)
        weight = re.search(r"font-weight:\s*([^;]+);", block).group(1).strip()
        name = f"nunito-{subset}-{weight.replace(' ', '-')}.woff2"
        if url not in done:
            files[name] = fetch(url)
            done[url] = name
        result.append(block.replace(url, f"fonts/{done[url]}"))
    header = "/* Nunito (SIL OFL), скачан tools/fetch_fonts.py */\n"
    return header + "\n".join(result) + "\n", files


def main():
    css, files = convert(get(CSS_URL).decode("utf-8"), get)
    if not files:
        raise SystemExit("Не удалось разобрать CSS Google Fonts")
    out_dir = STATIC / "fonts"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (out_dir / name).write_bytes(data)
        print("скачан", name)
    (STATIC / "fonts.css").write_text(css, encoding="utf-8")
    print("Готово: static/fonts.css")


if __name__ == "__main__":
    main()
