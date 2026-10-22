# -*- coding: utf-8 -*-
"""Темы после 51-го урока (id 52–56): прошедшее время, сравнения, «как часто», путешествия.
Место в курсе задаётся в data/course.py (перед «Большим финалом»). Формат тот же, что в new_lessons.py."""

from data.new_lessons import _ch, _match, _order, _ti


def _mat(rows):
    return [{"en": en, "ru": ru, "hint": hint} for en, ru, hint in rows]


LATER_LESSONS = [
    # ===================================================== 52. PAST SIMPLE: WAS / WERE
    {
        "id": 52,
        "title": "Вчера: was и were 🕰️",
        "emoji": "🕰️",
        "description": "Говорим о том, что было: I was at home, they were happy.",
        "theory": {
            "intro": "Ты уже умеешь говорить «я есть» — <b>I am</b>. А как сказать «я была»? Для прошлого у глагола <b>to be</b> есть две формы: <b>was</b> и <b>were</b>.",
            "blocks": [
                {"title": "Was — для одного 👤", "text": "<b>I was</b> [ай уоз] — я был(а), <b>he was</b> — он был, <b>she was</b> — она была, <b>it was</b> — это было. Пример: <i>I was at school.</i> — Я была в школе."},
                {"title": "Were — для многих 👥", "text": "<b>we were</b> [уи: уэ:] — мы были, <b>you were</b> — ты был(а), вы были, <b>they were</b> — они были. Пример: <i>They were in the park.</i> — Они были в парке."},
                {"title": "Слова-подсказки ⏪", "text": "<b>yesterday</b> [йестэдэй] — вчера, <b>last week</b> [ла:ст уи:к] — на прошлой неделе, <b>two days ago</b> [эгоу] — два дня назад. Увидела их — значит, говорим о прошлом!"},
                {"title": "Не было и вопрос ❓", "text": "Отрицание: <b>was not = wasn't</b> [уознт], <b>were not = weren't</b> [уэ:нт]. Вопрос: ставим was/were вперёд — <i>Were you at home?</i> — <i>Yes, I was.</i> / <i>No, I wasn't.</i>"},
            ],
            "tip": "Расскажи маме по-английски, где ты была вчера: I was at school. I was at home. 🏡",
        },
        "material": _mat([
            ("Was", "был, была, было", "уоз"), ("Were", "были", "уэ:"), ("Yesterday", "вчера", "йестэдэй"),
            ("Last week", "на прошлой неделе", "ла:ст уи:к"), ("Ago", "назад", "эгоу"), ("Wasn't", "не был(а)", "уознт"),
            ("Weren't", "не были", "уэ:нт"), ("I was at home.", "Я была дома.", "ай уоз эт хоум"),
            ("They were happy.", "Они были счастливы.", "зэй уэ: хэпи"), ("Were you at school?", "Ты была в школе?", "уэ: ю эт ску:л"),
            ("Tired", "уставший", "тайэд"), ("Happy", "счастливый, весёлый", "хэпи"),
        ]),
        "exercises": [
            _ch("Выбери: I ___ at home yesterday.", "was", ["were", "am"], 0, "С I в прошлом — was."),
            _ch("Выбери: They ___ in the park.", "were", ["was", "is"], 0, "С they в прошлом — were."),
            _ti("Напиши по-английски «вчера»:", "yesterday", "Yesterday — вчера."),
            _match("Соедини 🤝", ["Was", "Were", "Ago", "Last week"], ["был, была", "были", "назад", "на прошлой неделе"],
                   "Was — был(а); Were — были; Ago — назад; Last week — на прошлой неделе."),
            _order("Составь: «Мы были счастливы вчера.»", "We were happy yesterday", ["happy", "We", "yesterday", "were"],
                   "We were happy yesterday."),
        ],
        "test": [
            _ch("Выбери: She ___ tired.", "was", ["were", "are"], 0, "She — одна, значит was."),
            _ch("Выбери: We ___ at school.", "were", ["was", "is"], 0, "We — много, значит were."),
            _ch("Что значит «yesterday»?", "вчера", ["завтра", "сегодня"], 0, "Yesterday — вчера (завтра — tomorrow)."),
            _ti("Напиши «не был» коротко (was not):", "wasn't", "Was not = wasn't.", accept=["wasnt", "was not"]),
            _ch("Как спросить «Ты была дома?»", "Were you at home?", ["Was you at home?", "You were at home?"], 0, "С you всегда were: Were you at home?"),
            _ch("Ответь коротко «да» на «Was it fun?»", "Yes, it was.", ["Yes, it were.", "Yes, it is."], 0, "It — was: Yes, it was."),
            _ti("Напиши по-английски «назад» (two days ...):", "ago", "Two days ago — два дня назад."),
            _ch("Что значит «They weren't at home»?", "Их не было дома.", ["Они дома.", "Они были дома."], 0, "Weren't = were not — не были."),
        ],
    },
    # ===================================================== 53. PAST SIMPLE: -ED И DID
    {
        "id": 53,
        "title": "Вчера я играла: окончание -ed 📜",
        "emoji": "📜",
        "description": "Played, watched, visited — и первые «неправильные»: went, saw, ate.",
        "theory": {
            "intro": "Чтобы рассказать, что ты <b>делала</b> вчера, к глаголу добавляем хвостик <b>-ed</b>. play → <b>played</b> — играла. Это прошедшее время, <b>Past Simple</b>.",
            "blocks": [
                {"title": "Хвостик -ed 🐾", "text": "<b>play → played</b> [плэйд], <b>watch → watched</b> [уотчт], <b>visit → visited</b> [визитид], <b>cook → cooked</b> [кукт]. Форма одна для всех: <i>I played, she played, they played.</i>"},
                {"title": "Неправильные глаголы 🤪", "text": "Некоторые глаголы меняются целиком — их просто запоминаем: <b>go → went</b> [уэнт] — пошёл, <b>see → saw</b> [со:] — увидел, <b>eat → ate</b> [эйт] — съел, <b>have → had</b> [хэд] — имел, <b>do → did</b> — сделал."},
                {"title": "Не делала: didn't 🚫", "text": "<b>didn't</b> [диднт] + обычный глагол без -ed: <i>I didn't play.</i> — Я не играла. <i>She didn't go.</i> — Она не пошла."},
                {"title": "Вопрос: Did…? ❓", "text": "<b>Did</b> ставим в начало, глагол — без -ed: <i>Did you play?</i> — Ты играла? Ответ: <i>Yes, I did.</i> / <i>No, I didn't.</i>"},
            ],
            "tip": "Вечером скажи три фразы о своём дне: I played… I watched… I ate… 🌙",
        },
        "material": _mat([
            ("Played", "играл(а)", "плэйд"), ("Watched", "смотрел(а)", "уотчт"), ("Visited", "навещал(а), посетил(а)", "визитид"),
            ("Cooked", "готовил(а)", "кукт"), ("Went", "пошёл, поехал(а)", "уэнт"), ("Saw", "увидел(а)", "со:"),
            ("Ate", "съел(а)", "эйт"), ("Had", "имел(а), было", "хэд"), ("Did", "сделал(а); вспомогательное слово", "дид"),
            ("Didn't", "не (в прошлом)", "диднт"), ("I watched a film.", "Я смотрела фильм.", "ай уотчт э филм"),
            ("Did you play?", "Ты играла?", "дид ю плэй"),
        ]),
        "exercises": [
            _ch("Как будет «играла»?", "played", ["plaied", "playing"], 0, "play + ed = played."),
            _ch("Прошедшее от go:", "went", ["goed", "gone"], 0, "Go — неправильный глагол: went."),
            _ti("Напиши прошедшее от watch:", "watched", "watch + ed = watched."),
            _match("Соедини глагол и прошедшее 🤝", ["see", "eat", "have", "do"], ["saw", "ate", "had", "did"],
                   "see — saw, eat — ate, have — had, do — did."),
            _order("Составь: «Я не смотрела телевизор.»", "I didn't watch TV", ["watch", "I", "TV", "didn't"],
                   "После didn't глагол без -ed: I didn't watch TV."),
        ],
        "test": [
            _ch("Выбери: Yesterday I ___ football.", "played", ["play", "plays"], 0, "Yesterday — прошлое: played."),
            _ch("Прошедшее от see:", "saw", ["seed", "sees"], 0, "See — saw."),
            _ti("Напиши прошедшее от visit:", "visited", "visit + ed = visited."),
            _ch("Как спросить «Ты готовила?»", "Did you cook?", ["Did you cooked?", "You did cook?"], 0, "После did — глагол без -ed."),
            _ch("Ответь «нет»: Did she go to school?", "No, she didn't.", ["No, she wasn't.", "No, she don't."], 0, "Did → didn't."),
            _ti("Напиши прошедшее от eat:", "ate", "Eat — ate (неправильный глагол)."),
            _ch("Что значит «We had pizza»?", "У нас была пицца.", ["У нас есть пицца.", "Мы хотим пиццу."], 0, "Had — прошедшее от have."),
            _ch("Выбери: I didn't ___ TV.", "watch", ["watched", "watches"], 0, "После didn't — глагол без -ed."),
        ],
    },
    # ===================================================== 54. СРАВНЕНИЯ
    {
        "id": 54,
        "title": "Больше, быстрее, самый-самый 🏆",
        "emoji": "🏆",
        "description": "Сравниваем: bigger than, the biggest, better, the best.",
        "theory": {
            "intro": "Слон большой, а кит — ещё <b>больше</b>! Чтобы сравнивать, к короткому прилагательному добавляем <b>-er</b>, а чтобы сказать «самый» — <b>the … -est</b>.",
            "blocks": [
                {"title": "Больше, чем… 🐘", "text": "<b>big → bigger</b> [бигэ] — больше, <b>small → smaller</b> — меньше, <b>tall → taller</b> — выше, <b>fast → faster</b> — быстрее. «Чем» — это <b>than</b> [зэн]: <i>A whale is bigger than an elephant.</i> — Кит больше слона."},
                {"title": "Самый-самый 🥇", "text": "<b>the biggest</b> — самый большой, <b>the smallest</b> — самый маленький, <b>the fastest</b> — самый быстрый. Перед ними всегда <b>the</b>: <i>The cheetah is the fastest animal.</i>"},
                {"title": "Длинные слова 📏", "text": "С длинными словами говорим <b>more</b> [мо:] — более и <b>the most</b> — самый: <i>more beautiful</i> — красивее, <i>the most beautiful</i> — самый красивый."},
                {"title": "Хитрые слова 🤪", "text": "<b>good → better → the best</b> — хороший, лучше, самый лучший. <b>bad → worse → the worst</b> — плохой, хуже, самый плохой."},
            ],
            "tip": "Сравни членов семьи: Dad is taller than me. Mum is the best! 😊",
        },
        "material": _mat([
            ("Bigger", "больше", "бигэ"), ("Smaller", "меньше", "смо:лэ"), ("Taller", "выше", "то:лэ"), ("Faster", "быстрее", "фа:стэ"),
            ("Than", "чем", "зэн"), ("The biggest", "самый большой", "зэ бигист"), ("The fastest", "самый быстрый", "зэ фа:стист"),
            ("Better", "лучше", "бэтэ"), ("The best", "самый лучший", "зэ бэст"), ("More beautiful", "красивее", "мо: бью:тифул"),
            ("Whale", "кит", "уэйл"), ("Elephant", "слон", "элифэнт"),
        ]),
        "exercises": [
            _ch("Как будет «больше»?", "bigger", ["biger", "more big"], 0, "big → bigger (буква g удваивается)."),
            _ch("Выбери: A cat is ___ than a dog.", "smaller", ["small", "the smallest"], 0, "Сравниваем двоих — smaller than."),
            _ti("Напиши «лучше»:", "better", "Good → better → the best."),
            _match("Соедини 🤝", ["Taller", "Faster", "The best", "Than"], ["выше", "быстрее", "самый лучший", "чем"],
                   "Taller — выше; Faster — быстрее; The best — самый лучший; Than — чем."),
            _order("Составь: «Кит больше слона.»", "A whale is bigger than an elephant",
                   ["bigger", "A whale", "an elephant", "is", "than"], "A whale is bigger than an elephant."),
        ],
        "test": [
            _ch("Что значит «faster»?", "быстрее", ["самый быстрый", "медленнее"], 0, "Faster — быстрее."),
            _ch("Выбери: The cheetah is ___ animal.", "the fastest", ["faster", "fast"], 0, "«Самый» — the fastest."),
            _ti("Напиши по-английски «чем» (bigger ... a cat):", "than", "Than — чем."),
            _ch("Как сказать «красивее»?", "more beautiful", ["beautifuler", "the beautiful"], 0, "Длинное слово — more beautiful."),
            _ch("good → better → ?", "the best", ["the goodest", "the better"], 0, "Good, better, the best."),
            _ti("Напиши «выше» (о росте):", "taller", "Tall → taller."),
            _ch("Что значит «the biggest»?", "самый большой", ["больше", "большой"], 0, "The biggest — самый большой."),
            _ch("Выбери: My sister is ___ than me.", "taller", ["the tallest", "tall"], 0, "Сравниваем двоих — taller than."),
        ],
    },
    # ===================================================== 55. КАК ЧАСТО?
    {
        "id": 55,
        "title": "Как часто? always, usually, never 🔁",
        "emoji": "🔁",
        "description": "Всегда, обычно, иногда, никогда — рассказываем о привычках.",
        "theory": {
            "intro": "Ты уже умеешь рассказывать о своём дне. Теперь добавим, <b>как часто</b> что-то бывает: всегда, обычно, иногда или никогда.",
            "blocks": [
                {"title": "Слова частоты 📊", "text": "<b>always</b> [о:луэйз] — всегда (100%), <b>usually</b> [ю:жуэли] — обычно, <b>often</b> [офэн] — часто, <b>sometimes</b> [самтаймз] — иногда, <b>never</b> [нэвэ] — никогда (0%)."},
                {"title": "Куда ставить? 📍", "text": "Перед обычным глаголом: <i>I <b>always</b> brush my teeth.</i> — Я всегда чищу зубы. Но после <b>am / is / are</b>: <i>She <b>is</b> always happy.</i>"},
                {"title": "Never — уже «не» 🚫", "text": "В английском только одно отрицание: <i>I <b>never</b> eat onions.</i> — Я никогда не ем лук. Не нужно добавлять don't!"},
                {"title": "Как часто? ⏱️", "text": "<b>How often…?</b> [хау офэн] — Как часто? Ответ: <b>every day</b> — каждый день, <b>once a week</b> [уанс] — раз в неделю, <b>twice a week</b> [туайс] — два раза в неделю."},
            ],
            "tip": "Составь про себя: I always… I sometimes… I never… 😄",
        },
        "material": _mat([
            ("Always", "всегда", "о:луэйз"), ("Usually", "обычно", "ю:жуэли"), ("Often", "часто", "офэн"), ("Sometimes", "иногда", "самтаймз"),
            ("Never", "никогда", "нэвэ"), ("How often?", "Как часто?", "хау офэн"), ("Every day", "каждый день", "эври дэй"),
            ("Once a week", "раз в неделю", "уанс э уи:к"), ("Twice a week", "два раза в неделю", "туайс э уи:к"),
            ("I always brush my teeth.", "Я всегда чищу зубы.", "ай о:луэйз браш май ти:с"), ("I never eat onions.", "Я никогда не ем лук.", "ай нэвэ и:т аньенз"),
            ("Habit", "привычка", "хэбит"),
        ]),
        "exercises": [
            _ch("Что значит «never»?", "никогда", ["всегда", "иногда"], 0, "Never — никогда."),
            _ch("Как будет «обычно»?", "usually", ["always", "often"], 0, "Usually — обычно."),
            _ti("Напиши «иногда»:", "sometimes", "Sometimes — иногда."),
            _match("Соедини 🤝", ["Always", "Often", "Once a week", "Every day"], ["всегда", "часто", "раз в неделю", "каждый день"],
                   "Always — всегда; Often — часто; Once a week — раз в неделю; Every day — каждый день."),
            _order("Составь: «Я всегда чищу зубы.»", "I always brush my teeth", ["brush", "I", "my teeth", "always"],
                   "Слово частоты — перед глаголом: I always brush my teeth."),
        ],
        "test": [
            _ch("Что значит «always»?", "всегда", ["никогда", "часто"], 0, "Always — всегда."),
            _ch("Выбери правильно:", "I never eat onions.", ["I don't never eat onions.", "I eat never onions."], 0,
                "Never уже значит «не», ставится перед глаголом."),
            _ti("Напиши «часто»:", "often", "Often — часто."),
            _ch("Выбери: She ___ happy.", "is always", ["always is", "always"], 0, "После is: She is always happy."),
            _ch("Что значит «twice a week»?", "два раза в неделю", ["раз в неделю", "каждую неделю"], 0, "Twice — дважды."),
            _ti("Напиши «никогда»:", "never", "Never — никогда."),
            _ch("Как спросить «Как часто?»", "How often?", ["How much?", "How old?"], 0, "How often? — Как часто?"),
        ],
    },
    # ===================================================== 56. ПУТЕШЕСТВИЯ И СТРАНЫ
    {
        "id": 56,
        "title": "Путешествия и страны ✈️",
        "emoji": "✈️",
        "description": "Страны, аэропорт, чемодан и билеты — едем в отпуск!",
        "theory": {
            "intro": "Летом многие уезжают в путешествие. Давай узнаем, как называются страны и что нужно в аэропорту!",
            "blocks": [
                {"title": "Страны 🌍", "text": "<b>Russia</b> [рашэ] — Россия, <b>England</b> [ингланд] — Англия, <b>the USA</b> [зэ ю: эс эй] — США, <b>France</b> [фра:нс] — Франция, <b>China</b> [чайнэ] — Китай. Названия стран пишутся с большой буквы!"},
                {"title": "Откуда ты? 🗺️", "text": "<b>Where are you from?</b> [уэа а: ю фром] — Откуда ты? Ответ: <i>I'm from Russia.</i> — Я из России."},
                {"title": "В аэропорту 🛫", "text": "<b>airport</b> [эапо:т] — аэропорт, <b>plane</b> [плэйн] — самолёт, <b>ticket</b> [тикит] — билет, <b>passport</b> [па:спо:т] — паспорт, <b>suitcase</b> [сью:ткейс] — чемодан."},
                {"title": "Отдых 🏖️", "text": "<b>holiday</b> [холидэй] — отпуск, каникулы; <b>sea</b> [си:] — море; <b>beach</b> [би:ч] — пляж. <i>We go on holiday by plane.</i> — Мы летим в отпуск на самолёте."},
            ],
            "tip": "Найди на карте мира Россию, Англию и Францию и назови их по-английски 🌍",
        },
        "material": _mat([
            ("Country", "страна", "кантри"), ("Russia", "Россия", "рашэ"), ("England", "Англия", "ингланд"), ("France", "Франция", "фра:нс"),
            ("Where are you from?", "Откуда ты?", "уэа а: ю фром"), ("I'm from Russia.", "Я из России.", "айм фром рашэ"),
            ("Airport", "аэропорт", "эапо:т"), ("Plane", "самолёт", "плэйн"), ("Ticket", "билет", "тикит"), ("Passport", "паспорт", "па:спо:т"),
            ("Suitcase", "чемодан", "сью:ткейс"), ("Holiday", "отпуск, каникулы", "холидэй"), ("Beach", "пляж", "би:ч"),
        ]),
        "exercises": [
            _ch("Что значит «suitcase»?", "чемодан", ["билет", "паспорт"], 0, "Suitcase — чемодан."),
            _ch("Как спросить «Откуда ты?»", "Where are you from?", ["Where are you?", "How are you?"], 0, "Where are you from? — Откуда ты?"),
            _ti("Напиши по-английски «самолёт»:", "plane", "Plane — самолёт.", accept=["airplane", "aeroplane"]),
            _match("Соедини 🤝", ["Airport", "Ticket", "Beach", "Country"], ["аэропорт", "билет", "пляж", "страна"],
                   "Airport — аэропорт; Ticket — билет; Beach — пляж; Country — страна."),
            _order("Составь: «Я из России.»", "I'm from Russia", ["Russia", "from", "I'm"], "I'm from Russia."),
        ],
        "test": [
            _ch("Что значит «passport»?", "паспорт", ["чемодан", "пляж"], 0, "Passport — паспорт."),
            _ch("Как по-английски «Франция»?", "France", ["England", "Russia"], 0, "France — Франция."),
            _ti("Напиши по-английски «билет»:", "ticket", "Ticket — билет."),
            _ch("Ответь на «Where are you from?»", "I'm from Russia.", ["I'm fine.", "I'm ten."], 0, "Откуда — I'm from…"),
            _ch("Что значит «holiday»?", "отпуск, каникулы", ["праздничный торт", "гостиница"], 0, "Holiday — отпуск, каникулы."),
            _ti("Напиши по-английски «аэропорт»:", "airport", "Airport — аэропорт."),
            _ch("Как будет «пляж»?", "beach", ["sea", "bench"], 0, "Beach — пляж (sea — море)."),
        ],
    },
]
