# -*- coding: utf-8 -*-
"""Сквозная история курса «Поездка к Тому»: тест урока — сцена-диалог (эпизод истории).

Сюжет: ученица получает письмо от друга Тома из Англии и летит к нему в гости; Чик-чик прячется
у неё в рюкзаке. Острова курса — главы поездки, уроки — эпизоды; в конце эпизода — крючок
(что будет дальше). Герои: Tom и его сестра Anna, их Mum и Dad, Grandma, пёс Rex.
  1 «Первые шаги» — прилёт: встреча в аэропорту, Чик-чик потерялся, поиски по запискам, нашёлся у моря.
  2 «Я и моя семья» — семья Тома, знакомство, кто есть кто.
  3 «Вокруг меня» — дом, питомцы, ферма у бабушки, погода.
  4 «Вкусно и полезно» — кухня, рынок, кафе.
  5 «Мой день» — школьный день с Томом, распорядок, время.
  6 «Прямо сейчас» — видеозвонок домой: что все сейчас делают.
  7 «Большой мир» — поездка по городу, дорога, путешествия.
  8 «Вчера и завтра» — ученица дома рассказывает о поездке и строит планы.

Сцена: {"title", "intro" (что было раньше, по-русски), "lines", "outro" (крючок)}.
В репликах {name} — имя ученицы (в английских — латиницей), {ключ} — её выбор из pick.
Слова урока (material) при первом появлении в реплике показываются карточками под ней — так ученица
их ещё раз (до истории они были на шаге «Слова»). В вариантах choice тоже можно {name}.
Строки: say(кто, en, ru) — реплика героя (только английский — её читает озвучка; перевод видно по нажатию,
и всё равно в реплике прямо над вопросом не называем проверяемое слово); note(ru) — слова рассказчика;
ask(вопрос) — ход ученицы: вопрос в формате теста (choice / type_in / order, можно "audio"; у type_in —
accept с синонимами), "q" — понятная формулировка для разбора ошибок. Вопросы сцены и есть тест урока
(practice.augment), проверяются как тест. Новые сцены сначала проверяет методист.
"""


def say(who, en, ru):
    return {"say": who, "en": en, "ru": ru}


def note(ru):
    return {"note": ru}


def ask(q, ok=None, no=None, review=False):
    """Ход ученицы. ok — реплика героя после верного ответа (say(...)); no — после неверного:
    say(...) на любой неверный ответ или {номер варианта: say(...)} — на конкретный вариант.
    review=True — ход-повторение: верный ответ — слово/фраза из прошлых уроков курса (вплетено в сюжет)."""
    d = {"ask": q}
    if review:
        d["review"] = True
    if ok:
        d["ok"] = ok
    if no:
        d["no"] = no
    return d


def pick(key, q, options):
    """Выбор без правильного ответа («Red or blue?»): дальше в репликах {key} → v, в переводе {key} → v_ru.
    options — [(что говорит ученица en, ru, v, v_ru), …]."""
    return {"pick": key, "q": q,
            "options": [{"en": en, "ru": ru, "v": v, "v_ru": v_ru} for en, ru, v, v_ru in options]}


def speak(en, ru):
    """«Скажи вслух»: по желанию, без оценки (в тест не входит)."""
    return {"speak": en, "ru": ru}


def choice(q, options, answer, explain="", audio=None, pics=False):
    """pics=True — варианты показываются картинками (options — английские слова с картинкой)."""
    d = {"type": "choice", "q": q, "options": options, "answer": answer, "explain": explain}
    if audio:
        d["audio"] = audio
    if pics:
        d["pics"] = True
    return d


def write(q, answer, explain="", accept=()):
    d = {"type": "type_in", "q": q, "answer": answer, "explain": explain}
    if accept:
        d["accept"] = list(accept)
    return d


def order(q, answer, explain="", audio=None):
    words = answer.rstrip(".!?").split()
    d = {"type": "order", "q": q, "answer": answer, "words": words, "explain": explain}
    if audio:
        d["audio"] = audio
    return d


SCENES = {
    9: {"title": "Привет, Англия!",
        "intro": "Пришло письмо из Англии от друга Тома: «Come to visit us!» — «Приезжай в гости!». "
                 "Ты летишь в самолёте, а в рюкзаке тихонько сидит Чик-чик. Самолёт приземлился!",
        "lines": [
            note("Ты выходишь из самолёта. У двери стоит лётчица и прощается с пассажирами."),
            say("Pilot", "Thank you for flying with us! Have a nice day!", "Спасибо, что летели с нами! Хорошего дня!"),
            ask(choice("Попрощайся с лётчицей", ["Goodbye!", "Hello!", "Nice to meet you!"], 0,
                       "Goodbye! — До свидания! Так прощаются."),
                ok=say("Pilot", "Bye-bye! Welcome to England!", "Пока-пока! Добро пожаловать в Англию!"),
                no={1: say("Pilot", "Hello? Ha-ha! No, it's bye-bye now!", "Привет? Ха-ха! Нет, сейчас пора прощаться!")}),
            note("В зале прилёта мальчик держит табличку с твоим именем. Это Том! Рядом с ним — девочка."),
            say("Tom", "There you are! I'm Tom! Welcome!", "Вот и ты! Я Том! Добро пожаловать!"),
            ask(choice("Поздоровайся с Томом", ["Hi, Tom!", "Bye, Tom!", "Thank you, Tom!"], 0,
                       "Hi! — Привет! (по-дружески)"),
                ok=say("Tom", "This is my sister.", "Это моя сестра.")),
            say("Anna", "Hi! I'm Anna. What's your name?", "Привет! Я Анна. А тебя как зовут?"),
            ask(order("Ответь Анне: собери «Привет! Меня зовут…»", "Hello my name is",
                      "Hello! My name is… — Привет! Меня зовут…"),
                ok=say("Anna", "{name}! Nice to meet you!", "{name}! Приятно познакомиться!")),
            ask(choice("Ответь Анне", ["Nice to meet you too!", "What's your name?", "Goodbye!"], 0,
                       "Nice to meet you too! — Мне тоже приятно познакомиться!"),
                ok=say("Anna", "We are friends now!", "Теперь мы друзья!")),
            say("Tom", "How are you, {name}?", "Как ты, {name}?"),
            ask(choice("Послушай Тома ещё раз и ответь ему", ["I'm fine, thank you.", "My name is Tom.", "Bye!"], 0,
                       "I'm fine, thank you. — У меня всё хорошо, спасибо.", audio="How are you?"),
                ok=say("Tom", "Great!", "Отлично!"),
                no={1: say("Tom", "Ha-ha! No, I'm Tom!", "Ха-ха! Нет, Том — это я!")}),
            note("У Тома звонит телефон. Это его мама — она ждёт вас дома и пишет сообщение."),
            say("Tom", "It's my mum! Write to her!", "Это моя мама! Напиши ей!"),
            ask(write("Напиши маме Тома «Привет» по-английски", "hi", "Hi / Hello — привет.", accept=["hello"]),
                ok=say("Mum", "Hi, {name}! See you at home!", "Привет, {name}! Увидимся дома!")),
            speak("Hello! My name is {name}.", "Привет! Меня зовут {name}."),
            note("Тебе тоже хочется что-то спросить у Анны."),
            ask(order("Спроси Анну, как у неё дела", "How are you?", "How are you? — Как дела?"),
                ok=say("Anna", "I'm fine, thank you! Can I see Chick-chick?",
                       "У меня всё хорошо, спасибо! А можно посмотреть на Чик-чика?")),
        ],
        "outro": "Ты открываешь рюкзак, чтобы показать Тому и Анне Чик-чика… а рюкзак пустой! Где же Чик-чик?"},

    1: {"title": "Кто видел Чик-чика?",
        "intro": "Рюкзак пустой! Наверное, Чик-чик выпрыгнул, пока ты ждал(а) чемодан. "
                 "Вы с Томом и Анной идёте искать его по всему аэропорту.",
        "lines": [
            say("Tom", "Don't worry, {name}! We can find him. Look at the signs!",
                "Не волнуйся, {name}! Мы его найдём. Смотри на вывески!"),
            note("Первая вывеска — над кафе. На ней нарисован зверь с усами."),
            ask(choice("Анна читает вывеску вслух. Нажми на того, кто нарисован на вывеске", ["cat", "dog", "pig"], 0,
                       "Cat — кот. В слове cat буква A звучит коротко: [кэт].", audio="Cat café!", pics=True),
                ok=say("Anna", "Cat café! Cats, cats… but no chick.", "Кошачье кафе! Коты, коты… а цыплёнка нет.")),
            note("В кафе тётенька вытирает стол. На столе что-то опрокинуто, а рядом лежит жёлтое пёрышко!"),
            say("Lady", "Oh no! Look at my table! A little yellow bird!", "Ой-ой! Посмотрите на мой стол! Маленькая жёлтая птичка!"),
            ask(choice("Что опрокинул Чик-чик? Покажи Тому", ["cup", "cat", "pen"], 0, "Cup — чашка: [кап].", pics=True),
                ok=say("Tom", "A cup! Chick-chick was here!", "Чашка! Чик-чик был здесь!"),
                no={1: say("Anna", "A cat? No, look — a cup!", "Кот? Нет, смотри — чашка!")}),
            say("Anna", "Look! Yellow feathers on the floor. This way!", "Смотри! Жёлтые пёрышки на полу. Сюда!"),
            note("Пёрышки ведут к магазину игрушек. На вывеске нарисована свинка, но одна буква отвалилась: P _ G."),
            ask(choice("Послушай, как Том читает вывеску. Какой буквы не хватает?", ["I", "A", "U"], 0,
                       "Pig [пиг] — короткий звук [и] даёт буква I.", audio="Pig!"),
                ok=say("Tom", "Pig! It's a toy shop!", "Свинка! Это магазин игрушек!")),
            note("На полке — игрушечные звери: кошка, свинка… и маленький жёлтый цыплёнок! А рядом с ним — ещё игрушка и ценник: DOG."),
            say("Tom", "Is it Chick-chick?", "Это Чик-чик?"),
            ask(choice("Прочитай ценник: кто сидит рядом с игрушечным цыплёнком?", ["dog", "cat", "pig"], 0,
                       "Dog — собака: [дог].", pics=True),
                ok=say("Anna", "A toy dog and a toy chick. It's not our Chick-chick…",
                       "Игрушечная собака и игрушечный цыплёнок. Это не наш Чик-чик…")),
            note("Под стулом у кассы лежит бумажка с жёлтым пёрышком. Анна хочет записать, где вы её нашли."),
            ask(choice("Послушай Анну и дай ей то, что она просит", ["pen", "cup", "dog"], 0, "Pen — ручка: [пэн].",
                       audio="Give me a pen, please!", pics=True),
                ok=say("Anna", "A pen! Thank you!", "Ручка! Спасибо!")),
            say("Tom", "Let's write to my mum. Chick-chick is lost!", "Давай напишем моей маме. Чик-чик потерялся!"),
            ask(write("Допиши сообщение маме Тома: «Help! Chick-chick is lost! Café, yellow feathers, a …» — что он опрокинул?",
                      "cup", "Cup — чашка."),
                ok=say("Mum", "Oh no, a cup! Find him, kids!", "Ой-ой, чашка! Найдите его, ребята!")),
            speak("A cat, a dog, a pig, a cup, a pen!", "Кот, собака, свинья, чашка, ручка!"),
        ],
        "outro": "Анна разворачивает бумажку. На ней не слова, а какие-то буквы… Это записка от Чик-чика!"},

    33: {"title": "Записка из букв",
         "intro": "Под стулом в аэропорту вы нашли записку с жёлтым пёрышком. В ней не слова, а буквы — это шифр!",
         "lines": [
             say("Tom", "Letters! It's a code! I can read it…", "Буквы! Это шифр! Я могу прочитать…"),
             ask(choice("Том читает первую строчку: «Find locker…». Послушай, какую букву он назвал", ["E", "I", "A"], 0,
                        "E — [и:], а I — [ай]. Не перепутай!", audio="Locker E!"),
                 ok=say("Tom", "Locker E! The lockers are over there.", "Ящик E! Ящики вон там."),
                 no={1: say("Tom", "No, that's I. I said E!", "Нет, это I [ай]. Я сказал E [и:]!")}),
             note("У ящиков для вещей стоит девочка с чемоданом."),
             say("Lily", "Hi! I'm Lily. What's your name?", "Привет! Я Лили. Как тебя зовут?"),
             ask(choice("Ответь Лили", ["My name is {name}.", "I'm fine, thank you.", "A, B, C!"], 0,
                        "My name is… — Меня зовут…"),
                 ok=say("Lily", "Nice to meet you, {name}! Good luck!", "Приятно познакомиться, {name}! Удачи!"),
                 review=True),
             note("Ящики подписаны буквами: A, B, C, D… Вот ящик E! Но он закрыт на кодовый замок. На замке: F _ H."),
             say("Anna", "We need the missing letter!", "Нужна пропущенная буква!"),
             ask(write("Набери на замке пропущенную букву: F _ H", "G", "F, G, H — между F и H стоит G."),
                 ok=say("Anna", "F, G, H! It's open!", "F, G, H! Открылось!")),
             note("В ящике — игрушечная рыбка, яйцо… и жёлтые пёрышки!"),
             ask(choice("Том называет по буквам, что он нашёл. Послушай и нажми на картинку", ["fish", "egg", "ball"], 0,
                        "F-I-S-H — fish, рыба.", audio="F-I-S-H!", pics=True),
                 ok=say("Tom", "A fish! Chick-chick likes fish? Ha-ha!", "Рыбка! Чик-чик любит рыбу? Ха-ха!")),
             ask(choice("А теперь Анна называет по буквам вторую находку", ["egg", "apple", "ball"], 0,
                        "E-G-G — egg, яйцо.", audio="E-G-G!", pics=True),
                 ok=say("Anna", "An egg! Is it Chick-chick's egg? Ha-ha!", "Яйцо! Это яйцо Чик-чика? Ха-ха!")),
             note("Под яйцом — ещё одна записка. На ней три буквы. Том читает их вслух."),
             ask(order("Послушай Тома и собери буквы записки по порядку", "C A B", "C — [си:], A — [эй], B — [би:].",
                       audio="C, A, B."),
                 ok=say("Anna", "C-A-B. Cab! A cab is a taxi!", "C-A-B. Cab! Кэб — это такси!")),
             speak("A, B, C, D, E, F, G, H, I!", "Алфавит от A до I — как песенка!"),
         ],
         "outro": "CAB — значит такси! Чик-чик ждёт у такси! Бегом к стоянке!"},
    10: {"title": "Такси номер семь",
         "intro": "У выхода из аэропорта — много такси. Чик-чика не видно, но к вам идёт папа Тома.",
         "lines": [
             say("Dad", "Hello, {name}! I'm Tom's dad.", "Привет, {name}! Я папа Тома."),
             ask(choice("Ответь папе Тома", ["Nice to meet you!", "Goodbye!", "My name is Tom."], 0,
                        "Nice to meet you! — Приятно познакомиться!"),
                 ok=say("Dad", "Nice to meet you too! Our taxi is over there!",
                        "Мне тоже приятно! Наше такси вон там!"),
                 no={1: say("Dad", "Goodbye? But you've just arrived! Ha-ha!", "До свидания? Ты же только приехал(а)! Ха-ха!")},
                 review=True),
             ask(choice("Послушай папу Тома: какой номер у вашего такси?", ["7", "1", "4"], 0, "Seven — семь (7).",
                        audio="Our taxi is number seven."),
                 ok=say("Dad", "Yes! Number seven. Let's go!", "Да! Номер семь. Пошли!")),
             say("Dad", "How many bags have you got?", "Сколько у тебя сумок?"),
             note("У тебя рюкзак и чемодан — две сумки."),
             ask(choice("Ответь папе Тома", ["Two!", "Ten!", "Tree!"], 0, "Two — два (2). Tree — это дерево!"),
                 ok=say("Dad", "Two bags. OK!", "Две сумки. Хорошо!"),
                 no={1: say("Dad", "Ten bags? Ha-ha! No, look — one, two.", "Десять сумок? Ха-ха! Нет, смотри — одна, две."),
                     2: say("Dad", "A tree? Ha-ha! T-W-O, two!", "Дерево? Ха-ха! T-W-O — two, два!")}),
             say("Anna", "I can count! One, two, three…", "Я умею считать! Один, два, три…"),
             ask(order("Помоги Анне считать дальше: собери «четыре, пять, шесть»", "four five six",
                       "Four, five, six — четыре, пять, шесть."),
                 ok=say("Anna", "Seven, eight, nine, ten! We can count!", "Семь, восемь, девять, десять! Мы умеем считать!")),
             pick("lucky", "Анна спрашивает: «What's your lucky number?» — «Какое твоё счастливое число?» Выбери своё!",
                  [("Seven!", "Семь!", "Seven", "Семь"), ("Three!", "Три!", "Three", "Три"),
                   ("Ten!", "Десять!", "Ten", "Десять")]),
             say("Anna", "{lucky}? Cool! My lucky number is five.", "{lucky}? Здорово! А моё счастливое число — пять."),
             say("Driver", "Hello! Where to?", "Здравствуйте! Куда едем?"),
             note("Том показывает тебе бумажку с адресом: дом 8."),
             ask(choice("Скажи таксисту, куда ехать", ["Number eight, please!", "Number nine, please!", "Number three, please!"], 0,
                        "Eight — восемь (8)."),
                 ok=say("Driver", "Number eight. OK, let's go!", "Номер восемь. Хорошо, поехали!"),
                 no={1: say("Tom", "Nine? No, no! Our house is number eight!", "Девять? Нет-нет! Наш дом — номер восемь!"),
                     2: say("Tom", "Three? No! Our house is number eight!", "Три? Нет! Наш дом — номер восемь!")}),
             note("Такси едет по улицам. Вдруг Том показывает в окно: на дороге жёлтые пёрышки — раз, два, три, четыре, пять!"),
             say("Tom", "Look! Yellow feathers! How many?", "Смотри! Жёлтые пёрышки! Сколько их?"),
             ask(write("Напиши Тому, сколько пёрышек: 5 словом", "five", "Five — пять."),
                 ok=say("Tom", "Five feathers! Chick-chick was here!", "Пять пёрышек! Чик-чик был здесь!")),
             speak("One, two, three, four, five!", "Один, два, три, четыре, пять!"),
             note("Такси остановилось у дома. Из окна выглядывает бабушка Тома."),
             say("Grandma", "Hello, {name}! Welcome! How are you?", "Здравствуй, {name}! Добро пожаловать! Как дела?"),
             ask(choice("Ответь бабушке", ["I'm fine, thank you.", "I'm seven.", "Bye!"], 0,
                        "I'm fine, thank you. — У меня всё хорошо, спасибо."),
                 ok=say("Grandma", "Lovely! Listen — can you hear my cats?", "Чудесно! Послушай — слышишь моих котов?"),
                 review=True),
             ask(choice("Послушай бабушку: сколько у неё котов? Нажми на число", ["three", "nine", "six"], 0, "Three — три (3).",
                        audio="I've got three cats.", pics=True),
                 ok=say("Grandma", "Yes, three cats! Come in!", "Да, три кота! Заходи!")),
             note("На калитке записка с жёлтым пёрышком: «Find me! Look at the door!» — «Найди меня! Посмотри на дверь!». "
                  "А под ней нарисованы палочки: IIIII IIIII."),
             ask(write("Сосчитай палочки — столько шагов до двери. Напиши число словом", "ten", "Ten — десять (10)."),
                 ok=say("Tom", "Ten steps to the door! Come on!", "Десять шагов до двери! Бежим!")),
         ],
         "outro": "Раз, два, три… десять шагов — и вы у двери дома. А на ней — новая записка с жёлтым пёрышком!"},

    2: {"title": "Волшебная записка",
        "intro": "Десять шагов — и вы у двери дома Тома. Дверь открывает его мама.",
        "lines": [
            say("Mum", "Hello, {name}! Welcome!", "Здравствуй, {name}! Добро пожаловать!"),
            ask(choice("Ответь маме Тома", ["Hello! Nice to meet you!", "My cake!", "My name is Anna."], 0,
                       "Nice to meet you! — Приятно познакомиться!"),
                ok=say("Mum", "Nice to meet you too! Come in!", "Мне тоже приятно! Заходи!"),
                no={2: say("Anna", "Ha-ha! No, I'm Anna!", "Ха-ха! Нет, Анна — это я!")},
                review=True),
            note("На коврике у двери большими буквами написано слово. Мама Тома показывает на него."),
            ask(choice("Прочитай слово на коврике. Что там написано?", ["home", "hat", "cake"], 0,
                       "Home [хоум] — дом. Волшебная E молчит, а O читается [оу].", pics=True),
                ok=say("Mum", "Yes, HOME! Welcome to our home!", "Да, HOME — дом! Добро пожаловать к нам домой!")),
            note("На двери — записка с жёлтым пёрышком: «Find me near the CAKE!»"),
            ask(choice("Прочитай записку Чик-чика. Где его искать?", ["cake", "bike", "home"], 0,
                       "Cake [кэйк] — торт. Волшебная E в конце молчит, а A читается [эй].", pics=True),
                ok=say("Mum", "A cake? My cake is in the kitchen!", "Торт? Мой торт на кухне!")),
            note("На кухне торт… а на торте следы маленьких лапок! Следы ведут дальше."),
            say("Mum", "Oh! Who ate my cake?", "Ой! Кто ел мой торт?"),
            ask(choice("Послушай маму: где ещё следы? Нажми на картинку", ["tap", "cake", "bike"], 0,
                       "Tap [тэп] — кран. Без E на конце A звучит коротко.", audio="Look at the tap!", pics=True),
                ok=say("Mum", "Yes, the tap! Water and yellow feathers!", "Да, кран! Вода и жёлтые пёрышки!"),
                no={1: say("Tom", "No, the cake is here. Mum said tap!", "Нет, торт — вот он. Мама сказала tap — кран!")}),
            note("На холодильнике — буквы-магнитики: N O T. Рядом лежит буква E, а под ней приписка Чик-чика: «Add me!»"),
            say("Anna", "Magic E! Let's add it!", "Волшебная E! Давай её добавим!"),
            ask(write("Добавь к N O T волшебную E. Какое слово получилось? Напиши его", "note",
                      "Not + E = note [ноут] — записка."),
                ok=say("Anna", "Note! A note from Chick-chick! Look, under the fridge!",
                       "Note — записка! Записка от Чик-чика! Смотри, под холодильником!")),
            note("Записка под холодильником: «I like cake. I like bikes! Look outside!»"),
            pick("like", "Анна спрашивает: «Cake or bikes — what do you like?» Что тебе больше нравится?",
                 [("Cake!", "Торт!", "Cake", "Торт"), ("Bikes!", "Велосипеды!", "Bikes", "Велосипеды")]),
            say("Anna", "{like}! Me too! But Chick-chick likes everything! Ha-ha!",
                "{like}! Мне тоже! А Чик-чику нравится всё! Ха-ха!"),
            note("У двери на улицу стоит велосипед Тома. На руле висит шапка, а из шапки торчат жёлтые пёрышки!"),
            ask(choice("Послушай Тома: где пёрышки? Нажми на картинку", ["hat", "home", "cake"], 0,
                       "Hat [хэт] — шапка. Коротко, без волшебной E.", audio="Look in my hat!", pics=True),
                ok=say("Tom", "My hat! And a new note!", "Моя шапка! И новая записка!")),
            speak("Cake, bike, home, note — magic E!", "Торт, велосипед, дом, записка — волшебная E!"),
        ],
        "outro": "В шапке записка: «Ищи меня в саду!» Но калитка в сад закрыта на замок с буквами."},

    34: {"title": "Замок на калитке",
         "intro": "Калитка в сад закрыта на кодовый замок. Вместо цифр на нём — буквы от J до R.",
         "lines": [
             say("Tom", "I know! Grandma's code is…", "Я знаю! Бабушкин код —…"),
             ask(choice("Том называет код по буквам. Какое слово получилось? Нажми на картинку", ["lion", "mouse", "juice"], 0,
                        "L-I-O-N — lion, лев.", audio="L-I-O-N!", pics=True),
                 ok=say("Tom", "Lion! L-I-O-N… Oh no, it doesn't open.", "Лев! L-I-O-N… Ой, не открывается.")),
             note("На заборе кто-то сидит и говорит: «Мяу!»"),
             say("Anna", "Look! Who is that?", "Смотри! Кто это?"),
             ask(choice("Ответь Анне", ["A cat!", "A dog!", "A lion!"], 0, "Cat — кот."),
                 ok=say("Anna", "Yes, it's Grandma's cat! He wants to help.", "Да, это бабушкин кот! Он хочет помочь."),
                 no={2: say("Anna", "A lion? Ha-ha! No, it's a cat!", "Лев? Ха-ха! Нет, это кот!")},
                 review=True),
             note("Вдруг под калиткой пробегает кто-то маленький и серый. Кот — за ним!"),
             ask(choice("Том кричит по буквам, кто пробежал. Нажми на картинку", ["mouse", "lion", "juice"], 0,
                        "M-O-U-S-E — mouse, мышь.", audio="A M-O-U-S-E!", pics=True),
                 ok=say("Tom", "A mouse! Ha-ha! Run, mouse, run!", "Мышка! Ха-ха! Беги, мышка, беги!")),
             say("Anna", "Let's try my favourite animal. Press the first letter!", "Давай попробуем моего любимого зверя. Нажми первую букву!"),
             ask(choice("Послушай Анну и найди букву на замке", ["R", "A", "O"], 0, "R — [а:], а A — [эй].", audio="R!"),
                 ok=say("Anna", "R! Good!", "R! Молодец!"),
                 no={1: say("Anna", "That's A. I said R!", "Это A [эй]. Я сказала R [а:]!")}),
             ask(order("Анна называет весь код. Послушай и собери буквы", "R A B B I T", "R-A-B-B-I-T — rabbit, кролик.",
                       audio="R-A-B-B-I-T."),
                 ok=say("Anna", "Rabbit! Oh no! It still doesn't open!", "Кролик! Ой, всё равно не открывается!")),
             note("Из-за забора прилетает бумажный самолётик с жёлтым пёрышком. На нём: «The code is my favourite fruit: O R A _ G E»."),
             ask(write("Какой буквы не хватает? Набери её на замке", "N", "O-R-A-N-G-E — orange, апельсин. N — [эн]."),
                 ok=say("Tom", "N! O-R-A-N-G-E — orange!", "N! O-R-A-N-G-E — апельсин!")),
             speak("J, K, L, M, N, O, P, Q, R!", "Алфавит от J до R!"),
         ],
         "outro": "Щёлк! Калитка открылась. В саду — разноцветные шарики, а за кустом что-то мелькнуло…"},

    12: {"title": "Кто за кустом?",
         "intro": "Калитка открылась! В саду бабушка Тома устроила праздник: везде разноцветные шарики.",
         "lines": [
             say("Grandma", "Hello, {name}! Look at my balloons! Red, blue, green, yellow…",
                 "Здравствуй, {name}! Посмотри на мои шарики! Красные, синие, зелёные, жёлтые…"),
             pick("colour", "Бабушка спрашивает: «What's your favourite colour?» — «Какой твой любимый цвет?» Выбери!",
                  [("Pink!", "Розовый!", "pink", "розовый"), ("Blue!", "Синий!", "blue", "синий"),
                   ("Green!", "Зелёный!", "green", "зелёный"), ("Purple!", "Фиолетовый!", "purple", "фиолетовый")]),
             say("Grandma", "Here is a {colour} balloon for you!", "Вот тебе {colour} шарик!"),
             note("На заборе висят шарики: красный, синий, зелёный, жёлтый, оранжевый, розовый."),
             say("Grandma", "How many balloons can you see?", "Сколько шариков ты видишь?"),
             ask(choice("Посчитай шарики и ответь бабушке", ["Six!", "Ten!", "Two!"], 0, "Six — шесть (6)."),
                 ok=say("Grandma", "Six! Well done!", "Шесть! Молодец!"),
                 review=True),
             say("Anna", "Look! Something is moving there!", "Смотри! Там что-то шевелится!"),
             ask(choice("Послушай Анну: какого цвета то, что за кустом? Нажми на цвет", ["yellow", "black", "pink"], 0,
                        "Yellow — жёлтый, как Чик-чик.", audio="Something yellow!", pics=True),
                 ok=say("Tom", "Yellow? Is it Chick-chick?", "Жёлтое? Это Чик-чик?")),
             say("Rex", "Woof! Woof!", "Гав! Гав!"),
             note("Из-за куста выбегает пёс Рекс — белый, с чёрными пятнами."),
             say("Tom", "No, it's Rex, our dog! What colour is he?", "Нет, это Рекс, наша собака! Какого он цвета?"),
             ask(choice("Ответь Тому", ["Black and white!", "Red and green!", "Orange!"], 0,
                        "Black — чёрный, white — белый."),
                 ok=say("Tom", "Yes! Black and white. Good boy, Rex!", "Да! Чёрно-белый. Хороший пёс, Рекс!")),
             note("Рекс принёс что-то в зубах и спрятался за Томом. Тебе не видно, что это."),
             ask(order("Спроси Тома, какого это цвета", "What colour is it?", "What colour is it? — Какого это цвета?"),
                 ok=say("Tom", "It's purple. It's Anna's ball!", "Он фиолетовый. Это мяч Анны!")),
             note("За кустом сидит игрушечная уточка: сама жёлтая, а клюв — цвета апельсина."),
             ask(choice("Скажи Анне, какого цвета клюв у уточки", ["Orange!", "Purple!", "Grey!"], 0,
                        "Orange — оранжевый (и апельсин тоже orange)."),
                 ok=say("Anna", "Orange! It's a toy duck, not Chick-chick.", "Оранжевый! Это игрушечная уточка, а не Чик-чик.")),
             say("Anna", "Let's make a poster: LOST CHICK!", "Давай сделаем объявление: ПОТЕРЯЛСЯ ЦЫПЛЁНОК!"),
             ask(write("Допиши объявление: «LOST: a little … chick» — какого цвета Чик-чик?", "yellow", "Yellow — жёлтый."),
                 ok=say("Anna", "A little yellow chick. Great poster!", "Маленький жёлтый цыплёнок. Отличное объявление!")),
             speak("Red, yellow, pink, green, purple, orange, blue!", "Красный, жёлтый, розовый, зелёный, фиолетовый, оранжевый, синий!"),
         ],
         "outro": "Вдруг у Анны звенит телефон — пришло фото…"},

    3: {"title": "Фото на телефоне",
        "intro": "У Анны звенит телефон. Пришло фото от знакомого рыбака с пристани.",
        "lines": [
            say("Anna", "Look! A photo on my phone!", "Смотри! Фото у меня в телефоне!"),
            note("На фото — море, большой корабль и рыба в сетке. Внизу подпись: SHIP."),
            ask(choice("Прочитай подпись под фото. Что на нём главное?", ["ship", "fish", "phone"], 0,
                       "Ship [шип] — корабль. SH читается [ш].", pics=True),
                ok=say("Tom", "A big ship! And a fish!", "Большой корабль! И рыба!")),
            say("Anna", "And look at the ship… a little yellow…", "А посмотри на корабль… маленький жёлтый…"),
            ask(choice("Послушай Анну. Кого она увидела на корабле?", ["chick", "fish", "ship"], 0,
                       "Chick [чик] — цыплёнок. CH читается [ч].", audio="A little yellow chick!"),
                ok=say("Tom", "Chick-chick! It's him!", "Чик-чик! Это он!")),
            say("Fisherman", "Hello! I've got a little yellow bird. He likes my fish!",
                "Здравствуйте! У меня маленькая жёлтая птичка. Ей нравится моя рыба!"),
            ask(order("Ответь рыбаку в чате: «Да, это мой цыплёнок!»", "Yes this is my chick",
                      "This [зис] — это. TH — язык между зубами."),
                ok=say("Fisherman", "Good! He is OK. Where are you now?", "Хорошо! С ним всё в порядке. А вы сейчас где?")),
            ask(choice("Ответь рыбаку", ["At home!", "On the ship!", "In the cake!"], 0, "At home — дома. Home — дом."),
                ok=say("Fisherman", "At home? Come to the sea! My ship is number nine.",
                       "Дома? Приезжайте к морю! Мой корабль — номер девять."),
                review=True),
            say("Tom", "What do you think, {name}?", "Что ты думаешь, {name}?"),
            ask(choice("Ответь Тому", ["I think we can go!", "I think it's a cat!", "Goodbye!"], 0,
                       "I think… — Я думаю… TH — язык между зубами."),
                ok=say("Tom", "I think so too!", "Я тоже так думаю!")),
            ask(write("Напиши рыбаку: «Please keep my …!» — кого ему нужно сберечь?", "chick", "Chick — цыплёнок."),
                ok=say("Fisherman", "OK! Your chick is with me. Chat soon!", "Хорошо! Твой цыплёнок со мной. До связи!")),
            speak("Ship, fish, chick, phone!", "Корабль, рыба, цыплёнок, телефон!"),
        ],
        "outro": "Это Чик-чик на корабле у моря! Папа Тома заводит машину: «Let's go to the sea!»"},

    4: {"title": "Под звёздами",
        "intro": "Вечер. Папа Тома ждёт вас у машины, чтобы ехать к морю.",
        "lines": [
            say("Dad", "Get in the car, please! What colour is my car?",
                "Садитесь в машину, пожалуйста! Какого цвета моя машина?"),
            note("Машина папы Тома — красная, как помидор."),
            ask(choice("Ответь папе Тома", ["Red!", "Blue!", "Star!"], 0, "Red — красный."),
                ok=say("Dad", "Yes, red! Let's go!", "Да, красная! Поехали!"),
                review=True),
            say("Anna", "Look up!", "Посмотри вверх!"),
            ask(choice("Послушай Анну и нажми на то, что она увидела в небе", ["star", "moon", "tree"], 0,
                       "Star [ста:] — звезда. AR — долгий [а:].", audio="A star! A big star!", pics=True),
                ok=say("Anna", "A star! And the moon!", "Звезда! И луна!")),
            say("Dad", "We are here! The sea!", "Мы на месте! Море!"),
            note("У моря растёт большое дерево, а за ним стоит корабль номер 9."),
            ask(choice("Послушай Тома: где корабль? Нажми на картинку", ["tree", "door", "car"], 0,
                       "Tree [три:] — дерево. EE — долгий [и:].", audio="The ship is near the tree!", pics=True),
                ok=say("Tom", "There! Ship number nine!", "Вон он! Корабль номер девять!")),
            say("Fisherman", "Hello! Your chick is in my room.", "Здравствуйте! Ваш цыплёнок в моей каюте."),
            ask(choice("Послушай рыбака и нажми на картинку", ["door", "fork", "car"], 0,
                       "Door [до:] — дверь. OOR — долгий [о:].", audio="Open the door, please!", pics=True),
                ok=say("Tom", "The door is closed. Look, a code!", "Дверь закрыта. Смотри, кодовый замок!")),
            note("На двери каюты замок с буквами и подсказка Чик-чика: «Code: it is in the sky at night, not a star. 4 letters»."),
            ask(write("Что ночью в небе, но не звезда? Набери слово на замке", "moon", "Moon [му:н] — луна. OO — долгий [у:]."),
                ok=say("Tom", "M-O-O-N! It's open!", "M-O-O-N! Открылось!")),
            say("Chick-chick", "Cheep-cheep! I'm here! I want to see the stars!",
                "Пип-пип! Я здесь! Я хочу посмотреть на звёзды!"),
            note("Вы садитесь на палубе. Мама Тома дала с собой пикник."),
            ask(choice("Послушай Анну и дай ей то, что она просит", ["fork", "star", "door"], 0,
                       "Fork [фо:к] — вилка. OR — долгий [о:].", audio="A fork, please!", pics=True),
                ok=say("Anna", "Thank you! Cake for everyone!", "Спасибо! Торт для всех!")),
            pick("sky", "Чик-чик спрашивает: «Do you like the moon or the stars?»",
                 [("The moon!", "Луну!", "The moon", "Луна"), ("The stars!", "Звёзды!", "The stars", "Звёзды")]),
            say("Chick-chick", "{sky}! I like them too! Cheep!", "{sky} — здорово! Мне тоже нравится! Пип!"),
            speak("Twinkle, twinkle, little star!", "Мерцай, мерцай, маленькая звёздочка!"),
        ],
        "outro": "Чик-чик нашёлся! Он просто хотел увидеть море и звёзды. Завтра Том покажет фотоальбом своей семьи!"},
}
