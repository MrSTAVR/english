# -*- coding: utf-8 -*-
"""Фермерское производство ингредиентов для пиццы.

Отдельный слой: новые культуры, продукты переработки и кладовая. Пиццерия пока
работает на старом «бесплатном» складе; этот модуль готовит связку с фермой.
"""

# Культуры, которых не было на ферме. early=True — доступны сразу: пицца уже открыта
# с первого дня, и нечестно запирать её за уроками, которые ребёнок ещё не прошёл.
CROPS = {
    "wheat": {"en": "wheat", "plural": "wheat", "one": "wheat", "ru": "пшеница", "minutes": 8, "yield": 3, "early": True, "lesson": 70, "uncountable": True},
    "mushroom": {"en": "mushroom", "plural": "mushrooms", "one": "mushroom", "ru": "гриб", "minutes": 25, "yield": 3, "early": True, "lesson": 999},
    "basil": {"en": "basil", "plural": "basil", "one": "basil", "ru": "базилик", "minutes": 20, "yield": 3, "early": True, "lesson": 999, "uncountable": True},
    "oregano": {"en": "oregano", "plural": "oregano", "one": "oregano", "ru": "орегано", "minutes": 20, "yield": 3, "early": True, "lesson": 999, "uncountable": True},
    "lettuce": {"en": "lettuce", "plural": "lettuce", "one": "lettuce", "ru": "салат", "minutes": 15, "yield": 3, "early": True, "lesson": 999, "uncountable": True},
    "cherry_tomato": {"en": "cherry tomato", "plural": "cherry tomatoes", "one": "cherry tomato", "ru": "черри", "minutes": 12, "yield": 4, "early": True, "lesson": 999},
}

PRODUCTS = {
    "flour": {"en": "flour", "ru": "мука", "lesson": 70},
    "dough": {"en": "dough", "ru": "тесто", "lesson": 70},
    "tomato_sauce": {"en": "tomato sauce", "ru": "томатный соус", "lesson": 70},
    "cheese": {"en": "cheese", "ru": "сыр", "lesson": 70},
    "mozzarella": {"en": "mozzarella", "ru": "моцарелла", "lesson": 999},
    "parmesan": {"en": "parmesan", "ru": "пармезан", "lesson": 999},
    "caesar_sauce": {"en": "caesar sauce", "ru": "соус цезарь", "lesson": 999},
}

# Что производится на кухне/мельнице. Всё, чего нет на ферме (соль, дрожжи, масло,
# пепперони, курица), доступно в кладовой бесплатно.
PROCESS = {
    "flour": {"station": "mill", "need": {"wheat": 2}, "give": {"flour": 1},
              "en": "mill the wheat", "ru": "Смелить пшеницу в муку"},
    "dough": {"station": "kitchen", "need": {"flour": 2, "egg": 1, "water": 1}, "give": {"dough": 1},
              "en": "make the dough", "ru": "Замесить тесто"},
    "tomato_sauce": {"station": "kitchen", "need": {"tomato": 2}, "give": {"tomato_sauce": 1},
                     "en": "make tomato sauce", "ru": "Сделать томатный соус"},
    "cheese": {"station": "kitchen", "need": {"milk": 2}, "give": {"cheese": 1},
               "en": "make cheese", "ru": "Сделать сыр"},
    "mozzarella": {"station": "kitchen", "need": {"milk": 2}, "give": {"mozzarella": 1},
                   "en": "make mozzarella", "ru": "Сделать моцареллу"},
    "parmesan": {"station": "kitchen", "need": {"milk": 3}, "give": {"parmesan": 1},
                 "en": "make parmesan", "ru": "Сделать пармезан"},
    "caesar_sauce": {"station": "kitchen", "need": {"egg": 1, "parmesan": 1}, "give": {"caesar_sauce": 1},
                     "en": "make caesar sauce", "ru": "Сделать соус цезарь"},
}

# Бесплатная кладовая: этого на ферме не бывает (или не растим).
PANTRY = {
    "water": {"en": "water", "ru": "вода"},
    "salt": {"en": "salt", "ru": "соль"},
    "yeast": {"en": "yeast", "ru": "дрожжи"},
    "oil": {"en": "olive oil", "ru": "оливковое масло"},
    "pepperoni": {"en": "pepperoni", "ru": "пепперони"},
    "chicken": {"en": "chicken", "ru": "курица"},
}


def barn(db, student_id):
    return {r["item"]: r["qty"] for r in db.execute(
        "SELECT item, qty FROM farm_barn WHERE student_id=? AND qty>0", (student_id,)).fetchall()}


def _add(db, student_id, item, qty):
    db.execute("INSERT INTO farm_barn (student_id, item, qty) VALUES (?, ?, ?) "
               "ON CONFLICT(student_id, item) DO UPDATE SET qty=qty+excluded.qty",
               (student_id, item, qty))


def can_process(db, student_id, key, qty=1):
    if key not in PROCESS or qty < 1:
        return False
    have = barn(db, student_id)
    return all(have.get(item, 0) >= n * qty for item, n in PROCESS[key]["need"].items())


def process(db, student_id, key, qty=1):
    """Переработать продукты. Возвращает (ok, сообщение)."""
    if key not in PROCESS:
        return False, "Такого рецепта нет."
    if qty < 1:
        return False, "Нужно хотя бы одно."
    recipe = PROCESS[key]
    for item, need in recipe["need"].items():
        ok = db.execute(
            "UPDATE farm_barn SET qty=qty-? WHERE student_id=? AND item=? AND qty>=?",
            (need * qty, student_id, item, need * qty)).rowcount
        if ok != 1:
            db.rollback()
            return False, "Не хватает продуктов."
    for item, give in recipe["give"].items():
        _add(db, student_id, item, give * qty)
    db.commit()
    return True, recipe["ru"]


def known_items(ids):
    """Какие новые продукты уже знакомы ребёнку (по урокам; early — всегда)."""
    out = set(PANTRY)
    for key, c in CROPS.items():
        if c.get("early") or c["lesson"] in ids:
            out.add(key)
    for key in PROCESS:
        if key in ("flour", "dough", "tomato_sauce", "cheese"):
            out.add(key)       # слова из урока 70 «Рецепт пиццы»
    return out
