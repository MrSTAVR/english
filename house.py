# -*- coding: utf-8 -*-
"""Домик Чик-чика: мебель и декор за монетки (отдельная страница, как сад)."""

SLOTS = [
    {"key": "wall", "title": "Стены", "emoji": "🧱"},
    {"key": "floor", "title": "Пол", "emoji": "🪵"},
    {"key": "window", "title": "Окно", "emoji": "🪟"},
    {"key": "bed", "title": "Кроватка", "emoji": "🛏️"},
    {"key": "rug", "title": "Коврик", "emoji": "🟣"},
    {"key": "shelf", "title": "Полка", "emoji": "📚"},
    {"key": "picture", "title": "Картина", "emoji": "🖼️"},
    {"key": "lamp", "title": "Лампа", "emoji": "💡"},
    {"key": "plant", "title": "Растение", "emoji": "🪴"},
    {"key": "toy", "title": "Игрушка", "emoji": "🧸"},
]

ITEMS = [
    {"key": "wall-cream", "slot": "wall", "name": "Кремовые стены", "cost": 0},
    {"key": "wall-blue", "slot": "wall", "name": "Голубые стены", "cost": 15},
    {"key": "wall-pink", "slot": "wall", "name": "Розовые стены", "cost": 15},
    {"key": "wall-green", "slot": "wall", "name": "Мятные стены", "cost": 15},
    {"key": "wall-stars", "slot": "wall", "name": "Звёздное небо", "cost": 25},
    {"key": "floor-wood", "slot": "floor", "name": "Деревянный пол", "cost": 0},
    {"key": "floor-carpet", "slot": "floor", "name": "Мягкий ковролин", "cost": 12},
    {"key": "floor-grass", "slot": "floor", "name": "Травка", "cost": 18},
    {"key": "win-day", "slot": "window", "name": "Окно с облачками", "cost": 14},
    {"key": "win-night", "slot": "window", "name": "Ночное окно", "cost": 14},
    {"key": "win-rainbow", "slot": "window", "name": "Окно с радугой", "cost": 22},
    {"key": "bed-small", "slot": "bed", "name": "Уютная кроватка", "cost": 20},
    {"key": "bed-royal", "slot": "bed", "name": "Королевская кровать", "cost": 40},
    {"key": "rug-round", "slot": "rug", "name": "Круглый коврик", "cost": 14},
    {"key": "rug-star", "slot": "rug", "name": "Коврик-звезда", "cost": 20},
    {"key": "shelf-books", "slot": "shelf", "name": "Полка с книгами", "cost": 18},
    {"key": "shelf-trophies", "slot": "shelf", "name": "Полка с кубками", "cost": 24},
    {"key": "pic-chick", "slot": "picture", "name": "Портрет цыплёнка", "cost": 10},
    {"key": "pic-sun", "slot": "picture", "name": "Картина «Солнце»", "cost": 12},
    {"key": "pic-rocket", "slot": "picture", "name": "Картина «Ракета»", "cost": 16},
    {"key": "lamp-floor", "slot": "lamp", "name": "Торшер", "cost": 12},
    {"key": "lamp-ball", "slot": "lamp", "name": "Светящийся шар", "cost": 16},
    {"key": "plant-pot", "slot": "plant", "name": "Цветок в горшке", "cost": 10},
    {"key": "plant-cactus", "slot": "plant", "name": "Кактус", "cost": 10},
    {"key": "plant-tree", "slot": "plant", "name": "Пальма", "cost": 20},
    {"key": "toy-ball", "slot": "toy", "name": "Мячик", "cost": 8},
    {"key": "toy-duck", "slot": "toy", "name": "Уточка", "cost": 12},
    {"key": "toy-teddy", "slot": "toy", "name": "Мишка", "cost": 18},
]
ITEMS_BY_KEY = {i["key"]: i for i in ITEMS}
FREE_KEYS = {i["key"] for i in ITEMS if i["cost"] == 0}
DEFAULT_PLACED = {"wall": "wall-cream", "floor": "floor-wood"}


def owned_keys(db, student_id):
    rows = db.execute("SELECT item_key FROM house_items WHERE student_id=?", (student_id,)).fetchall()
    return {r["item_key"] for r in rows if r["item_key"] in ITEMS_BY_KEY} | FREE_KEYS


def bought_count(db, student_id):
    return db.execute("SELECT COUNT(*) FROM house_items WHERE student_id=?", (student_id,)).fetchone()[0]


def placed(db, student_id):
    """{slot: key} — что стоит в домике (стены и пол по умолчанию есть всегда)."""
    out = dict(DEFAULT_PLACED)
    for r in db.execute("SELECT slot, item_key FROM house_place WHERE student_id=?", (student_id,)).fetchall():
        it = ITEMS_BY_KEY.get(r["item_key"])
        if it and it["slot"] == r["slot"]:
            out[r["slot"]] = r["item_key"]
    return out


def _set(db, student_id, slot, key):
    db.execute("INSERT INTO house_place (student_id, slot, item_key) VALUES (?,?,?) "
               "ON CONFLICT(student_id, slot) DO UPDATE SET item_key=excluded.item_key", (student_id, slot, key))


def buy(db, student_id, key):
    from garden import get_garden
    it = ITEMS_BY_KEY.get(key)
    if not it:
        return False, "Такой вещи нет."
    if key in owned_keys(db, student_id):
        return False, "Она уже у тебя!"
    g = get_garden(db, student_id)
    if g["coins"] < it["cost"]:
        return False, f"Не хватает монеток: нужно {it['cost']}, а у тебя {g['coins']}."
    db.execute("UPDATE garden SET coins=coins-? WHERE student_id=?", (it["cost"], student_id))
    db.execute("INSERT OR IGNORE INTO house_items (student_id, item_key) VALUES (?,?)", (student_id, key))
    _set(db, student_id, it["slot"], key)
    db.commit()
    return True, f"«{it['name']}» куплено и уже стоит в домике! 🏠"


def place(db, student_id, key):
    """Поставить купленное; повторное нажатие убирает (стены и пол остаются стандартными)."""
    it = ITEMS_BY_KEY.get(key)
    if not it or key not in owned_keys(db, student_id):
        return False, "Сначала это нужно купить."
    cur = placed(db, student_id).get(it["slot"])
    if cur == key:
        if it["slot"] in DEFAULT_PLACED:
            return False, "Стены и пол всегда на месте — выбери другие."
        db.execute("DELETE FROM house_place WHERE student_id=? AND slot=?", (student_id, it["slot"]))
        msg = f"«{it['name']}» убрано."
    else:
        _set(db, student_id, it["slot"], key)
        msg = f"«{it['name']}» стоит в домике! ✨"
    db.commit()
    return True, msg
