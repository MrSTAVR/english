# -*- coding: utf-8 -*-
"""SVG-медали для ачивок (дизайн 3.0): плоские цвета палитры макета, внутри — контурный значок
категории из спрайта base.html (#o-*). Форма и цвета зависят от уровня награды."""

import itertools
import math

from markupsafe import Markup

# ring — обод, edge — его контур, face — середина, ink — значок, ribbon — ленточки
TIERS = {
    "bronze": {"name": "Бронзовая", "ring": "#9A3B00", "edge": "#9A3B00", "face": "#FFE9D6", "ink": "#9A3B00", "ribbon": "#2563C9"},
    "silver": {"name": "Серебряная", "ring": "#5E6478", "edge": "#5E6478", "face": "#E3EDFC", "ink": "#1E4FA8", "ribbon": "#2563C9"},
    "gold": {"name": "Золотая", "ring": "#FFC83D", "edge": "#D99A00", "face": "#FFEFC2", "ink": "#8A5A00", "ribbon": "#2563C9"},
    "legend": {"name": "Легендарная", "ring": "#2563C9", "edge": "#173F87", "face": "#FFC83D", "ink": "#173F87", "ribbon": "#FFC83D"},
}
TIER_ORDER = ["bronze", "silver", "gold", "legend"]
LOCKED = {"ring": "#FFF3D9", "edge": "#E3CFA4", "face": "#FFF3D9", "ink": "#B3A27F", "ribbon": "#E3CFA4"}

# Значок медали — по категории ачивки (контурные иконки спрайта)
CAT_ICONS = {"lessons": "book", "tests": "check", "answers": "flame", "words": "abc", "time": "clock",
             "grit": "mountain", "speak": "mic", "review": "repeat", "goals": "target", "games": "game",
             "garden": "sprout", "special": "gift"}

_uid = itertools.count(1)


def _star_points(cx, cy, r_out, r_in, n):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = -math.pi / 2 + i * math.pi / n
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    return " ".join(pts)


def icon_for(a):
    return CAT_ICONS.get(a.get("cat"), "medal")


def badge_svg(icon="medal", tier="bronze", locked=False):
    """Возвращает <svg> медали (viewBox 0 0 100 112). icon — имя значка спрайта без «o-»."""
    c = LOCKED if locked else TIERS.get(tier, TIERS["bronze"])
    clip = f"c{next(_uid)}"
    dy = 4                                                       # «объёмная» тень снизу, как у карточек
    if locked or tier in ("bronze", "silver"):
        shape = '<circle cx="50" cy="{y}" r="42" fill="{f}"{s}/>'
    elif tier == "gold":
        shape = f'<polygon points="{_star_points(50, 50, 46, 40, 20)}" transform="translate(0 {{d}})" fill="{{f}}"{{s}}/>'
    else:
        shape = f'<polygon points="{_star_points(50, 50, 48, 38, 12)}" transform="translate(0 {{d}})" fill="{{f}}"{{s}}/>'
    dash = ' stroke-dasharray="5 4"' if locked else ""
    edge = f' stroke="{c["edge"]}" stroke-width="2.5" stroke-linejoin="round"{dash}'
    out = ['<svg class="medal-svg" viewBox="0 0 100 112" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">',
           f'<defs><clipPath id="{clip}"><circle cx="50" cy="50" r="31"/></clipPath></defs>',
           # ленточки
           f'<path d="M34 76 L26 108 L38 101 L46 110 L50 84Z" fill="{c["ribbon"]}"/>'
           f'<path d="M66 76 L74 108 L62 101 L54 110 L50 84Z" fill="{c["ribbon"]}"/>']
    if not locked:
        out.append(shape.format(y=50 + dy, d=dy, f="rgba(30,42,69,.18)", s=""))
    out.append(shape.format(y=50, d=0, f=c["ring"], s=edge))
    out.append(f'<circle cx="50" cy="50" r="31" fill="{c["face"]}" stroke="{c["edge"]}" stroke-width="2"/>')
    name = "lock" if locked else icon
    out.append(f'<use href="#o-{name}" x="31" y="31" width="38" height="38" color="{c["ink"]}" style="color:{c["ink"]}"/>')
    if not locked:
        out.append(f'<g clip-path="url(#{clip})"><rect class="m-shine" x="-60" y="10" width="20" height="90" '
                   f'fill="rgba(255,255,255,.55)" transform="rotate(25 50 50)"/></g>')
    out.append("</svg>")
    return "".join(out)


def medal(a, size=None, locked=None):
    """Фильтр шаблона: HTML медали для ачивки (словарь каталога + 'earned')."""
    if locked is None:
        locked = not a.get("earned", True)
    tier = a.get("tier", "bronze")
    style = f' style="--s:{int(size)}px"' if size else ""
    cls = f"medal tier-{tier}{' is-locked' if locked else ''}"
    return Markup(f'<span class="{cls}"{style}>{badge_svg(icon_for(a), tier, locked)}</span>')
