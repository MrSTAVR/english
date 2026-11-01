# -*- coding: utf-8 -*-
"""Пиццерия v1: четыре рецепта, шесть стадий, награда за первый рецепт.

Ассеты — PNG из low-poly движка (analytics/pizza-mockup/engine/out), лежат в static/pizza.
"""

from datetime import datetime

import garden
import pizza_farm

COINS_FIRST = 3          # монеток за первый раз приготовленный рецепт

# Ключ -> название, ингредиенты для подсказки и начинки на пицце.
RECIPES = {
    "margherita": {
        "en": "Margherita",
        "ru": "Маргарита",
        "ingredients": [
            {"key": "mozzarella", "en": "mozzarella", "ru": "моцарелла"},
            {"key": "tomato_sauce", "en": "tomato sauce", "ru": "томатный соус"},
            {"key": "basil", "en": "basil", "ru": "базилик"},
        ],
        "toppings": [
            {"key": "basil", "en": "basil", "ru": "базилик"},
            {"key": "cherry_tomato", "en": "cherry tomato", "ru": "черри"},
        ],
    },
    "pepperoni": {
        "en": "Pepperoni",
        "ru": "Пепперони",
        "ingredients": [
            {"key": "mozzarella", "en": "mozzarella", "ru": "моцарелла"},
            {"key": "tomato_sauce", "en": "tomato sauce", "ru": "томатный соус"},
            {"key": "pepperoni", "en": "pepperoni", "ru": "пепперони"},
        ],
        "toppings": [
            {"key": "pepperoni", "en": "pepperoni", "ru": "пепперони"},
        ],
    },
    "mushroom": {
        "en": "Mushroom",
        "ru": "Грибная",
        "ingredients": [
            {"key": "mozzarella", "en": "mozzarella", "ru": "моцарелла"},
            {"key": "tomato_sauce", "en": "tomato sauce", "ru": "томатный соус"},
            {"key": "mushroom", "en": "mushrooms", "ru": "грибы"},
            {"key": "oregano", "en": "oregano", "ru": "орегано"},
        ],
        "toppings": [
            {"key": "mushroom", "en": "mushrooms", "ru": "грибы"},
            {"key": "oregano", "en": "oregano", "ru": "орегано"},
        ],
    },
    "caesar": {
        "en": "Caesar",
        "ru": "Цезарь",
        "ingredients": [
            {"key": "mozzarella", "en": "mozzarella", "ru": "моцарелла"},
            {"key": "caesar_sauce", "en": "caesar sauce", "ru": "соус цезарь"},
            {"key": "chicken", "en": "chicken", "ru": "курица"},
            {"key": "lettuce", "en": "lettuce", "ru": "салат"},
            {"key": "parmesan", "en": "parmesan", "ru": "пармезан"},
        ],
        "toppings": [
            {"key": "chicken", "en": "chicken", "ru": "курица"},
            {"key": "lettuce", "en": "lettuce", "ru": "салат"},
            {"key": "parmesan", "en": "parmesan", "ru": "пармезан"},
            {"key": "cherry_tomato", "en": "cherry tomato", "ru": "черри"},
        ],
    },
}


# Что нужно для рецепта из фермерских продуктов. Пепперони/курица — кладовая, не тратятся.
NEEDS = {
    "margherita": {"dough": 1, "tomato_sauce": 1, "mozzarella": 2, "basil": 1, "cherry_tomato": 2},
    "pepperoni": {"dough": 1, "tomato_sauce": 1, "mozzarella": 2},
    "mushroom": {"dough": 1, "tomato_sauce": 1, "mozzarella": 2, "mushroom": 3, "oregano": 1},
    "caesar": {"dough": 1, "caesar_sauce": 1, "mozzarella": 1, "lettuce": 2, "parmesan": 1, "cherry_tomato": 2},
}

# Стартовый набор бабушкиной кухни: хватает на одну пиццу каждого рецепта.
STARTER = {
    "dough": 4, "tomato_sauce": 3, "mozzarella": 8, "caesar_sauce": 1,
    "basil": 1, "cherry_tomato": 4, "mushroom": 3, "oregano": 1, "lettuce": 2, "parmesan": 1,
}


def _barn(db, student_id):
    return {r["item"]: r["qty"] for r in db.execute(
        "SELECT item, qty FROM farm_barn WHERE student_id=? AND qty>0", (student_id,)).fetchall()}


def _add(db, student_id, item, qty):
    db.execute("INSERT INTO farm_barn (student_id, item, qty) VALUES (?, ?, ?) "
               "ON CONFLICT(student_id, item) DO UPDATE SET qty=qty+excluded.qty",
               (student_id, item, qty))


def ensure_starter(db, student_id):
    """Один раз выдать стартовый набор, чтобы пиццу можно было приготовить сразу."""
    now = datetime.now().isoformat(timespec="seconds")
    cur = db.execute("INSERT OR IGNORE INTO pizza_starter (student_id, created_at) VALUES (?, ?)",
                     (student_id, now))
    if cur.rowcount != 1:
        return False
    for item, qty in STARTER.items():
        _add(db, student_id, item, qty)
    db.commit()
    return True


def stock(db, student_id):
    have = _barn(db, student_id)
    return {k: have.get(k, 0) for k in {i for n in NEEDS.values() for i in n}}


def recipe_status(db, student_id, key):
    have = _barn(db, student_id)
    need = []
    for item, qty in NEEDS[key].items():
        info = pizza_farm.PRODUCTS.get(item) or pizza_farm.CROPS.get(item) or {}
        need.append({"key": item, "en": info.get("en", item), "ru": info.get("ru", item),
                     "need": qty, "have": have.get(item, 0)})
    return need, all(n["have"] >= n["need"] for n in need)


def recipes_view(db, student_id):
    """Список рецептов для страницы и JS (с наличием продуктов)."""
    out = []
    for key, r in RECIPES.items():
        need, can = recipe_status(db, student_id, key)
        out.append({
            "key": key,
            "en": r["en"],
            "ru": r["ru"],
            "ingredients": [dict(i) for i in r["ingredients"]],
            "toppings": [dict(i) for i in r["toppings"]],
            "need": need,
            "can": can,
        })
    return out


def recipes_config():
    """Статическая часть рецептов (для тестов и данных)."""
    return [{"key": k, "en": r["en"], "ru": r["ru"]} for k, r in RECIPES.items()]


def completed(db, student_id):
    rows = db.execute("SELECT recipe FROM pizza_history WHERE student_id=?", (student_id,)).fetchall()
    return {r["recipe"] for r in rows}


def state(db, student_id):
    ensure_starter(db, student_id)
    g = garden.get_garden(db, student_id)
    return {
        "coins": g["coins"],
        "completed": sorted(completed(db, student_id)),
        "recipes": recipes_view(db, student_id),
        "stock": stock(db, student_id),
        "reward": COINS_FIRST,
    }


def finish(db, student_id, recipe):
    """Приготовить рецепт: списать фермерские продукты, начислить монетки за первый раз.

    Возвращает (ok, gained, already, coins, missing). Продукты списываются всегда,
    даже при повторе; при нехватке — откат и список missing.
    """
    if recipe not in RECIPES:
        return False, 0, False, 0, []
    ensure_starter(db, student_id)
    missing = []
    have = _barn(db, student_id)
    for item, qty in NEEDS[recipe].items():
        if have.get(item, 0) < qty:
            missing.append(item)
    if missing:
        return False, 0, False, 0, missing
    for item, qty in NEEDS[recipe].items():
        if db.execute("UPDATE farm_barn SET qty=qty-? WHERE student_id=? AND item=? AND qty>=?",
                      (qty, student_id, item, qty)).rowcount != 1:
            db.rollback()
            return False, 0, False, 0, [item]
    now = datetime.now().isoformat(timespec="seconds")
    cur = db.execute(
        "INSERT OR IGNORE INTO pizza_history (student_id, recipe, created_at) VALUES (?, ?, ?)",
        (student_id, recipe, now))
    if cur.rowcount != 1:
        db.commit()
        coins = db.execute("SELECT coins FROM garden WHERE student_id=?", (student_id,)).fetchone()
        return True, 0, True, coins["coins"] if coins else 0, []
    db.execute("INSERT OR IGNORE INTO garden (student_id) VALUES (?)", (student_id,))
    db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?", (COINS_FIRST, student_id))
    db.commit()
    row = db.execute("SELECT coins FROM garden WHERE student_id=?", (student_id,)).fetchone()
    return True, COINS_FIRST, False, row["coins"], []


def forget_student(db, student_id):
    db.execute("DELETE FROM pizza_history WHERE student_id=?", (student_id,))
    db.execute("DELETE FROM pizza_starter WHERE student_id=?", (student_id,))
