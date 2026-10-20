# -*- coding: utf-8 -*-
"""Дополнительные уроки: доступны ВСЕГДА, независимо от основного курса.
Формат полностью совпадает с LESSONS из lessons.py (теория, карточки,
тренировка, тест). Флаг is_extra=True включает их в отдельный блок."""

EXTRA_LESSONS = [
   {
    "id": 10001,
    "title": "Подготовка к диктанту: Здания в городе 🏙️",
    "emoji": "🏙️",
    "is_extra": True,
    "description": "Готовимся к диктанту: учим писать названия зданий и мест в городе.",
    "theory": {
        "intro": "Сегодня мы готовимся к диктанту! Ты услышишь 8 слов и должен будешь правильно их написать. Давай разберём каждое слово и запомним, как оно пишется.",
        "blocks": [
            {"title": "Транспорт и машины 🚂🚗", "text": "<b>station</b> [стэйшн] — вокзал. Запомни: начинается на st-, заканчивается на -tion. <b>garage</b> [гэра:ж] — гараж. Французское слово, заканчивается на -age."},
            {"title": "Еда и покупки 🥐🥦", "text": "<b>café</b> [кафэ] — кафе. Обрати внимание на ударение и акцент над e! <b>baker's</b> [бэйкэз] — булочная. Не забудь апостроф 's — это значит 'магазин пекаря'. <b>greengrocer's</b> [гри:нгросэз] — магазин овощей. Длинное слово: green (зелёный) + grocer (торговец) + 's."},
            {"title": "Важные места 🏥", "text": "<b>theatre</b> [сиэтр] — театр. Английское написание: theatre (не theater!). <b>hospital</b> [хо́спитл] — больница. Начинается на h-, ударение на первый слог. <b>post office</b> [по́ст о́фис] — почта. Два слова: post (почта) + office (офис)."},
            {"title": "Советы для диктанта ✍️", "text": "Слушай внимательно! Если слово длинное — разбей его на части: green-gro-cer's. Не забудь апостроф в baker's и greengrocer's. café пишется с акцентом!"},
        ],
        "tip": "Прочитай все слова вслух 3 раза, потом закрой перевод и попробуй написать их по памяти. Проверь себя!",
    },
    "material": [
        {"word": "station", "translate": "вокзал, станция", "hint": "[стэйшн]"},
        {"word": "garage", "translate": "гараж, автосервис", "hint": "[гэра:ж]"},
        {"word": "café", "translate": "кафе", "hint": "[кафэ]"},
        {"word": "theatre", "translate": "театр", "hint": "[сиэтр]"},
        {"word": "baker's", "translate": "булочная", "hint": "[бэйкэз]"},
        {"word": "hospital", "translate": "больница", "hint": "[хо́спитл]"},
        {"word": "greengrocer's", "translate": "магазин овощей и фруктов", "hint": "[гри:нгросэз]"},
        {"word": "post office", "translate": "почта", "hint": "[по́ст о́фис]"},
    ],
    "exercises": [
        {"type": "type_in", "q": "Напиши по-английски: вокзал",
         "answer": "station", "accept": ["station"], "explain": "station — вокзал. Запомни: st- + -ation."},
        {"type": "type_in", "q": "Напиши по-английски: гараж",
         "answer": "garage", "accept": ["garage"], "explain": "garage — гараж. Заканчивается на -age."},
        {"type": "type_in", "q": "Напиши по-английски: театр",
         "answer": "theatre", "accept": ["theatre", "theater"], "explain": "theatre — театр (британское написание)."},
        {"type": "type_in", "q": "Напиши по-английски: булочная (не забудь апостроф!)",
         "answer": "baker's", "accept": ["baker's", "bakers"], "explain": "baker's — булочная. Апостроф показывает принадлежность."},
        {"type": "match", "q": "Соедини слово с переводом:",
         "pairs": [["café", "кафе"], ["hospital", "больница"], ["post office", "почта"]],
         "explain": "café — кафе, hospital — больница, post office — почта."},
    ],
    "test": [
        {"type": "type_in", "q": "Диктант. Напиши слово: вокзал",
         "answer": "station", "accept": ["station"], "explain": "station — вокзал."},
        {"type": "type_in", "q": "Диктант. Напиши слово: гараж",
         "answer": "garage", "accept": ["garage"], "explain": "garage — гараж."},
        {"type": "type_in", "q": "Диктант. Напиши слово: кафе",
         "answer": "café", "accept": ["café", "cafe"], "explain": "café — кафе."},
        {"type": "type_in", "q": "Диктант. Напиши слово: театр",
         "answer": "theatre", "accept": ["theatre", "theater"], "explain": "theatre — театр."},
        {"type": "type_in", "q": "Диктант. Напиши слово: булочная",
         "answer": "baker's", "accept": ["baker's", "bakers"], "explain": "baker's — булочная."},
        {"type": "type_in", "q": "Диктант. Напиши слово: больница",
         "answer": "hospital", "accept": ["hospital"], "explain": "hospital — больница."},
        {"type": "type_in", "q": "Диктант. Напиши слово: магазин овощей и фруктов",
         "answer": "greengrocer's", "accept": ["greengrocer's", "greengrocers"], "explain": "greengrocer's — магазин овощей."},
        {"type": "type_in", "q": "Диктант. Напиши слово: почта",
         "answer": "post office", "accept": ["post office"], "explain": "post office — почта."},
    ],
}
]
