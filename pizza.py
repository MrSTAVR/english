# -*- coding: utf-8 -*-
"""Пиццерия v1: четыре рецепта, шесть стадий, награда за первый рецепт.

Ассеты — PNG из low-poly движка (analytics/pizza-mockup/engine/out), лежат в static/pizza.
"""

from datetime import datetime

import garden

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


def recipes_view():
    """Список рецептов для страницы и JS (без мутаций данных)."""
    out = []
    for key, r in RECIPES.items():
        out.append({
            "key": key,
            "en": r["en"],
            "ru": r["ru"],
            "ingredients": [dict(i) for i in r["ingredients"]],
            "toppings": [dict(i) for i in r["toppings"]],
        })
    return out


def completed(db, student_id):
    rows = db.execute("SELECT recipe FROM pizza_history WHERE student_id=?", (student_id,)).fetchall()
    return {r["recipe"] for r in rows}


def state(db, student_id):
    g = garden.get_garden(db, student_id)
    return {
        "coins": g["coins"],
        "completed": sorted(completed(db, student_id)),
        "recipes": recipes_view(),
        "reward": COINS_FIRST,
    }


def finish(db, student_id, recipe):
    """Завершить рецепт. Возвращает (ok, gained, already, coins).

    История, сад и монеты — в одной транзакции: PK не даёт наградить рецепт дважды,
    а сбой на любом шаге не оставляет строку без монет.
    """
    if recipe not in RECIPES:
        return False, 0, False, 0
    now = datetime.now().isoformat(timespec="seconds")
    cur = db.execute(
        "INSERT OR IGNORE INTO pizza_history (student_id, recipe, created_at) VALUES (?, ?, ?)",
        (student_id, recipe, now))
    if cur.rowcount != 1:
        db.rollback()
        coins = db.execute("SELECT coins FROM garden WHERE student_id=?", (student_id,)).fetchone()
        return True, 0, True, coins["coins"] if coins else 0
    db.execute("INSERT OR IGNORE INTO garden (student_id) VALUES (?)", (student_id,))
    db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?", (COINS_FIRST, student_id))
    db.commit()
    row = db.execute("SELECT coins FROM garden WHERE student_id=?", (student_id,)).fetchone()
    return True, COINS_FIRST, False, row["coins"]
def forget_student(db, student_id):
    db.execute("DELETE FROM pizza_history WHERE student_id=?", (student_id,))
