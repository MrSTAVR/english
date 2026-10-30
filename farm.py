# -*- coding: utf-8 -*-
"""Ферма бабушки Тома (замена замка и сада, AGENTS.md → «Ферма»).

Капли воды — топливо фермы, даются только за учёбу (on_test, on_goal_done, on_review, on_game);
мелкие награды (старание, «Исправь ошибки», повторение, игры) — не больше SMALL_CAP в день.
Грядки: посадка бесплатно, полив WATER_COST капель запускает рост; урожай не вянет и ждёт сколько угодно.
Животные: корм FEED_COST капель → через время продукт (яйца, молоко). Амбар — собранное.
Заказы от Tom / Anna / Grandma по-английски: до ORDERS_PER_DAY новых в день, не сгорают;
ученица сама выбирает, что отдать (fulfil), неверный выбор — без штрафа. Монетки — общие (garden.coins).
"""
import json
import math
import random
from datetime import date, datetime, timedelta

DROPS_PASS = 12          # урок/сцена сдана впервые
DROPS_PERFECT = 3        # + за 100% с первой попытки (не после «Исправь ошибки»)
DROPS_GOAL = 4           # цель дня
DROPS_EFFORT = 4         # «за старание»: не сдан, но от EFFORT_MIN%
DROPS_FIX = 3            # «Исправь ошибки» сдано — раз в день на урок
DROPS_REVIEW = 3         # каждые REVIEW_EVERY слов повторения за день
REVIEW_EVERY = 10
DROPS_GAME = 1           # игра хотя бы на 1 звезду
SMALL_CAP = 10           # мелких капель (старание, исправление, повторение, игры) — не больше в день
EFFORT_MIN = 40
SMALL = ("effort", "fix", "review", "game")

WATER_COST = 2
FEED_COST = 2
PLOTS = 6                # грядок с начала
PLOT_COSTS = [40, 70, 100]   # грядки 7–9 — за монетки (сток монеток вместо замка)
ORDERS_PER_DAY = 3       # новые заказы открывает учёба дня: занятие / сданный урок / цель дня (order_slots)
ORDER_BASE = 1           # монеток за заказ: 1 + половина «веса» вещей (молоко весит 2), чтобы заказ не стоил больше урока
WEEK_GOAL = 12           # заказов за неделю (пн–вс)
WEEK_COINS = 10
WORDS_LESSON = 19        # названия культур — после урока «Фрукты и овощи» (до него в заказе картинка и число)
COWSHED_COST = 120       # коровник — монетки, после урока «Домашние животные»
COW_LESSON = 17

# культуры: время роста (мин), сколько собираем, с какого числа пройденных уроков открыты
CROPS = {
    "carrot": {"en": "carrot", "plural": "carrots", "ru": "морковка", "minutes": 3, "yield": 3, "from": 0},
    "tomato": {"en": "tomato", "plural": "tomatoes", "ru": "помидор", "minutes": 10, "yield": 3, "from": 0},
    "potato": {"en": "potato", "plural": "potatoes", "ru": "картошка", "minutes": 180, "yield": 4, "from": 5},
    "apple": {"en": "apple", "plural": "apples", "ru": "яблоко", "minutes": 360, "yield": 5, "from": 10},
    "peach": {"en": "peach", "plural": "peaches", "ru": "персик", "minutes": 720, "yield": 5, "from": 20},
    "corn": {"en": "corn", "plural": "corn cobs", "one": "corn cob", "ru": "кукуруза", "minutes": 240, "yield": 4, "from": 30},
    "pumpkin": {"en": "pumpkin", "plural": "pumpkins", "ru": "тыква", "minutes": 600, "yield": 2, "from": 40},
}
ANIMALS = {
    "chicken": {"en": "chicken", "ru": "курица", "product": "egg", "minutes": 20, "yield": 3},
    "cow": {"en": "cow", "ru": "корова", "product": "milk", "minutes": 120, "yield": 2},
}
PRODUCTS = {"egg": {"en": "egg", "plural": "eggs", "ru": "яйцо"}, "milk": {"en": "milk", "plural": "bottles of milk",
                                                                         "ru": "бутылка молока", "one": "bottle of milk"}}
GIVERS = ["Grandma", "Tom", "Anna"]
NUMBERS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
NUMBERS_LESSON = 10      # числа словом — после урока «Цифры 1–10», до него — цифрами


def now():
    return datetime.now()


def _today():
    return now().date()


def _stamp(t=None):
    return (t or now()).isoformat(timespec="seconds")


# ── капли ──

def drops(db, student_id):
    r = db.execute("SELECT COALESCE(SUM(amount), 0) FROM farm_drops WHERE student_id=?", (student_id,)).fetchone()
    return r[0]


def _small_today(db, student_id, day):
    marks = ",".join("?" * len(SMALL))
    return db.execute(f"SELECT COALESCE(SUM(amount), 0) FROM farm_drops WHERE student_id=? AND day=? AND reason IN ({marks})",
                      (student_id, day.isoformat(), *SMALL)).fetchone()[0]


def give(db, student_id, reason, ref, amount):
    """Начисляет капли один раз на (reason, ref); мелкие — в пределах SMALL_CAP за день. Возвращает начислено."""
    day = _today()
    if reason in SMALL:
        amount = min(amount, SMALL_CAP - _small_today(db, student_id, day))
    if amount <= 0:
        return 0
    cur = db.execute("INSERT OR IGNORE INTO farm_drops (student_id, day, reason, ref, amount, at) VALUES (?, ?, ?, ?, ?, ?)",
                     (student_id, day.isoformat(), reason, str(ref), amount, _stamp()))
    db.commit()
    return amount if cur.rowcount else 0


def _spend(db, student_id, reason, ref, amount):
    """Списать капли, только если их хватает — одной командой (без «проверил, потом записал»)."""
    cur = db.execute(
        "INSERT INTO farm_drops (student_id, day, reason, ref, amount, at) SELECT ?, ?, ?, ?, ?, ? "
        "WHERE (SELECT COALESCE(SUM(amount), 0) FROM farm_drops WHERE student_id=?) >= ?",
        (student_id, _today().isoformat(), reason, f"{ref}@{_stamp()}#{random.random():.6f}", -amount, _stamp(),
         student_id, amount))
    return cur.rowcount == 1


def set_drops(db, student_id, value):
    """Администратор выставляет число капель (поправка reason='admin')."""
    delta = max(0, int(value)) - drops(db, student_id)
    if delta:
        db.execute("INSERT INTO farm_drops (student_id, day, reason, ref, amount, at) VALUES (?, ?, 'admin', ?, ?, ?)",
                   (student_id, _today().isoformat(), f"{_stamp()}#{random.random():.6f}", delta, _stamp()))
        db.commit()


def on_test(db, student_id, lesson_id, attempt_id, percent, passed, first_pass, fixed, first_try):
    """Капли за тест/сцену урока. first_try — это первая попытка в этом уроке."""
    if passed and first_pass:
        got = give(db, student_id, "lesson", lesson_id, DROPS_PASS)
        if percent == 100 and first_try and not fixed:
            got += give(db, student_id, "perfect", lesson_id, DROPS_PERFECT)
        return got
    if passed:                                             # пересдача уже сданного — капель нет
        return give(db, student_id, "fix", f"{lesson_id}:{_today().isoformat()}", DROPS_FIX) if fixed else 0
    if percent >= EFFORT_MIN:
        return give(db, student_id, "effort", f"{lesson_id}:{_today().isoformat()}", DROPS_EFFORT)
    return 0


def on_goal_done(db, student_id, day=None):
    return give(db, student_id, "goal", (day or _today()).isoformat(), DROPS_GOAL)


def on_review(db, student_id, words_today):
    """После очередного слова повторения: каждые REVIEW_EVERY слов за день — капли."""
    if words_today and words_today % REVIEW_EVERY == 0:
        return give(db, student_id, "review", f"{_today().isoformat()}:{words_today}", DROPS_REVIEW)
    return 0


def on_game(db, student_id, stars):
    if stars < 1:
        return 0
    return give(db, student_id, "game", _stamp() + f"#{random.random():.6f}", DROPS_GAME)


# ── грядки ──

def lessons_done(db, student_id):
    from stats import compute_stats
    return compute_stats(db, student_id)["lessons_completed"]


def open_crops(done):
    return [k for k, c in CROPS.items() if done >= c["from"]]


def _plot_rows(db, student_id):
    return {r["slot"]: r for r in db.execute("SELECT * FROM farm_plots WHERE student_id=?", (student_id,)).fetchall()}


def plot_state(row, t=None):
    """empty / planted (ждёт полива) / growing / ready."""
    if row is None or not row["crop"]:
        return "empty"
    if not row["ready_at"]:
        return "planted"
    return "ready" if datetime.fromisoformat(row["ready_at"]) <= (t or now()) else "growing"


def plots_count(db, student_id):
    extra = db.execute("SELECT COUNT(*) FROM farm_plots WHERE student_id=? AND slot>=?", (student_id, PLOTS)).fetchone()[0]
    return PLOTS + extra


def buy_plot(db, student_id):
    """Ещё одна грядка за монетки (до PLOTS + len(PLOT_COSTS)): купленная — пустая строка в farm_plots."""
    from garden import get_garden
    n = plots_count(db, student_id) - PLOTS
    if n >= len(PLOT_COSTS):
        return False, "Больше грядок не поместится."
    cost = PLOT_COSTS[n]
    get_garden(db, student_id)
    if db.execute("UPDATE garden SET coins=coins-? WHERE student_id=? AND coins>=?", (cost, student_id, cost)).rowcount != 1:
        return False, f"Нужно {cost} монеток."
    if db.execute("INSERT OR IGNORE INTO farm_plots (student_id, slot) VALUES (?, ?)", (student_id, PLOTS + n)).rowcount != 1:
        db.rollback()                                      # второе нажатие — грядка уже куплена
        return False, "Грядка уже куплена."
    db.commit()
    return True, ""


def plant(db, student_id, slot, crop, done=None):
    if not 0 <= slot < plots_count(db, student_id) or crop not in CROPS:
        return False, "Такой грядки или семян нет."
    done = lessons_done(db, student_id) if done is None else done
    if crop not in open_crops(done):
        return False, "Эти семена откроются позже — проходи уроки!"
    cur = db.execute("INSERT INTO farm_plots (student_id, slot, crop, planted_at, ready_at) VALUES (?, ?, ?, ?, NULL) "
                     "ON CONFLICT(student_id, slot) DO UPDATE SET crop=excluded.crop, planted_at=excluded.planted_at, ready_at=NULL "
                     "WHERE farm_plots.crop IS NULL", (student_id, slot, crop, _stamp()))
    db.commit()
    return (True, "") if cur.rowcount == 1 else (False, "Грядка занята.")


def water(db, student_id, slot):
    row = _plot_rows(db, student_id).get(slot)
    if plot_state(row) != "planted":
        return False, "Здесь нечего поливать."
    ready = now() + timedelta(minutes=CROPS[row["crop"]]["minutes"])
    cur = db.execute("UPDATE farm_plots SET ready_at=? WHERE student_id=? AND slot=? AND crop IS NOT NULL AND ready_at IS NULL",
                     (_stamp(ready), student_id, slot))
    if cur.rowcount != 1:                                  # уже полито (второе нажатие)
        db.rollback()
        return False, "Здесь нечего поливать."
    if not _spend(db, student_id, "water", slot, WATER_COST):
        db.rollback()
        return False, f"Нужно {drops_words(WATER_COST)}. Капли дают за уроки!"
    db.commit()
    return True, ""


def _add_barn(db, student_id, item, qty):
    db.execute("INSERT INTO farm_barn (student_id, item, qty) VALUES (?, ?, ?) "
               "ON CONFLICT(student_id, item) DO UPDATE SET qty=qty+excluded.qty", (student_id, item, qty))


def harvest(db, student_id, slot):
    row = _plot_rows(db, student_id).get(slot)
    if plot_state(row) != "ready":
        return False, 0
    cur = db.execute("UPDATE farm_plots SET crop=NULL, planted_at=NULL, ready_at=NULL "
                     "WHERE student_id=? AND slot=? AND crop=? AND ready_at IS NOT NULL AND ready_at<=?",
                     (student_id, slot, row["crop"], _stamp()))
    if cur.rowcount != 1:                                  # уже собрано (второе нажатие)
        db.rollback()
        return False, 0
    n = CROPS[row["crop"]]["yield"]
    _add_barn(db, student_id, row["crop"], n)
    db.commit()
    return True, n


def harvest_all(db, student_id):
    """Собрать все поспевшие грядки сразу. Возвращает {культура: сколько}."""
    got = {}
    for slot, row in _plot_rows(db, student_id).items():
        if plot_state(row) == "ready":
            ok, n = harvest(db, student_id, slot)
            if ok:
                got[row["crop"]] = got.get(row["crop"], 0) + n
    return got


# ── животные ──

def has_animal(db, student_id, kind):
    if kind == "chicken":
        return True                                        # курица есть с самого начала
    return db.execute("SELECT 1 FROM farm_animals WHERE student_id=? AND kind=?", (student_id, kind)).fetchone() is not None


def can_buy_cow(stats):
    return COW_LESSON in stats["completed_ids"]


def buy_cow(db, student_id, stats):
    from garden import get_garden
    if has_animal(db, student_id, "cow"):
        return False, "Корова уже есть."
    if not can_buy_cow(stats):
        return False, "Коровник откроется после урока «Домашние животные»."
    get_garden(db, student_id)
    paid = db.execute("UPDATE garden SET coins=coins-? WHERE student_id=? AND coins>=?", (COWSHED_COST, student_id, COWSHED_COST))
    if paid.rowcount != 1:
        return False, f"Нужно {COWSHED_COST} монеток."
    if db.execute("INSERT OR IGNORE INTO farm_animals (student_id, kind) VALUES (?, 'cow')", (student_id,)).rowcount != 1:
        db.rollback()
        return False, "Корова уже есть."
    db.commit()
    return True, ""


def _animal_row(db, student_id, kind):
    r = db.execute("SELECT * FROM farm_animals WHERE student_id=? AND kind=?", (student_id, kind)).fetchone()
    if r is None and kind == "chicken":
        db.execute("INSERT OR IGNORE INTO farm_animals (student_id, kind) VALUES (?, 'chicken')", (student_id,))
        r = db.execute("SELECT * FROM farm_animals WHERE student_id=? AND kind=?", (student_id, kind)).fetchone()
    return r


def animal_state(row, t=None):
    """hungry / busy (продукт ещё не готов) / ready."""
    if row is None or not row["ready_at"]:
        return "hungry"
    return "ready" if datetime.fromisoformat(row["ready_at"]) <= (t or now()) else "busy"


def feed(db, student_id, kind):
    if kind not in ANIMALS or not has_animal(db, student_id, kind):
        return False, "Такого животного пока нет."
    row = _animal_row(db, student_id, kind)
    if animal_state(row) != "hungry":
        return False, "Уже сыта!"
    ready = now() + timedelta(minutes=ANIMALS[kind]["minutes"])
    cur = db.execute("UPDATE farm_animals SET fed_at=?, ready_at=? WHERE student_id=? AND kind=? AND ready_at IS NULL",
                     (_stamp(), _stamp(ready), student_id, kind))
    if cur.rowcount != 1:
        db.rollback()
        return False, "Уже сыта!"
    if not _spend(db, student_id, "feed", kind, FEED_COST):
        db.rollback()
        return False, f"Нужно {drops_words(FEED_COST)}. Капли дают за уроки!"
    db.commit()
    return True, ""


def collect(db, student_id, kind):
    row = _animal_row(db, student_id, kind) if kind in ANIMALS else None
    if animal_state(row) != "ready":
        return False, 0
    a = ANIMALS[kind]
    cur = db.execute("UPDATE farm_animals SET fed_at=NULL, ready_at=NULL WHERE student_id=? AND kind=? "
                     "AND ready_at IS NOT NULL AND ready_at<=?", (student_id, kind, _stamp()))
    if cur.rowcount != 1:
        db.rollback()
        return False, 0
    _add_barn(db, student_id, a["product"], a["yield"])
    db.commit()
    return True, a["yield"]


def barn(db, student_id):
    return {r["item"]: r["qty"] for r in db.execute("SELECT item, qty FROM farm_barn WHERE student_id=? AND qty>0",
                                                     (student_id,)).fetchall()}


# ── заказы ──

def item_info(item):
    return CROPS.get(item) or PRODUCTS[item]


def _phrase(item, n, words):
    info = item_info(item)
    num = NUMBERS[n] if words else str(n)
    name = info["plural"] if n > 1 else info.get("one", info["en"])
    if n == 1 and words:
        num = "an" if name[0] in "aeiou" else "a"
    return f"{num} {name}"


def order_text(giver, items, words):
    parts = [_phrase(k, n, words) for k, n in items.items()]
    what = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    who = {"Grandma": "Grandma needs", "Tom": "Tom needs", "Anna": "Anna needs"}[giver]
    return f"{who} {what}."


def order_ru(giver, items):
    who = {"Grandma": "Бабушке", "Tom": "Тому", "Anna": "Анне"}[giver]
    return who + " нужно: " + ", ".join(f"{item_info(k)['ru']} — {n}" for k, n in items.items()) + "."


def producible(db, student_id, done):
    out = open_crops(done) + ["egg"]
    if has_animal(db, student_id, "cow"):
        out.append("milk")
    return out


def _new_order(db, student_id, day, k, done):
    rng = random.Random(f"{student_id}:{day.isoformat()}:{k}")
    pool = producible(db, student_id, done)
    kinds = rng.sample(pool, min(len(pool), 1 if rng.random() < 0.6 or done < 5 else 2))
    items = {it: rng.randint(1, 2 if it == "milk" else 3 if done < 10 else 5) for it in kinds}
    giver = GIVERS[(k + day.toordinal()) % len(GIVERS)]
    coins = order_coins(items)
    db.execute("INSERT OR IGNORE INTO farm_orders (student_id, day, k, giver, items_json, coins, created_at) "
               "VALUES (?, ?, ?, ?, ?, ?, ?)",
               (student_id, day.isoformat(), k, giver, json.dumps(items), coins, _stamp()))


def order_slots(db, student_id, day=None):
    """Сколько новых заказов открыла учёба сегодня: занятие, сданный урок, выполненная цель дня."""
    d = (day or _today()).isoformat()
    row = db.execute("SELECT lessons, words FROM daily_goal WHERE student_id=? AND day=?", (student_id, d)).fetchone()
    studied = bool(db.execute("SELECT 1 FROM activity WHERE student_id=? AND day=?", (student_id, d)).fetchone())         or bool(row and (row["lessons"] or row["words"]))
    lesson = db.execute("SELECT 1 FROM attempts WHERE student_id=? AND passed=1 AND substr(finished_at, 1, 10)=?",
                        (student_id, d)).fetchone()
    goal = db.execute("SELECT 1 FROM daily_goal WHERE student_id=? AND day=? AND done=1", (student_id, d)).fetchone()
    return int(studied) + int(bool(lesson)) + int(bool(goal))


def order_coins(items):
    weight = sum((2 if it == "milk" else 1) * n for it, n in items.items())
    return ORDER_BASE + math.ceil(weight / 2)


def orders(db, student_id, done=None, stats=None):
    """Открытые заказы; новые за сегодня создаются здесь — сколько открыла учёба (order_slots),
    всего открытых не больше ORDERS_PER_DAY. Невыполненные не сгорают."""
    done = lessons_done(db, student_id) if done is None else done
    day = _today()
    made = db.execute("SELECT COUNT(*) FROM farm_orders WHERE student_id=? AND day=?",
                      (student_id, day.isoformat())).fetchone()[0]
    open_n = db.execute("SELECT COUNT(*) FROM farm_orders WHERE student_id=? AND done_at IS NULL", (student_id,)).fetchone()[0]
    k = made
    allowed = min(ORDERS_PER_DAY, order_slots(db, student_id, day))
    while open_n < ORDERS_PER_DAY and k < allowed:
        _new_order(db, student_id, day, k, done)
        k += 1
        open_n += 1
    db.commit()
    words = _numbers_known(db, student_id, stats)
    names = _names_known(db, student_id, stats)
    out = []
    for r in db.execute("SELECT * FROM farm_orders WHERE student_id=? AND done_at IS NULL ORDER BY id", (student_id,)):
        items = json.loads(r["items_json"])
        out.append({"id": r["id"], "giver": r["giver"], "items": items, "coins": r["coins"], "names": names,
                    "en": order_text(r["giver"], items, words), "ru": order_ru(r["giver"], items)})
    return out


def _names_known(db, student_id, stats=None):
    """Названия культур уже пройдены — в заказе можно без картинки (иначе картинка + число)."""
    if stats is None:
        from stats import compute_stats
        stats = compute_stats(db, student_id)
    return WORDS_LESSON in stats["completed_ids"]


def _numbers_known(db, student_id, stats=None):
    if stats is None:
        from stats import compute_stats
        stats = compute_stats(db, student_id)
    return NUMBERS_LESSON in stats["completed_ids"]


def fulfil(db, student_id, order_id, given):
    """given — {товар: сколько} — что ученица выбрала. Верно → товар из амбара, монетки; неверно — без штрафа."""
    r = db.execute("SELECT * FROM farm_orders WHERE id=? AND student_id=? AND done_at IS NULL", (order_id, student_id)).fetchone()
    if not r:
        return {"ok": False, "why": "gone"}
    need = json.loads(r["items_json"])
    given = {k: int(v) for k, v in (given or {}).items() if int(v) > 0}
    if given != need:
        return {"ok": False, "why": "wrong"}
    have = barn(db, student_id)
    if any(have.get(k, 0) < n for k, n in need.items()):
        return {"ok": False, "why": "short"}
    from garden import get_garden
    get_garden(db, student_id)
    if db.execute("UPDATE farm_orders SET done_at=? WHERE id=? AND done_at IS NULL", (_stamp(), order_id)).rowcount != 1:
        return {"ok": False, "why": "gone"}                # второе нажатие «Отдать»
    for k, n in need.items():
        if db.execute("UPDATE farm_barn SET qty=qty-? WHERE student_id=? AND item=? AND qty>=?",
                      (n, student_id, k, n)).rowcount != 1:
            db.rollback()
            return {"ok": False, "why": "short"}
    coins = r["coins"]
    week = week_done(db, student_id)
    bonus = WEEK_COINS if week == WEEK_GOAL else 0         # ровно на WEEK_GOAL-м заказе недели — один раз
    db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?", (coins + bonus, student_id))
    db.commit()
    return {"ok": True, "coins": coins, "bonus": bonus, "week": week}


def _week_start(day=None):
    d = day or _today()
    return d - timedelta(days=d.weekday())


def week_done(db, student_id):
    start = datetime.combine(_week_start(), datetime.min.time()).isoformat(timespec="seconds")
    return db.execute("SELECT COUNT(*) FROM farm_orders WHERE student_id=? AND done_at>=?", (student_id, start)).fetchone()[0]


# ── время словами ──

def time_words(ready_at, t=None):
    left = (datetime.fromisoformat(ready_at) - (t or now())).total_seconds()
    if left <= 0:
        return "готово!"
    mins = math.ceil(left / 60)
    if mins < 2:
        return "через минутку"
    if mins < 60:
        return f"через {mins} {_plural(mins, 'минуту', 'минуты', 'минут')}"
    ready = datetime.fromisoformat(ready_at)
    today = (t or now()).date()
    if ready.date() == today:
        hours = round(left / 3600)
        return "через час" if hours <= 1 else f"через {hours} {_plural(hours, 'час', 'часа', 'часов')}"
    if ready.date() == today + timedelta(days=1):
        return "завтра утром" if ready.hour < 12 else "завтра"
    return "через пару дней"


def drops_words(n):
    return f"{n} {_plural(n, 'капля', 'капли', 'капель')}"


def _plural(n, one, few, many):
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


BRICK_COINS = 2          # кирпичик замка при переезде — 2 монетки


def move_from_castle(db, student_id):
    """Переезд из замка (один раз): монетки за построенные уровни комнат — 100% назад
    (первый уровень спальни был бесплатным), оставшиеся кирпичики — по BRICK_COINS. Данные замка не стираются.
    Возвращает число монеток, если переезд случился сейчас, иначе None."""
    import castle
    from garden import get_garden
    had = db.execute("SELECT 1 FROM castle WHERE student_id=?", (student_id,)).fetchone()
    if db.execute("INSERT OR IGNORE INTO farm_moves (student_id, coins, note_seen, at) VALUES (?, 0, 1, ?)",
                  (student_id, _stamp())).rowcount != 1:
        return None                                        # уже переехали (или переезжаем во втором запросе)
    if had:
        coins = sum(castle.COST[lv][1] for room, level in castle.levels(db, student_id).items()
                    for lv in range(2 if room == "bedroom" else 1, level + 1))
        coins += max(0, castle.bricks(db, student_id)) * BRICK_COINS
        get_garden(db, student_id)
        db.execute("UPDATE garden SET coins=coins+? WHERE student_id=?", (coins, student_id))
    else:                                       # замка не было: castle.ensure вернёт монетки за вещи старого домика
        castle.ensure(db, student_id, ())
        db.execute("UPDATE castle SET note_seen=1 WHERE student_id=?", (student_id,))
        coins = db.execute("SELECT moved_coins FROM castle WHERE student_id=?", (student_id,)).fetchone()[0]
    levels = castle.levels(db, student_id)
    seen = 0 if (coins or levels.get("bedroom", 0) > 1 or len(levels) > 1) else 1
    db.execute("UPDATE farm_moves SET coins=?, note_seen=? WHERE student_id=?", (coins, seen, student_id))
    db.commit()
    return coins


def take_move_note(db, student_id):
    """Сообщение о переезде на ферму — один раз: сколько монеток вернули (None — показывать нечего)."""
    r = db.execute("SELECT coins, note_seen FROM farm_moves WHERE student_id=?", (student_id,)).fetchone()
    if not r or r["note_seen"]:
        return None
    db.execute("UPDATE farm_moves SET note_seen=1 WHERE student_id=?", (student_id,))
    db.commit()
    return r["coins"]


def forget_student(db, student_id):
    for t in ("farm_drops", "farm_plots", "farm_barn", "farm_animals", "farm_orders", "farm_moves"):
        db.execute(f"DELETE FROM {t} WHERE student_id=?", (student_id,))


def summary(db, student_id):
    """Для админки и проверок: капли, грядки, амбар, заказы."""
    return {"drops": drops(db, student_id), "barn": barn(db, student_id),
            "plots": {s: plot_state(r) for s, r in _plot_rows(db, student_id).items()}, "date": date.today().isoformat()}


# ── состояние для экрана фермы ──

def _secs(ready_at, t):
    return max(0, int((datetime.fromisoformat(ready_at) - t).total_seconds())) if ready_at else None


def state(db, student_id, stats):
    """Всё, что нужно экрану /student/farm (JSON)."""
    from data.emoji import emoji_for
    from garden import STREAK_CAP, get_garden, refresh_garden, tree_stage
    t = now()
    g = refresh_garden(db, student_id)                                 # сад (серия дней) — уголок фермы
    done = stats["lessons_completed"]
    rows = _plot_rows(db, student_id)
    n_plots = plots_count(db, student_id)
    plots = []
    for slot in range(n_plots):
        r = rows.get(slot)
        st = plot_state(r, t)
        plots.append({"slot": slot, "state": st, "crop": r["crop"] if r is not None else None,
                      "left": _secs(r["ready_at"], t) if st == "growing" else None,
                      "when": time_words(r["ready_at"], t) if st == "growing" else ""})
    extra = n_plots - PLOTS
    animals = []
    for kind, a in ANIMALS.items():
        has = has_animal(db, student_id, kind)
        r = _animal_row(db, student_id, kind) if has else None
        st = animal_state(r, t) if has else "none"
        animals.append({"kind": kind, "en": a["en"], "ru": a["ru"], "state": st, "product": a["product"],
                        "yield": a["yield"], "minutes": a["minutes"], "pic": emoji_for(a["en"]),
                        "left": _secs(r["ready_at"], t) if st == "busy" else None,
                        "when": time_words(r["ready_at"], t) if st == "busy" else ""})
    db.commit()
    have = barn(db, student_id)
    items = list(CROPS) + list(PRODUCTS)
    return {
        "drops": drops(db, student_id), "coins": get_garden(db, student_id)["coins"],
        "water": WATER_COST, "feed": FEED_COST,
        "plots": plots, "plot_cost": PLOT_COSTS[extra] if extra < len(PLOT_COSTS) else None,
        "crops": [{"key": k, "en": c["en"], "ru": c["ru"], "pic": emoji_for(c["en"]), "yield": c["yield"],
                   "grow": _grow_words(c["minutes"]), "open": done >= c["from"], "from": c["from"]} for k, c in CROPS.items()],
        "animals": animals,
        "cow": {"can": can_buy_cow(stats), "cost": COWSHED_COST},
        "barn": [{"item": k, "en": item_info(k)["en"], "ru": item_info(k)["ru"], "qty": have[k],
                  "pic": emoji_for(item_info(k)["en"])} for k in items if have.get(k)],
        "orders": orders(db, student_id, done, stats),
        "week": {"done": week_done(db, student_id), "goal": WEEK_GOAL, "coins": WEEK_COINS},
        "slots_today": order_slots(db, student_id),
        "numbers": _numbers_known(db, student_id, stats),
        "pics": {k: emoji_for(item_info(k)["en"]) for k in items},
        "garden": {"days": g["streak_days"], "grown": min(STREAK_CAP, max(g["streak_days"], g["best_streak"])), "cap": STREAK_CAP,
                   "waits": bool(g["broken"]), "stage": tree_stage(min(STREAK_CAP, max(g["streak_days"], g["best_streak"])))["name"]},
    }


def _grow_words(minutes):
    if minutes < 60:
        return f"{minutes} {_plural(minutes, 'минута', 'минуты', 'минут')}"
    h = minutes // 60
    return f"{h} {_plural(h, 'час', 'часа', 'часов')}"
