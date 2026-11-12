# -*- coding: utf-8 -*-
"""Пиццерия v1: четыре рецепта, шесть стадий, награда за первый рецепт.

Ассеты — PNG из low-poly движка (analytics/pizza-mockup/engine/out), лежат в static/pizza.
"""

import farm
import garden
import pizza_farm

COINS_FIRST = 3          # монеток за первый раз приготовленный рецепт
PIECES_MIN = 1           # сколько кусков на пицце — рисует фронтенд; бэкенд только проверяет
PIECES_MAX = 20

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
    "egg": 6, "milk": 12, "water": 4,
}

# Бабушкин запас раз в день: хватает на одну простую пиццу без коровы/фермы.
DAILY = {"milk": 4, "egg": 2, "flour": 2, "tomato": 2, "water": 2}


def ensure_starter(db, student_id):
    """Один раз выдать стартовый набор, чтобы пиццу можно было приготовить сразу."""
    now = farm.now().isoformat(timespec="seconds")
    cur = db.execute("INSERT OR IGNORE INTO pizza_starter (student_id, created_at) VALUES (?, ?)",
                     (student_id, now))
    if cur.rowcount != 1:
        return False
    for item, qty in STARTER.items():
        pizza_farm.add(db, student_id, item, qty)
    db.commit()
    return True


def ensure_daily(db, student_id):
    """Раз в день бабушка оставляет молоко, яйца, муку и помидоры — на одну пиццу."""
    t = farm.now()                               # farm.now() — чтобы тест мог подменить дату
    day = t.date().isoformat()
    now = t.isoformat(timespec="seconds")
    cur = db.execute("INSERT OR IGNORE INTO pizza_daily (student_id, day, created_at) VALUES (?, ?, ?)",
                     (student_id, day, now))
    if cur.rowcount != 1:
        return False
    for item, qty in DAILY.items():
        pizza_farm.add(db, student_id, item, qty)
    db.commit()
    return True


def stock(db, student_id):
    """Амбар для пиццерии: все продукты из рецептов (даже нулевые — фронтенду проще)."""
    have = pizza_farm.barn(db, student_id)
    return {k: have.get(k, 0) for k in sorted({i for n in NEEDS.values() for i in n})}


def recipe_status(db, student_id, key):
    have = pizza_farm.barn(db, student_id)
    need = []
    for item, qty in NEEDS[key].items():
        info = pizza_farm.PRODUCTS.get(item) or pizza_farm.CROPS.get(item) or {}
        need.append({"key": item, "en": info.get("en", item), "ru": info.get("ru", item),
                     "need": qty, "have": have.get(item, 0)})
    return need, all(n["have"] >= n["need"] for n in need)


def recipes_view(db, student_id, known=None):
    """Список рецептов для страницы и JS (с наличием продуктов и знакомством слов)."""
    if known is None:
        known = pizza_farm.known_items(farm.completed_ids(db, student_id))
    out = []
    for key, r in RECIPES.items():
        need, can = recipe_status(db, student_id, key)
        out.append({
            "key": key,
            "en": r["en"],
            "ru": r["ru"],
            "ingredients": [dict(i) for i in r["ingredients"]],
            # EN и RU показываем всегда, known — можно ли уже показывать слово как знакомое
            "toppings": [dict(i, known=i["key"] in known) for i in r["toppings"]],
            "need": need,
            "can": can,
        })
    return out


def completed(db, student_id):
    rows = db.execute("SELECT recipe FROM pizza_history WHERE student_id=?", (student_id,)).fetchall()
    return {r["recipe"] for r in rows}


def state(db, student_id):
    ensure_starter(db, student_id)
    ensure_daily(db, student_id)
    g = garden.get_garden(db, student_id)
    known = pizza_farm.known_items(farm.completed_ids(db, student_id))
    return {
        "coins": g["coins"],
        "completed": sorted(completed(db, student_id)),
        "recipes": recipes_view(db, student_id, known),
        "stock": stock(db, student_id),
        "reward": COINS_FIRST,
    }


def _pieces_ok(pieces):
    """Кусков на пицце: не передали — пусть решает фронтенд; передали — только 1..20."""
    if pieces is None:
        return True
    return isinstance(pieces, int) and not isinstance(pieces, bool) and PIECES_MIN <= pieces <= PIECES_MAX


def finish(db, student_id, recipe, pieces=None):
    """Приготовить рецепт: списать фермерские продукты, начислить монетки за первый раз.

    Повторный запрос по уже приготовленному рецепту (pizza_history) — идемпотентный:
    продукты не списываются, монетки не начисляются, ответ ok с already_done=True.
    При нехватке продуктов — ничего не списываем (rollback) и отдаём missing.
    """
    if not _pieces_ok(pieces):
        return {"ok": False, "error": "bad_pieces",
                "message": f"Кусков должно быть от {PIECES_MIN} до {PIECES_MAX}."}
    if recipe not in RECIPES:
        return {"ok": False, "error": "unknown_recipe", "message": "Такого рецепта нет."}

    coins = garden.get_garden(db, student_id)["coins"]
    if recipe in completed(db, student_id):
        # Уже готовили: второй раз ничего не тратим и не награждаем (двойное нажатие, ретрай).
        return {"ok": True, "gained": 0, "already": True, "already_done": True,
                "coins": coins, "missing": []}

    ensure_starter(db, student_id)
    ensure_daily(db, student_id)

    have = pizza_farm.barn(db, student_id)
    missing = [item for item, qty in NEEDS[recipe].items() if have.get(item, 0) < qty]
    if missing:
        return {"ok": False, "error": "missing_products", "missing": missing,
                "message": "Не хватает продуктов для пиццы."}

    for item, qty in NEEDS[recipe].items():
        if db.execute("UPDATE farm_barn SET qty=qty-? WHERE student_id=? AND item=? AND qty>=?",
                      (qty, student_id, item, qty)).rowcount != 1:
            db.rollback()                   # не хватило между проверкой и списанием — всё вернуть
            return {"ok": False, "error": "missing_products", "missing": [item],
                    "message": "Не хватает продуктов для пиццы."}

    now = farm.now().isoformat(timespec="seconds")
    cur = db.execute(
        "INSERT OR IGNORE INTO pizza_history (student_id, recipe, created_at) VALUES (?, ?, ?)",
        (student_id, recipe, now))
    if cur.rowcount != 1:                   # параллельный запрос уже записал рецепт
        db.rollback()                       # вернуть списанные продукты
        return {"ok": True, "gained": 0, "already": True, "already_done": True,
                "coins": garden.get_garden(db, student_id)["coins"], "missing": []}

    # award_coins — только про тесты (COIN_PASS/PERFECT по attempts) и дал бы 10 монеток вместо 3,
    # поэтому разовую награду пишем через общий учёт garden.credit_coins (одно место смены coins).
    garden.credit_coins(db, student_id, COINS_FIRST, commit=False)
    db.commit()
    return {"ok": True, "gained": COINS_FIRST, "already": False, "already_done": False,
            "coins": garden.get_garden(db, student_id)["coins"], "missing": []}


def forget_student(db, student_id):
    db.execute("DELETE FROM pizza_history WHERE student_id=?", (student_id,))
    db.execute("DELETE FROM pizza_starter WHERE student_id=?", (student_id,))
    db.execute("DELETE FROM pizza_daily WHERE student_id=?", (student_id,))
