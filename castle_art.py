# -*- coding: utf-8 -*-
"""Рисунки замка Чик-чика (SVG, как в макете дизайн-ориентира): комнаты, зверята-соседи, ворота,
кирпичик и монетка. Плоские цвета, без градиентов; это рисунки, а не значки интерфейса."""

COIN = ('<svg width="{s}" height="{s}" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="#FFC83D" stroke="#D99A00" stroke-width="2"></circle>'
        '<path d="M12 8v8M9.5 10h4a1.5 1.5 0 0 1 0 3h-3" stroke="#8A5A00" stroke-width="2" fill="none" stroke-linecap="round"></path></svg>')
BRICK = ('<svg width="{s}" height="{s}" viewBox="0 0 24 24" aria-hidden="true"><rect x="2" y="6" width="20" height="12" rx="2" fill="#D9661A"></rect>'
         '<path d="M2 12h20M8 6v6M16 6v6M12 12v6M5 12v6M19 12v6" stroke="#FFE9D6" stroke-width="1.6"></path></svg>')
STAR = '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"></path>'
CHECK = '<path d="M5 12l5 5 9-10"></path>'

def coin(s=18):
    return COIN.format(s=s)


def brick(s=18):
    return BRICK.format(s=s)


# ---------- жители — зверята-соседи ----------
PEOPLE = {   # имя → вид, цвет, светлый цвет
    "Benny": {"kind": "bear", "c": "#A8724A", "l": "#E8C9A6", "ru": "медвежонок Бенни"},
    "Olly": {"kind": "owl", "c": "#7A5BC4", "l": "#E3D9FF", "ru": "совёнок Олли"},
    "Mia": {"kind": "cat", "c": "#9AA6BD", "l": "#FFFFFF", "ru": "кошечка Мия"},
    "Felix": {"kind": "fox", "c": "#D9661A", "l": "#FFF3D9", "ru": "лисёнок Феликс"},
    "Max": {"kind": "dog", "c": "#E3B77F", "l": "#FFF3D9", "ru": "щенок Макс"},
    "Bella": {"kind": "bunny", "c": "#F4F4F4", "l": "#FFD6E3", "ru": "зайка Белла"},
}
INK = "#1E2A45"


def _animal(name):
    """Зверёк в viewBox 0 0 40 48: голова, ушки, мордочка, тельце с животиком."""
    a = PEOPLE[name]; c, l, k = a["c"], a["l"], a["kind"]
    edge = ' stroke="#C9D3E3" stroke-width="1.2"' if k == "bunny" else ""
    ears = {
        "bear": f'<circle cx="10" cy="8" r="5" fill="{c}"></circle><circle cx="30" cy="8" r="5" fill="{c}"></circle><circle cx="10" cy="8" r="2.5" fill="{l}"></circle><circle cx="30" cy="8" r="2.5" fill="{l}"></circle>',
        "owl": f'<path d="M9 4l5 8-8 1zM31 4l-5 8 8 1z" fill="{c}"></path>',
        "cat": f'<path d="M8 3l8 7-9 3zM32 3l-8 7 9 3z" fill="{c}"></path><path d="M9.5 6l4 4-4.5 1.5zM30.5 6l-4 4 4.5 1.5z" fill="#FFB3C7"></path>',
        "fox": f'<path d="M7 1l9 9-10 3zM33 1l-9 9 10 3z" fill="{c}"></path><path d="M7 1l3 3-3 1zM33 1l-3 3 3 1z" fill="{INK}"></path>',
        "dog": "",
        "bunny": f'<ellipse cx="14" cy="-2" rx="4" ry="11" fill="{c}"{edge}></ellipse><ellipse cx="26" cy="-2" rx="4" ry="11" fill="{c}"{edge}></ellipse><ellipse cx="14" cy="-2" rx="2" ry="8" fill="{l}"></ellipse><ellipse cx="26" cy="-2" rx="2" ry="8" fill="{l}"></ellipse>',
    }[k]
    body = (f'<ellipse cx="20" cy="37" rx="11" ry="10" fill="{c}"{edge}></ellipse><ellipse cx="20" cy="39" rx="7" ry="7" fill="{l if k != "bunny" else "#FFFFFF"}"></ellipse>'
            f'<ellipse cx="14" cy="46" rx="4" ry="2.4" fill="{c}"{edge}></ellipse><ellipse cx="26" cy="46" rx="4" ry="2.4" fill="{c}"{edge}></ellipse>')
    head = f'<circle cx="20" cy="18" r="12" fill="{c}"{edge}></circle>'
    if k == "owl":
        face = (f'<circle cx="15" cy="17" r="5" fill="#FFFFFF"></circle><circle cx="25" cy="17" r="5" fill="#FFFFFF"></circle>'
                f'<circle cx="15.5" cy="17.5" r="2.4" fill="{INK}"></circle><circle cx="24.5" cy="17.5" r="2.4" fill="{INK}"></circle>'
                f'<path d="M18 22h4l-2 4z" fill="#FFC83D"></path><path d="M9 33q-4 4 0 10M31 33q4 4 0 10" stroke="{c}" stroke-width="5" stroke-linecap="round" fill="none"></path>')
    else:
        muzzle = {"bear": f'<ellipse cx="20" cy="23" rx="6" ry="4.5" fill="{l}"></ellipse>',
                  "fox": f'<path d="M10 20q10 12 20 0q-3 8-10 8t-10-8z" fill="{l}"></path>',
                  "dog": f'<ellipse cx="20" cy="23" rx="6.5" ry="4.5" fill="{l}"></ellipse>'}.get(k, "")
        whisk = ('<path d="M6 21h6M6 24l6-1M34 21h-6M34 24l-6-1" stroke="#5E6478" stroke-width=".8"></path>' if k == "cat" else "")
        nose = "#FF8FB8" if k in ("cat", "bunny") else INK
        face = (f'{muzzle}<circle cx="15" cy="16" r="1.9" fill="{INK}"></circle><circle cx="25" cy="16" r="1.9" fill="{INK}"></circle>'
                f'<circle cx="15.6" cy="15.4" r=".6" fill="#FFFFFF"></circle><circle cx="25.6" cy="15.4" r=".6" fill="#FFFFFF"></circle>'
                f'<ellipse cx="20" cy="21" rx="2" ry="1.4" fill="{nose}"></ellipse><path d="M18 23.5q2 1.6 4 0" stroke="{INK}" stroke-width=".9" fill="none"></path>{whisk}'
                f'<ellipse cx="11" cy="21" rx="2.2" ry="1.3" fill="#FF8FB8" opacity=".55"></ellipse><ellipse cx="29" cy="21" rx="2.2" ry="1.3" fill="#FF8FB8" opacity=".55"></ellipse>')
        if k == "dog":
            face += '<ellipse cx="8" cy="19" rx="4" ry="8" fill="#8A6B4A" transform="rotate(15 8 19)"></ellipse><ellipse cx="32" cy="19" rx="4" ry="8" fill="#8A6B4A" transform="rotate(-15 32 19)"></ellipse>'
    return ears + body + head + face


def person(name, x, y, h=44, svg=False):
    """Зверёк высотой h (имя оставлено прежним, чтобы не переписывать раскладку)."""
    inner = _animal(name)
    s = h / 52
    if svg:
        return f'<g transform="translate({x} {y + 4 * s}) scale({s:.3f})">{inner}</g>'
    return (f'<svg width="{40 * s:.0f}" height="{h}" viewBox="0 -4 40 52" aria-hidden="true" style="position: absolute; left: {x}px; bottom: {y}px; overflow: visible">{inner}</svg>')


def avatar(name, size=44):
    return (f'<span style="width: {size}px; height: {size}px; border-radius: 50%; background: #FFF3D9; border: 2px solid #F0E3C8; display: flex; align-items: center; justify-content: center; overflow: hidden; flex-shrink: 0; box-sizing: border-box">'
            f'<svg width="{size * .86:.0f}" height="{size * .86:.0f}" viewBox="0 -6 40 40" aria-hidden="true">{_animal(name)}</svg></span>')



# ---------- рисунки комнат (viewBox 0 0 300 180: стена 0–132, пол 132–180) ----------
WALL = {"bedroom": "#E3EDFC", "kitchen": "#FFF3D9", "library": "#FFEFC2", "classroom": "#DDF5E7", "living": "#FFE9D6",
        "music": "#E3EDFC", "gym": "#FFF3D9", "workshop": "#FFEFC2", "roof": "#CFE6FF"}
FLOOR = {"bedroom": "#D9B48A", "kitchen": "#E3CFA4", "library": "#C9A27A", "classroom": "#D9B48A", "living": "#C9A27A",
         "music": "#E3CFA4", "gym": "#E8B86B", "workshop": "#C9A27A", "roof": "#8EDB8A"}


def win(x, y, w=56, h=46):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="#BFE0FF" stroke="#8A6B4A" stroke-width="4"></rect>'
            f'<path d="M{x + w / 2} {y}V{y + h}M{x} {y + h / 2}H{x + w}" stroke="#8A6B4A" stroke-width="3"></path>')


ART = {
    "bedroom": lambda: (win(128, 22) +
        '<rect x="14" y="96" width="104" height="38" rx="6" fill="#8A6B4A"></rect><rect x="18" y="84" width="96" height="30" rx="8" fill="#2563C9"></rect>'
        '<rect x="20" y="78" width="32" height="20" rx="8" fill="#FFFFFF" stroke="#E3CFA4" stroke-width="2"></rect>'
        '<rect x="216" y="40" width="66" height="94" rx="4" fill="#C9A27A" stroke="#8A6B4A" stroke-width="3"></rect><path d="M249 40v94" stroke="#8A6B4A" stroke-width="3"></path>'
        '<circle cx="244" cy="88" r="3" fill="#8A6B4A"></circle><circle cx="254" cy="88" r="3" fill="#8A6B4A"></circle>'
        '<rect x="170" y="98" width="4" height="36" fill="#6B4F32"></rect><path d="M158 100h28l-6-22h-16z" fill="#FFC83D" stroke="#D99A00" stroke-width="2"></path>'
        '<ellipse cx="150" cy="160" rx="56" ry="10" fill="#E8618C" opacity=".85"></ellipse>'),
    "kitchen": lambda: (win(122, 20) +
        '<rect x="12" y="34" width="56" height="100" rx="8" fill="#FFFFFF" stroke="#C9D3E3" stroke-width="3"></rect><path d="M12 72h56" stroke="#C9D3E3" stroke-width="3"></path>'
        '<rect x="56" y="46" width="4" height="16" rx="2" fill="#9AA6BD"></rect><rect x="56" y="82" width="4" height="22" rx="2" fill="#9AA6BD"></rect>'
        '<rect x="76" y="92" width="60" height="42" rx="4" fill="#5E6478"></rect><rect x="76" y="86" width="60" height="8" rx="2" fill="#1E2A45"></rect>'
        '<circle cx="92" cy="88" r="5" fill="#9AA6BD"></circle><circle cx="120" cy="88" r="5" fill="#9AA6BD"></circle><rect x="84" y="102" width="44" height="24" rx="3" fill="#2B2F3F"></rect>'
        '<path d="M100 72h22l-2 14h-18z" fill="#D9661A"></path><path d="M122 76q8 0 8 6" stroke="#D9661A" stroke-width="3" fill="none"></path>'
        '<rect x="196" y="104" width="94" height="8" rx="3" fill="#8A6B4A"></rect><rect x="204" y="112" width="6" height="22" fill="#8A6B4A"></rect><rect x="276" y="112" width="6" height="22" fill="#8A6B4A"></rect>'
        '<ellipse cx="222" cy="102" rx="14" ry="3" fill="#FFFFFF" stroke="#C9D3E3" stroke-width="2"></ellipse>'
        '<path d="M250 90h16v10a8 8 0 0 1-16 0z" fill="#2563C9"></path><path d="M266 92q6 0 5 6t-5 4" stroke="#2563C9" stroke-width="2.5" fill="none"></path>'
        '<rect x="196" y="40" width="92" height="6" rx="2" fill="#8A6B4A"></rect><path d="M204 40q8-14 16 0zM230 40q9-12 18 0z" fill="#FFFFFF" stroke="#C9D3E3" stroke-width="2"></path>'
        '<rect x="262" y="24" width="8" height="16" rx="2" fill="#9AA6BD"></rect><rect x="274" y="22" width="8" height="18" rx="2" fill="#9AA6BD"></rect>'),
    "library": lambda: (
        ''.join(f'<rect x="{x}" y="22" width="76" height="112" rx="4" fill="#8A6B4A"></rect>' +
                ''.join(f'<rect x="{x + 4}" y="{y}" width="68" height="4" fill="#6B4F32"></rect>' for y in (54, 88, 122)) +
                ''.join(f'<rect x="{x + 6 + i * 10}" y="{y - 26 + (i % 3) * 3}" width="8" height="{26 - (i % 3) * 3}" fill="{c}"></rect>'
                        for y in (54, 88, 122) for i, c in enumerate(("#E8618C", "#2563C9", "#1E9E5A", "#FFC83D", "#7A5BC4", "#D9661A")))
                for x in (12, 212)) +
        '<circle cx="150" cy="92" r="20" fill="#7FC4F5" stroke="#2563C9" stroke-width="3"></circle><path d="M138 84q8 4 6 12q10-2 14 6" stroke="#1E9E5A" stroke-width="4" fill="none"></path>'
        '<rect x="148" y="112" width="4" height="14" fill="#8A6B4A"></rect><rect x="136" y="126" width="28" height="8" rx="3" fill="#8A6B4A"></rect>'),
    "classroom": lambda: (
        '<rect x="70" y="18" width="160" height="70" rx="6" fill="#1F5A3E" stroke="#8A6B4A" stroke-width="5"></rect>'
        '<text x="150" y="62" text-anchor="middle" font-family="Nunito, sans-serif" font-weight="900" font-size="26" fill="#FFFFFF">A B C</text>'
        '<circle cx="264" cy="40" r="16" fill="#FFFFFF" stroke="#1E2A45" stroke-width="3"></circle><path d="M264 30v10l7 5" stroke="#1E2A45" stroke-width="3" fill="none"></path>'
        + ''.join(f'<rect x="{x}" y="112" width="70" height="8" rx="2" fill="#C9A27A"></rect><rect x="{x + 6}" y="120" width="6" height="16" fill="#8A6B4A"></rect><rect x="{x + 58}" y="120" width="6" height="16" fill="#8A6B4A"></rect>'
                  f'<rect x="{x + 20}" y="100" width="22" height="12" rx="2" fill="#2563C9"></rect>' for x in (24, 206)) +
        '<rect x="120" y="96" width="60" height="30" rx="4" fill="#1E2A45"></rect><rect x="124" y="100" width="52" height="22" rx="2" fill="#7FC4F5"></rect><rect x="140" y="126" width="20" height="8" fill="#5E6478"></rect>'),
    "living": lambda: (
        '<rect x="110" y="26" width="64" height="44" rx="4" fill="#1E2A45"></rect><rect x="114" y="30" width="56" height="36" rx="2" fill="#2563C9"></rect><rect x="138" y="70" width="8" height="10" fill="#5E6478"></rect>'
        '<rect x="20" y="88" width="120" height="46" rx="12" fill="#E8618C"></rect><rect x="12" y="98" width="20" height="36" rx="8" fill="#C94A72"></rect><rect x="128" y="98" width="20" height="36" rx="8" fill="#C94A72"></rect>'
        '<rect x="34" y="78" width="40" height="26" rx="8" fill="#F28AAA"></rect><rect x="82" y="78" width="40" height="26" rx="8" fill="#F28AAA"></rect>'
        '<path d="M232 134l6-34h20l6 34z" fill="#2563C9"></path><path d="M248 100c-2-14-14-22-20-30M248 100c2-16 10-26 18-30M248 100v-36" stroke="#1E9E5A" stroke-width="3" fill="none"></path>'
        '<circle cx="228" cy="70" r="7" fill="#FFC83D"></circle><circle cx="266" cy="70" r="7" fill="#E8618C"></circle><circle cx="248" cy="62" r="7" fill="#FFFFFF"></circle>'
        '<rect x="214" y="22" width="48" height="36" rx="3" fill="#FFFFFF" stroke="#8A6B4A" stroke-width="4"></rect><circle cx="238" cy="40" r="9" fill="#FFC83D"></circle>'
        '<ellipse cx="150" cy="160" rx="70" ry="11" fill="#7A5BC4" opacity=".7"></ellipse>'),
    "music": lambda: (
        '<rect x="16" y="70" width="110" height="64" rx="6" fill="#1E2A45"></rect>' +
        ''.join(f'<rect x="{22 + i * 13}" y="78" width="11" height="34" fill="#FFFFFF"></rect>' for i in range(7)) +
        ''.join(f'<rect x="{31 + i * 13}" y="78" width="7" height="20" fill="#1E2A45"></rect>' for i in (0, 1, 3, 4, 5)) +
        '<ellipse cx="190" cy="108" rx="22" ry="26" fill="#D9661A"></ellipse><circle cx="190" cy="108" r="7" fill="#6B3A16"></circle><rect x="186" y="30" width="8" height="64" fill="#8A6B4A"></rect>'
        '<ellipse cx="262" cy="118" rx="26" ry="10" fill="#E8618C"></ellipse><rect x="236" y="104" width="52" height="16" fill="#E8618C"></rect><ellipse cx="262" cy="104" rx="26" ry="10" fill="#FFF3D9" stroke="#C94A72" stroke-width="3"></ellipse>'
        '<path d="M232 58l24 30M292 58l-24 30" stroke="#8A6B4A" stroke-width="4" stroke-linecap="round"></path>'),
    "gym": lambda: (
        '<rect x="236" y="20" width="44" height="30" rx="2" fill="#FFFFFF" stroke="#1E2A45" stroke-width="3"></rect><path d="M244 50h28l-4 18h-20z" fill="none" stroke="#D9661A" stroke-width="3"></path>'
        '<rect x="276" y="20" width="6" height="114" fill="#5E6478"></rect><circle cx="70" cy="118" r="16" fill="#D9661A"></circle><path d="M54 118h32M70 102v32" stroke="#6B3A16" stroke-width="2"></path>'
        '<rect x="110" y="122" width="100" height="12" rx="4" fill="#2563C9"></rect><circle cx="26" cy="40" r="10" fill="#FFC83D"></circle>'),
    "workshop": lambda: (
        '<rect x="40" y="96" width="220" height="10" rx="3" fill="#8A6B4A"></rect><rect x="50" y="106" width="8" height="28" fill="#6B4F32"></rect><rect x="242" y="106" width="8" height="28" fill="#6B4F32"></rect>'
        '<rect x="70" y="84" width="60" height="12" fill="#FFFFFF" stroke="#C9D3E3" stroke-width="2"></rect>' +
        ''.join(f'<rect x="{150 + i * 22}" y="78" width="16" height="18" rx="3" fill="{c}"></rect>' for i, c in enumerate(("#E8618C", "#2563C9", "#FFC83D", "#1E9E5A"))) +
        '<rect x="24" y="24" width="80" height="50" rx="4" fill="#FFFFFF" stroke="#8A6B4A" stroke-width="4"></rect><path d="M34 62l18-22 14 16 10-10 18 16" stroke="#1E9E5A" stroke-width="4" fill="none"></path>'),
    "roof": lambda: (
        '<circle cx="262" cy="34" r="18" fill="#FFC83D"></circle>' +
        ''.join(f'<path d="M{x} 134v-26" stroke="#1E9E5A" stroke-width="3"></path><circle cx="{x}" cy="104" r="8" fill="{c}"></circle><circle cx="{x}" cy="104" r="3" fill="#FFC83D"></circle>'
                for x, c in ((40, "#E8618C"), (66, "#FFFFFF"), (92, "#7A5BC4"), (210, "#E8618C"), (236, "#FFFFFF"))) +
        '<rect x="120" y="108" width="70" height="8" rx="3" fill="#8A6B4A"></rect><rect x="126" y="116" width="6" height="18" fill="#6B4F32"></rect><rect x="178" y="116" width="6" height="18" fill="#6B4F32"></rect>'),
}


# Где стоит каждое слово-предмет на рисунке комнаты (единицы viewBox 300×180):
# (x, y, 0) — предмет уже нарисован; (x, y, размер[, картинка]) — рисуем картинку слова (эмодзи) в этом месте.
POS = {
    "bedroom": {"bed": (50, 118, 0), "wardrobe": (249, 64, 0), "lamp": (172, 90, 0), "window": (156, 45, 0), "carpet": (150, 162, 0),
                "pillow": (36, 86, 0), "blanket": (95, 96, 0), "chair": (140, 122, 20), "desk": (28, 160, 20), "shelf": (36, 40, 20),
                "picture": (70, 40, 20), "mirror": (104, 44, 20), "toy": (268, 160, 20)},
    "kitchen": {"fridge": (40, 84, 0), "kettle": (111, 76, 0), "cooker": (80, 94, 0), "oven": (106, 116, 0), "plate": (222, 100, 0),
                "bowl": (217, 34, 0), "sink": (160, 100, 20), "glass": (286, 96, 16), "spoon": (196, 72, 16), "knife": (228, 72, 16),
                "pan": (262, 70, 18)},
    "library": {"book": (50, 70, 0), "shelf": (250, 100, 0), "map": (150, 40, 24), "letter": (190, 40, 18, "✉️"), "pencil": (110, 60, 14),
                "lamp": (110, 24, 16), "armchair": (180, 120, 26), "plant": (30, 160, 22)},
    "classroom": {"clock": (264, 40, 0), "desk": (59, 124, 0), "book": (55, 104, 0), "notebook": (237, 104, 0), "computer": (150, 110, 0),
                  "map": (36, 46, 22), "pencil": (200, 96, 16), "ruler": (264, 76, 18), "rubber": (100, 96, 14)},
    "living": {"tv": (142, 48, 0), "sofa": (80, 106, 0), "vase": (248, 118, 0), "plant": (248, 72, 0), "rug": (150, 164, 0),
               "armchair": (282, 122, 22), "curtains": (40, 44, 24), "fireplace": (60, 162, 20), "computer": (240, 164, 18)},
    "music": {"piano": (70, 100, 0), "guitar": (190, 96, 0), "drum": (262, 112, 0), "violin": (130, 40, 22), "trumpet": (60, 40, 22)},
    "gym": {"basketball": (70, 118, 0), "ball": (24, 124, 18), "tennis": (104, 116, 14), "racket": (150, 110, 18), "skates": (110, 162, 20),
            "skateboard": (270, 162, 22), "kite": (120, 40, 24), "doll": (165, 44, 20), "puzzle": (205, 44, 20), "robot": (40, 162, 22)},
    "workshop": {"paper": (100, 88, 0), "paint": (190, 86, 0), "scissors": (140, 86, 14), "glue": (246, 84, 18), "brush": (150, 48, 22),
                 "box": (60, 160, 24)},
    "roof": {"sun": (262, 34, 0), "flower": (66, 104, 0), "bench": (155, 112, 0), "grass": (150, 160, 0), "bee": (110, 60, 18),
             "butterfly": (190, 50, 20), "bird": (60, 30, 20)},
}
RESIDENT_X = {"library": 112, "roof": 112, "classroom": 192}   # центр жителя на большом рисунке (по умолчанию 200)


def items_svg(key, words):
    """Картинки слов, которых нет на основном рисунке (появляются с уровнем комнаты)."""
    out = []
    for w in words:
        p = POS[key].get(w["en"].lower())
        if p and p[2]:
            pic = p[3] if len(p) > 3 else w.get("pic")
            if pic:
                out.append(f'<text x="{p[0]}" y="{p[1]}" font-size="{p[2] * 1.35:g}" text-anchor="middle" dominant-baseline="central">{pic}</text>')
    return "".join(out)


def room_svg(key, w=None, h=None, extra=""):
    size = f' width="{w}" height="{h}"' if w else ' width="100%" height="100%"'
    return (f'<svg viewBox="0 0 300 180"{size} preserveAspectRatio="xMidYMid slice" aria-hidden="true" style="display: block">'
            f'<rect width="300" height="180" fill="{WALL[key]}"></rect><rect y="134" width="300" height="46" fill="{FLOOR[key]}"></rect>'
            f'<path d="M0 134h300" stroke="rgba(30,42,69,.12)" stroke-width="3"></path>{ART[key]()}{extra}</svg>')


GATE = (  # ворота замка: каменная арка, решётка, двустворчатые двери с железными полосами, фонари
    '<svg width="{w}" height="{h}" viewBox="0 0 120 64" aria-hidden="true" style="display: block">'
    '<path d="M22 64V30a38 30 0 0 1 76 0v34z" fill="#C9A27A"></path>'
    '<path d="M22 30a38 30 0 0 1 76 0" fill="none" stroke="#8A6B4A" stroke-width="2"></path>'
    '<path d="M60 0v8M44 4l3 7M76 4l-3 7M31 12l5 6M89 12l-5 6M24 23l7 3M96 23l-7 3" stroke="#8A6B4A" stroke-width="2"></path>'
    '<path d="M32 64V32a28 22 0 0 1 56 0v32z" fill="#4A3524"></path>'
    '<path d="M32 26h56M32 36h56M42 12v52M52 10v54M60 10v54M68 10v54M78 12v52" stroke="#2B1E14" stroke-width="2" opacity=".55"></path>'
    '<path d="M35 64V40a25 18 0 0 1 24-16v40z" fill="#8A5A36"></path><path d="M85 64V40a25 18 0 0 0-24-16v40z" fill="#8A5A36"></path>'
    '<path d="M41 64V33M47 64V28M53 64V25M67 64V25M73 64V28M79 64V33" stroke="#6B4224" stroke-width="1.5"></path>'
    '<path d="M35 44h24M61 44h24M35 56h24M61 56h24" stroke="#3B4152" stroke-width="3"></path>'
    '<circle cx="55" cy="50" r="2.4" fill="#FFC83D"></circle><circle cx="65" cy="50" r="2.4" fill="#FFC83D"></circle>'
    '<path d="M59.5 24v40" stroke="#4A2E18" stroke-width="2"></path>'
    '<rect x="8" y="30" width="8" height="12" rx="2" fill="#FFC83D" stroke="#5E6478" stroke-width="2"></rect><path d="M12 42v8M8 30h8l-4-5z" stroke="#5E6478" stroke-width="2" fill="#5E6478"></path>'
    '<rect x="104" y="30" width="8" height="12" rx="2" fill="#FFC83D" stroke="#5E6478" stroke-width="2"></rect><path d="M108 42v8M104 30h8l-4-5z" stroke="#5E6478" stroke-width="2" fill="#5E6478"></path>'
    '</svg>')


def gate(h):
    return GATE.format(w=int(h * 120 / 64), h=h)

