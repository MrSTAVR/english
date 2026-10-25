/* Урок (дизайн 4.0): подпись текущего шага, озвучка фраз в теории, колода «Новые слова»
   — одна большая карточка, перевод по нажатию, точки, список всех слов (на телефоне — шторка снизу).
   Место в уроке (шаг, слово, ответы) сохраняется на сервере и восстанавливается при возврате. */
(function () {
  'use strict';
  var STEPS = { 'step-theory': ['Теория', 1], 'step-material': ['Слова', 2], 'step-exercises': ['Тренировка', 3], 'step-test': ['Тест', 4] };
  function say(text, slow) { if (window.ttsSpeak) window.ttsSpeak(text, slow ? 0.55 : null); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function ICO(name) { return '<svg class="ico" aria-hidden="true"><use href="#o-' + name + '"/></svg>'; }
  var $ = function (id) { return document.getElementById(id); };

  var curStep = 'step-theory';
  var deck = null;
  var progress = null;

  /* ---------- шаг урока: подпись «Слова · 2/4» (на телефоне) ---------- */
  var now = $('ls-now');
  window.lessonStepChanged = function (id) {
    curStep = id;
    var s = STEPS[id];
    if (now && s) now.textContent = s[0] + ' · ' + s[1] + '/4';
    if (id === 'step-material' && deck) deck.show();
    if (progress) progress.save();
  };

  /* ---------- теория: английские фразы (жирным) озвучиваются по нажатию ---------- */
  document.querySelectorAll('#step-theory .theory-block b, #step-theory .theory-intro b').forEach(function (b) {
    var text = b.textContent.trim();
    if (!/[A-Za-z]/.test(text) || /[А-Яа-яЁё]/.test(text)) return;
    // не <button>: кнопка в Chrome всегда «блок в строке» — не переносится и раздувает строку;
    // строчный <span> с ролью кнопки переносится вместе с текстом
    var btn = document.createElement('span');
    btn.className = 'th-say';
    btn.setAttribute('role', 'button');
    btn.tabIndex = 0;
    btn.title = 'Послушать';
    var sp = text.indexOf(' ');                         // значок не отрывается от первого слова при переносе
    var head = sp < 0 ? text : text.slice(0, sp), tail = sp < 0 ? '' : text.slice(sp);
    btn.innerHTML = '<span class="th-say-head">' + ICO('sound') + '<b lang="en">' + esc(head) + '</b></span>' +
      (tail ? '<b lang="en">' + esc(tail) + '</b>' : '');
    btn.addEventListener('click', function () { say(text.replace(/…|\.\.\./g, '')); });
    btn.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); btn.click(); } });
    b.replaceWith(btn);
  });

  /* ---------- колода слов ---------- */
  deck = (function () {
    var dataEl = $('wd-data');
    var W = [];
    try { W = JSON.parse(dataEl ? dataEl.textContent : '[]'); } catch (e) { W = []; }
    if (!W.length) return null;
    var card = $('wd-card'), sheet = $('wd-sheet');
    var i = 0, flipped = false, seen = {};

    function picHtml(w) { return w.pic ? '<span class="wd-emoji">' + esc(w.pic) + '</span>' : ICO('chat'); }
    function rowsHtml() {
      return W.map(function (w, k) {
        return '<button type="button" class="wd-row' + (k === i ? ' is-on' : '') + '" data-k="' + k + '">' +
          '<span class="wd-row-pic' + (w.pic ? '' : ' no-pic') + '">' + picHtml(w) + '</span>' +
          '<span class="wd-row-text"><b lang="en">' + esc(w.en) + '</b><small>' + esc(w.ru) + '</small></span>' +
          '<span class="wd-mark' + (seen[k] ? ' on' : '') + '">' + ICO('check') + '</span></button>';
      }).join('');
    }
    function render() {
      var w = W[i];
      $('wd-num').textContent = (i + 1) + ' из ' + W.length;
      $('wd-know').hidden = !seen[i];
      var pic = $('wd-pic');
      pic.className = 'wd-pic' + (w.pic ? '' : ' no-pic');
      pic.innerHTML = picHtml(w);
      $('wd-en').textContent = w.en;
      $('wd-hint').textContent = w.hint ? '[' + w.hint + ']' : '';
      $('wd-ru').textContent = w.ru;
      $('wd-ru').hidden = !flipped;
      $('wd-tap').hidden = flipped;
      card.setAttribute('aria-label', flipped ? 'Спрятать перевод' : 'Показать перевод');
      $('wd-prev').disabled = i === 0;
      $('wd-next').textContent = i === W.length - 1 ? 'К тренировке →' : 'Дальше →';
      $('wd-dots').innerHTML = W.map(function (x, k) {
        return '<button type="button" class="wd-dot' + (k === i ? ' is-on' : seen[k] ? ' is-seen' : '') + '" data-k="' + k + '" aria-label="' + esc(x.en) + '"></button>';
      }).join('');
      $('wd-rows').innerHTML = $('wd-rows2').innerHTML = rowsHtml();
      $('wd-count').textContent = $('wd-count2').textContent = 'знаю ' + Object.keys(seen).length + ' из ' + W.length;
    }
    function changed() { if (progress) progress.save(); }
    function go(k) {
      seen[i] = true;                                   // слово показали — оно «знакомое»
      i = Math.max(0, Math.min(W.length - 1, k));
      flipped = false;
      render();
      say(W[i].en);
      changed();
    }
    function openSheet(open) {
      sheet.hidden = !open;
      document.body.classList.toggle('wd-sheet-open', open);
      if (open) { var on = sheet.querySelector('.wd-row.is-on'); if (on) on.scrollIntoView({ block: 'center' }); }
    }

    card.addEventListener('click', function () { flipped = !flipped; if (flipped) seen[i] = true; render(); changed(); });
    card.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); card.click(); } });
    $('wd-say').addEventListener('click', function () { say(W[i].en); });
    $('wd-slow').addEventListener('click', function () { say(W[i].en, true); });
    $('wd-prev').addEventListener('click', function () { go(i - 1); });
    $('wd-next').addEventListener('click', function () {
      if (i === W.length - 1) { seen[i] = true; changed(); if (window.goStep) window.goStep('step-exercises'); return; }
      go(i + 1);
    });
    $('wd-all').addEventListener('click', function () { openSheet(true); });
    [$('wd-dots'), $('wd-rows'), $('wd-rows2')].forEach(function (box) {
      box.addEventListener('click', function (e) {
        var b = e.target.closest('[data-k]');
        if (!b) return;
        go(+b.dataset.k);
        openSheet(false);
      });
    });
    sheet.addEventListener('click', function (e) { if (e.target.closest('[data-close]')) openSheet(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !sheet.hidden) openSheet(false); });
    render();
    return {
      show: render,
      get: function () { return { i: i, seen: Object.keys(seen).map(Number) }; },
      set: function (st) {
        if (!st) return;
        seen = {};
        (st.seen || []).forEach(function (k) { if (k >= 0 && k < W.length) seen[k] = true; });
        i = Math.max(0, Math.min(W.length - 1, st.i | 0));
        flipped = false;
        render();
      }
    };
  })();

  /* ---------- сохранение места в уроке ---------- */
  progress = (function () {
    var stateEl = $('ls-state');
    if (!stateEl || !window.fetch) return null;
    var lessonId = stateEl.dataset.lesson, timer = null, ready = false;
    var saved = null;
    try { saved = JSON.parse(stateEl.textContent || 'null'); } catch (e) { saved = null; }
    function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ''; }
    function post(body) {
      return fetch('/api/lesson/' + lessonId + '/progress', {
        method: 'POST', credentials: 'same-origin', keepalive: true,
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() }, body: JSON.stringify(body)
      }).catch(function () { /* офлайн — сохраним в следующий раз */ });
    }
    /* ответы в тренировке и тесте: выбранные варианты (по name) и введённые слова (по порядку) */
    /* ответы на шаге: выбранные варианты (по name), введённые слова, проверенные задания,
       перетаскивания («Соедини пары», «Разложи по корзинам»), собранные слова и предложения */
    function chipsText(el) { return el ? [].map.call(el.querySelectorAll('.word-chip'), function (c) { return c.textContent; }) : []; }
    function answers(stepId) {
      var box = $(stepId), out = { radio: {}, text: [], checked: [], match: [], sort: [], lines: {} };
      if (!box) return out;
      box.querySelectorAll('input[type=radio]:checked').forEach(function (r) { if (r.name) out.radio[r.name] = r.value; });
      box.querySelectorAll('input.typein').forEach(function (t) { out.text.push(t.value); });
      box.querySelectorAll('.exercise').forEach(function (ex, k) {
        var res = ex.querySelector('.ex-result'), exp = ex.querySelector('.explain');
        if (res && /\b(ok|bad)\b/.test(res.className)) {
          out.checked.push({ k: k, t: res.textContent, ok: /\bok\b/.test(res.className), exp: !!exp && !exp.classList.contains('hidden') });
        }
      });
      box.querySelectorAll('.dnd-match').forEach(function (root) { out.match.push(root._pairs || {}); });
      box.querySelectorAll('.dnd-sort').forEach(function (root) {
        var m = {};
        root.querySelectorAll('.bin').forEach(function (bin) { bin.querySelectorAll('.sort-word').forEach(function (w) { m[w.dataset.word] = bin.dataset.cat; }); });
        out.sort.push(m);
      });
      box.querySelectorAll('.answer-line').forEach(function (line, k) { var t = chipsText(line); if (t.length) out.lines[k] = t; });
      return out;
    }
    function putAnswers(stepId, a) {
      var box = $(stepId);
      if (!box || !a) return;
      Object.keys(a.radio || {}).forEach(function (name) {
        var r = box.querySelector('input[type=radio][name="' + CSS.escape(name) + '"][value="' + CSS.escape(String(a.radio[name])) + '"]');
        if (r) r.checked = true;
      });
      var inputs = box.querySelectorAll('input.typein');
      (a.text || []).forEach(function (v, k) { if (inputs[k] && typeof v === 'string') inputs[k].value = v; });
      var roots = box.querySelectorAll('.dnd-match');
      (a.match || []).forEach(function (pairs, k) {
        var root = roots[k];
        if (!root || !window.placePair) return;
        Object.keys(pairs || {}).forEach(function (l) {
          var tile = root.querySelector('.match-tile[data-left="' + CSS.escape(l) + '"]');
          var slot = root.querySelector('.match-slot[data-right="' + CSS.escape(String(pairs[l])) + '"]');
          if (tile && slot) window.placePair(root, slot, tile);
        });
      });
      var sorts = box.querySelectorAll('.dnd-sort');
      (a.sort || []).forEach(function (m, k) {
        var root = sorts[k];
        if (!root) return;
        Object.keys(m || {}).forEach(function (word) {
          var w = root.querySelector('.sort-tray .sort-word[data-word="' + CSS.escape(word) + '"]');
          var bin = root.querySelector('.bin[data-cat="' + CSS.escape(String(m[word])) + '"] .bin-body');
          if (w && bin) bin.appendChild(w);
        });
        if (window.fillHidden) window.fillHidden(root);
      });
      var lines = box.querySelectorAll('.answer-line');
      Object.keys(a.lines || {}).forEach(function (k) {
        var line = lines[k];
        if (!line) return;
        var bank = line.parentNode.querySelector('.word-bank');
        (a.lines[k] || []).forEach(function (t) {
          var chip = bank && [].filter.call(bank.querySelectorAll('.word-chip'), function (c) { return c.textContent === t && c.style.display !== 'none'; })[0];
          if (chip) chip.click();                       // тест: pickWord; тренировка: буква переезжает в строку
        });
      });
      var exs = box.querySelectorAll('.exercise');
      (a.checked || []).forEach(function (c) {
        var ex = exs[c.k];
        if (!ex) return;
        var res = ex.querySelector('.ex-result'), exp = ex.querySelector('.explain');
        if (res) { res.textContent = c.t; res.className = 'ex-result ' + (c.ok ? 'ok' : 'bad'); }
        if (exp && c.exp) exp.classList.remove('hidden');
        if (c.ok) ex.classList.add('done');
      });
    }
    function state() {
      var start = typeof window.START_TS === 'number' ? window.START_TS : null;
      return {
        step: curStep,
        scroll: Math.round(window.scrollY || 0),
        words: deck ? deck.get() : null,
        ex: answers('step-exercises'),
        test: answers('step-test'),
        dlg: window.LessonDialogs ? window.LessonDialogs.get() : null,
        speak: ($('speak-block') && $('speak-block')._speak) ? $('speak-block')._speak.get() : null,
        secs: start ? Math.max(0, Math.round(Date.now() / 1000 - start)) : 0
      };
    }
    function saveNow() { if (ready) post({ state: state() }); }
    function save() { if (!ready) return; clearTimeout(timer); timer = setTimeout(saveNow, 700); }

    ['step-exercises', 'step-test'].forEach(function (id) {
      var box = $(id);
      if (box) ['change', 'input', 'click', 'pointerup'].forEach(function (ev) { box.addEventListener(ev, save); });
    });
    document.addEventListener('lesson:changed', save);   // диалоги и «Скажи вслух» сообщают сами
    var scrollT = null;                                  // место на странице — тоже часть «где остановились»
    window.addEventListener('scroll', function () { clearTimeout(scrollT); scrollT = setTimeout(save, 400); }, { passive: true });
    document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') { clearTimeout(timer); saveNow(); } });
    var form = $('test-form');
    if (form) form.addEventListener('submit', function () { ready = false; clearTimeout(timer); });   // после теста — сервер сам сотрёт

    var restart = $('ls-restart');
    if (restart) restart.addEventListener('click', function () {
      ready = false; clearTimeout(timer);
      post({ reset: true }).then(function () { location.reload(); });
    });

    /* восстанавливаем, когда скрипт страницы (goStep, START_TS) уже загружен */
    document.addEventListener('DOMContentLoaded', function () {
      var useful = saved && (saved.step !== 'step-theory' || (saved.scroll | 0) > 200 || (saved.words && (saved.words.seen || []).length));
      if (useful) {
        if (deck && saved.words) deck.set(saved.words);
        putAnswers('step-exercises', saved.ex);
        putAnswers('step-test', saved.test);
        if (saved.step && saved.step !== 'step-theory' && window.goStep) window.goStep(saved.step);
        setTimeout(function () {                         // диалоги и «Скажи вслух» строятся на DOMContentLoaded после нас
          if (saved.dlg && window.LessonDialogs) window.LessonDialogs.set(saved.dlg);
          var sb = $('speak-block');
          if (saved.speak && sb && sb._speak) sb._speak.set(saved.speak);
        }, 0);
        var y = saved.scroll | 0;
        if (y > 0) setTimeout(function () { window.scrollTo({ top: y, behavior: 'auto' }); }, 80);   // goStep сначала поднимает наверх
        var form2 = $('test-form');
        if (form2) form2.dispatchEvent(new Event('change', { bubbles: true }));   // полоска «Отвечено»
        var note = $('ls-resume');
        if (note) note.hidden = false;
      }
      ready = true;
    });
    return { save: save };
  })();
})();
