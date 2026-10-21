# -*- coding: utf-8 -*-
"""Мини-диалоги: партнёр говорит реплику, ученик выбирает правильный ответ.

Формат реплики:
  партнёр: {"en": "Hello!", "ru": "Привет!"}
  ученик:  {"options": ["Hi!", "Bye!", "I'm ten."], "answer": 0, "ru": "Привет!"}
Диалог привязан к уроку ("lesson") и открывается, когда урок пройден (или открыт для
повторения на самой странице урока)."""


def _p(en, ru):
    return {"en": en, "ru": ru}


def _me(options, answer, ru):
    return {"options": options, "answer": answer, "ru": ru}


DIALOGS = [
    {"key": "greet-meet", "lesson": 9, "title": "Знакомимся", "partner": "Tom", "lines": [
        _p("Hello! What's your name?", "Привет! Как тебя зовут?"),
        _me(["My name is Masha.", "I'm fine, thank you.", "Goodbye!"], 0, "Меня зовут Маша."),
        _p("Nice to meet you!", "Приятно познакомиться!"),
        _me(["Nice to meet you too!", "What's your name?", "Goodbye!"], 0, "Мне тоже приятно!"),
    ]},
    {"key": "greet-how", "lesson": 9, "title": "Как дела?", "partner": "Anna", "lines": [
        _p("Hi! How are you?", "Привет! Как дела?"),
        _me(["I'm fine, thank you.", "My name is Anna.", "Nice to meet you!"], 0, "Хорошо, спасибо."),
        _p("Goodbye!", "До свидания!"),
        _me(["Bye!", "Hello!", "I'm fine."], 0, "Пока!"),
    ]},
    {"key": "family-photo", "lesson": 13, "title": "Семейное фото", "partner": "Tom", "lines": [
        _p("Who is this?", "Кто это?"),
        _me(["This is my mother.", "I am ten.", "Yes, I can."], 0, "Это моя мама."),
        _p("And who is he?", "А кто он?"),
        _me(["He is my brother.", "She is my sister.", "It is red."], 0, "Он мой брат."),
    ]},
    {"key": "be-questions", "lesson": 15, "title": "Ты счастлива?", "partner": "Anna", "lines": [
        _p("Are you happy?", "Ты счастлива?"),
        _me(["Yes, I am.", "Yes, I do.", "Yes, I can."], 0, "Да."),
        _p("Is your brother at home?", "Твой брат дома?"),
        _me(["No, he isn't.", "No, I'm not.", "No, you aren't."], 0, "Нет."),
    ]},
    {"key": "can-swim", "lesson": 18, "title": "Что ты умеешь?", "partner": "Tom", "lines": [
        _p("Can you swim?", "Ты умеешь плавать?"),
        _me(["Yes, I can.", "Yes, I do.", "Yes, I am."], 0, "Да, умею."),
        _p("Can you fly?", "А летать умеешь?"),
        _me(["No, I can't. I'm not a bird!", "Yes, I fly.", "No, I'm not."], 0, "Нет, не умею. Я же не птица!"),
    ]},
    {"key": "like-food", "lesson": 20, "title": "Любимая еда", "partner": "Anna", "lines": [
        _p("Do you like apples?", "Ты любишь яблоки?"),
        _me(["Yes, I do.", "Yes, I am.", "Yes, I can."], 0, "Да, люблю."),
        _p("Do you like milk?", "А молоко любишь?"),
        _me(["No, I don't.", "No, I'm not.", "No, I can't."], 0, "Нет, не люблю."),
    ]},
    {"key": "days-today", "lesson": 36, "title": "Какой сегодня день?", "partner": "Tom", "lines": [
        _p("What day is it today?", "Какой сегодня день?"),
        _me(["It's Monday.", "It's May.", "It's ten."], 0, "Сегодня понедельник."),
        _p("Is it the weekend?", "Сегодня выходной?"),
        _me(["No, it isn't.", "No, I don't.", "No, I can't."], 0, "Нет."),
    ]},
    {"key": "birthday", "lesson": 37, "title": "День рождения", "partner": "Anna", "lines": [
        _p("When is your birthday?", "Когда у тебя день рождения?"),
        _me(["My birthday is in May.", "My birthday is Monday.", "I am ten."], 0, "Мой день рождения в мае."),
        _p("Happy birthday!", "С днём рождения!"),
        _me(["Thank you!", "Goodbye!", "Where?"], 0, "Спасибо!"),
    ]},
    {"key": "age", "lesson": 38, "title": "Сколько тебе лет?", "partner": "Tom", "lines": [
        _p("How old are you?", "Сколько тебе лет?"),
        _me(["I'm ten years old.", "I'm ten o'clock.", "I have got ten."], 0, "Мне десять лет."),
        _p("My brother is thirty!", "Моему брату тридцать!"),
        _me(["Wow! He is old.", "Wow! He is small.", "Wow! It is red."], 0, "Ого! Он взрослый."),
    ]},
    {"key": "have-pet", "lesson": 40, "title": "Домашние животные", "partner": "Anna", "lines": [
        _p("Have you got a pet?", "У тебя есть питомец?"),
        _me(["Yes, I have. I have got a cat.", "Yes, I am a cat.", "No, I can't."], 0, "Да, у меня есть кот."),
        _p("Has your cat got a name?", "У твоего кота есть имя?"),
        _me(["Yes, it has.", "Yes, it is.", "Yes, it does."], 0, "Да, есть."),
    ]},
    {"key": "where-bag", "lesson": 27, "title": "Где моя сумка?", "partner": "Tom", "lines": [
        _p("Where is my bag?", "Где моя сумка?"),
        _me(["It is under the table.", "It is Monday.", "It is ten."], 0, "Она под столом."),
        _p("Thank you! Where is my pen?", "Спасибо! А где моя ручка?"),
        _me(["It is in your bag.", "It is not Monday.", "It can swim."], 0, "Она в твоей сумке."),
    ]},
    {"key": "present-simple", "lesson": 23, "title": "Что ты делаешь каждый день?", "partner": "Anna", "lines": [
        _p("Do you go to school?", "Ты ходишь в школу?"),
        _me(["Yes, I do.", "Yes, I am.", "Yes, I can."], 0, "Да, хожу."),
        _p("Does your brother go to school?", "А твой брат ходит в школу?"),
        _me(["No, he doesn't.", "No, he isn't.", "No, he don't."], 0, "Нет, не ходит."),
    ]},
    {"key": "doing-now", "lesson": 31, "title": "Что ты сейчас делаешь?", "partner": "Tom", "lines": [
        _p("Are you reading?", "Ты сейчас читаешь?"),
        _me(["Yes, I am.", "Yes, I do.", "Yes, I can."], 0, "Да, читаю."),
        _p("Is your mother sleeping?", "Твоя мама спит?"),
        _me(["No, she isn't.", "No, she doesn't.", "No, she can't."], 0, "Нет, не спит."),
    ]},
    {"key": "weather", "lesson": 29, "title": "Какая погода?", "partner": "Anna", "lines": [
        _p("What is the weather like?", "Какая сегодня погода?"),
        _me(["It is sunny.", "It is Monday.", "It is a cat."], 0, "Солнечно."),
        _p("Is it cold?", "Холодно?"),
        _me(["No, it isn't. It is hot!", "No, I'm not.", "Yes, I do."], 0, "Нет. Жарко!"),
    ]},
    {"key": "final-me", "lesson": 32, "title": "Расскажи о себе", "partner": "Tom", "lines": [
        _p("Hello! What's your name?", "Привет! Как тебя зовут?"),
        _me(["Hello! My name is Masha.", "I am fine.", "I have got a cat."], 0, "Привет! Меня зовут Маша."),
        _p("How old are you?", "Сколько тебе лет?"),
        _me(["I am ten years old.", "I am ten o'clock.", "I can ten."], 0, "Мне десять лет."),
        _p("What do you like?", "Что ты любишь?"),
        _me(["I like drawing.", "I am drawing a cat.", "I can drawing."], 0, "Я люблю рисовать."),
    ]},
]

def _d(key, lesson, title, partner, *lines):
    return {"key": key, "lesson": lesson, "title": title, "partner": partner, "lines": list(lines)}


DIALOGS += [
    _d("count-seven", 10, "Какое число?", "Sam",
       _p("Is it seven?", "Это семь?"),
       _me(["No, it isn't. It is eight.", "Yes, I am.", "No, I can't."], 0, "Нет. Это восемь."),
       _p("And this? Is it five?", "А это? Это пять?"),
       _me(["Yes, it is!", "Yes, I do.", "Yes, it can."], 0, "Да!")),
    _d("colors-bag", 12, "Какого цвета?", "Anna",
       _p("What color is your bag?", "Какого цвета твоя сумка?"),
       _me(["It is blue.", "It is ten.", "It is Monday."], 0, "Она синяя."),
       _p("Is your pen red?", "Твоя ручка красная?"),
       _me(["No, it is green.", "No, I am green.", "Yes, I can."], 0, "Нет, она зелёная.")),
    _d("be-intro", 14, "Кто ты?", "Tom",
       _p("I am Tom. Who are you?", "Я Том. А ты кто?"),
       _me(["I am Masha.", "I is Masha.", "You are Masha."], 0, "Я Маша."),
       _p("Are you a student?", "Ты ученица?"),
       _me(["Yes, I am a student.", "Yes, I have a student.", "Yes, you are."], 0, "Да, я ученица.")),
    _d("teacher-commands", 16, "На уроке", "Mr. Brown",
       _p("Stand up, please!", "Встань, пожалуйста!"),
       _me(["OK!", "Goodbye!", "I am a book."], 0, "Хорошо!"),
       _p("Sit down. Open your book!", "Садись. Открой книгу!"),
       _me(["OK, I open my book.", "OK, I am a book.", "No, I am blue."], 0, "Хорошо, открываю книгу."),
       _p("Listen and read!", "Слушай и читай!"),
       _me(["OK. Thank you!", "Yes, I can swim.", "It is Monday."], 0, "Хорошо. Спасибо!")),
    _d("zoo", 17, "В зоопарке", "Dad",
       _p("Look! What animal is this?", "Смотри! Что это за животное?"),
       _me(["It is a lion.", "It is red.", "It is Monday."], 0, "Это лев."),
       _p("Is it a cow?", "Это корова?"),
       _me(["No, it is a horse.", "No, I am a horse.", "Yes, I can."], 0, "Нет, это лошадь.")),
    _d("rex-dog", 17, "Говорящая собака", "Rex",
       _p("Woof! I am Rex. What is your name?", "Гав! Я Рекс. А тебя как зовут?"),
       _me(["My name is Masha.", "I am fine, thank you.", "Goodbye!"], 0, "Меня зовут Маша."),
       _p("Nice to meet you! Do you like dogs?", "Приятно познакомиться! Ты любишь собак?"),
       _me(["Yes, I do!", "Yes, I am.", "Yes, I can."], 0, "Да, люблю!")),
    _d("whats-this", 39, "Кто и что?", "Sam",
       _p("Who is she?", "Кто она?"),
       _me(["She is my sister.", "It is a pen.", "He is my sister."], 0, "Она моя сестра."),
       _p("What is this?", "Что это?"),
       _me(["It is a pen.", "She is a pen.", "I am a pen."], 0, "Это ручка.")),
    _d("my-your", 41, "Чьё это?", "Sam",
       _p("Is this your pen?", "Это твоя ручка?"),
       _me(["Yes, it is my pen.", "Yes, it is your pen.", "Yes, I am a pen."], 0, "Да, это моя ручка."),
       _p("Is that his dog?", "А то его собака?"),
       _me(["No, it is her dog.", "No, it is my cat.", "No, I am a dog."], 0, "Нет, это её собака.")),
    _d("cafe-fruit", 19, "Фруктовый лоток", "Ben",
       _p("Hello! What is this?", "Здравствуй! Что это?"),
       _me(["It is a banana.", "It is Monday.", "I am a banana."], 0, "Это банан."),
       _p("And this?", "А это?"),
       _me(["It is bread.", "It is blue.", "I can bread."], 0, "Это хлеб.")),
    _d("doctor", 21, "У доктора", "Doctor Kate",
       _p("Hello! What is this?", "Здравствуй! Что это?"),
       _me(["It is my nose.", "It is my Monday.", "I am a nose."], 0, "Это мой нос."),
       _p("And this?", "А это?"),
       _me(["It is my ear.", "It is my cat.", "I am an ear."], 0, "Это моё ухо.")),
    _d("daily-mom", 24, "Утро с мамой", "Mom",
       _p("Do you brush your teeth?", "Ты чистишь зубы?"),
       _me(["Yes, I do.", "Yes, I am.", "Yes, I can."], 0, "Да, чищу."),
       _p("Do you do your homework?", "Ты делаешь домашнее задание?"),
       _me(["Yes, I do. I do my homework.", "Yes, I am a homework.", "No, I am blue."], 0, "Да, делаю.")),
    _d("spell-it", 35, "Как пишется?", "Mr. Brown",
       _p("How do you spell cat?", "Как пишется cat по буквам?"),
       _me(["C-A-T", "K-A-T", "C-O-T"], 0, "C-A-T"),
       _p("Good! How do you spell dog?", "Хорошо! А dog?"),
       _me(["D-O-G", "D-A-G", "T-O-G"], 0, "D-O-G")),
    _d("this-these", 42, "Что это?", "Anna",
       _p("Is this a pen?", "Это ручка?"),
       _me(["Yes, it is.", "Yes, they are.", "Yes, I do."], 0, "Да."),
       _p("Are these pens?", "А это ручки?"),
       _me(["Yes, they are.", "Yes, it is.", "Yes, I am."], 0, "Да.")),
    _d("big-small", 44, "Большой или маленький?", "Dad",
       _p("Is the elephant small?", "Слон маленький?"),
       _me(["No, it is big.", "No, I am big.", "Yes, it can."], 0, "Нет, он большой."),
       _p("Is a turtle fast?", "Черепаха быстрая?"),
       _me(["No, it is slow.", "No, it is hot.", "Yes, I am."], 0, "Нет, она медленная.")),
    _d("clothes-shop", 26, "В магазине одежды", "Ben",
       _p("Hello! Look at this T-shirt.", "Здравствуй! Посмотри на эту футболку."),
       _me(["I like it!", "I am a T-shirt.", "It is Monday."], 0, "Мне нравится!"),
       _p("Is it red?", "Она красная?"),
       _me(["No, it is blue.", "No, I am blue.", "Yes, I can."], 0, "Нет, она синяя."),
       _p("Do you like the jeans?", "А джинсы тебе нравятся?"),
       _me(["Yes, I do.", "Yes, I am.", "Yes, they can."], 0, "Да.")),
    _d("house-tour", 28, "Дом бабушки", "Grandma",
       _p("This is my house. Is this your bedroom?", "Это мой дом. Это твоя спальня?"),
       _me(["No, it is the kitchen.", "No, I am the kitchen.", "Yes, I can."], 0, "Нет, это кухня."),
       _p("Is this the bathroom?", "А это ванная?"),
       _me(["Yes, it is.", "Yes, I am.", "Yes, it does."], 0, "Да.")),
    _d("hobbies-sam", 30, "Хобби", "Sam",
       _p("What do you like?", "Что ты любишь?"),
       _me(["I like drawing.", "I am drawing a cat.", "I can drawing."], 0, "Я люблю рисовать."),
       _p("Do you like football?", "Любишь футбол?"),
       _me(["No, I don't. I like swimming.", "No, I am swimming.", "Yes, I swim."], 0, "Нет. Я люблю плавать.")),
    _d("weekdays-like", 36, "Любимый день", "Anna",
       _p("Do you like Monday?", "Ты любишь понедельник?"),
       _me(["No, I don't. I like Saturday.", "No, I am Saturday.", "Yes, I can."], 0, "Нет. Я люблю субботу."),
       _p("Why?", "Почему?"),
       _me(["It is the weekend!", "It is blue!", "I am the weekend!"], 0, "Это выходной!")),
    _d("city-places", 10001, "Что это за здание?", "Mr. Brown",
       _p("Look! Is this a hospital?", "Смотри! Это больница?"),
       _me(["No, it is a theatre.", "No, I am a theatre.", "Yes, I can."], 0, "Нет, это театр."),
       _p("And is this a station?", "А это вокзал?"),
       _me(["Yes, it is!", "Yes, I am.", "Yes, I do."], 0, "Да!")),
]

CHARACTERS = {
    "Tom": ("👦", "друг", "#cfe8ff"), "Anna": ("👧", "подруга", "#ffd9ec"), "Sam": ("🧒", "одноклассник", "#d8f5d0"),
    "Mom": ("👩", "мама", "#ffe0cf"), "Dad": ("👨", "папа", "#d9e0ff"), "Grandma": ("👵", "бабушка", "#f3dcff"),
    "Mr. Brown": ("👨\u200d🏫", "учитель", "#fff0b8"), "Doctor Kate": ("👩\u200d⚕️", "доктор", "#d4f4f0"),
    "Ben": ("🧑\u200d💼", "продавец", "#ffe8b5"), "Rex": ("🐶", "собака", "#f0e0c8"),
}


def character(name):
    pic, role, bg = CHARACTERS.get(name, ("🙂", "", "#e6e6f5"))
    return {"pic": pic, "role": role, "bg": bg}


DIALOGS_BY_KEY = {d["key"]: d for d in DIALOGS}
