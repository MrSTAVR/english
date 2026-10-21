# -*- coding: utf-8 -*-
"""Гардероб Чик-чика: шапки, очки, шарфы и цвет перьев за монетки.

Рисунки предметов живут в static/chick.js (по ключам). Здесь — каталог, цены и правила."""

SLOTS = [
    {"key": "hat", "title": "Шапки", "emoji": "🎩"},
    {"key": "face", "title": "Очки и лицо", "emoji": "🕶️"},
    {"key": "neck", "title": "Шея", "emoji": "🎀"},
    {"key": "color", "title": "Цвет перьев", "emoji": "🎨"},
]

ITEMS = [
    # шапки
    {"key": "hat-cap", "slot": "hat", "name": "Бейсболка", "cost": 12},
    {"key": "hat-party", "slot": "hat", "name": "Праздничный колпак", "cost": 12},
    {"key": "hat-flowers", "slot": "hat", "name": "Венок из цветов", "cost": 15},
    {"key": "hat-bunny", "slot": "hat", "name": "Ушки зайчика", "cost": 16},
    {"key": "hat-chef", "slot": "hat", "name": "Поварской колпак", "cost": 18},
    {"key": "hat-phones", "slot": "hat", "name": "Наушники", "cost": 20},
    {"key": "hat-santa", "slot": "hat", "name": "Колпак Деда Мороза", "cost": 22},
    {"key": "hat-top", "slot": "hat", "name": "Цилиндр", "cost": 26},
    {"key": "hat-grad", "slot": "hat", "name": "Шапка выпускника", "cost": 30},
    {"key": "hat-wizard", "slot": "hat", "name": "Шляпа волшебника", "cost": 35},
    {"key": "hat-crown", "slot": "hat", "name": "Золотая корона", "cost": 50},
    # лицо
    {"key": "face-glasses", "slot": "face", "name": "Умные очки", "cost": 10},
    {"key": "face-mustache", "slot": "face", "name": "Усы", "cost": 10},
    {"key": "face-sun", "slot": "face", "name": "Тёмные очки", "cost": 14},
    {"key": "face-hearts", "slot": "face", "name": "Очки-сердечки", "cost": 16},
    {"key": "face-stars", "slot": "face", "name": "Очки-звёзды", "cost": 16},
    {"key": "face-mask", "slot": "face", "name": "Маска героя", "cost": 20},
    # шея
    {"key": "neck-bow", "slot": "neck", "name": "Бабочка", "cost": 10},
    {"key": "neck-tie", "slot": "neck", "name": "Галстук", "cost": 10},
    {"key": "neck-bandana", "slot": "neck", "name": "Бандана", "cost": 12},
    {"key": "neck-scarf", "slot": "neck", "name": "Тёплый шарф", "cost": 14},
    {"key": "neck-lei", "slot": "neck", "name": "Цветочные бусы", "cost": 16},
    {"key": "neck-medal", "slot": "neck", "name": "Золотая медаль", "cost": 24},
    # цвет перьев
    {"key": "color-yellow", "slot": "color", "name": "Классический жёлтый", "cost": 0},
    {"key": "color-pink", "slot": "color", "name": "Розовый", "cost": 20},
    {"key": "color-blue", "slot": "color", "name": "Голубой", "cost": 20},
    {"key": "color-green", "slot": "color", "name": "Зелёный", "cost": 20},
    {"key": "color-purple", "slot": "color", "name": "Фиолетовый", "cost": 20},
    {"key": "color-white", "slot": "color", "name": "Снежный белый", "cost": 28},
]
ITEMS_BY_KEY = {i["key"]: i for i in ITEMS}
FREE_KEYS = {i["key"] for i in ITEMS if i["cost"] == 0}


def owned_keys(db, student_id):
    rows = db.execute("SELECT item_key FROM wardrobe_items WHERE student_id=?", (student_id,)).fetchall()
    return {r["item_key"] for r in rows if r["item_key"] in ITEMS_BY_KEY} | FREE_KEYS


def outfit(db, student_id):
    """{slot: key} — что надето сейчас."""
    rows = db.execute("SELECT slot, item_key FROM wardrobe_wear WHERE student_id=?", (student_id,)).fetchall()
    return {r["slot"]: r["item_key"] for r in rows
            if r["item_key"] in ITEMS_BY_KEY and ITEMS_BY_KEY[r["item_key"]]["slot"] == r["slot"]}


def bought_count(db, student_id):
    return db.execute("SELECT COUNT(*) FROM wardrobe_items WHERE student_id=?", (student_id,)).fetchone()[0]


def buy(db, student_id, key):
    """-> (ok, сообщение). Списывает монетки из сада."""
    from garden import get_garden
    item = ITEMS_BY_KEY.get(key)
    if not item:
        return False, "Такого наряда нет."
    if key in owned_keys(db, student_id):
        return False, "Он уже у тебя!"
    g = get_garden(db, student_id)
    if g["coins"] < item["cost"]:
        return False, f"Не хватает монеток: нужно {item['cost']}, а у тебя {g['coins']}."
    db.execute("UPDATE garden SET coins=coins-? WHERE student_id=?", (item["cost"], student_id))
    db.execute("INSERT OR IGNORE INTO wardrobe_items (student_id, item_key) VALUES (?, ?)", (student_id, key))
    db.execute("INSERT INTO wardrobe_wear (student_id, slot, item_key) VALUES (?, ?, ?) "
               "ON CONFLICT(student_id, slot) DO UPDATE SET item_key=excluded.item_key", (student_id, item["slot"], key))
    db.commit()
    return True, f"«{item['name']}» куплено и сразу надето! 🎉"


def wear(db, student_id, key):
    """Надеть купленное; повторное нажатие на надетое — снять. -> (ok, сообщение)."""
    item = ITEMS_BY_KEY.get(key)
    if not item or key not in owned_keys(db, student_id):
        return False, "Сначала это нужно купить."
    cur = outfit(db, student_id).get(item["slot"])
    if cur == key:
        db.execute("DELETE FROM wardrobe_wear WHERE student_id=? AND slot=?", (student_id, item["slot"]))
        msg = f"«{item['name']}» снято."
    else:
        db.execute("INSERT INTO wardrobe_wear (student_id, slot, item_key) VALUES (?, ?, ?) "
                   "ON CONFLICT(student_id, slot) DO UPDATE SET item_key=excluded.item_key", (student_id, item["slot"], key))
        msg = f"«{item['name']}» надето! ✨"
    db.commit()
    return True, msg
