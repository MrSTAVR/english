# -*- coding: utf-8 -*-
"""SVG-сцена сада: дерево, 30 ежедневных находок и украшения магазина.

Чистые функции без зависимостей от Flask и БД — их легко тестировать.
  render_scene(day, active, thumb=False) -> Markup   полная сцена
  tree_mini_svg(day)                     -> Markup   маленькое дерево для главной
  FINDS                                              что появляется каждый день
"""
import math

from markupsafe import Markup

MAX_DAY = 30
BR, GA, GB, GC = "#8B5A2B", "#3FA34D", "#58BD62", "#2E8B3D"
THEME_KEYS = ("night", "sunset", "dawn")
TOP_SPAN_KEYS = ("garland", "flags", "lights")

THEMES = {
    "day": dict(sky="#BDE7FB", h1="#A5D98B", h2="#8CCB74", g1="#7CC565", g2="#6FBB59",
                sun=(70, 62, "#FFD54F"), cloud="#FFFFFF", tint=None),
    "night": dict(sky="#1B2A5E", h1="#3C7A5A", h2="#336B4E", g1="#3B7A57", g2="#33684A",
                  sun=None, cloud="#C9D3F0", tint=("#0B1740", 0.28)),
    "sunset": dict(sky="#FFB56B", h1="#B7CF7E", h2="#9FBF6C", g1="#92B861", g2="#85AB57",
                   sun=(70, 108, "#FF8A3D"), cloud="#FFE9CC", tint=("#FF7043", 0.10)),
    "dawn": dict(sky="#F6C6E0", h1="#B5DB93", h2="#9CCB7D", g1="#86C46C", g2="#79B960",
                 sun=(70, 118, "#FFE082"), cloud="#FFF3F8", tint=("#CE93D8", 0.10)),
}


# ---------------------------------------------------------------- примитивы
def f(v):
    s = ("%.1f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def E(x, y, rx, ry, c, extra=""):
    return (f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(rx)}" ry="{f(ry)}" fill="{c}"'
            + (f" {extra}" if extra else "") + "/>")


def C(x, y, r, c, extra=""):
    return f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{c}"' + (f" {extra}" if extra else "") + "/>"


def R(x, y, w, h, c, rx=0):
    return (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{c}"'
            + (f' rx="{f(rx)}"' if rx else "") + "/>")


def poly(pts, c, extra=""):
    d = "L".join(f"{f(px)} {f(py)}" for px, py in pts)
    return f'<path d="M{d}Z" fill="{c}"' + (f" {extra}" if extra else "") + "/>"


def line(d, stroke, w=1, extra="", cap="round"):
    return (f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{f(w)}" stroke-linecap="{cap}"'
            + (f" {extra}" if extra else "") + "/>")


# ---------------------------------------------------------------- дерево
PTS = [(-.5, -.3), (.45, -.5), (0, .25), (.62, .12), (-.2, -.72),
       (-.66, .2), (.2, -.12), (.5, -.2), (-.4, .45), (.1, -.62)]


def growth(d):
    """Доля роста 0..1: быстро в начале, плавно дальше (+ немного линейной части)."""
    e = (1 - math.exp(-d / 8)) / (1 - math.exp(-MAX_DAY / 8))
    return .65 * e + .35 * d / MAX_DAY


def _leaf(x, y, rot, c, s):
    return E(x, y, 9 * s, 4.5 * s, c, f'transform="rotate({rot} {f(x)} {f(y)})"')


def tree(x, y, d, s):
    """Дерево на d-й день роста. Возвращает (svg, crown) — crown=(cx, cy, r) или None."""
    if d <= 0:
        return E(x, y, 18 * s, 5 * s, "#6b4423") + E(x, y - 6 * s, 5 * s, 7 * s, "#C08A45"), None
    g = growth(d)
    th, tw = (10 + 160 * g) * s, (3 + 12.5 * g) * s
    o = E(x, y, tw * 2.4, tw * .55, "#5aa84a")
    o += R(x - tw / 2, y - th, tw, th, "#4CAF50" if d < 3 else BR, tw / 2)
    if d < 3:
        ly = y - th + 3
        o += _leaf(x - 9 * s, ly, -25, GB, s) + _leaf(x + 9 * s, ly, 25, GA, s)
        if d >= 2:
            o += _leaf(x - 8 * s, y - th * .5, -20, GA, s * .9) + _leaf(x + 8 * s, y - th * .5, 20, GB, s * .9)
        return o, (x, ly - 6, 10)
    cr = (9 + 76 * g) * s
    cy = y - th - cr * .35
    n, cols = min(8, 2 + d // 3), (GC, GA, GB)
    for i in range(n):
        px, py = PTS[i]
        o += C(x + px * cr, cy + py * cr, cr * (.6 + (i % 3) * .08), cols[i % 3])
    o += C(x, cy, cr * .82, GA)
    if d >= 8:
        for i in range(min(10, d - 7)):
            px, py = PTS[i]
            o += C(x + px * cr * .85, cy + py * cr * .85, 2.8 * s + 1, "#FF8FB3")
    if d >= 20:
        for i in range(min(9, d - 19)):
            px, py = PTS[(i + 4) % 10]
            fx, fy = x + px * cr * .75, cy + py * cr * .75 + 4
            o += C(fx, fy, 3.6 * s + 1, "#E53935") + C(fx - 1, fy - 1, 1, "#fff")
    return o, (x, cy, cr)


# ---------------------------------------------------------------- находки дня
def tuft(x, y):
    return poly([(x - 6, y), (x - 3, y - 9), (x, y), (x + 3, y - 11), (x + 6, y)], "#4a9d3f")


def tulip(x, y):
    cup = (f'<path d="M{f(x-6)} {f(y-24)}Q{f(x-6)} {f(y-11)} {f(x)} {f(y-11)}Q{f(x+6)} {f(y-11)} '
           f'{f(x+6)} {f(y-24)}L{f(x+3)} {f(y-18)}L{f(x)} {f(y-25)}L{f(x-3)} {f(y-18)}Z" fill="#E53935"/>')
    return R(x - 1, y - 12, 2, 12, "#3a8a3a") + cup


def butterfly(x, y, a, b):
    return ('<g class="g-fl">' + E(x - 6, y - 3, 7, 5, a) + E(x + 6, y - 3, 7, 5, a)
            + E(x - 5, y + 4, 5, 4, b) + E(x + 5, y + 4, 5, 4, b) + R(x - 1, y - 6, 2, 14, "#4E342E", 1) + "</g>")


def shroom(x, y):
    cap = f'<path d="M{f(x-11)} {f(y-9)}A11 10 0 0 1 {f(x+11)} {f(y-9)}Z" fill="#E53935"/>'
    return R(x - 3, y - 10, 6, 10, "#F5E9D3", 2) + cap + C(x - 4, y - 14, 2, "#fff") + C(x + 4, y - 13, 2, "#fff")


def bunny(x, y):
    return (E(x - 1, y - 10, 13, 10, "#fff") + C(x - 14, y - 9, 4, "#fff") + E(x + 9, y - 27, 3, 9, "#fff")
            + E(x + 15, y - 26, 3, 8, "#fff") + E(x + 9, y - 27, 1.3, 6, "#F8BBD0") + C(x + 11, y - 19, 8, "#fff")
            + C(x + 14, y - 20, 1.5, "#333") + C(x + 18, y - 17, 1.5, "#F48FB1"))


def bee(x, y):
    return ('<g class="g-fl" style="animation-delay:-1s">' + E(x, y - 6, 8, 5, "#B3E5FC", 'opacity=".8"')
            + E(x, y, 8, 5.5, "#FFC107") + R(x - 2, y - 5, 2.5, 10, "#333") + R(x + 3, y - 4, 2.5, 8, "#333") + "</g>")


def daisy(x, y):
    o = ""
    for i in range(6):
        a = i * math.pi / 3
        o += C(x + math.cos(a) * 5, y + math.sin(a) * 5, 3.2, "#fff")
    return R(x - 1, y, 2, 12, "#3a8a3a") + o + C(x, y, 3, "#FFC107")


def ladybug(x, y):
    return C(x, y, 6, "#E53935") + C(x - 6, y, 3, "#222") + C(x - 1, y - 2, 1.3, "#222") + C(x + 2, y + 2, 1.3, "#222")


def cloud(x, y, c="#fff"):
    return E(x, y, 26, 11, c) + E(x + 18, y + 3, 20, 9, c) + E(x - 18, y + 4, 18, 8, c)


def chick(x, y):
    return (C(x, y - 8, 9, "#FFD54F") + C(x + 7, y - 15, 6, "#FFD54F")
            + poly([(x + 12, y - 15), (x + 18, y - 13), (x + 12, y - 12)], "#FB8C00") + C(x + 9, y - 16, 1.2, "#333")
            + R(x - 3, y - 1, 1.5, 5, "#FB8C00") + R(x + 2, y - 1, 1.5, 5, "#FB8C00"))


def sunflower(x, y):
    o = R(x - 1.5, y, 3, 40, "#3a8a3a") + E(x + 8, y + 24, 8, 3.5, GB, f'transform="rotate(-20 {f(x+8)} {f(y+24)})"')
    for i in range(12):
        a = i * math.pi / 6
        px, py = x + math.cos(a) * 10, y + math.sin(a) * 10
        o += E(px, py, 5, 2.6, "#FFC107", f'transform="rotate({i*30} {f(px)} {f(py)})"')
    return o + C(x, y, 7, "#6D4C41")


def squirrel(x, y):
    return (E(x + 12, y - 14, 7, 13, "#C98A4B", f'transform="rotate(20 {f(x+12)} {f(y-14)})"')
            + E(x, y - 8, 9, 8, "#B8733A") + C(x - 6, y - 17, 6, "#B8733A") + C(x - 9, y - 23, 2.5, "#B8733A")
            + C(x - 8, y - 18, 1.2, "#222"))


def pond(x, y):
    return E(x, y, 80, 15, "#5DB9E8") + E(x - 12, y - 3, 50, 7, "#86CFF3")


def duck(x, y):
    return (E(x, y - 5, 10, 6, "#FFD54F") + C(x + 8, y - 13, 6, "#FFD54F")
            + poly([(x + 13, y - 13), (x + 19, y - 11), (x + 13, y - 10)], "#FB8C00") + C(x + 10, y - 14, 1.2, "#333"))


def frog(x, y):
    return (E(x, y, 15, 5, "#2E8B3D") + E(x, y - 6, 8, 6, "#7CB342") + C(x - 4, y - 12, 3, "#7CB342")
            + C(x + 4, y - 12, 3, "#7CB342") + C(x - 4, y - 12, 1.2, "#222") + C(x + 4, y - 12, 1.2, "#222"))


def house(x, y):
    return (R(x - 18, y - 22, 36, 22, "#FFF3E0") + poly([(x - 23, y - 22), (x, y - 42), (x + 23, y - 22)], "#D84315")
            + R(x - 4, y - 13, 8, 13, "#6D4C41") + R(x + 8, y - 18, 7, 7, "#81D4FA") + R(x + 11, y - 48, 5, 12, "#8D6E63"))


def rainbow():
    o = ""
    for i, c in enumerate(("#E53935", "#FB8C00", "#FDD835", "#43A047", "#1E88E5", "#8E24AA")):
        r = 215 - i * 9
        o += line(f"M{340-r} 262A{r} {r} 0 0 1 {340+r} 262", c, 9, cap="butt")
    return o


def bench(x, y):
    return (R(x - 20, y - 18, 40, 4, "#A1665A", 1) + R(x - 20, y - 10, 40, 5, "#C0806C", 1)
            + R(x - 17, y - 5, 3, 9, "#6D4C41") + R(x + 14, y - 5, 3, 9, "#6D4C41"))


def back_fence():
    o = R(0, 270, 680, 3, "#C9A06A") + R(0, 278, 680, 3, "#C9A06A")
    for x in range(6, 680, 30):
        o += R(x, 262, 7, 26, "#D7B07A", 2)
    return o


def balloons():
    o = ""
    for bx, by, col in ((600, 115, "#E53935"), (618, 100, "#FDD835"), (636, 118, "#1E88E5")):
        o += line(f"M{bx} {by+14}Q{bx-3} {by+50} 618 168", "#777", 1) + E(bx, by, 10, 13, col)
    return o


def hedgehog(x, y):
    o = E(x, y - 7, 14, 9, "#6D4C41")
    for i in range(7):
        o += poly([(x - 13 + i * 4, y - 12), (x - 11 + i * 4, y - 22), (x - 9 + i * 4, y - 12)], "#4E342E")
    return o + E(x - 13, y - 4, 6, 4, "#E0B88A") + C(x - 17, y - 4, 1.6, "#222")


def bird(crown):
    if not crown:
        return ""
    x, y = crown[0] + crown[2] * .6, crown[1] - crown[2] * .78
    return (E(x, y, 8, 6, "#42A5F5") + C(x - 7, y - 4, 4.5, "#42A5F5")
            + poly([(x - 11, y - 4), (x - 16, y - 3), (x - 11, y - 2)], "#FB8C00") + C(x - 8, y - 5, 1, "#222")
            + poly([(x + 7, y), (x + 15, y + 4), (x + 6, y + 4)], "#1E88E5"))


def _star_shape(px, py, k, c, extra=""):
    return poly([(px, py - k), (px + k / 3, py - k / 3), (px + k, py), (px + k / 3, py + k / 3), (px, py + k),
                 (px - k / 3, py + k / 3), (px - k, py), (px - k / 3, py - k / 3)], c, extra)


def small_stars():
    pts = [(60, 50), (160, 90), (250, 40), (420, 60), (500, 110), (560, 45), (620, 85), (110, 200), (560, 215), (300, 150)]
    return "".join(_star_shape(px, py, 6, "#FFE57F", f'class="g-tw" style="animation-delay:-{f(i*.3)}s"')
                   for i, (px, py) in enumerate(pts)).replace("-0s", "0s")


def gold_crown(crown):
    if not crown:
        return ""
    cx, cy, cr = crown
    top = cy - cr
    d = poly([(cx - 14, top + 4), (cx - 14, top - 12), (cx - 7, top - 4), (cx, top - 16), (cx + 7, top - 4),
              (cx + 14, top - 12), (cx + 14, top + 4)], "#FFC107", 'stroke="#E69F00" stroke-width="1"')
    return d + _star_shape(cx, top - 26, 5, "#FFF59D", 'class="g-tw"')


def _F(day, title, c=None, layer=None, y=None, draw=None):
    return {"day": day, "title": title, "c": c, "layer": layer, "y": y, "draw": draw}


FINDS = [
    _F(1, "Проклюнулся росток"),
    _F(2, "Выросла травка", (330, 335), "ground", 340,
       lambda cr: "".join(tuft(x, 336 + i % 3 * 10) for i, x in enumerate((60, 115, 195, 265, 420, 500, 560, 625)))),
    _F(3, "Расцвёл первый тюльпан", (250, 305), "ground", 320, lambda cr: tulip(250, 320)),
    _F(4, "Прилетела бабочка", (395, 200), "air", None, lambda cr: butterfly(395, 205, "#F48FB1", "#BA68C8")),
    _F(5, "Выросло второе деревце!", (150, 250)),
    _F(6, "Появился грибочек", (470, 320), "ground", 332, lambda cr: shroom(470, 332)),
    _F(7, "Неделя! Прискакал зайчик", (575, 308), "ground", 326, lambda cr: bunny(575, 326)),
    _F(8, "Прилетела пчёлка", (280, 230), "air", None, lambda cr: bee(280, 235)),
    _F(9, "Расцвели ромашки", (150, 325), "ground", 342,
       lambda cr: daisy(140, 330) + daisy(158, 336) + daisy(172, 328)),
    _F(10, "Выросло третье деревце!", (545, 250)),
    _F(11, "Приползла божья коровка", (195, 345), "ground", 350, lambda cr: ladybug(195, 350)),
    _F(12, "Набежали облачка", (520, 70), "back", None, lambda cr: cloud(520, 70)),
    _F(13, "Вылупился цыплёнок", (430, 332), "ground", 348, lambda cr: chick(430, 348)),
    _F(14, "Две недели! Подсолнухи", (95, 310), "ground", 352, lambda cr: sunflower(95, 312) + sunflower(118, 320)),
    _F(15, "Выросло четвёртое деревце!", (232, 250)),
    _F(16, "Прибежала белочка", (622, 290), "ground", 304, lambda cr: squirrel(622, 304)),
    _F(17, "Появился пруд", (340, 350), "ground", 0, lambda cr: pond(340, 352)),
    _F(18, "Приплыла уточка", (315, 342), "ground", 353, lambda cr: duck(312, 354)),
    _F(19, "Прискакала лягушка", (378, 346), "ground", 352, lambda cr: frog(378, 354)),
    _F(20, "Домик на холме", (600, 222), "far", None, lambda cr: house(600, 250)),
    _F(21, "Три недели! Радуга", (340, 110), "back", None, lambda cr: rainbow()),
    _F(22, "Выросло пятое деревце!", (462, 248)),
    _F(23, "Птичка села на дерево", None, "air", None, bird),
    _F(24, "Поставили скамейку", (410, 305), "ground", 322, lambda cr: bench(410, 322)),
    _F(25, "Построили заборчик", (330, 272), "fence", None, lambda cr: back_fence()),
    _F(26, "Улетели шарики", (618, 115), "air", None, lambda cr: balloons()),
    _F(27, "Пришёл ёжик", (130, 340), "ground", 356, lambda cr: hedgehog(130, 356)),
    _F(28, "Выросло шестое деревце!", (76, 265)),
    _F(29, "Зажглись звёздочки", (300, 150), "air", None, lambda cr: small_stars()),
    _F(30, "Легендарный сад! Золотая корона", (340, 40), "air", None, gold_crown),
]
FIND_BY_DAY = {x["day"]: x for x in FINDS}

# (день рождения, x, y, масштаб) дополнительных деревьев — совпадает с garden.TREES_EVERY
EXTRA_TREES = ((5, 150, 290, .8), (10, 545, 288, .8), (15, 232, 277, .7), (22, 462, 279, .7), (28, 76, 302, .75))


# ---------------------------------------------------------------- украшения
def _sag(x, period=170, depth=11):
    return depth * math.sin(math.pi * ((x % period) / period))


def deco_sun(th):
    sx, sy, col = th["sun"]
    rays = "".join(line(f"M{f(sx+math.cos(a)*32)} {f(sy+math.sin(a)*32)}L{f(sx+math.cos(a)*44)} {f(sy+math.sin(a)*44)}",
                        col, 5) for a in (i * math.pi / 6 for i in range(12)))
    face = (C(sx, sy, 26, col) + C(sx - 9, sy - 4, 2.6, "#6b4a00") + C(sx + 9, sy - 4, 2.6, "#6b4a00")
            + line(f"M{sx-10} {sy+6}Q{sx} {sy+17} {sx+10} {sy+6}", "#8a5a00", 2.5)
            + C(sx - 16, sy + 5, 4, "#FF8A65", 'opacity=".55"') + C(sx + 16, sy + 5, 4, "#FF8A65", 'opacity=".55"'))
    return f'<g class="g-spin" style="transform-origin:{sx}px {sy}px">{rays}</g>{face}'


def deco_moon(th):
    return (C(602, 72, 36, "#FFF3B0", 'opacity=".22"') + C(602, 72, 28, "#FFF3B0")
            + C(614, 64, 24, th["sky"]) + C(588, 80, 2, "#E6D98A") + C(595, 92, 3, "#E6D98A"))


def deco_stars():
    big = [(40, 130), (130, 40), (210, 120), (380, 30), (470, 80), (540, 150), (640, 40), (90, 90), (330, 70), (600, 120)]
    o = "".join(_star_shape(px, py, 9 if i % 2 else 7, "#FFF9C4", f'class="g-tw" style="animation-delay:-{f(i*.4)}s"')
                for i, (px, py) in enumerate(big)).replace("-0s", "0s")
    shoot = '<g class="g-shoot">' + line("M0 0L-44 16", "#fff", 2.5) + C(0, 0, 3.5, "#fff") + "</g>"
    return o + shoot


def deco_clouds(th):
    c, o = th["cloud"], ""
    for i, (x, y, dur) in enumerate(((110, 44, 46), (330, 100, 60), (540, 56, 52))):
        o += (f'<g class="g-drift" style="animation-duration:{dur}s;animation-delay:-{i*9}s">'
              + E(x, y, 36, 15, c) + E(x + 24, y + 4, 28, 12, c) + E(x - 24, y + 5, 24, 10, c) + E(x + 4, y - 10, 22, 13, c) + "</g>")
    return o


def deco_plane():
    x, y = 250, 150
    banner = (poly([(x - 70, y - 12), (x - 130, y - 8), (x - 130, y), (x - 70, y - 4)], "#FDD835")
              + poly([(x - 70, y - 4), (x - 130, y), (x - 130, y + 6), (x - 70, y + 4)], "#FFFFFF")
              + poly([(x - 70, y + 4), (x - 130, y + 6), (x - 130, y + 14), (x - 70, y + 10)], "#66BB6A"))
    plane = (line(f"M{x-32} {y-4}L{x-70} {y-4}", "#777", 1) + banner + E(x, y, 26, 8, "#EF5350")
             + poly([(x - 22, y - 2), (x - 34, y - 16), (x - 27, y - 16), (x - 14, y - 3)], "#C62828")
             + E(x, y - 9, 13, 3, "#C62828") + C(x + 10, y - 3, 4, "#B3E5FC") + R(x + 26, y - 9, 2, 18, "#555"))
    return f'<g class="g-plane">{plane}</g>'


def deco_snow():
    return "".join(C((i * 53) % 680 + (i % 3) * 7, (i * 37) % 360, 2 + i % 3, "#FFFFFF",
                     f'class="g-snow" style="animation-duration:{6 + i % 5}s;animation-delay:-{f((i * .9) % 6)}s"')
                   for i in range(26)).replace("-0s", "0s")


def deco_petals():
    return "".join(E((i * 61) % 680 + 10, (i * 41) % 360, 4.2, 2.3, "#FFB7D0" if i % 2 else "#FF8FB3",
                     f'class="g-petal" style="animation-duration:{8 + i % 4}s;animation-delay:-{f((i * 1.1) % 8)}s"')
                   for i in range(20)).replace("-0s", "0s")


def deco_fireflies():
    o = ""
    for i in range(14):
        x, y = (i * 47 + 30) % 650 + 10, 235 + (i * 29) % 120
        o += (f'<g class="g-blink" style="animation-delay:-{f(i*.45)}s">'
              + C(x, y, 8, "#FFF59D", 'opacity=".3"') + C(x, y, 2.6, "#FFEB3B") + "</g>")
    return o.replace("-0s", "0s")


def deco_garland(row):
    y0, o = 8 + row * 30, ""
    o += line(f"M0 {y0}Q85 {y0+22} 170 {y0}T340 {y0}T510 {y0}T680 {y0}", "#7a5a2f", 2)
    for i in range(10):
        x = 34 + i * 68
        y = y0 + _sag(x)
        col = ("#FF6B6B", "#FFD166", "#6FD47F", "#74C0FC", "#E599F7")[i % 5]
        o += (line(f"M{x} {f(y)}L{x} {f(y+7)}", "#555", 1.5)
              + C(x, y + 12, 6, col, f'class="g-blink" style="animation-delay:-{f(i*.3)}s"'))
    return o.replace("-0s", "0s")


def deco_flags(row):
    y0, o = 6 + row * 30, ""
    o += line(f"M0 {y0}Q85 {y0+22} 170 {y0}T340 {y0}T510 {y0}T680 {y0}", "#8a5a2b", 2)
    for i in range(16):
        x = 20 + i * 41
        y = y0 + _sag(x) * .95
        col = ("#FF6B6B", "#FFD166", "#6FD47F", "#74C0FC")[i % 4]
        o += poly([(x - 10, y + 1), (x + 10, y + 1), (x, y + 21)], col,
                  f'class="g-swing" style="transform-origin:{x}px {f(y)}px;animation-delay:-{f(i*.25)}s"')
    return o.replace("-0s", "0s")


def deco_lanterns(row):
    y0, o = 4 + row * 30, ""
    o += R(0, y0, 680, 3, "#8a5a2b", 1)
    for i in range(8):
        x = 40 + i * 85
        ln = 16 + (i % 3) * 14
        col = ("#EF5350", "#FFA726", "#F06292")[i % 3]
        o += (f'<g class="g-swing" style="transform-origin:{x}px {y0}px;animation-delay:-{f(i*.5)}s">'
              + line(f"M{x} {y0+2}L{x} {y0+ln}", "#6b4a2b", 1.5) + R(x - 5, y0 + ln, 10, 4, "#6b4a2b", 1)
              + E(x, y0 + ln + 17, 11, 14, col) + E(x - 3, y0 + ln + 13, 3, 6, "#FFFFFF", 'opacity=".35"')
              + R(x - 5, y0 + ln + 30, 10, 3, "#6b4a2b", 1) + line(f"M{x} {y0+ln+33}L{x} {y0+ln+40}", "#FFD54F", 2) + "</g>")
    return o.replace("-0s", "0s")


def deco_flower_fence():
    o = R(0, 358, 680, 4, "#E1C9A0") + R(0, 368, 680, 4, "#E1C9A0")
    pastel = ("#F8BBD0", "#FFF59D", "#B2EBF2", "#C5E1A5", "#D1C4E9")
    for i, x in enumerate(range(4, 680, 26)):
        o += poly([(x, 380), (x, 350), (x + 8, 342), (x + 16, 350), (x + 16, 380)], pastel[i % 5])
        if i % 4 == 2:
            o += C(x + 8, 338, 4, "#FF8FB3") + C(x + 8, 338, 1.6, "#FFF176")
    return o


def _theme_of(active):
    for k in reversed(list(active)):
        if k in THEME_KEYS:
            return k
    return "day"


# ---------------------------------------------------------------- сцена
def render_scene(day, active=(), thumb=False):
    """Полная сцена сада для дня серии `day` (0..30) и списка ключей украшений."""
    day = max(0, min(int(day), MAX_DAY))
    active = [k for k in active]
    th = THEMES[_theme_of(active)]
    pop = (lambda fd: '<g class="g-new">' if fd["day"] == day and not thumb else "<g>")
    ring = (lambda fd: "" if thumb or fd["day"] != day or not fd["c"] or not fd["c"][0] else
            f'<circle class="g-ring" cx="{fd["c"][0]}" cy="{fd["c"][1]}" r="22" fill="none" stroke="#FFB300" stroke-width="3"/>')
    vis = [x for x in FINDS if x["day"] <= day and x["draw"]]

    # 1. дерево и его окружение
    main_svg, crown = tree(340, 300, day, 1)
    o = R(0, 0, 680, 380, th["sky"])
    if th["sun"] and "sun" not in active:
        sx, sy, scol = th["sun"]
        o += C(sx, sy, 26, scol)
    elif th["sun"]:
        o += deco_sun(th)
    o += cloud(190, 64, th["cloud"]) + cloud(430, 100, th["cloud"])
    for x in vis:
        if x["layer"] == "back":
            o += pop(x) + x["draw"](crown) + "</g>" + ring(x)
    o += (f'<path d="M0 250Q120 205 260 240T520 232T680 245L680 270L0 270Z" fill="{th["h1"]}"/>'
          f'<path d="M0 262Q170 228 340 255T680 250L680 290L0 290Z" fill="{th["h2"]}"/>')
    for x in vis:
        if x["layer"] == "far":
            o += pop(x) + x["draw"](crown) + "</g>" + ring(x)
    o += R(0, 258, 680, 122, th["g1"]) + R(0, 322, 680, 58, th["g2"])
    for x in vis:
        if x["layer"] == "fence":
            o += pop(x) + x["draw"](crown) + "</g>" + ring(x)
    if "fence" in active:
        o += deco_flower_fence()

    ground = [(300, ('<g class="g-new">' if day == 1 and not thumb else "<g>") + main_svg + "</g>")]
    for born, tx, ty, ts in EXTRA_TREES:
        if day >= born:
            svg, _ = tree(tx, ty, day - born + 1, ts)
            is_new = day == born and not thumb
            ground.append((ty, ('<g class="g-new">' if is_new else "<g>") + svg + "</g>"
                           + (f'<circle class="g-ring" cx="{tx}" cy="{ty-40}" r="26" fill="none" stroke="#FFB300" stroke-width="3"/>'
                              if is_new else "")))
    for x in vis:
        if x["layer"] == "ground":
            ground.append((x["y"], pop(x) + x["draw"](crown) + "</g>" + ring(x)))
    for _, s in sorted(ground, key=lambda t: t[0]):
        o += s
    if th["tint"]:
        o += R(0, 0, 680, 380, th["tint"][0]).replace("/>", f' opacity="{th["tint"][1]}"/>')

    # 2. воздух: находки и небесные украшения
    for x in vis:
        if x["layer"] == "air":
            o += pop(x) + x["draw"](crown) + "</g>" + ring(x)
    for k in active:
        if k == "moon":
            o += deco_moon(th)
        elif k == "stars":
            o += deco_stars()
        elif k == "clouds":
            o += deco_clouds(th)
        elif k == "plane":
            o += deco_plane()
        elif k == "snow":
            o += deco_snow()
        elif k == "petals":
            o += deco_petals()
        elif k == "fireflies":
            o += deco_fireflies()
    row = 0
    for k in active:
        if k in TOP_SPAN_KEYS:
            o += {"garland": deco_garland, "flags": deco_flags, "lights": deco_lanterns}[k](min(row, 2))
            row += 1

    label = "Сад, день серии %d" % day
    cls = "garden-svg" + (" thumb" if thumb else "")
    attrs = 'aria-hidden="true"' if thumb else f'role="img" aria-label="{label}"'
    return Markup(f'<svg class="{cls}" viewBox="0 0 680 380" {attrs}>{o}</svg>')


def tree_mini_svg(day):
    """Маленькое дерево (иконка на главной ученика)."""
    day = max(0, min(int(day or 0), MAX_DAY))
    g = growth(day) if day else 0
    height = 14 if day <= 0 else ((10 + 160 * g) + 12 if day < 3 else (10 + 160 * g) + (9 + 76 * g) * 1.35)
    s = min(.6, 78 / height)
    svg, _ = tree(50, 92, day, s)
    return Markup(f'<svg class="gt-svg" viewBox="0 0 100 100" aria-hidden="true">'
                  f'{E(50, 94, 34, 6, "#8CCB74")}{svg}</svg>')
