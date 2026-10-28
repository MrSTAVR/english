# -*- coding: utf-8 -*-
"""Уроки по ревизии методиста (28.10.2026): «Проверь себя» в конце островов и темы, которых не было
(чьё это — 's / Whose, даты). id 61+; место в курсе — data/course.py. Формат тот же, что в new_lessons.py.

«Проверь себя» не даёт новых слов: материал — фразы острова для повторения, задания — чтение,
«найди ошибку», сборка предложений. В тесте — не больше двух «напиши» (practice.limit_writing)."""

from data.new_lessons import _ch, _match, _order, _ti


def _mat(rows):
    return [{"en": en, "ru": ru, "hint": hint} for en, ru, hint in rows]


TOPIC_LESSONS = [
    # ===================================================== 61. ПРОВЕРЬ СЕБЯ: Я И МОЯ СЕМЬЯ
    {
        "id": 61,
        "title": "Проверь себя: я и моя семья ⭐",
        "emoji": "⭐",
        "description": "Повторяем остров: семья, to be, «какой?», вежливые слова, «как пишется», числа 11–20, my / his / her.",
        "theory": {
            "intro": "Ты прошла целый остров! Новых слов здесь нет — только то, что ты уже знаешь. Посмотри короткие подсказки и проверь себя.",
            "blocks": [
                {"title": "Кто это? 👨‍👩‍👧", "text": "<b>This is my mom.</b> — Это моя мама. <b>This is my grandma.</b> — Это моя бабушка. <b>His name is Tom.</b> — Его зовут Том. <b>Her name is Anna.</b> — Её зовут Анна. <b>Mum</b> = <b>Mom</b> — мама (mum говорят в Англии)."},
                {"title": "am / is / are 🔑", "text": "<b>I am</b> (I'm), <b>he / she / it is</b> (he's, she's), <b>we / you / they are</b> (we're, they're). Отрицание («не»): <b>I'm not</b>, <b>she isn't</b>, <b>they aren't</b>. Вопрос: <b>Are you happy?</b> — <b>Yes, I am.</b>"},
                {"title": "Какой? 🎈", "text": "Слово-описание (какой?) стоит перед предметом: <b>a big dog</b> — большая собака, <b>a small cat</b> — маленькая кошка. После am / is / are: <b>She is sad.</b> — Она грустная. Пары: <b>big — small</b>, <b>happy — sad</b>, <b>hot — cold</b>."},
                {"title": "Вежливо, по буквам и по числам 🙏", "text": "<b>Please</b> — пожалуйста, <b>Thank you!</b> — спасибо, <b>You're welcome!</b> — пожалуйста (в ответ на спасибо), <b>Sorry!</b> — извини. <b>How do you spell it?</b> — Как это пишется? Числа: <b>eleven</b> — 11, <b>twelve</b> — 12, <b>fifteen</b> — 15, <b>twenty</b> — 20."},
            ],
            "tip": "Расскажи о своей семье в трёх предложениях: This is my… His / Her name is… He / She is… 😊",
        },
        "material": _mat([
            ("This is my mom.", "Это моя мама.", "зис из май мом"), ("His name is Tom.", "Его зовут Том.", "хиз нэйм из том"),
            ("Her name is Anna.", "Её зовут Анна.", "хё: нэйм из энэ"), ("She is happy.", "Она счастлива.", "ши из хэпи"),
            ("He isn't sad.", "Он не грустный.", "хи изнт сэд"), ("Are you ten?", "Тебе десять?", "а: ю тэн"),
            ("Yes, I am.", "Да.", "йес ай эм"), ("You're welcome!", "Пожалуйста! (в ответ на спасибо)", "ё: уэлкам"),
            ("How do you spell it?", "Как это пишется?", "хау ду ю спэл ит"), ("Twelve", "двенадцать", "твэлв"),
        ]),
        "exercises": [
            _ch("Выбери: My brother ___ ten.", "is", ["am", "are"], 0, "Brother — он, значит is."),
            _ch("Выбери: This is my sister. ___ name is Kate.", "Her", ["His", "My"], 0, "Сестра — она: her name."),
            _match("Соедини числа 🔢", ["eleven", "twelve", "fifteen", "twenty"], ["11", "12", "15", "20"],
                   "eleven — 11, twelve — 12, fifteen — 15, twenty — 20."),
            _ch("Как сказать «большая собака»?", "a big dog", ["a dog big", "big a dog"], 0, "Слово-описание — перед предметом: a big dog."),
            _ch("Как спросить «Как это пишется?»", "How do you spell it?", ["How are you?", "How old are you?"], 0,
                "Spell — называть по буквам."),
            _order("Составь: «Это мой папа.»", "This is my dad", ["my", "This", "dad", "is"], "This is my dad."),
            _ti("Напиши по-английски «спасибо»:", "thank you", "Thank you — спасибо.", accept=["thanks"]),
        ],
        "test": [
            _ch("Прочитай: «This is my grandma. Her name is Olga. She is happy.» Как зовут бабушку?", "Olga", ["Anna", "Kate"], 0,
                "Her name is Olga — её зовут Ольга."),
            _ch("Прочитай ещё раз: «She is happy.» Какая бабушка?", "счастливая", ["грустная", "старая"], 0, "Happy — счастливый."),
            _ch("Какое предложение без ошибки?", "I am not sad.", ["I is not sad.", "I are not sad."], 0,
                "С I — только am: I am not (I'm not)."),
            _ch("Выбери: This is my grandpa. ___ name is Ivan.", "His", ["Her", "Its"], 0, "Дедушка — он: his name."),
            _ch("Тебе сказали «Thank you». Что ответишь?", "You're welcome.", ["Excuse me.", "Sorry."], 0,
                "На thank you отвечают You're welcome."),
            _order("Составь: «Его зовут Макс.»", "His name is Max", ["is", "Max", "His", "name"], "His name is Max."),
            _ch("Слово, противоположное «big»:", "small", ["sad", "cold"], 0, "big — small."),
            _ti("Напиши число 15 словом:", "fifteen", "15 — fifteen."),
        ],
    },
    # ===================================================== 63. ЧЬЁ ЭТО? 'S И WHOSE
    {
        "id": 63,
        "title": "Чьё это? Tom's bag 🎒",
        "emoji": "🎒",
        "description": "Как сказать «сумка Тома», «мамин телефон» и спросить «Чьё это?» — Whose is this?",
        "theory": {
            "intro": "По-русски мы говорим «сумка Тома». По-английски проще: к имени добавляем хвостик <b>'s</b> и ставим его <b>перед</b> предметом — <b>Tom's bag</b>.",
            "blocks": [
                {"title": "Хвостик 's 🐾", "text": "<b>Tom's bag</b> [томз бэг] — сумка Тома, <b>Masha's cat</b> — кошка Маши, <b>Mum's phone</b> — мамин телефон, <b>my sister's book</b> — книга моей сестры. Сначала <b>чей</b>, потом <b>что</b>."},
                {"title": "Чьё это? ❓", "text": "<b>Whose</b> [ху:з] — чей, чья, чьё. <i>Whose bag is this?</i> — Чья это сумка? Или короче: <i>Whose is this?</i> — Чьё это? Ответ: <i>It's Tom's.</i> — Тома. Или полностью: <i>It's Tom's bag.</i>"},
                {"title": "Не путай 🧐", "text": "<b>Tom's bag</b> — сумка Тома (чья?). А <b>Tom is</b> тоже можно сократить до <b>Tom's</b>: <i>Tom's ten.</i> — Тому десять. Если 's можно заменить на is — это «Tom is»: Tom's ten, Tom's happy. Если после 's сразу идёт вещь (Tom's bag) — это «чей»."},
            ],
            "tip": "Покажи на вещи дома и скажи, чьи они: Mum's cup, Dad's car, my cat… 🏠",
        },
        "material": _mat([
            ("Whose", "чей, чья, чьё", "ху:з"), ("Whose is this?", "Чьё это?", "ху:з из зис"),
            ("Tom's bag", "сумка Тома", "томз бэг"), ("Masha's cat", "кошка Маши", "машэз кэт"),
            ("Mum's phone", "мамин телефон", "мамз фоун"), ("Dad's car", "папина машина", "дэдз ка:"),
            ("It's Anna's.", "Это Анны.", "итс энэз"), ("my sister's book", "книга моей сестры", "май систэз бук"),
        ]),
        "exercises": [
            _ch("Как сказать «сумка Тома»?", "Tom's bag", ["bag Tom", "Tom bag's"], 0, "Сначала чей + 's, потом что: Tom's bag."),
            _ch("Что значит «Whose is this?»", "Чьё это?", ["Что это?", "Где это?"], 0, "Whose — чей, чья, чьё."),
            _match("Соедини 🤝", ["Mum's phone", "Dad's car", "Masha's cat", "Tom's bag"],
                   ["мамин телефон", "папина машина", "кошка Маши", "сумка Тома"], "Хвостик 's — «чей»."),
            _order("Составь: «Это книга Анны.»", "It is Anna's book", ["Anna's", "is", "book", "It"], "It is Anna's book."),
            _ti("Напиши по-английски «кошка Маши» (Masha …):", "masha's cat", "Masha's cat — кошка Маши.", accept=["mashas cat"]),
        ],
        "test": [
            _ch("Как сказать «папина машина»?", "Dad's car", ["Car Dad's", "Dad car"], 0, "Чей + 's + что: Dad's car."),
            _ch("Как спросить «Чья это ручка?»", "Whose pen is this?", ["Who pen is this?", "What is this pen?"], 0,
                "Чей — whose: Whose pen is this?"),
            _ch("Ответь на «Whose bike is this?» (это велосипед Макса)", "It's Max's.", ["It's Max.", "It's Max is."], 0,
                "Велосипед Макса — Max's."),
            _ch("Какое предложение без ошибки?", "This is my brother's dog.", ["This is dog my brother's.", "This is my brother dog's."], 0,
                "Сначала чей (my brother's), потом что (dog)."),
            _ch("«Tom's ten.» — что здесь значит 's?", "is — Тому десять", ["чей — десять Тома", "много Томов"], 0,
                "После 's нет предмета — значит это Tom is."),
            _order("Составь: «Это мамин телефон.»", "This is Mum's phone", ["phone", "This", "Mum's", "is"], "This is Mum's phone."),
            _ti("Напиши по-английски «чей»:", "whose", "Whose — чей."),
            _match("Соедини 🤝", ["Whose", "Mum's", "Dad's"], ["чей", "мамин", "папин"], "Whose — чей; Mum's — мамин; Dad's — папин."),
        ],
    },
    # ===================================================== 65. ДАТЫ
    {
        "id": 65,
        "title": "Даты: first, second, third 📅",
        "emoji": "📅",
        "description": "First, second, third… и как сказать дату: My birthday is on the 19th of June.",
        "theory": {
            "intro": "Чтобы назвать дату, нужны числа-«который»: <b>первый, второй, третий</b>. По-английски почти все они получаются из обычных чисел с хвостиком <b>-th</b>.",
            "blocks": [
                {"title": "Первые три — особенные 🥇", "text": "<b>first</b> [фё:ст] — первый (1st), <b>second</b> [сэкэнд] — второй (2nd), <b>third</b> [сё:д] — третий (3rd). Их просто запоминаем."},
                {"title": "Дальше — хвостик -th 🐾", "text": "<b>four → fourth</b> (4th), <b>six → sixth</b>, <b>ten → tenth</b>, <b>nineteen → nineteenth</b> (19th). Чуть меняются: <b>five → fifth</b>, <b>eight → eighth</b> (одна t), <b>nine → ninth</b> (без e), <b>twelve → twelfth</b>, <b>twenty → twentieth</b>. После двадцати последнее слово — как в начале: <b>twenty-first</b> (21st), <b>twenty-second</b> (22nd), <b>twenty-third</b> (23rd)."},
                {"title": "Как сказать дату 📅", "text": "<b>on the 5th of May</b> [он зэ фифс ов мэй] — пятого мая. День рождения: <i>My birthday is on the 19th of June.</i> — Мой день рождения 19 июня. Вопрос: <i>When is your birthday?</i> — Когда твой день рождения?"},
                {"title": "in, on, at — шпаргалка 🗂️", "text": "<b>in</b> + месяц: <i>in May</i>. <b>on</b> + день недели или дата: <i>on Monday</i>, <i>on the 5th of May</i>. <b>at</b> + время: <i>at 7 o'clock</i>."},
            ],
            "tip": "Узнай дни рождения всей семьи и скажи их по-английски: Mum's birthday is on the… (числа больше 23 выучим позже) 🎉",
        },
        "material": _mat([
            ("First", "первый", "фё:ст"), ("Second", "второй", "сэкэнд"), ("Third", "третий", "сё:д"),
            ("Fifth", "пятый", "фифс"), ("Tenth", "десятый", "тэнс"), ("Twentieth", "двадцатый", "твэнтиэс"),
            ("Birthday", "день рождения", "бё:сдэй"), ("When is your birthday?", "Когда твой день рождения?", "уэн из ё: бё:сдэй"),
            ("on the 5th of May", "пятого мая", "он зэ фифс ов мэй"), ("on the 19th of June", "девятнадцатого июня", "он зэ найнти:нс ов джу:н"),
        ]),
        "exercises": [
            _match("Соедини 🔢", ["first", "second", "third", "fifth"], ["1st", "2nd", "3rd", "5th"],
                   "first — 1st, second — 2nd, third — 3rd, fifth — 5th."),
            _ch("Как будет «десятый»?", "tenth", ["tenst", "tened"], 0, "ten + th = tenth."),
            _ch("Выбери: My birthday is ___ the 19th of June.", "on", ["in", "at"], 0, "Дата — on: on the 19th of June."),
            _ch("Выбери: ___ May", "in", ["on", "at"], 0, "Месяц — in: in May."),
            _order("Составь: «Когда твой день рождения?»", "When is your birthday", ["your", "When", "birthday", "is"],
                   "When is your birthday?"),
            _ti("Напиши по-английски «первый»:", "first", "First — первый."),
        ],
        "test": [
            _ch("Как будет «третий»?", "third", ["threeth", "thirth"], 0, "Третий — third (запоминаем)."),
            _ch("Как будет «пятый»?", "fifth", ["fiveth", "fivest"], 0, "five → fifth."),
            _ch("Выбери: ___ Monday", "on", ["in", "at"], 0, "День недели — on."),
            _ch("Выбери: ___ 7 o'clock", "at", ["on", "in"], 0, "Время — at."),
            _ch("Что значит «on the 2nd of March»?", "второго марта", ["двадцатого марта", "второй март"], 0,
                "2nd — second, второе."),
            _ch("Как ответить на «When is your birthday?»", "It's on the 10th of May.", ["It's in the 10th of May.", "I'm ten."], 0,
                "Дата — on the 10th of May."),
            _order("Составь: «Мой день рождения 5 мая.»", "My birthday is on the 5th of May",
                   ["on", "May", "My", "the", "is", "of", "birthday", "5th"], "Дата — on the 5th of May."),
            _ti("Напиши по-английски «второй»:", "second", "Second — второй."),
        ],
    },
]
