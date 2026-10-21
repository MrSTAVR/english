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

DIALOGS_BY_KEY = {d["key"]: d for d in DIALOGS}
