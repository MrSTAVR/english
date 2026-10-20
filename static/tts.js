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

  function stripForSpeech(text) {
    return String(text)
      .replace(/[«»"'`]/g, '')
      .replace(/\(.*?\)/g, '')          // убираем транскрипцию [prɪˈpəz]
      .replace(/\[.*?\]/g, '')
      .replace(/[^A-Za-z0-9\s.,!?:;-]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  /* Основной вызов: speak("Hello, how are you?") */
  function speak(text, rate) {
    if (!synth || !text) return false;
    var clean = stripForSpeech(text);
    if (!clean) return false;
    try { synth.cancel(); } catch (e) { /* noop */ }
    var u = new SpeechSynthesisUtterance(clean);
    u.lang = 'en-US';
    if (enVoice) u.voice = enVoice;
    u.rate = rate || 0.85;   // чуть медленнее обычного — ребёнку легче воспринять
    u.pitch = 1.05;
    u.volume = 1;
    synth.speak(u);
    return true;
  }
  window.ttsSpeak = speak;

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
    document.querySelectorAll('.opt').forEach(function (label) {
      label.addEventListener('click', function () {
        var t = label.textContent.trim();
        if (t) speak(t);
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
