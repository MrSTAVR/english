# -*- coding: utf-8 -*-
"""Рисует иконки приложения (цыплёнок на фиолетовом фоне). Запуск: python tools/make_icons.py
Нужен Pillow: pip install pillow (только для генерации, на сервере не нужен)."""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "static" / "icons"
S = 1024  # рисуем крупно, потом уменьшаем (сглаживание)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw():
    img = Image.new("RGB", (S, S))
    px = img.load()
    top, bot = (146, 118, 255), (90, 63, 214)       # --primary → --primary-dark
    for y in range(S):
        c = lerp(top, bot, y / (S - 1))
        for x in range(S):
            px[x, y] = c
    d = ImageDraw.Draw(img)
    cx, cy = S // 2, S // 2 + 30
    # тень
    d.ellipse((cx - 250, cy + 215, cx + 250, cy + 275), fill=(70, 48, 180))
    # лапки
    for dx in (-80, 80):
        d.rectangle((cx + dx - 12, cy + 190, cx + dx + 12, cy + 240), fill=(255, 150, 60))
        d.polygon([(cx + dx - 45, cy + 250), (cx + dx + 45, cy + 250), (cx + dx, cy + 225)],
                  fill=(255, 150, 60))
    # тело и голова — один «колобок»
    d.ellipse((cx - 250, cy - 230, cx + 250, cy + 230), fill=(255, 201, 60))
    d.ellipse((cx - 205, cy - 195, cx + 205, cy + 195), fill=(255, 214, 102))   # светлее в центре
    # хохолок
    for dx, h in ((-30, 95), (10, 125), (50, 90)):
        d.ellipse((cx + dx - 26, cy - 230 - h + 40, cx + dx + 26, cy - 215 + 40), fill=(255, 201, 60))
    # крылышки
    d.ellipse((cx - 255, cy - 20, cx - 130, cy + 130), fill=(255, 183, 40))
    d.ellipse((cx + 130, cy - 20, cx + 255, cy + 130), fill=(255, 183, 40))
    # глаза
    for dx in (-85, 85):
        d.ellipse((cx + dx - 34, cy - 85, cx + dx + 34, cy - 10), fill=(36, 29, 71))
        d.ellipse((cx + dx - 6, cy - 72, cx + dx + 16, cy - 48), fill=(255, 255, 255))
    # щёчки
    for dx in (-150, 150):
        d.ellipse((cx + dx - 38, cy + 0, cx + dx + 38, cy + 50), fill=(255, 122, 182))
    # клюв
    d.polygon([(cx - 55, cy + 5), (cx + 55, cy + 5), (cx, cy + 75)], fill=(255, 130, 40))
    d.polygon([(cx - 55, cy + 5), (cx + 55, cy + 5), (cx, cy + 32)], fill=(255, 160, 60))
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src = draw()
    for name, size in (("icon-192.png", 192), ("icon-512.png", 512), ("maskable-512.png", 512),
                       ("apple-touch-icon.png", 180), ("favicon-32.png", 32)):
        src.resize((size, size), Image.LANCZOS).save(OUT / name, optimize=True)
    print("Иконки записаны в", OUT)


if __name__ == "__main__":
    main()
