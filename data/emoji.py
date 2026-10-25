# -*- coding: utf-8 -*-
"""Картинки-эмодзи к словам (для карточек, словаря и повторения).
Ключ — слово в нижнем регистре; для «Mother / Mom» берётся первое слово."""

_PAIRS = """
cat 🐱|pen 🖊️|pig 🐷|dog 🐶|cup ☕|hat 🎩|tap 🚰|note 📝|cake 🍰|bike 🚲|home 🏠|house 🏠|flat 🏢
red 🔴|blue 🔵|green 🟢|yellow 🟡|orange 🟠|purple 🟣|pink 🌸|black ⚫|white ⚪|brown 🟤|grey 🔘
one 1️⃣|two 2️⃣|three 3️⃣|four 4️⃣|five 5️⃣|six 6️⃣|seven 7️⃣|eight 8️⃣|nine 9️⃣|ten 🔟
ship 🚢|fish 🐟|chat 💬|chip 🍟|think 🤔|phone 📱|photo 📷|tree 🌳|sea 🌊|moon 🌙|car 🚗|star ⭐|fork 🍴|door 🚪|clock 🕐|crab 🦀|swim 🏊|lamb 🐑|climb 🧗|wrong ❌|write ✍️|go 🚶|cycle 🚲|city 🏙️|gym 🏋️
mother 👩|father 👨|sister 👧|brother 👦|grandmother 👵|grandfather 👴|family 👨‍👩‍👧‍👦|man 👨|woman 👩|child 🧒|children 🧒
horse 🐴|sheep 🐑|cow 🐮|duck 🦆|chicken 🐔|lion 🦁|tiger 🐯|bear 🐻|fox 🦊|elephant 🐘|monkey 🐵|giraffe 🦒|mouse 🐭|mice 🐭
apple 🍎|banana 🍌|grape 🍇|peach 🍑|carrot 🥕|tomato 🍅|potato 🥔|bread 🍞|milk 🥛|water 💧|juice 🧃|cheese 🧀|egg 🥚|ice cream 🍦
head 🙂|face 😀|eye 👁️|ear 👂|nose 👃|mouth 👄|hair 💇|hand ✋|arm 💪|leg 🦵|foot 🦶|feet 🦶|finger ☝️|tooth 🦷|teeth 🦷
t-shirt 👕|shirt 👔|jeans 👖|trousers 👖|shoes 👟|socks 🧦|coat 🧥|dress 👗
kitchen 🍳|bedroom 🛏️|bathroom 🛁|living room 🛋️|garden 🌷
spring 🌸|summer ☀️|autumn 🍂|winter ❄️|sunny ☀️|rainy 🌧️|cloudy ☁️|snowy 🌨️|windy 💨
football ⚽|swimming 🏊|cycling 🚴|drawing 🎨|dancing 💃|reading 📖|playing games 🎮
station 🚉|garage 🛠️|café ☕|theatre 🎭|baker's 🥖|hospital 🏥|greengrocer's 🥦|post office 📮
big 🐘|small 🐜|long 📏|short 🤏|hot 🔥|cold 🥶|fast 🐆|slow 🐢|happy 😊|sad 😢|new ✨
hello 👋|hi 👋|goodbye 👋|bye 👋|weekend 🎉|jump 🦘|listen 👂|look 👀|read 📖|stand up 🧍|sit down 🪑
wake up ⏰|brush my teeth 🦷|have breakfast 🥣|go to school 🏫|have lunch 🥪|play with friends 🧑‍🤝‍🧑|do homework ✏️|have dinner 🍽️|read a book 📖|go to bed 😴
book 📕|notebook 📓|pencil ✏️|ruler 📏|rubber 🧽|teacher 👩‍🏫|classroom 🏫|maths 🧮|english 🇬🇧|art 🎨|music 🎵|pe 🏃
doctor 👩‍⚕️|cook 👨‍🍳|driver 🚌|farmer 🧑‍🌾|pilot 👨‍✈️|singer 🎤|policeman 👮|artist 🧑‍🎨
clock 🕐|time ⏰|morning 🌅|afternoon ☀️|evening 🌆
ruble 🪙|rubles 🪙|price 🏷️|shop 🛍️|money 💰|expensive 💎|cheap 🏷️|buy 🛒
bus 🚌|train 🚆|plane ✈️|boat ⛵|taxi 🚕|map 🗺️|street 🛣️
menu 📋|waiter 🧑‍🍳|table 🪑|bill 🧾|pizza 🍕|soup 🍲|salad 🥗|burger 🍔|delicious 😋
please 🙏|thank you 🙏|thanks 🙏|sorry 🙇|good morning 🌅|good night 🌙
bed 🛏️|chair 🪑|desk 🖥️|wardrobe 🚪|shelf 📚|lamp 💡|window 🪟|mirror 🪞|carpet 🟥|picture 🖼️|pillow 🛌|blanket 🛌|toy 🧸
fridge 🧊|cooker 🔥|oven ♨️|kettle 🫖|sink 🚰|plate 🍽️|bowl 🥣|glass 🥛|spoon 🥄|knife 🔪|pan 🍳
piano 🎹|guitar 🎸|drum 🥁|violin 🎻|trumpet 🎺|song 🎶|sing 🎤|dance 💃|concert 🎪|loud 🔊|quiet 🤫
ball ⚽|basketball 🏀|tennis 🎾|racket 🏸|skates ⛸️|skateboard 🛹|kite 🪁|doll 🪆|puzzle 🧩|robot 🤖|throw 🤾|catch 🧤
sofa 🛋️|armchair 💺|tv 📺|curtains 🪟|fireplace 🔥|vase 🏺|plant 🪴|rug 🟫|computer 💻
flower 🌸|grass 🌿|sun ☀️|bee 🐝|butterfly 🦋|bird 🐦|bench 🪑|paper 📄|scissors ✂️|glue 🧴|paint 🎨|brush 🖌️|box 📦
"""

EMOJI = {}
for _chunk in _PAIRS.replace("\n", "|").split("|"):
    _chunk = _chunk.strip()
    if _chunk:
        _word, _, _pic = _chunk.rpartition(" ")
        EMOJI[_word.strip().lower()] = _pic

# Для этих слов подходящего эмодзи нет (стул вместо стола, лампочка вместо лампы…) — свой рисунок
# static/pics/<слово>.svg; в данных пишется «@слово», выводится фильтром |pic и window.picHtml.
DRAWN = ("table", "desk", "wardrobe", "carpet", "rug", "curtains", "armchair", "fireplace", "rubber", "glue",
         "sink", "shelf", "cooker", "oven", "lamp", "blanket", "pillow")
EMOJI.update({_w: "@" + _w for _w in DRAWN})


def emoji_for(en):
    """Эмодзи к слову или '' (для фраз и абстрактных слов картинки нет)."""
    key = en.split("/")[0].strip().lower()
    return EMOJI.get(key, "")
