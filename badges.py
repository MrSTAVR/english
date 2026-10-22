# -*- coding: utf-8 -*-
"""SVG-медали для ачивок: форма и цвета зависят от уровня награды."""

import itertools
import math

from markupsafe import Markup, escape

TIERS = {
    "bronze": {"name": "Бронзовая", "ring": ("#f4a261", "#b4621f"), "face": ("#ffe3c4", "#f6b27a"), "ribbon": ("#7c5cff", "#5a3fd6")},
    "silver": {"name": "Серебряная", "ring": ("#f1f5ff", "#98a5c2"), "face": ("#ffffff", "#dde5f6"), "ribbon": ("#7c5cff", "#5a3fd6")},
    "gold": {"name": "Золотая", "ring": ("#fff0a0", "#e5a600"), "face": ("#fff8d6", "#ffd54f"), "ribbon": ("#ff7ab6", "#d6407f")},
    "legend": {"name": "Легендарная", "ring": ("#ff7ab6", "#7c5cff"), "face": ("#ffffff", "#efe6ff"), "ribbon": ("#ff7ab6", "#7c5cff")},
}
TIER_ORDER = ["bronze", "silver", "gold", "legend"]

_uid = itertools.count(1)


def _star_points(cx, cy, r_out, r_in, n):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = -math.pi / 2 + i * math.pi / n
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    return " ".join(pts)


def badge_svg(emoji, tier="bronze", locked=False):
    """Возвращает <svg> медали (viewBox 0 0 100 112). Градиенты у каждой медали свои."""
    t = TIERS.get(tier, TIERS["bronze"])
    u = next(_uid)
    g_ring, g_face, g_rib, clip = f"r{u}", f"f{u}", f"b{u}", f"c{u}"
    if locked:
        ring, face, rib = ("#e4e0f0", "#b9b3cf"), ("#f3f1f8", "#dcd8ea"), ("#cfcade", "#b9b3cf")
    else:
        ring, face, rib = t["ring"], t["face"], t["ribbon"]
    ring_stops = (f'<stop offset="0" stop-color="{ring[0]}"/><stop offset="1" stop-color="{ring[1]}"/>'
                  if tier != "legend" or locked else
                  '<stop offset="0" stop-color="#ff7ab6"/><stop offset=".35" stop-color="#ffd54f"/>'
                  '<stop offset=".65" stop-color="#6fe3b0"/><stop offset="1" stop-color="#7c5cff"/>')
    out = ['<svg class="medal-svg" viewBox="0 0 100 112" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">',
           f'<defs><linearGradient id="{g_ring}" x1="0" y1="0" x2="1" y2="1">{ring_stops}</linearGradient>'
           f'<linearGradient id="{g_face}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{face[0]}"/>'
           f'<stop offset="1" stop-color="{face[1]}"/></linearGradient>'
           f'<linearGradient id="{g_rib}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{rib[0]}"/>'
           f'<stop offset="1" stop-color="{rib[1]}"/></linearGradient>'
           f'<clipPath id="{clip}"><circle cx="50" cy="50" r="33"/></clipPath></defs>']
    # ленточки
    out.append(f'<path d="M34 78 L26 108 L38 101 L46 110 L50 84Z" fill="url(#{g_rib})"/>'
               f'<path d="M66 78 L74 108 L62 101 L54 110 L50 84Z" fill="url(#{g_rib})"/>')
    # фигура медали
    if tier == "legend" and not locked:
        out.append(f'<polygon points="{_star_points(50, 50, 48, 40, 14)}" fill="url(#{g_ring})"/>')
    elif tier == "gold" and not locked:
        out.append(f'<polygon points="{_star_points(50, 50, 46, 41, 24)}" fill="url(#{g_ring})"/>')
    else:
        out.append(f'<circle cx="50" cy="50" r="42" fill="url(#{g_ring})"/>')
    dash = ' stroke-dasharray="4 4"' if locked else ""
    out.append(f'<circle cx="50" cy="50" r="35" fill="url(#{g_face})" stroke="rgba(0,0,0,.12)" stroke-width="2"{dash}/>')
    out.append('<circle cx="50" cy="50" r="30" fill="none" stroke="rgba(255,255,255,.55)" stroke-width="1.5"/>')
    if locked:
        out.append('<text class="m-emoji" x="50" y="63" text-anchor="middle" font-size="34" font-weight="900" '
                   'fill="#b3adcc" font-family="Nunito,sans-serif">?</text>')
    else:
        out.append(f'<text class="m-emoji" x="50" y="62" text-anchor="middle" font-size="34">{escape(emoji)}</text>')
        out.append(f'<g clip-path="url(#{clip})"><rect class="m-shine" x="-60" y="10" width="26" height="90" '
                   f'fill="rgba(255,255,255,.65)" transform="rotate(25 50 50)"/></g>')
    out.append("</svg>")
    return "".join(out)


def medal(a, size=None, locked=None):
    """Фильтр шаблона: HTML медали для ачивки (словарь каталога + 'earned')."""
    if locked is None:
        locked = not a.get("earned", True)
    tier = a.get("tier", "bronze")
    style = f' style="--s:{int(size)}px"' if size else ""
    cls = f"medal tier-{tier}{' is-locked' if locked else ''}"
    return Markup(f'<span class="{cls}"{style}>{badge_svg(a["emoji"], tier, locked)}</span>')
