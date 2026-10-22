# -*- coding: utf-8 -*-
"""Новый год: слова сезона, мини-викторина и адвент-календарь на декабрь."""

WORDS = [
    {"en": "snowman", "ru": "снеговик", "pic": "⛄"},
    {"en": "snowflake", "ru": "снежинка", "pic": "❄️"},
    {"en": "Christmas tree", "ru": "ёлка", "pic": "🎄"},
    {"en": "present", "ru": "подарок", "pic": "🎁"},
    {"en": "Santa Claus", "ru": "Санта-Клаус", "pic": "🎅"},
    {"en": "reindeer", "ru": "северный олень", "pic": "🦌"},
    {"en": "star", "ru": "звезда", "pic": "⭐"},
    {"en": "candle", "ru": "свеча", "pic": "🕯️"},
    {"en": "bell", "ru": "колокольчик", "pic": "🔔"},
    {"en": "sledge", "ru": "санки", "pic": "🛷"},
    {"en": "skates", "ru": "коньки", "pic": "⛸️"},
    {"en": "mittens", "ru": "варежки", "pic": "🧤"},
    {"en": "fireworks", "ru": "салют", "pic": "🎆"},
    {"en": "cookie", "ru": "печенье", "pic": "🍪"},
]
PHRASE = {"en": "Happy New Year!", "ru": "С Новым годом!"}
QUIZ_LEN = 8
PASS_MARK = 6
DAILY_COINS = 3

INTRO = ("Зимние праздничные слова! Нажми на карточку — услышишь слово. Потом пройди викторину: {pass_mark} из {quiz_len} — "
         "и {coins} монетки (раз в день). В гардеробе появились новогодние наряды — только пока идёт праздник! 🎅")
BANNER = "🎄 Новый год! Зимние слова, викторина и новогодние наряды для Чик-чика →"
WIN_TEXT = "Ура! Дед Мороз тобой гордится!"
WIN_EMOJI, LOSE_EMOJI = "🎄", "⛄"

# Адвент-календарь: окошко на каждый день декабря (слово или фраза дня)
ADVENT_COINS = 1          # за окошко, открытое в свой день
ADVENT = [
    {"en": "winter", "ru": "зима", "pic": "❄️"},
    {"en": "snow", "ru": "снег", "pic": "🌨️"},
    {"en": "cold", "ru": "холодный", "pic": "🥶"},
    {"en": "It is snowing.", "ru": "Идёт снег.", "pic": "🌨️"},
    {"en": "scarf", "ru": "шарф", "pic": "🧣"},
    {"en": "hot chocolate", "ru": "горячий шоколад", "pic": "☕"},
    {"en": "ice", "ru": "лёд", "pic": "🧊"},
    {"en": "snowball", "ru": "снежок", "pic": "⚪"},
    {"en": "Let's make a snowman!", "ru": "Давай слепим снеговика!", "pic": "⛄"},
    {"en": "holidays", "ru": "каникулы", "pic": "🎒"},
    {"en": "decorate", "ru": "украшать", "pic": "🎀"},
    {"en": "Christmas ball", "ru": "ёлочный шар", "pic": "🔴"},
    {"en": "tinsel", "ru": "мишура", "pic": "✨"},
    {"en": "lights", "ru": "огоньки", "pic": "💡"},
    {"en": "Make a wish!", "ru": "Загадай желание!", "pic": "🌠"},
    {"en": "card", "ru": "открытка", "pic": "✉️"},
    {"en": "box", "ru": "коробка", "pic": "📦"},
    {"en": "surprise", "ru": "сюрприз", "pic": "🎉"},
    {"en": "party", "ru": "праздник", "pic": "🥳"},
    {"en": "dance", "ru": "танцевать", "pic": "💃"},
    {"en": "sweets", "ru": "сладости", "pic": "🍭"},
    {"en": "cake", "ru": "торт", "pic": "🎂"},
    {"en": "tangerine", "ru": "мандарин", "pic": "🍊"},
    {"en": "I love winter!", "ru": "Я люблю зиму!", "pic": "💙"},
    {"en": "family", "ru": "семья", "pic": "👨‍👩‍👧"},
    {"en": "friends", "ru": "друзья", "pic": "🤝"},
    {"en": "together", "ru": "вместе", "pic": "🫶"},
    {"en": "midnight", "ru": "полночь", "pic": "🕛"},
    {"en": "clock", "ru": "часы", "pic": "⏰"},
    {"en": "Thank you for the present!", "ru": "Спасибо за подарок!", "pic": "🎁"},
    {"en": "Happy New Year!", "ru": "С Новым годом!", "pic": "🎆"},
]
