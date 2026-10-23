/* ============================================================
   🐣 Чик-чик 2.0 — виртуальный помощник в стиле приложения.
   • рисуется в SVG (цвета иконки приложения), живой: дышит, моргает,
     оглядывается, машет крыльями, клюёт, танцует, засыпает;
   • комментирует шаги урока, ответы, результаты, сад, словарь, теорию;
   • если быстро-быстро тыкать — надувается и ВЗРЫВАЕТСЯ перьями,
     а потом возвращается одним из трёх способов.
   Стили: static/mascot.css
   ============================================================ */
(function () {
  'use strict';

  var S = window.MASCOT_SETTINGS || {};
  if (S.enabled === false) return;

  var NAME = S.name || 'Чик-чик';
  var WHO = S.student ? ', ' + S.student : '';           // «, Маша» или пусто
  var RM = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  var HIDE_AFTER = 22000;        // облачко сворачивается через …
  var SLEEP_AFTER = 75000;       // засыпает без действий
  var CHAIN_GAP = 650;           // макс. пауза между «быстрыми» тыками
  var EXPLODE_AT = 8;            // тык, на котором взрывается

  /* ---------- тексты ---------- */
  var T = {
    helloMorning: ['Доброе утро{who}! ☀️ Чем займёмся сегодня?', 'Утро! Самое время для пары новых слов{who} 🌅'],
    helloDay: ['Привет{who}! 👋 Готов(а)… то есть, готовы учить английский?', 'Добрый день{who}! Я скучал по тебе 🐣'],
    helloEvening: ['Добрый вечер{who}! 🌙 Давай ещё один урок — и отдыхать!', 'Вечер — отличное время, чтобы повторить слова 🌆'],
    helloNight: ['Уже так поздно{who}! 🌛 Один урок — и спать, ладно?', 'Ночь на дворе… Я зеваю 🥱 Давай быстренько, и баиньки!'],
    helloAnon: ['Привет! Я {name} — твой помощник. Готовы учить английский? 🎈',
                'Хи-хи! Это я, {name}! Давай сегодня выучим что-нибудь классное ✨'],
    lessonStart: ['Урок «{title}»! Мы с тобой всё одолеем 💪',
                  'Начинаем «{title}». Читай вслух — так слова запоминаются лучше!',
                  '«{title}» — поехали! Я буду рядом 🐣'],
    theoryDone: ['Отлично, теория прочитана! 📖 Теперь знакомься со словами.',
                 'Молодец! Запомнила главное? Идём к карточкам! 🧠'],
    wordsDone: ['Слова почти в кармане 😎 Теперь потренируемся!',
                'Уже столько слов! Потренируйся — и можно сдавать тест 📝'],
    testOpen: ['Это итоговый тест. Не торопись, читай каждый вопрос дважды 😉',
               'Тест пошёл! Я рядом — держу за тебя крылышки 🤞'],
    right: ['Так правильно! 🎉', 'Верно! Ты умница 🌟', 'Есть! Так держать 🔥', 'Ура, правильный ответ! 👏',
            'Бинго! 🎯', 'Вот это да! Ни разу не ошиблась… ну, почти 😄', 'Чирик-чирик, верно! 🐥'],
    wrong: ['Пока нет 🤔 Прочитай вопрос ещё раз — ты близко!',
            'Не расстраивайся! На ошибках учатся — попробуй ещё разок 💪',
            'Хм, не то. Вспомни карточки — там был ответ! 🧠',
            'Почти! Перечитай задание внимательно 😉',
            'Ошибка — это ступенька вверх 🪜 Пробуем снова!'],
    tapHint: 'Сначала коснись карточки, потом цели — это работает так же, как перетаскивание ✋',
    dragHint: 'Перетащи карточку на её пару 🖱️ или просто кликни карточку, потом цель ✋',
    allMatched: 'Все пары соединены! Жми «Проверить ✔️» 😊',
    allSorted: 'Все слова в корзинах! Проверяй — удачи! 🍀',
    allExercises: 'Все упражнения выполнены! 🎊 Теперь — боевой тест! 📝',
    coinsEarned: 'И не забудь: тебе начислено {n} монеток — можно купить украшение для сада! 🪙',
    gardenHello: ['Ого, какой у тебя сад! 🌳 Растёт не по дням, а по урокам!',
                  'Привет в твоём саду! 👋 Видишь, какое дерево? Это всё твоя серия занятий!'],
    gardenBroken: 'Серия прервалась, и дерево сдулось до жёлудя 🍂 Позанимайся сегодня — и оно оживёт!',
    gardenStreak: 'Серия — {n} дн. подряд! 🌱➡️🌳',
    gardenShop: 'Кстати, за монетки можно украсить сад. Чем больше занимаешься — тем он красивее ✨',
    wordsPage: ['Это твой словарь{who}! 📚 Нажимай 🔊 и повторяй за диктором.',
                'Столько слов выучено! Попробуй «скрыть перевод» и вспомнить сама 🧠',
                'Каждое слово тут — твоя победа 🏅'],
    achPage: ['Вот твоя коллекция! 🏅 Собрано {n} из {total}. Загляни в «Скоро получишь» — там видно, сколько осталось!',
              'Столько медалей! ✨ {n} из {total}. Золотые и легендарные — самые редкие 👑'],
    achPageEmpty: 'Тут пока пусто, но это ненадолго: пройди урок — и получишь первую медаль! 🥉',
    speakPage: ['Сейчас потренируем произношение! 🎤 Нажми на микрофон и скажи слово вслух.',
                'Говорим по-английски! 🗣️ Сначала послушай 🔊, потом повтори.'],
    speakStars3: ['Отлично! Как настоящая англичанка! 🌟', 'Три звезды! Произношение — супер ✨', 'Чистый звук! 🔔 Так держать!'],
    speakStars2: ['Хорошо! Почти идеально 👍 Попробуй ещё разок — на три звезды?', 'Неплохо! Ещё чуть-чуть чётче 🎯'],
    speakStars1: ['Я почти понял(а) 🤔 Послушай 🐢 медленно и повтори.', 'Близко! Скажи погромче и отчётливее 🎤'],
    speakStars0: ['Не расслышал(а) 🙈 Попробуй ещё раз — я верю в тебя!', 'Ничего страшного! Послушай ещё раз 🔊 и повтори.'],
    reviewPage: ['Время повторить слова! 🔁 Чем чаще повторяешь, тем крепче память.', 'Повторение — мать учения 🧠 Поехали!'],
    reviewOk: ['Верно! ✅', 'Молодец! 🌟', 'Так держать! 💪', 'Отлично, ты помнишь! 🧠'],
    reviewBad: ['Ничего, это слово вернётся — запомнишь! 🌱', 'Упс! Посмотри правильный ответ 👀', 'Не беда, повторение для этого и нужно 🤗'],
    reviewDone: ['Раунд пройден! 🏅 Память становится крепче с каждым разом.', 'Ура, повторили! 🎉'],
    goalDone: ['Цель дня выполнена! 🎯 Держи монетки для сада!', 'Ура, цель на сегодня достигнута! 🌟 Ты молодец!'],
    writingPage: ['Пишем по-английски! ✍️ Слово за словом — и получится предложение.', 'Ошибся? Не страшно — на ошибках мы и учимся! 🌱'],
    storiesPage: ['Давай почитаем! 📖 Нажимай на слова — я подскажу перевод.', 'А можно послушать историю на слух 🎧 — это тоже тренировка!'],
    wardrobePage: ['Ооо, гардероб! 🎩 Давай выберем мне наряд!', 'Хочу шляпу! Или очки! Или всё сразу? 😎', 'Как я тебе в этом? Красавчик, правда? 🐥'],
    gamesPage: ['Играем! 🎮 Выбирай игру — слова запоминаются сами.', 'Игры со словами — мои любимые! 🐣 С какой начнём?'],
    dialogsPage: ['Давай поговорим по-английски! 💬 Выбирай правильные ответы.', 'Диалоги — это почти настоящий разговор! 🗣️'],
    game3: ['Три звезды! Ты чемпион! 🏆', 'Отлично сыграно! ⭐⭐⭐'], game2: ['Хорошо! Попробуй ещё — на три звезды? 🏅'], game1: ['Неплохо! В следующий раз получится лучше 💪'], game0: ['Ничего, потренируйся — и всё получится! 🌱'],
    dialogDone: ['Диалог пройден! 💬 Так и разговаривают англичане!', 'Ты отлично поговорила! 🗣️'],
    wordsEmpty: 'Здесь пока пусто — пройди первый урок, и слова появятся! 🌱',
    theoryPage: ['Тут вся теория, что мы прошли 📖 Если что-то забылось — заглядывай сюда!',
                 'Хочешь повторить правило? Открывай нужный урок и читай вслух 🗣️'],
    theoryEmpty: 'Теории пока нет — пройди первый урок, и правила соберутся здесь 📚',
    resultPass100: ['ВОСХИТИТЕЛЬНО! 100%! 🎆 Я знал, что ты сможешь!', 'СТО ПРОЦЕНТОВ!!! 🏆 Ни одной ошибки!'],
    resultPass: ['Урок пройден! 🎉 Отличная работа!', 'Сдано! Мама с папой будут гордиться 😊'],
    resultNear: 'Очень близко к финишу! Ещё чуть-чуть — и урок твой 🌈',
    resultLow: 'Ничего страшного! Давай повторим слова и попробуем ещё раз 🤗',
    achIntro: ['СТОП! Стой смирно 🫡 У меня для тебя кое-что есть…',
               'Так-так-так… *нюхает* Чую, пахнет подарком! 🎁',
               'Ты даже не представляешь, что я принёс! 😲'],
    achOpen: ['Ура!! Твоя награда: «{title}» {emoji} Ты её честно заслужила!',
              'Смотри, какой клад! «{title}» {emoji} — так и сияет! ✨',
              '«{title}» {emoji} — теперь в твоей коллекции! Я тобой горжусь 💛'],
    achTier: {
      bronze: ['Бронзовая награда «{title}» {emoji} — отличное начало! 🥉', 'Есть! «{title}» {emoji} — первая ступенька к серебру 🪜'],
      silver: ['Серебро! «{title}» {emoji} — вот это класс! 🥈', '«{title}» {emoji} — серебряная награда, ты растёшь на глазах ✨'],
      gold: ['ЗОЛОТО!!! «{title}» {emoji} Ты просто звезда! 🥇', 'Золотая награда «{title}» {emoji}! Я так тобой горжусь! 🌟'],
      legend: ['ЛЕГЕНДАРНАЯ НАГРАДА!!! «{title}» {emoji} Такое получают единицы! 🎆👑', '«{title}» {emoji} — ЛЕГЕНДА! Я в полном восторге, чирик-чирик-чирик!!! 🎇']
    },
    achAfter: ['Каждая ачивка — шажок к большому английскому 🇬🇧',
               'Откроешь все ачивки — устроим целый салют! 🎆',
               'Покажи маме с папой — они будут в восторге! 👨‍👩‍👧'],
    doneAll: 'ТЫ ПРОШЛА ВСЕ УРОКИ!!! 🏆🎆 Мы самая крутая команда!',
    welcomeBack: ['С возвращением{who}! Продолжаем с того места, где остановились 🚀',
                  'О, ты вернулась! Я уже заждался 🐣'],
    hiAgain: ['А, это снова ты! 👋', 'Привет-привет! Нажми на меня — поболтаем 🐥', 'Я тут! Чем помочь? 🙂'],

    /* --- обычные тычки по Чик-чику --- */
    pokes: ['Чем могу помочь? Жми «Дальше» — и идём вперёд 🙂',
            '*подмигивает* Ты суперская! 😜',
            'Я верю в тебя! Даже когда ты сомневаешься 💛',
            'Чирик! 🐥 Это я так говорю «привет».',
            'Щекотно! Хи-хи 🤭',
            'Хочешь секрет? Английский — это весело 🤫',
            'Знаешь, что я люблю больше зёрнышек? Когда ты учишься! 🌾',
            'Тук-тук! Кто там? Это я, твой помощник 🚪'],
    giggle: ['Хи-хи-хи! Щекотно! 🤭', 'Ой-ой, перестань! 😂', 'Ха-ха, ну хватит! 😆'],
    puffing: ['Эй, я что-то… надуваюсь? 😮', 'Ой, мне как-то тесно в перьях… 😳', 'Стой-стой, я раздуваюсь!'],
    dizzy: ['Голова кружится… 😵‍💫', 'Звёздочки перед глазами ✨', 'Ай-яй-яй, ну всё, достаточно!'],
    nearBoom: ['Я СЕЙЧАС ЛОПНУ!!! 😱', 'Не-не-не! Пожалуйста, не надо больше! 🙈', 'Предупреждаю: я могу взорваться!!!'],
    relief: ['Фух… Чуть не лопнул! 😮‍💨', 'Ох, отпустило… Больше так не делай, ладно? 😅', 'Уф! Перья на месте? Проверю… Да 🐥'],
    afterBoom: ['Ух ты, я вернулся! Перья на месте? Все до одного? 🪶', 'Бабах! Это было громко 💥 Давай больше не будем, ладно?',
                'Я где? Я что? Ага, я снова здесь 🐣', 'Фууух… Вот это приключение! Перья собрал, всё в порядке 😅'],
    afterBoom2: ['Опять?! Ну ты даёшь! 😂', 'Третий раз за день… у меня скоро перья закончатся 🪶', 'Ты — настоящий мастер взрывов 🧨'],
    afterBoomMany: ['Ладно, мы теперь профессионалы по взрыванию 😎', 'Я начинаю привыкать. Бабах — и готово 🥱'],

    wake: ['Ой! Я не спал, я думал 🤔', 'А? Что? Я здесь! 🐥', 'Чирик! Я проснулся 😄', '*потягивается* Давай учиться! 🌞'],
    sleepLine: 'Zzz… 💤',

    /* --- болталка, когда ничего не происходит --- */
    tips: ['Повторяй слова вслух — так они запоминаются быстрее 🗣️',
           'Лучше заниматься по чуть-чуть каждый день, чем раз в неделю 📅',
           'Нажми 🔊 и повторяй за диктором — копируй произношение!',
           'Ошибаться — нормально. Мозг запоминает лучше, когда исправляет ошибки 🧠',
           'Перед сном повтори пять новых слов — утром они «приживутся» 🌙',
           'Придумай картинку к слову — так его проще запомнить 🎨',
           'Если не вспомнила слово — не подглядывай сразу. Подумай 10 секунд 🕙'],
    facts: ['В английском алфавите 26 букв, а звуков — около 44 🔤',
            'Самая частая буква в английских словах — E 📊',
            'Слово I («я») всегда пишется с большой буквы — оно такое важное! 👑',
            'В слове queue («очередь») читается только первая буква — Q, остальные четыре молчат 🤫',
            'Mom, dad, wow, noon — слова-перевёртыши: читаются одинаково в обе стороны ↔️',
            'Во фразе «The quick brown fox jumps over the lazy dog» есть все буквы английского алфавита 🦊',
            'На английском говорят больше чем в 60 странах мира 🌍',
            'Слово «hello» стало популярным лишь около 150 лет назад — раньше говорили «hail»… 📞'],
    jokes: ['— Как по-английски «кот»? — Cat. — А «коты»? — Cats! Просто добавь s 😺',
            'Знаешь, почему курица выучила английский? Чтобы сказать «egg» правильно! 🥚',
            'Что сказал цыплёнок, выучив слово «egg»? «Это же моя мама!» 🐣',
            'Я учил английский так усердно, что теперь даже чирикаю с акцентом 🐥',
            'Почему буква «Т» всегда в чае? Потому что tea — это T 🍵'],
    praise: ['Ты сегодня в ударе! 🔥', 'Я очень рад, что мы учимся вместе 💛', 'Ты стала лучше, чем вчера, — это главное 🌱',
             'Горжусь тобой! 🏅']
  };

  function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
  function rnd(a, b) { return a + Math.random() * (b - a); }
  function fmt(tpl, vars) {
    vars = vars || {};
    vars.who = WHO; vars.name = NAME;
    return noEmoji(String(tpl).replace(/\{(\w+)\}/g, function (_, k) { return vars[k] == null ? '' : vars[k]; }));
  }
  /* дизайн 3.0: в репликах нет цветных значков — только слова */
  var EMOJI = /[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{2300}-\u{23FF}\u{FE0F}\u{200D}\u{20E3}]/gu;
  function noEmoji(t) { return t.replace(EMOJI, '').replace(/\s+([!?.,:;)])/g, '$1').replace(/\s{2,}/g, ' ').trim(); }
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; });
  }
  function truthy(v) { return Array.isArray(v) ? v.length > 0 : !!v; }
  function hello() {
    var h = new Date().getHours();
    var set = h >= 5 && h < 11 ? T.helloMorning : h >= 11 && h < 17 ? T.helloDay : h >= 17 && h < 22 ? T.helloEvening : T.helloNight;
    return fmt(pick(set));
  }

  /* ---------- SVG-персонаж (цвета иконки приложения) ---------- */
  function chickSVG() { return window.Chick.svg(S.outfit || {}); }

  /* ---------- DOM ---------- */
  var root = document.createElement('div');
  root.className = 'mascot';
  root.innerHTML =
    '<div class="mascot-balloon" role="status" aria-live="polite">' +
      '<span class="mb-name">' + esc(NAME) + '</span>' +
      '<div class="mb-text"></div>' +
      '<button type="button" class="mb-close" title="Скрыть до конца страницы" aria-label="Скрыть помощника">✕</button>' +
    '</div>' +
    '<button type="button" class="mascot-body" aria-label="Помощник ' + esc(NAME) + '"><div class="m-puff">' + chickSVG() + '</div></button>';
  document.body.appendChild(root);

  var bodyEl = root.querySelector('.mascot-body');
  var balloon = root.querySelector('.mascot-balloon');
  var textEl = root.querySelector('.mb-text');
  var closeBtn = root.querySelector('.mb-close');
  var svg = root.querySelector('svg.chick');
  var lookEl = svg.querySelector('.c-look');

  var busy = false, sleeping = false;
  var hideTimer = null, typeTimer = null, faceTimer = null, fxTimer = null, wingTimer = null, lookTimer = null;

  /* ---------- мимика, позы, эффекты ---------- */
  var FACES = ['happy', 'wide', 'dizzy', 'sad', 'wink'];
  function setFace(name, ms) {
    FACES.forEach(function (f) { svg.classList.remove('s-' + f); });
    clearTimeout(faceTimer);
    if (!name) return;
    svg.classList.add('s-' + name);
    if (ms) faceTimer = setTimeout(function () { svg.classList.remove('s-' + name); }, ms);
  }
  var FX = ['love', 'stars', 'sleep', 'sweat', 'spark'];
  function setFx(name, ms) {
    FX.forEach(function (f) { svg.classList.remove('fx-' + f); });
    clearTimeout(fxTimer);
    if (!name) return;
    svg.classList.add('fx-' + name);
    if (ms) fxTimer = setTimeout(function () { svg.classList.remove('fx-' + name); }, ms);
  }
  function wings(name, ms) {
    ['w-flap', 'w-wave', 'w-up', 'w-out', 'w-stretch'].forEach(function (c) { svg.classList.remove(c); });
    clearTimeout(wingTimer);
    if (!name) return;
    void svg.getBoundingClientRect();
    svg.classList.add('w-' + name);
    wingTimer = setTimeout(function () { svg.classList.remove('w-' + name); }, ms || 1500);
  }
  function look(dx, dy, ms) {
    lookEl.style.transform = 'translate(' + dx + 'px,' + dy + 'px)';
    clearTimeout(lookTimer);
    lookTimer = setTimeout(function () { lookEl.style.transform = ''; }, ms || 1100);
  }
  var POSES = ['hop', 'jump', 'spin', 'dance', 'shake', 'wobble', 'peck', 'giggle', 'startle', 'popin', 'drop', 'tremble', 'sleepy'];
  function clearPose() { POSES.forEach(function (p) { bodyEl.classList.remove('a-' + p); }); }
  function pose(name) {
    clearPose();
    if (!name) return;
    void bodyEl.offsetWidth;                            // перезапуск анимации
    bodyEl.classList.add('a-' + name);
    if (name === 'tremble' || name === 'sleepy') return; // «зацикленные»
    var done = function (e) {
      if (e && e.target !== bodyEl) return;
      bodyEl.removeEventListener('animationend', done);
      bodyEl.classList.remove('a-' + name);
    };
    bodyEl.addEventListener('animationend', done);
    setTimeout(done, 2200);
  }

  /* настроение → набор движений */
  function react(mood) {
    if (sleeping || busy) return;
    switch (mood) {
      case 'cheer': setFace('happy', 2000); pose('jump'); setFx('spark', 1800); wings('flap', 1300); break;
      case 'happy': setFace('happy', 1600); pose('hop'); break;
      case 'love':  setFace('happy', 2400); setFx('love', 2400); pose('giggle'); break;
      case 'wow':   setFace('wide', 1600); pose('startle'); setFx('stars', 1500); break;
      case 'sad':   setFace('sad', 2400); pose('wobble'); break;
      case 'think': setFace('wide', 1200); look(0, -4, 1500); break;
      case 'wave':  wings('wave', 1300); pose('hop'); setFace('happy', 1400); break;
      case 'party': setFace('happy', 2400); pose('dance'); setFx('spark', 2200); wings('up', 1400); break;
      case 'cool':  setFace('wink', 1200); pose('hop'); break;
      case 'giggle': setFace('happy', 1000); pose('giggle'); break;
      default: break;
    }
  }

  /* ---------- моргание ---------- */
  (function blinkLoop() {
    setTimeout(function () {
      if (!sleeping && !busy && !document.hidden) {
        svg.classList.add('s-blink');
        setTimeout(function () { svg.classList.remove('s-blink'); }, 140);
        if (Math.random() < 0.2) {                     // иногда моргает дважды
          setTimeout(function () {
            svg.classList.add('s-blink');
            setTimeout(function () { svg.classList.remove('s-blink'); }, 120);
          }, 260);
        }
      }
      blinkLoop();
    }, rnd(2400, 6000));
  })();

  /* ---------- реплики ---------- */
  function say(text, o) {
    o = o || {};
    if (!text || busy) return;
    if (sleeping) wake(true);
    text = fmt(text);
    clearTimeout(hideTimer); clearInterval(typeTimer);
    balloon.classList.remove('collapsed');
    balloon.classList.add('visible');
    textEl.dataset.full = text;
    svg.classList.add('is-talking');
    var finish = function () {
      clearInterval(typeTimer);
      textEl.textContent = text;
      svg.classList.remove('is-talking');
      if (!o.persist) hideTimer = setTimeout(collapse, HIDE_AFTER);
    };
    if (o.instant || RM) {
      finish();
    } else {
      var i = 0, step = Math.max(1, Math.ceil(text.length / 48));
      textEl.textContent = '';
      var node = document.createTextNode(''), caret = document.createElement('span');
      caret.className = 'caret';
      textEl.appendChild(node); textEl.appendChild(caret);
      typeTimer = setInterval(function () {
        i += step;
        if (i >= text.length) { finish(); return; }
        node.nodeValue = text.slice(0, i);
      }, 26);
    }
    react(o.mood === undefined ? 'happy' : o.mood);
  }
  function collapse() {
    balloon.classList.add('collapsed');
    balloon.classList.remove('visible');
    svg.classList.remove('is-talking');
  }
  var chatTimes = [];
  function say2(list, ms, o) {                           // вторая реплика с задержкой
    setTimeout(function () { say(Array.isArray(list) ? pick(list) : list, o); }, ms);
  }

  /* ---------- сон и пробуждение ---------- */
  var lastActive = Date.now();
  function sleep() {
    if (sleeping || busy) return;
    sleeping = true;
    collapse();
    setFace(null); setFx('sleep'); svg.classList.add('s-sleep');
    pose('sleepy');
  }
  function wake(quiet) {
    if (!sleeping) return;
    sleeping = false;
    svg.classList.remove('s-sleep');
    setFx(null); clearPose();
    setFace('wide', 900); pose('startle');
    if (!quiet) setTimeout(function () { say(pick(T.wake), { mood: 'happy' }); }, 600);
  }
  function touchActive() {
    lastActive = Date.now();
    if (sleeping) wake();
  }
  ['pointerdown', 'keydown', 'touchstart', 'wheel'].forEach(function (ev) {
    document.addEventListener(ev, touchActive, { passive: true, capture: true });
  });

  /* ---------- «жизнь» в простое ---------- */
  var nextTrick = Date.now() + rnd(6000, 11000);
  var nextChat = Date.now() + rnd(45000, 80000);
  var TRICKS = [
    function () { look(-5, 1, 1300); setTimeout(function () { look(5, 1, 1300); }, 1400); },
    function () { look(5, -2, 1200); },
    function () { pose('hop'); },
    function () { wings('flap', 1400); },
    function () { wings('stretch', 1000); pose('hop'); },
    function () { pose('peck'); },
    function () { wings('wave', 1300); setFace('happy', 1300); },
    function () { pose('wobble'); setFace('wide', 900); },
    function () { pose('dance'); setFace('happy', 1500); },
    function () { pose('spin'); setFace('happy', 1100); setFx('spark', 1200); },
    function () { setFace('wink', 900); look(4, -1, 900); }
  ];
  function inTest() {
    var t = document.getElementById('step-test');
    return t && !t.classList.contains('hidden');
  }
  setInterval(function () {
    if (document.hidden || busy || root.classList.contains('mascot-off')) return;
    var now = Date.now();
    if (!sleeping && now - lastActive > SLEEP_AFTER) { sleep(); return; }
    if (sleeping) return;
    if (now >= nextTrick) {
      pick(TRICKS)();
      nextTrick = now + rnd(7000, 15000);
    }
    if (now >= nextChat && now - lastActive > 15000 && !balloon.classList.contains('visible') && !inTest()) {
      var pool = [T.tips, T.facts, T.jokes, T.praise];
      say(pick(pick(pool)), { mood: Math.random() < 0.5 ? 'happy' : 'cool' });
      nextChat = now + rnd(55000, 95000);
    }
  }, 1000);

  /* ---------- тыки по Чик-чику: щекотка → надувание → ВЗРЫВ ---------- */
  var chain = 0, lastTap = 0, deflateTimer = null, pokeTotal = 0, explosions = 0, lastVariant = -1;
  function setPuff(n) {
    var p = n >= 3 ? 1 + Math.min(n - 2, 6) * 0.1 : 1;
    bodyEl.style.setProperty('--puff', p.toFixed(2));
  }
  function deflate() {
    var was = chain;
    chain = 0;
    setPuff(0);
    if (bodyEl.classList.contains('a-tremble')) pose(null);
    setFx(null); setFace(null);
    if (was >= 5 && !busy) say(pick(T.relief), { mood: 'sad' });
  }
  bodyEl.addEventListener('click', function () {
    if (busy) return;
    touchActive();
    var now = Date.now();
    chain = (now - lastTap < CHAIN_GAP) ? chain + 1 : 1;
    lastTap = now;
    pokeTotal++;
    clearTimeout(deflateTimer);
    deflateTimer = setTimeout(deflate, 1100);
    setPuff(chain);

    if (chain >= EXPLODE_AT) { clearTimeout(deflateTimer); explode(); return; }
    if (chain === 1) {
      var line = pokeTotal % 7 === 0 ? pick(T.facts) : pokeTotal % 5 === 0 ? pick(T.jokes) : pick(T.pokes);
      say(line, { mood: pokeTotal % 3 === 0 ? 'love' : 'happy' });
    } else if (chain === 2) {
      say(pick(T.giggle), { instant: true, mood: 'giggle' });
    } else if (chain === 3) {
      say(pick(T.puffing), { instant: true, mood: null });
      setFace('wide'); pose('startle');
    } else if (chain === 4) {
      say(pick(T.puffing), { instant: true, mood: null });
      setFace('wide'); pose('shake');
    } else if (chain === 5) {
      say(pick(T.dizzy), { instant: true, mood: null });
      setFace('dizzy'); setFx('stars'); pose('tremble');
    } else {
      say(pick(T.nearBoom), { instant: true, mood: null });
      setFace('wide'); setFx('sweat'); pose('tremble');
    }
  });

  /* ---------- 💥 взрыв перьями ---------- */
  var FEATHER_COLORS = ['#FFD54F', '#FFE082', '#FFC947', '#FFF3C4', '#FFFFFF', '#FFB74D', '#FFECB3'];
  function featherEl(w, h, color) {
    var el = document.createElement('div');
    el.className = 'feather';
    el.style.width = w + 'px'; el.style.height = h + 'px';
    el.innerHTML = '<svg viewBox="0 0 20 60" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">' +
      '<path d="M10 1 C19 14 19 40 10 58 C1 40 1 14 10 1 Z" fill="' + color + '" stroke="#E8A317" stroke-width="1.4"/>' +
      '<path d="M10 6 L10 59" stroke="#E8A317" stroke-width="1.6" stroke-linecap="round"/>' +
      '<path d="M10 20 L5 14 M10 28 L4 21 M10 36 L5 30 M10 20 L15 14 M10 28 L16 21 M10 36 L15 30" stroke="#E8A317" stroke-width=".9" opacity=".6"/>' +
      '</svg>';
    return el;
  }
  function T3(x, y, r, s) { return 'translate(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px) rotate(' + r.toFixed(0) + 'deg) scale(' + s + ')'; }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

  function explode() {
    if (busy) return;
    busy = true;
    explosions++;
    var k = RM ? 0.45 : 1;
    var r = bodyEl.getBoundingClientRect();
    var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    var vw = window.innerWidth, vh = window.innerHeight;
    collapse();
    clearPose(); setFx(null); setFace(null);
    bodyEl.style.setProperty('--puff', '1');
    bodyEl.classList.add('is-gone');

    var layer = document.createElement('div');
    layer.className = 'feather-layer';
    document.body.appendChild(layer);

    var N = RM ? 12 : 38, feathers = [];
    for (var i = 0; i < N; i++) {
      var w = rnd(9, 17), h = w * rnd(2.6, 3.4);
      var f = featherEl(w, h, FEATHER_COLORS[i % FEATHER_COLORS.length]);
      f.style.transform = T3(cx - w / 2, cy - h / 2, 0, 0.3);
      layer.appendChild(f);
      var ang = (i / N) * Math.PI * 2 + rnd(-0.25, 0.25);
      var dist = rnd(110, 330) * (RM ? 0.6 : 1);
      var ex = clamp(cx + Math.cos(ang) * dist, 4, vw - w - 4) - w / 2;
      var ey = clamp(cy + Math.sin(ang) * dist + rnd(30, 90), 4, vh - h - 4) - h / 2;
      var mx = cx + (ex - cx) * 0.7, my = cy + (ey - cy) * 0.7 - rnd(30, 80);
      var rot = rnd(-420, 420);
      var anim = f.animate([
        { transform: T3(cx - w / 2, cy - h / 2, 0, 0.3), opacity: 1 },
        { transform: T3(mx - w / 2, my - h / 2, rot * 0.7, 1.15), opacity: 1, offset: 0.55 },
        { transform: T3(ex, ey, rot, 1), opacity: 1 }
      ], { duration: rnd(900, 1500) * k, easing: 'cubic-bezier(.12,.75,.3,1)', fill: 'forwards' });
      feathers.push({ el: f, w: w, h: h, ex: ex, ey: ey, rot: rot, anim: anim });
    }

    var variant;
    do { variant = Math.floor(Math.random() * 3); } while (variant === lastVariant);
    lastVariant = variant;
    setTimeout(function () {
      if (variant === 0) returnSwirl(feathers, layer, cx, cy, k);
      else if (variant === 1) returnDrop(feathers, layer, k);
      else returnEgg(feathers, layer, r, cx, k);
    }, 2300 * k);
  }

  function fadeFeathers(feathers, ms, done) {
    var last = 0;
    feathers.forEach(function (f) {
      var d = ms + rnd(0, 250);
      last = Math.max(last, d);
      f.el.animate([{ opacity: 1, transform: T3(f.ex, f.ey, f.rot, 1) },
                    { opacity: 0, transform: T3(f.ex + rnd(-20, 20), f.ey - rnd(20, 50), f.rot + rnd(-90, 90), .8) }],
                   { duration: d, easing: 'ease-out', fill: 'forwards' });
    });
    setTimeout(done, last + 60);
  }

  function comeBack(layer, how) {
    layer.remove();
    bodyEl.classList.remove('is-gone');
    setFace('wide', 900);
    pose(how === 'drop' ? 'drop' : 'popin');
    setTimeout(function () { setFx('spark', 1500); setFace('happy', 1800); }, how === 'drop' ? 1300 : 700);
    var wait = how === 'drop' ? 1900 : 1000;
    setTimeout(function () {
      busy = false;
      lastActive = Date.now();
      var line = explosions >= 4 ? pick(T.afterBoomMany) : explosions >= 2 ? pick(T.afterBoom2) : pick(T.afterBoom);
      say(line, { mood: 'cheer' });
    }, wait);
  }

  /* вариант 1: перья закручиваются обратно в вихре — и Чик-чик «выскакивает» */
  function returnSwirl(feathers, layer, cx, cy, k) {
    var longest = 0;
    feathers.forEach(function (f) {
      var dx = (f.ex + f.w / 2) - cx, dy = (f.ey + f.h / 2) - cy;
      var a = Math.atan2(dy, dx) + 1.1, d = Math.sqrt(dx * dx + dy * dy) * 0.55;
      var mx = cx + Math.cos(a) * d, my = cy + Math.sin(a) * d;
      var dur = rnd(850, 1250) * k, delay = rnd(0, 300) * k;
      longest = Math.max(longest, dur + delay);
      f.el.animate([
        { transform: T3(f.ex, f.ey, f.rot, 1), opacity: 1 },
        { transform: T3(mx - f.w / 2, my - f.h / 2, f.rot + 360, .9), opacity: 1, offset: 0.55 },
        { transform: T3(cx - f.w / 2, cy - f.h / 2, f.rot + 720, .2), opacity: 1 }
      ], { duration: dur, delay: delay, easing: 'cubic-bezier(.55,.05,.7,.6)', fill: 'forwards' });
    });
    setTimeout(function () { comeBack(layer, 'popin'); }, longest + 40);
  }

  /* вариант 2: перья тают, а Чик-чик падает с неба и приземляется «лепёшкой» */
  function returnDrop(feathers, layer, k) {
    fadeFeathers(feathers, 600 * k, function () {
      comeBack(layer, 'drop');
    });
  }

  /* вариант 3: на месте взрыва — яйцо; оно трясётся, трескается, и из него вылупляется Чик-чик */
  function returnEgg(feathers, layer, r, cx, k) {
    fadeFeathers(feathers, 500 * k, function () {
      var W = 72, H = 88;
      var egg = document.createElement('div');
      egg.className = 'egg';
      egg.style.width = W + 'px'; egg.style.height = H + 'px';
      egg.style.left = (cx - W / 2) + 'px';
      egg.style.top = (r.bottom - H - 4) + 'px';
      egg.innerHTML =
        '<svg viewBox="0 0 70 88" xmlns="http://www.w3.org/2000/svg">' +
          '<g class="shell-bot"><path d="M5 54 L16 48 L26 56 L36 46 L46 56 L56 48 L65 54 C66 74 52 86 35 86 C18 86 4 74 5 54Z" fill="#FFF8E1" stroke="#E0C58F" stroke-width="2.4" stroke-linejoin="round"/>' +
            '<circle cx="24" cy="72" r="3.2" fill="#B39DFF" opacity=".7"/><circle cx="47" cy="68" r="2.6" fill="#FF8FB8" opacity=".7"/></g>' +
          '<g class="shell-top"><path d="M5 54 L16 48 L26 56 L36 46 L46 56 L56 48 L65 54 C65 24 50 3 35 3 C20 3 5 24 5 54Z" fill="#FFF8E1" stroke="#E0C58F" stroke-width="2.4" stroke-linejoin="round"/>' +
            '<circle cx="28" cy="22" r="3.4" fill="#7C5CFF" opacity=".55"/><circle cx="44" cy="34" r="2.8" fill="#FFD54F"/>' +
            '<path class="crack" d="M35 5 L31 16 L38 24 L32 34" stroke="#b88a3a" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>' +
        '</svg>';
      document.body.appendChild(egg);
      var top = egg.querySelector('.shell-top'), bot = egg.querySelector('.shell-bot');
      top.style.transformOrigin = '0% 100%';
      egg.animate([{ transform: 'translateY(-90vh) scale(.8)', opacity: 0 }, { transform: 'translateY(0) scale(1.1,.9)', opacity: 1, offset: .6 },
                   { transform: 'translateY(-14px)', offset: .8 }, { transform: 'none' }],
                  { duration: 650 * k, easing: 'ease-in', fill: 'forwards' }).onfinish = function () {
        egg.animate([{ transform: 'rotate(0)' }, { transform: 'rotate(-14deg)' }, { transform: 'rotate(12deg)' }, { transform: 'rotate(-10deg)' },
                     { transform: 'rotate(8deg)' }, { transform: 'rotate(-4deg)' }, { transform: 'rotate(0)' }],
                    { duration: 1100 * k, easing: 'ease-in-out' }).onfinish = function () {
          egg.classList.add('cracked');
          egg.animate([{ transform: 'translateX(0)' }, { transform: 'translateX(-4px) rotate(-3deg)' }, { transform: 'translateX(4px) rotate(3deg)' }, { transform: 'translateX(0)' }],
                      { duration: 380 * k, iterations: 2 }).onfinish = function () {
            top.animate([{ transform: 'translate(0,0) rotate(0)', opacity: 1 }, { transform: 'translate(-30px,-60px) rotate(-55deg)', opacity: 0 }],
                        { duration: 650 * k, easing: 'ease-out', fill: 'forwards' });
            bot.animate([{ opacity: 1 }, { opacity: 1, offset: .6 }, { opacity: 0 }], { duration: 900 * k, fill: 'forwards' });
            bodyEl.classList.remove('is-gone');
            setFace('wide', 900); pose('popin');
            setTimeout(function () { setFx('love', 1800); setFace('happy', 2000); }, 700);
            setTimeout(function () {
              egg.remove(); layer.remove();
              busy = false; lastActive = Date.now();
              var line = explosions >= 4 ? pick(T.afterBoomMany) : explosions >= 2 ? pick(T.afterBoom2) : pick(T.afterBoom);
              say('Вылупился! 🐣 ' + line, { mood: 'cheer' });
            }, 1050 * k);
          };
        };
      };
    });
  }

  /* ---------- скрытие / возврат ---------- */
  var reopenBtn = null;
  function showReopen() {
    if (reopenBtn) return;
    reopenBtn = document.createElement('button');
    reopenBtn.type = 'button';
    reopenBtn.className = 'mascot-reopen';
    reopenBtn.title = 'Вернуть помощника';
    reopenBtn.setAttribute('aria-label', 'Вернуть помощника');
    reopenBtn.innerHTML = chickSVG();
    reopenBtn.addEventListener('click', function () {
      try { sessionStorage.removeItem('mascot_hidden_' + location.pathname); } catch (e) {}
      root.classList.remove('mascot-off');
      reopenBtn.remove(); reopenBtn = null;
      pose('popin');
      setTimeout(function () { say(pick(T.hiAgain), { mood: 'wave' }); }, 500);
    });
    document.body.appendChild(reopenBtn);
  }
  closeBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    try { sessionStorage.setItem('mascot_hidden_' + location.pathname, '1'); } catch (err) {}
    root.classList.add('mascot-off');
    showReopen();
  });
  var hiddenHere = false;
  try { hiddenHere = !!sessionStorage.getItem('mascot_hidden_' + location.pathname); } catch (e) {}
  if (hiddenHere) { root.classList.add('mascot-off'); showReopen(); }

  /* ---------- 🎁 вручение наград: подарок → медали по одной ---------- */
  var TIER_FX = { bronze: ['#FFE9D6', '#9A3B00', '#FFFFFF'], silver: ['#E3EDFC', '#5E6478', '#FFFFFF'],      // цвета палитры макета
                  gold: ['#FFC83D', '#FFEFC2', '#D99A00', '#FFFFFF'], legend: ['#FFC83D', '#2563C9', '#E3EDFC', '#DDF5E7', '#FFFFFF'] };
  var STAR = '<svg width="100%" height="100%" viewBox="-10 -10 20 20"><path d="M0 -9 L2.4 -2.4 L9 0 L2.4 2.4 L0 9 L-2.4 2.4 L-9 0 L-2.4 -2.4Z" fill="{c}"/></svg>';

  function burstAt(x, y, colors, n, dist) {           // «салют»: разлетающиеся точки и звёздочки
    if (RM) return;
    for (var i = 0; i < n; i++) {
      var el = document.createElement('div');
      el.className = 'fx-dot';
      var size = rnd(6, 13), c = colors[i % colors.length], star = i % 3 === 0;
      el.style.width = el.style.height = size * (star ? 1.8 : 1) + 'px';
      if (star) el.innerHTML = STAR.replace('{c}', c); else { el.style.background = c; el.style.borderRadius = '50%'; }
      (giftEl || document.body).appendChild(el);
      var ang = (i / n) * Math.PI * 2 + rnd(-.2, .2), d = rnd(.55, 1) * dist;
      var dx = Math.cos(ang) * d, dy = Math.sin(ang) * d;
      var anim = el.animate([
        { transform: 'translate(' + x + 'px,' + y + 'px) scale(.2)', opacity: 1 },
        { transform: 'translate(' + (x + dx) + 'px,' + (y + dy) + 'px) scale(1.1)', opacity: 1, offset: .55 },
        { transform: 'translate(' + (x + dx * 1.05) + 'px,' + (y + dy * 1.05 + 70) + 'px) scale(.3)', opacity: 0 }
      ], { duration: rnd(900, 1500), easing: 'cubic-bezier(.15,.7,.3,1)' });
      anim.onfinish = (function (e) { return function () { e.remove(); }; })(el);
    }
  }
  function fireworks(n, colors) {
    for (var i = 0; i < n; i++) {
      setTimeout(function () {
        burstAt(rnd(.12, .88) * window.innerWidth, rnd(.12, .5) * window.innerHeight, colors, 26, rnd(110, 190));
      }, i * 280);
    }
  }
  function flashScreen() {
    if (RM) return;
    var f = document.createElement('div'); f.className = 'fx-flash';
    document.body.appendChild(f); setTimeout(function () { f.remove(); }, 1000);
  }
  function tierEffects(tier) {
    var cx = window.innerWidth / 2, cy = window.innerHeight * 0.36, cols = TIER_FX[tier] || TIER_FX.bronze;
    if (tier === 'legend') { flashScreen(); confettiBurst(80); fireworks(6, cols); burstAt(cx, cy, cols, 40, 240); }
    else if (tier === 'gold') { confettiBurst(54); fireworks(3, cols); burstAt(cx, cy, cols, 30, 200); }
    else if (tier === 'silver') { confettiBurst(34); burstAt(cx, cy, cols, 24, 170); }
    else { confettiBurst(20); burstAt(cx, cy, cols, 16, 140); }
  }

  var giftEl = null, giftIdx = 0, giftList = [];
  function celebrateAchievements(list) {
    if (giftEl || !list || !list.length) return;
    giftList = list; giftIdx = 0;
    document.body.classList.add('ceremony');
    say(pick(T.achIntro), { persist: true, mood: 'wow' });

    giftEl = document.createElement('div');
    giftEl.className = 'gift-stage';
    giftEl.setAttribute('role', 'dialog');
    giftEl.setAttribute('aria-label', 'Награда');
    giftEl.innerHTML =
      '<div class="gift-hint">Нажми на коробку! Чик-чик принёс тебе ' + (list.length > 1 ? list.length + ' награды' : 'награду') + '</div>' +
      '<button type="button" class="gift-box" aria-label="Открыть подарок">' +
      '  <svg viewBox="0 0 140 130" xmlns="http://www.w3.org/2000/svg">' +
      '    <g class="gb-lid"><rect x="8" y="26" width="124" height="26" rx="7" fill="#1E4FA8"/>' +
      '      <rect x="60" y="26" width="20" height="26" fill="#FFC83D"/>' +
      '      <path d="M70 30 Q52 6 42 16 Q38 26 70 30 Z" fill="#FFC83D" stroke="#D99A00" stroke-width="2"/>' +
      '      <path d="M70 30 Q88 6 98 16 Q102 26 70 30 Z" fill="#FFC83D" stroke="#D99A00" stroke-width="2"/></g>' +
      '    <rect x="16" y="52" width="108" height="70" rx="8" fill="#2563C9"/>' +
      '    <rect x="60" y="52" width="20" height="70" fill="#FFC83D"/>' +
      '    <rect x="16" y="52" width="108" height="10" fill="rgba(0,0,0,.12)"/>' +
      '  </svg></button>';
    document.body.appendChild(giftEl);
    var box = giftEl.querySelector('.gift-box');
    box.addEventListener('click', function () {
      if (giftEl.classList.contains('gift-open') || box.classList.contains('gift-shake')) return;
      giftEl.querySelector('.gift-hint').textContent = 'Ого, что же там…?';
      box.classList.add('gift-shake');                // коробка трясётся от нетерпения
      react('wow');
      setTimeout(function () {
        box.classList.remove('gift-shake');
        giftEl.classList.add('gift-open');
        var r = box.getBoundingClientRect();
        burstAt(r.left + r.width / 2, r.top + r.height * 0.3, TIER_FX.gold, 26, 170);
        setTimeout(function () { showAch(0); }, RM ? 100 : 850);
      }, RM ? 100 : 850);
    });
  }

  function showAch(i) {
    if (!giftEl) return;
    giftIdx = i;
    var a = giftList[i], last = i === giftList.length - 1;
    var dots = giftList.map(function (_, k) { return '<i class="' + (k < i ? 'done' : k === i ? 'on' : '') + '"></i>'; }).join('');
    giftEl.innerHTML =
      '<div class="ach-show tier-' + esc(a.tier) + '">' +
        '<div class="ach-rays"></div>' +
        '<div class="ach-tierlabel">' + esc(a.tierName) + ' награда</div>' +
        '<button type="button" class="ach-medal-big" aria-label="Медаль: ' + esc(a.title) + '">' +
          '<span class="medal tier-' + esc(a.tier) + '">' + a.svg + '</span></button>' +
        '<div class="ach-title-big">' + esc(a.title) + '</div>' +
        '<div class="ach-desc-big">' + esc(a.desc || '') + '</div>' +
        (giftList.length > 1 ? '<div class="ach-dots">' + dots + '</div>' : '') +
        '<div class="ach-actions"><button type="button" class="btn btn-secondary ach-next">' +
          (last ? 'Забрать в коллекцию!' : 'Дальше →') + '</button>' +
          (giftList.length > 1 && !last ? '<button type="button" class="ach-skip">Забрать все сразу</button>' : '') + '</div>' +
      '</div>';
    giftEl.classList.add('gift-reveal');
    setTimeout(function () { tierEffects(a.tier); }, RM ? 0 : 450);
    say(fmt(pick(T.achTier[a.tier] || T.achOpen), { title: a.title, emoji: a.emoji }),
        { persist: true, mood: a.tier === 'legend' || a.tier === 'gold' ? 'party' : 'cheer' });

    var medalBtn = giftEl.querySelector('.ach-medal-big');
    medalBtn.addEventListener('click', function () {   // можно покрутить медаль
      medalBtn.classList.remove('is-spin'); void medalBtn.offsetWidth; medalBtn.classList.add('is-spin');
      var r = medalBtn.getBoundingClientRect();
      burstAt(r.left + r.width / 2, r.top + r.height / 2, TIER_FX[a.tier] || TIER_FX.bronze, 14, 120);
    });
    giftEl.querySelector('.ach-next').addEventListener('click', function () { last ? finishGift() : nextAch(); });
    var skip = giftEl.querySelector('.ach-skip');
    if (skip) skip.addEventListener('click', finishGift);
  }
  function nextAch() {
    var show = giftEl && giftEl.querySelector('.ach-show');
    if (show && !RM) { show.classList.add('leaving'); setTimeout(function () { showAch(giftIdx + 1); }, 300); }
    else showAch(giftIdx + 1);
  }
  function finishGift() {                              // медаль «улетает» к Чик-чику
    if (!giftEl) return;
    var medal = giftEl.querySelector('.ach-medal-big'), target = bodyEl.getBoundingClientRect();
    var done = function () { closeGift(); };
    if (medal && !RM) {
      var r = medal.getBoundingClientRect();
      var dx = target.left + target.width / 2 - (r.left + r.width / 2), dy = target.top + target.height / 2 - (r.top + r.height / 2);
      giftEl.querySelector('.ach-show').classList.add('leaving');
      medal.animate([{ transform: 'none', opacity: 1 }, { transform: 'translate(' + dx * 0.5 + 'px,' + (dy * 0.5 - 60) + 'px) scale(.6) rotate(200deg)', opacity: 1, offset: .55 },
                     { transform: 'translate(' + dx + 'px,' + dy + 'px) scale(.12) rotate(420deg)', opacity: 0 }],
                    { duration: 650, easing: 'cubic-bezier(.5,0,.7,.5)', fill: 'forwards' });
      setTimeout(done, 620);
    } else done();
  }
  function closeGift() {
    if (!giftEl) return;
    giftEl.remove(); giftEl = null;
    document.body.classList.remove('ceremony');
    pose('popin'); setFx('love', 2200); setFace('happy', 2400);
    var n = giftList.length;
    setTimeout(function () {
      say(n > 1 ? 'Все ' + n + ' награды теперь в твоей коллекции! ' + pick(T.achAfter) : pick(T.achAfter), { mood: 'love' });
    }, 500);
  }
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && giftEl) finishGift(); });

  function confettiBurst(n) {
    if (RM) return;
    var colors = ['#2563C9', '#FFC83D', '#E3EDFC', '#1E9E5A', '#FFE9D6', '#FFFFFF'];
    n = n || 34;
    for (var i = 0; i < n; i++) {
      var c = document.createElement('i');
      c.className = 'confetti';
      c.style.left = (4 + Math.random() * 92) + 'vw';
      c.style.background = colors[i % colors.length];
      c.style.animationDuration = (1.4 + Math.random() * 1.8) + 's';
      c.style.animationDelay = (Math.random() * 0.5) + 's';
      c.style.transform = 'rotate(' + (Math.random() * 360) + 'deg)';
      (giftEl || document.body).appendChild(c);
      (function (el) { setTimeout(function () { el.remove(); }, 4200); })(c);
    }
  }

  /* ---------- приветствия по страницам ---------- */
  var seen = {};
  try { seen = JSON.parse(sessionStorage.getItem('mascot_seen') || '{}'); } catch (e) {}
  function markSeen(key) {
    seen[key] = 1;
    try { sessionStorage.setItem('mascot_seen', JSON.stringify(seen)); } catch (e) {}
  }
  function later(ms, fn) { setTimeout(function () { if (!root.classList.contains('mascot-off')) fn(); }, ms); }

  later(0, function () { pose('popin'); });
  if (S.page === 'index') {
    later(900, function () { say(fmt(pick(T.helloAnon)), { mood: 'wave' }); });
  } else if (S.page === 'home') {
    later(800, function () {
      if (S.allDone) say(T.doneAll, { mood: 'party' });
      else if (S.alreadyStarted && !seen.homeHi) { say(fmt(pick(T.welcomeBack)), { mood: 'wave' }); markSeen('homeHi'); }
      else if (!seen.homeHi) { say(hello(), { mood: 'wave' }); markSeen('homeHi'); }
      else say(pick(T.hiAgain), { mood: 'happy' });
    });
  } else if (S.page === 'lesson') {
    var firstKey = 'ls' + (S.lessonId || '');
    later(800, function () {
      if (!seen[firstKey]) { say(fmt(pick(T.lessonStart), { title: S.lessonTitle || '' }), { mood: 'cheer' }); markSeen(firstKey); }
      else say(pick(T.hiAgain), { mood: 'happy' });
    });
  } else if (S.page === 'garden') {
    later(800, function () {
      if (S.streak <= 0) { say(T.gardenBroken, { mood: 'sad' }); return; }
      var msg = pick(T.gardenHello);
      if (S.streak >= 2) msg += ' ' + fmt(T.gardenStreak, { n: S.streak });
      say(msg, { mood: 'love' });
      say2(T.gardenShop, 6500, { mood: 'cool' });
    });
  } else if (S.page === 'words') {
    later(700, function () { say(S.empty ? T.wordsEmpty : fmt(pick(T.wordsPage)), { mood: S.empty ? 'think' : 'happy' }); });
  } else if (S.page === 'writing') {
    later(700, function () { say(S.empty ? T.wordsEmpty : pick(T.writingPage), { mood: 'happy' }); });
  } else if (S.page === 'stories') {
    later(700, function () { say(S.empty ? T.wordsEmpty : pick(T.storiesPage), { mood: 'happy' }); });
  } else if (S.page === 'wardrobe') {
    later(700, function () { say(pick(T.wardrobePage), { mood: 'happy' }); });
  } else if (S.page === 'games') {
    later(700, function () { say(S.empty ? T.wordsEmpty : pick(T.gamesPage), { mood: 'happy' }); });
  } else if (S.page === 'dialogs') {
    later(700, function () { say(S.empty ? T.wordsEmpty : pick(T.dialogsPage), { mood: 'happy' }); });
  } else if (S.page === 'review') {
    later(700, function () { say(S.empty ? T.wordsEmpty : pick(T.reviewPage), { mood: 'happy' }); });
  } else if (S.page === 'speak') {
    later(700, function () { say(pick(T.speakPage), { mood: 'happy' }); });
  } else if (S.page === 'achievements') {
    later(700, function () {
      say(S.earned ? fmt(pick(T.achPage), { n: S.earned, total: S.total }) : T.achPageEmpty, { mood: S.earned ? 'cheer' : 'think' });
    });
  } else if (S.page === 'theory') {
    later(700, function () { say(S.empty ? T.theoryEmpty : pick(T.theoryPage), { mood: S.empty ? 'think' : 'happy' }); });
  } else if (S.page === 'result') {
    later(700, function () {
      var p = S.percent || 0;
      var msg = p === 100 ? pick(T.resultPass100) : (p >= 70 || S.passed) ? pick(T.resultPass) : p >= 50 ? T.resultNear : T.resultLow;
      say(msg, { persist: true, mood: p === 100 ? 'party' : (p >= 70 || S.passed) ? 'cheer' : p >= 50 ? 'think' : 'sad' });
      if (S.coinsEarned) say2(fmt(T.coinsEarned, { n: S.coinsEarned }), 3200, { mood: 'cool' });
      if (S.goalDone) setTimeout(function () { say(pick(T.goalDone) + ' +' + S.goalCoins + ' 🪙', { persist: true, mood: 'party' }); explode && explode(); }, 6500);
      if (truthy(S.newAchievements)) {
        var list = Array.isArray(S.newAchievements) ? S.newAchievements : [];
        setTimeout(function () { if (list.length) celebrateAchievements(list); }, 2000);
      }
    });
  }

  /* ---------- слежение за уроком ---------- */
  if (S.page === 'lesson') {
    var steps = ['step-theory', 'step-material', 'step-exercises', 'step-test'];
    var stepMsgs = {
      'step-material': function () { return pick(T.theoryDone); },
      'step-exercises': function () { return pick(T.wordsDone); },
      'step-test': function () { return pick(T.testOpen); }
    };
    var currentStep = function () {
      for (var i = 0; i < steps.length; i++) {
        var el = document.getElementById(steps[i]);
        if (el && !el.classList.contains('hidden')) return steps[i];
      }
      return null;
    };
    var lastStep = currentStep();
    setInterval(function () {
      var s = currentStep();
      if (s && s !== lastStep) {
        lastStep = s;
        if (stepMsgs[s]) { react('cheer'); setTimeout(function () { say(stepMsgs[s](), { mood: 'happy' }); }, 600); }
      }
    }, 700);

    var exObserver = new MutationObserver(function (muts) {
      muts.forEach(function (m) {
        var res = m.target.nodeType === 3 ? m.target.parentElement : m.target;
        res = res && res.closest ? res.closest('.ex-result') : null;
        if (!res) return;
        var txt = res.textContent || '';
        if (txt.indexOf('✅') !== -1) say(pick(T.right), { mood: 'cheer' });
        else if (txt.indexOf('❌') !== -1) say(pick(T.wrong), { mood: 'sad' });
        else if (txt.indexOf('🧩') !== -1) say(T.allMatched, { mood: 'happy' });
        else if (txt.indexOf('🧺') !== -1) say(T.allSorted, { mood: 'happy' });
      });
    });
    document.querySelectorAll('.ex-result').forEach(function (el) {
      exObserver.observe(el, { childList: true, characterData: true, subtree: true });
    });

    /* подсказки по перетаскиванию (Pointer Events) */
    var dndHinted = false;
    document.querySelectorAll('.dnd').forEach(function (dnd) {
      dnd.addEventListener('pointerdown', function (e) {
        var t = e.target;
        if (dndHinted || !t.closest || !t.closest('.match-tile, .sort-word')) return;
        dndHinted = true;
        say(e.pointerType === 'mouse' ? T.dragHint : T.tapHint, { mood: 'think' });
      });
    });

    var cheered = false;
    setInterval(function () {
      var box = document.getElementById('step-exercises');
      if (!box || box.classList.contains('hidden') || cheered) return;
      var ok = box.querySelectorAll('.ex-result.ok'), total = box.querySelectorAll('.exercise');
      if (total.length && ok.length === total.length) { cheered = true; say(T.allExercises, { mood: 'party' }); }
    }, 1200);
  }

  document.addEventListener('speak:result', function (e) {
    var d = e.detail || {}, st = d.stars | 0;
    var list = st >= 3 ? T.speakStars3 : st === 2 ? T.speakStars2 : st === 1 ? T.speakStars1 : T.speakStars0;
    say(pick(list), { mood: st >= 3 ? 'cheer' : st === 2 ? 'happy' : 'think' });
  });
  var rvStreak = 0;
  document.addEventListener('review:answer', function (e) {
    var ok = e.detail && e.detail.ok;
    rvStreak = ok ? rvStreak + 1 : 0;
    if (ok && rvStreak % 3 !== 0) return;             // хвалим не каждый ответ, а каждый третий
    say(pick(ok ? T.reviewOk : T.reviewBad), { mood: ok ? 'cheer' : 'think' });
  });
  document.addEventListener('game:end', function (e) {
    var d = e.detail || {};
    if (d.dialog) { say(pick(T.dialogDone), { mood: 'cheer' }); return; }
    var st = d.stars | 0;
    say(pick(st >= 3 ? T.game3 : st === 2 ? T.game2 : st === 1 ? T.game1 : T.game0), { mood: st >= 3 ? 'party' : st >= 1 ? 'cheer' : 'think' });
  });
  document.addEventListener('ach:new', function (e) {
    var l = e.detail && e.detail.list;
    if (l && l.length) celebrateAchievements(l);
  });
  document.addEventListener('review:goal', function (e) {
    say(pick(T.goalDone) + ' +' + ((e.detail && e.detail.coins) || 0) + ' 🪙', { persist: true, mood: 'party' });
  });
  document.addEventListener('review:done', function () { say(pick(T.reviewDone), { mood: 'party' }); });
  document.addEventListener('review:achievements', function (e) {
    var l = e.detail && e.detail.list;
    if (l && l.length) celebrateAchievements(l);
  });
  document.addEventListener('speak:achievements', function (e) {
    var l = e.detail && e.detail.list;
    if (l && l.length) celebrateAchievements(l);
  });

  /* для тестов и отладки */
  window.__mascot = {
    explode: explode,
    celebrate: celebrateAchievements,
    say: say,
    state: function () { return { busy: busy, sleeping: sleeping, chain: chain, explosions: explosions }; }
  };
})();
