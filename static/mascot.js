/* ============================================================
   🐣 Чик-чик — анимированный виртуальный помощник.
   Живёт в правом нижнем углу, комментирует шаги ученицы
   и подбадривает. Работает на страницах: главная, уроки,
   карточки, упражнения, тест, результат.
   ============================================================ */
(function () {
  'use strict';

  var S = window.MASCOT_SETTINGS || {};
  if (S.enabled === false) return;

  var NAME = S.name || 'Чик-чик';
  var MSG_TIMEOUT = 30000;       // авто-скрытие balloon (30 сек)
  var IDLE_AFTER = 25000;        // balloon висит ~25 сек, потом сворачивается в "чаты"
  var NEXT_BTN = '.btn-primary, .btn-big';

  /* ---------- тексты ---------- */
  var T = {
    hello: [
      'Привет! Я {name} — твой помощник. Готовы учить английский? 🎈',
      'Хи-хи! Это я, {name}! Давай сегодня выучим что-нибудь классное ✨'
    ],
    lessonStart: [
      'Урок «{title}»! Мы с тобой всё одолеем 💪',
      'Начинаем урок «{title}». Читай вслух — так слова запоминаются лучше!'
    ],
    theoryDone: [
      'Отлично, теория прочитана! 📖 Теперь знакомься со словами.',
      'Молодец! Запомнил(а) главное? Идём дальше — к карточкам! 🧠'
    ],
    wordsDone: [
      'Красавчик! Слова почти в кармане 😎 Теперь потренируемся!',
      'Уже столько слов! Потренируйся — и можно будет сдать тест 📝'
    ],
    exercisesDone: [
      'Тренировка позади! Не бойся ошибаться — ошибки это ступеньки 🪜',
      'Супер! А теперь настоящий тест 📝 Ты справляешься, я в тебя верю!'
    ],
    testOpen: [
      'Это итоговый тест. Не торопись, читай каждый вопрос дважды 😉',
      'Тест пошёл! Я рядом — если что, подмигну тебе 🐣'
    ],
    right: ['Так правильно! 🎉', 'Верно! Ты умница 🌟', 'Есть! Так держать 🔥', 'Ура, правильный ответ! 👏'],
    wrong: [
      'Пока нет 🤔 Прочитай вопрос ещё раз — ты близко!',
      'Не расстраивайся! На ошибках учатся — попробуй ещё разок 💪',
      'Хм, не то. Вспомни карточки — там был ответ! 🧠',
      'Почти! Перечитай задание внимательно 😉'
    ],
    tapHint: 'Сначала коснись карточки, потом цели — так же работает, как перетаскивание ✋',
    dragHint: 'Перетащи карточку мышкой на пару ей 🖱️ или просто кликни карточку, потом цель ✋',
    allMatched: 'Все пары соединены! Жми «Проверить ✔️» 😊',
    allSorted: 'Все слова в корзинах! Проверяй — удачи! 🍀',
    resultPass100: 'ВОСХИТИТЕЛЬНО! 100%! 🎆🎆 Я знал(а), что ты сможешь!',
    resultPass: 'Урок пройден! 🎉 Отличная работа! Мама с папой будут гордиться 😊',
    resultNear: 'Очень близко к финишу! Ещё чуть-чуть — и урок твой 🌈',
    resultLow: 'Ничего страшного! Давай повторим слова и попробуем ещё раз 🤗',
    achIntro: ['СТОП! Стой смирно 🫡 У меня для тебя кое-что есть...',
               'Так-так-так... *нюхает носиком* Чую, тут пахнет подарком! 🎁',
               'Ты даже не представляешь, что я для тебя приготовил! 😲'],
    achOpen: ['Ура!! Это твоя награда: «{title}» {emoji} Ты её честно заслужил(а)! 🎊',
              'Смотри какой клад! Ачивка «{title}» {emoji} — так и сияет! ✨',
              '«{title}» {emoji} — теперь в твоей коллекции! Я тобой горжусь! 💛'],
    achAfter: ['Запомни: каждая ачивка — это шажок к большому английскому 🇬🇧',
               'Откроешь все ачивки — устроим целый салют! 🎆',
               'Показал(а)? Мама с папой будут в восторге! 👨‍👩‍👧'],

    doneAll: 'ТЫ ПРОШЛА ВСЕ УРОКИ!!! 🏆🎆 Мы самая крутая команда!',
    welcomeBack: 'С возвращением! Продолжаем с того места, где остановились 🚀',
    hiAgain: 'А, это снова ты! Привет-привет 👋 Нажми на меня, если нужна подсказка.'
  };

  function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
  function truthy(v) { return Array.isArray(v) ? v.length > 0 : !!v; }
  function fmt(tpl, vars) {
    return tpl.replace(/\{(\w+)\}/g, function (_, k) { return (vars && vars[k]) || ''; });
  }

  /* ---------- DOM ---------- */
  var root = document.createElement('div');
  root.className = 'mascot';
  root.innerHTML =
    '<div class="mascot-balloon"><span class="mascot-text"></span>' +
    '  <button class="mascot-close" title="Скрыть до конца страницы">✕</button></div>' +
    '<button class="mascot-body" aria-label="Помощник ' + NAME + '">' +
    '  <svg viewBox="0 0 92 96" xmlns="http://www.w3.org/2000/svg">' +
    '    <ellipse cx="46" cy="91" rx="25" ry="4.5" fill="rgba(0,0,0,.12)"/>' +
    '    <path d="M28 74 q-13 3 -16 -4 q10 -3 16 -5 z" fill="#F9A825"/>' +
    '    <path d="M64 74 q13 3 16 -4 q-10 -3 -16 -5 z" fill="#F9A825"/>' +
    '    <path d="M30 22 Q22 6 34 4 Q40 12 40 18 Z" fill="#FFD54F"/>' +
    '    <path d="M62 22 Q70 6 58 4 Q52 12 52 18 Z" fill="#FFD54F"/>' +
    '    <g class="m-wing m-wing-l"><path d="M22 46 Q4 52 8 68 Q18 72 26 62 Z" fill="#FFC947"/></g>' +
    '    <g class="m-wing m-wing-r"><path d="M70 46 Q88 52 84 68 Q74 72 66 62 Z" fill="#FFC947"/></g>' +
    '    <circle cx="46" cy="50" r="30" fill="#FFE082"/>' +
    '    <circle cx="46" cy="32" r="26" fill="#FFECB3"/>' +
    '    <g class="m-eyes">' +
    '      <circle cx="36" cy="30" r="5.5" fill="#4E342E"/>' +
    '      <circle cx="56" cy="30" r="5.5" fill="#4E342E"/>' +
    '      <circle cx="38" cy="28" r="1.8" fill="#fff"/>' +
    '      <circle cx="58" cy="28" r="1.8" fill="#fff"/>' +
    '    </g>' +
    '    <path class="m-blink" d="M30 30 Q36 34 42 30 M50 30 Q56 34 62 30" stroke="#4E342E" stroke-width="2.5" fill="none" stroke-linecap="round"/>' +
    '    <path d="M41 38 L46 43 L51 38 Q46 41 41 38 Z" fill="#FB8C00"/>' +
    '    <circle cx="28" cy="40" r="4" fill="#FFAB91" opacity=".65"/>' +
    '    <circle cx="64" cy="40" r="4" fill="#FFAB91" opacity=".65"/>' +
    '  </svg></button>';
  document.body.appendChild(root);

  var bodyEl = root.querySelector('.mascot-body');
  var balloon = root.querySelector('.mascot-balloon');
  var textEl = root.querySelector('.mascot-text');
  var closeBtn = root.querySelector('.mascot-close');
  var svg = root.querySelector('svg');
  var hideTimer = null, collapsed = false;

  /* ---------- показ сообщений ---------- */
  function say(text, opts) {
    opts = opts || {};
    if (!text) return;
    textEl.textContent = text;
    balloon.classList.remove('collapsed');
    balloon.classList.add('visible');
    collapsed = false;
    jump(opts.strong ? 3 : 2);
    if (opts.persist) {                 // висит, пока не скроют или не скажут новое
      clearTimeout(hideTimer);
      return;
    }
    clearTimeout(hideTimer);
    hideTimer = setTimeout(collapse, MSG_TIMEOUT);
    setTimeout(function () {
      if (!collapsed && balloon.classList.contains('visible')) collapse();
    }, IDLE_AFTER);
  }
  function collapse() {
    collapsed = true;
    balloon.classList.add('collapsed');
  }
  function expandLast() {
    if (textEl.textContent) {
      balloon.classList.remove('collapsed');
      balloon.classList.add('visible');
      collapsed = false;
      clearTimeout(hideTimer);
      hideTimer = setTimeout(collapse, MSG_TIMEOUT);
    } else {
      say(pick(T.hiAgain));
    }
  }

  function jump(n) {
    svg.classList.remove('m-jump', 'm-spin');
    void svg.offsetWidth;               // перезапуск анимации
    svg.classList.add(n >= 3 ? 'm-spin' : 'm-jump');
  }

  /* ---------- реакции на клики по самому чике ---------- */
  var pokeCount = 0;
  var pokes = ['Чем могу помочь? Нажми «Прочитал(а)!» и идём дальше 🙂',
               'Кликни на меня ещё раз — и я подмигну 😉',
               '*подмигивает* Ты суперская! 😜',
               'Не забудь читать слова вслух — ротик не мёрзнет! 🗣️',
               'Я верю в тебя! Даже когда ты сомневаешься 💛'];
  bodyEl.addEventListener('click', function () {
    pokeCount++;
    if (pokeCount % 3 === 0) wink();
    say(pick(pokes));
  });
  function wink() {
    svg.classList.add('m-wink');
    setTimeout(function () { svg.classList.remove('m-wink'); }, 700);
  }

  /* ---------- скрытие / возврат помощника ---------- */
  var reopenBtn = null;
  function showReopen() {
    if (reopenBtn) return;
    reopenBtn = document.createElement('button');
    reopenBtn.className = 'mascot-reopen';
    reopenBtn.textContent = '🐣';
    reopenBtn.title = 'Вернуть помощника';
    reopenBtn.addEventListener('click', function () {
      try { sessionStorage.removeItem('mascot_hidden_' + location.pathname); } catch (e) {}
      root.classList.remove('mascot-off');
      reopenBtn.remove();
      reopenBtn = null;
      say(pick(T.hiAgain), { strong: true });
    });
    document.body.appendChild(reopenBtn);
  }
  closeBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    try { sessionStorage.setItem('mascot_hidden_' + location.pathname, '1'); } catch (err) {}
    root.classList.add('mascot-off');
    showReopen();   // кнопка возврата появляется сразу, без перезагрузки страницы
  });
  balloon.addEventListener('click', function () { if (collapsed) expandLast(); });

  /* ---------- 🎁 вручение коробки с подарком за ачивку ---------- */
  var giftEl = null;
  function celebrateAchievements(list) {
    if (giftEl) return;                    // уже идёт вручение
    root.classList.add('mascot-off');      // чик «прячется», чтобы вынести коробку
    showReopen();                          // кнопка возврата всё ещё доступна
    say(pick(T.achIntro), { persist: true });

    var first = list[0];
    var extra = list.length - 1;
    giftEl = document.createElement('div');
    giftEl.className = 'gift-stage';
    giftEl.innerHTML =
      '<div class="gift-hint">Нажми на коробку! 🐣 принёс тебе подарок</div>' +
      '<button class="gift-box" aria-label="Открыть подарок">' +
      '  <svg viewBox="0 0 140 130" xmlns="http://www.w3.org/2000/svg">' +
      '    <g class="gb-lid"><rect x="8" y="26" width="124" height="26" rx="7" fill="#FF5D8F"/>' +
      '      <rect x="60" y="26" width="20" height="26" fill="#FFD54F"/>' +
      '      <path d="M70 30 Q52 6 42 16 Q38 26 70 30 Z" fill="#FFD54F"/>' +
      '      <path d="M70 30 Q88 6 98 16 Q102 26 70 30 Z" fill="#FFD54F"/></g>' +
      '    <rect x="16" y="52" width="108" height="70" rx="8" fill="#FF8FB8"/>' +
      '    <rect x="60" y="52" width="20" height="70" fill="#FFD54F"/>' +
      '    <rect x="16" y="52" width="108" height="10" fill="rgba(0,0,0,.08)"/>' +
      '  </svg></button>';
    document.body.appendChild(giftEl);

    var boxBtn = giftEl.querySelector('.gift-box');
    boxBtn.addEventListener('click', function () {
      if (giftEl.classList.contains('gift-open')) return;
      giftEl.classList.add('gift-open');
      jump(3);
      setTimeout(function () {
        var title = fmt(pick(T.achOpen), { title: first.title, emoji: first.emoji });
        if (extra > 0) title += ' И ещё ' + extra + ' шт.';
        root.classList.remove('mascot-off');
        if (reopenBtn) { reopenBtn.remove(); reopenBtn = null; }
        say(title, { strong: true, persist: true });
        confettiBurst();
        setTimeout(function () {
          giftEl.remove(); giftEl = null;
          setTimeout(function () { say(pick(T.achAfter)); }, 2500);
        }, 4200);
      }, 900);
    });
  }
  function confettiBurst() {
    var colors = ['#FF5D8F', '#FFD54F', '#4FC3F7', '#AED581', '#BA68C8', '#FB8C00'];
    for (var i = 0; i < 34; i++) {
      var c = document.createElement('i');
      c.className = 'confetti';
      c.style.left = (10 + Math.random() * 80) + 'vw';
      c.style.background = colors[i % colors.length];
      c.style.animationDuration = (1.4 + Math.random() * 1.6) + 's';
      c.style.animationDelay = (Math.random() * 0.35) + 's';
      c.style.transform = 'rotate(' + (Math.random() * 360) + 'deg)';
      document.body.appendChild(c);
      (function (el) { setTimeout(function () { el.remove(); }, 3600); })(c);
    }
  }

  /* ---------- очередь подсказок при переходе между шагами ---------- */
  var pending = null;
  function queue(msg, ms) {
    pending = msg;
    setTimeout(function () {
      if (pending === msg) { say(msg); pending = null; }
    }, ms || 4500);
  }

  /* ---------- интеграция с шагом теории ---------- */
  var curLesson = S.lessonTitle || null;
  var seen = {};
  try { seen = JSON.parse(sessionStorage.getItem('mascot_seen') || '{}'); } catch (e) {}
  function markSeen(key) {
    seen[key] = 1;
    try { sessionStorage.setItem('mascot_seen', JSON.stringify(seen)); } catch (e) {}
  }

  /* ---------- приветствие ---------- */
  var hiddenHere = false;
  try { hiddenHere = !!sessionStorage.getItem('mascot_hidden_' + location.pathname); } catch (e) {}
  if (hiddenHere) {
    root.classList.add('mascot-off');
    showReopen();   // кнопка возврата при уже скрытом помощнике
  }

  if (S.page === 'index') {
    setTimeout(function () { say(pick(T.hello), { strong: true }); }, 900);
  } else if (S.page === 'home') {
    var greeting = S.allDone ? T.doneAll : (S.alreadyStarted ? T.welcomeBack : T.hello[0]);
    setTimeout(function () { say(greeting, { strong: true }); }, 800);
  } else if (S.page === 'lesson') {
    var firstKey = 'ls' + (S.lessonId || '');
    setTimeout(function () {
      if (!seen[firstKey]) {
        say(fmt(pick(T.lessonStart), { title: curLesson }), { strong: true });
        markSeen(firstKey);
      } else {
        say(pick(T.hiAgain));
      }
    }, 800);
  } else if (S.page === 'result') {
    setTimeout(function () {
      var p = S.percent || 0;
      var msg = p === 100 ? T.resultPass100 :
                p >= 70 ? fmt(T.resultPass, { name: NAME }) :
                p >= 50 ? T.resultNear : T.resultLow;
      say(msg, { strong: true, persist: true });
      if (truthy(S.newAchievements)) {
        var list = Array.isArray(S.newAchievements) ? S.newAchievements : [];
        setTimeout(function () {
          if (list.length) celebrateAchievements(list);
          else say(pick(T.achIntro), { persist: true });   // совместимость со старым форматом
        }, 1800);
      }
    }, 700);
  }

  /* ---------- отслеживание шагов урока ---------- */
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
        if (stepMsgs[s]) {
          // сначала реакция на нажатую кнопку, потом реплика
          jump(2);
          setTimeout(function () { say(stepMsgs[s]()); }, 600);
        }
      }
    }, 700);

    /* ---------- обратная связь тренировок ---------- */
    var exObserver = new MutationObserver(function (muts) {
      muts.forEach(function (m) {
        var res = m.target;
        if (!res.classList || !res.classList.contains('ex-result')) return;
        var txt = res.textContent || '';
        if (txt.indexOf('✅') !== -1) say(pick(T.right));
        else if (txt.indexOf('❌') !== -1) say(pick(T.wrong));
        else if (txt.indexOf('🧩') !== -1) say(T.allMatched);
        else if (txt.indexOf('🧺') !== -1) say(T.allSorted);
      });
    });
    document.querySelectorAll('.ex-result').forEach(function (el) {
      exObserver.observe(el, { childList: true, characterData: true, subtree: true });
    });

    /* ---------- подсказки drag&drop ---------- */
    document.querySelectorAll('.dnd').forEach(function (dnd) {
      dnd.addEventListener('dragstart', function (e) {
        if (e.target === dnd || !e.target.getAttribute || !e.target.getAttribute('draggable')) return;
        dnd._hintShown = true;
        say(T.dragHint);
      });
      dnd.addEventListener('click', function (e) {
        var t = e.target;
        if (!t.classList) return;
        if (t.classList.contains('match-tile') ||
            (t.classList.contains('sort-word') && t.parentElement.classList.contains('sort-tray'))) {
          if (!dnd._tapHinted) { dnd._tapHinted = true; say(T.tapHint); }
        }
      });
    });

    /* ---------- завершение всех заданий тренировки ---------- */
    var checkExercisesDone = function () {
      var box = document.getElementById('step-exercises');
      if (!box || box.classList.contains('hidden')) return;
      var results = box.querySelectorAll('.ex-result.ok');
      var total = box.querySelectorAll('.exercise');
      if (total.length && results.length === total.length && !window._allExCheered) {
        window._allExCheered = true;
        say('Все упражнения выполнены! 🎊 Теперь — боевой тест! 📝', { strong: true });
        queue(null); // отменить возможные хвостовые очереди
      }
    };
    setInterval(checkExercisesDone, 1200);
  }
})();
