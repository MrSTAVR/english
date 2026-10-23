/* ============================================================
   Озвучивание английских слов и фраз (Web Speech API).
   Работает офлайн: голос берётся из системы (Chrome/Edge на
   Windows имеют встроенный английский голос "Microsoft ...").
   Никаких серверов и генерации файлов не требуется.
   ============================================================ */
(function () {
  'use strict';

  var synth = window.speechSynthesis;
  var enVoice = null;
  var ready = false;

  function pickVoice() {
    if (!synth) return;
    var voices = synth.getVoices();
    if (!voices || !voices.length) return;
    // Предпочитаем «нативные» голоса Microsoft/Helena/Samantha/Daniel —
    // у них лучшее произношение для детей; затем любой en-*.
    var preferred = ['helena', 'samantha', 'daniel', 'zira', 'george', 'karen', 'moira', 'tessa'];
    var en = voices.filter(function (v) { return /^en([-_]|$)/i.test(v.lang); });
    if (!en.length) return;
    for (var p = 0; p < preferred.length; p++) {
      for (var i = 0; i < en.length; i++) {
        if (en[i].name.toLowerCase().indexOf(preferred[p]) !== -1) { enVoice = en[i]; ready = true; return; }
      }
    }
    // голос Microsoft — отличный вариант на Windows
    for (var j = 0; j < en.length; j++) {
      if (/microsoft/i.test(en[j].name)) { enVoice = en[j]; ready = true; return; }
    }
    enVoice = en[0];
    ready = true;
  }

  if (synth) {
    pickVoice();
    synth.onvoiceschanged = pickVoice; // список голосов подгружается асинхронно
  }

  // Словарь замен слов с диакритикой/заимствований — чтобы голос читал их правильно
  // Ключи со звездочкой (*) читаются голосом как есть — это фонетическая подсказка.
  var SPEAK_MAP = {
    "café": "coffee", "cafe": "coffee", "crème": "cream", "creme": "cream",
    "cliché": "*shee shay", "fiancé": "*fee on say", "fiancée": "*fee on say",
    "croissant": "*kwa son", "crouton": "*crow ton", "pâté": "*pa tay",
    "résumé": "*rez um ay", "naïve": "*nye eev", "touché": "*too shay",
    "déjà vu": "*day zha voo", "ballet": "*ba lay", "buffet": "*bu fay",
    "soufflé": "*soo flay", "entrecôte": "*on tra kot", "hors d'oeuvre": "*or durv",
    "café au lait": "*ka fey o lay"
  };

  function stripForSpeech(text) {
    var s = String(text)
      .replace(/[«»"'`]/g, '')
      .replace(/\(.*?\)/g, '')          // убираем транскрипцию (IPA)
      .replace(/\[.*?\]/g, '');
    // Сначала снимаем диакритику с текста (NFD -> убрать комбинируемые метки),
    // затем матчим со словарём по нормализованным ключам — так замена сработает
    // независимо от формы Unicode, в которой слово пришло из БД/HTML.
    if (s.normalize) {
      s = s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    } else {
      s = s.replace(/[áàâäãåā]/g, 'a').replace(/[éèêëē]/g, 'e')
           .replace(/[íìîïī]/g, 'i').replace(/[óòôöõøō]/g, 'o')
           .replace(/[úùûüū]/g, 'u').replace(/[ç]/g, 's').replace(/[ñ]/g, 'n');
    }
    function normKey(k) {
      if (k.normalize) k = k.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
      return k.toLowerCase();
    }
    var phrases = [], words = [];
    Object.keys(SPEAK_MAP).forEach(function (k) {
      (k.indexOf(' ') >= 0 ? phrases : words).push(normKey(k));
    });
    phrases.sort(function (a, b) { return b.length - a.length; });
    function applyMap(list, isPhrase) {
      list.forEach(function (k) {
        var repl = SPEAK_MAP[Object.keys(SPEAK_MAP).filter(function (orig) {
          return normKey(orig) === k;
        })[0]];
        if (isPhrase) {
          s = s.replace(new RegExp(k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), repl);
        } else {
          var re = new RegExp('(^|[^A-Za-z])' + k + '($|[^A-Za-z])', 'gi');
          s = s.replace(re, '$1' + repl + '$2');
        }
      });
    }
    applyMap(phrases, true);
    applyMap(words, false);
    s = s.replace(/\*/g, '');   // звёздочки — маркеры фонетических замен, синтезу не нужны
    // NFD-разложение: é -> e + ́, затем выбрасываем комбинируемые диакритические метки
    if (s.normalize) {
      s = s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    } else {
      s = s.replace(/[áàâäãåā]/g, 'a').replace(/[éèêëē]/g, 'e')
           .replace(/[íìîïī]/g, 'i').replace(/[óòôöõøō]/g, 'o')
           .replace(/[úùûüū]/g, 'u').replace(/[ç]/g, 's').replace(/[ñ]/g, 'n');
    }
    // всё, что осталось не-ASCII (например, ø, œ), вырезаем — синтез их не любит
    s = s.replace(/[^A-Za-z0-9\s.,!?:;-]/g, ' ')
         .replace(/\s+/g, ' ')
         .trim();
    return s;
  }

  /* Основной вызов: speak("Hello, how are you?").
     Говорит только последнее слово: если голос ещё занят, сначала обрываем его и ждём чуть-чуть —
     иначе Chrome (особенно на Windows и Android) не всегда очищает очередь и старые слова
     звучат позже сами, например уже на следующем шаге урока. */
  var speakToken = 0;
  function speak(text, rate) {
    if (!synth || !text) return false;
    var clean = stripForSpeech(text);
    if (!clean) return false;
    var token = ++speakToken, busy = synth.speaking || synth.pending;
    try { synth.cancel(); } catch (e) { /* noop */ }
    if (busy) setTimeout(function () { if (token === speakToken) say(clean, rate); }, 60);
    else say(clean, rate);
    return true;
  }
  function say(clean, rate) {
    var u = new SpeechSynthesisUtterance(clean);
    u.lang = 'en-US';
    if (enVoice) u.voice = enVoice;
    u.rate = rate || 0.85;   // чуть медленнее обычного — ребёнку легче воспринять
    u.pitch = 1.05;
    u.volume = 1;
    synth.speak(u);
  }
  window.ttsSpeak = speak;

  /* Читаем список предложений подряд: ttsSpeakSeq(list, {rate, onSentence(i), onDone}) */
  var seqToken = 0;
  function stopSeq() { seqToken++; speakToken++; try { if (synth) synth.cancel(); } catch (e) { /* noop */ } }
  function speakSeq(list, o) {
    o = o || {};
    if (!synth || !list || !list.length) { if (o.onDone) o.onDone(); return false; }
    stopSeq();
    var token = seqToken, i = 0;
    function next() {
      if (token !== seqToken) return;
      if (i >= list.length) { if (o.onDone) o.onDone(); return; }
      var idx = i++, clean = stripForSpeech(list[idx]);
      if (!clean) { next(); return; }
      var u = new SpeechSynthesisUtterance(clean);
      u.lang = 'en-US'; if (enVoice) u.voice = enVoice;
      u.rate = o.rate || 0.85; u.pitch = 1.05; u.volume = 1;
      u.onstart = function () { if (token === seqToken && o.onSentence) o.onSentence(idx); };
      u.onend = u.onerror = function () { setTimeout(next, 250); };
      synth.speak(u);
    }
    setTimeout(next, 80);
    return true;
  }
  window.ttsSpeakSeq = speakSeq;
  window.ttsStop = stopSeq;

  /* Кнопка 🔊 рядом со словом/фразой */
  function makeBtn(text, opts) {
    opts = opts || {};
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'tts-btn' + (opts.small ? ' tts-small' : '');
    b.title = 'Послушать произношение';
    b.setAttribute('aria-label', 'Озвучить: ' + text);
    b.innerHTML = '<svg class="icon" aria-hidden="true"><use href="#i-sound"></use></svg>';
    b.addEventListener('click', function (ev) {
      ev.preventDefault();
      ev.stopPropagation();       // чтобы не переворачивать карточку
      speak(text, opts.rate);
      b.classList.remove('tts-pulse');
      void b.offsetWidth;         // перезапуск анимации
      b.classList.add('tts-pulse');
    });
    return b;
  }

  function supported() { return !!synth && typeof SpeechSynthesisUtterance !== 'undefined'; }

  document.addEventListener('DOMContentLoaded', function () {
    if (!supported()) {
      // Если голосов нет — показываем деликатное уведомление один раз
      var bar = document.getElementById('tts-warn');
      if (bar) bar.classList.remove('hidden');
      return;
    }

    // 1) Карточки слов: озвучка при клике на рубашку + отдельная кнопка 🔊
    document.querySelectorAll('.flashcard .fc-en').forEach(function (el) {
      var word = el.textContent.trim();
      if (!word) return;
      el.appendChild(makeBtn(word, { small: true }));
    });

    // 2) Элементы с data-tts — любые фразы (упражнения, тесты)
    document.querySelectorAll('[data-tts]').forEach(function (el) {
      var text = el.getAttribute('data-tts') || el.textContent.trim();
      if (!text) return;
      el.appendChild(makeBtn(text, { small: true }));
    });

    // 3) Автоматически озвучиваем варианты ответов в тестах/упражнениях choice
    //    (клик по варианту = услышал ответ)
    //    Слушаем выбор самого варианта (change), а не клик по подписи: клик по <label> приходит дважды
    //    (подпись + переключатель), а восстановление ответов урока ставит отметку без озвучки.
    document.querySelectorAll('.opt').forEach(function (label) {
      var inp = label.querySelector('input');
      if (!inp) return;
      inp.addEventListener('change', function () {
        var t = label.textContent.trim();
        if (t && inp.checked) speak(t);
      });
    });

    // 4) В заданиях «собери предложение» — озвучка собранной фразы
    window.ttsSpeakLine = function (idx) {
      var inp = document.getElementById('order-' + idx);
      if (inp && inp.value) speak(inp.value, 0.8);
    };

    // 5) Озвучка ответа, который ребёнок набрал сам (поле .typein рядом с кнопкой)
    window.ttsSpeakInput = function (btn) {
      var box = btn.closest('.exercise') || btn.closest('.question');
      var inp = box ? box.querySelector('.typein') : null;
      if (inp && inp.value.trim()) speak(inp.value.trim(), 0.85);
    };
  });
})();
