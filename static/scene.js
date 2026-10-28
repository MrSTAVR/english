/* Сцена истории вместо теста (scenes.py): реплики героев появляются по очереди, ученица отвечает за себя.
   Ответ проверяется сразу (можно попробовать ещё раз, после двух ошибок показываем верный и идём дальше),
   но на сервер уходит ПЕРВЫЙ ответ — скрытые поля q<i> / q<i>_order, сдача как у обычного теста.
   window.LessonScene.get()/set() — место в сцене и первые ответы (для «продолжить урок с того же места»). */
(function () {
  'use strict';
  var root = document.getElementById('scene');
  var dataEl = document.getElementById('scene-data');
  if (!root || !dataEl) return;
  var STEPS = [];
  try { STEPS = JSON.parse(dataEl.textContent) || []; } catch (e) { STEPS = []; }
  var form = document.getElementById('test-form'), panel = document.getElementById('scene-panel');
  var endBox = document.getElementById('scene-end');
  var me = { emoji: root.dataset.meEmoji || '🎒', name: root.dataset.meName || 'Я' };
  var tilesOpen = root.dataset.tilesOpen === '1';
  var LT = window.LetterTiles;

  var pos = 0, first = {}, tries = {}, touched = false, quiet = false;

  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function say(t) { if (window.ttsSpeak) window.ttsSpeak(t); }
  function changed() { document.dispatchEvent(new CustomEvent('lesson:changed')); }
  function ico(id) { return '<svg class="ico" aria-hidden="true"><use href="#' + id + '"/></svg>'; }
  function show(node) { root.appendChild(node); if (!quiet) node.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }

  function hidden(name, value) {
    var h = form.querySelector('input[type=hidden][name="' + name + '"]');
    if (!h) { h = el('input'); h.type = 'hidden'; h.name = name; form.appendChild(h); }
    h.value = value;
  }

  function bubble(who, en, ru, mine) {
    var row = el('div', 'dlg-row ' + (mine ? 'me' : 'them'));
    var ava;
    if (mine) ava = '<div class="dlg-ava" aria-hidden="true">' + esc(me.emoji) + '</div>';
    else if (who.chick) ava = '<div class="dlg-ava sc-chick" aria-hidden="true">' + ico('i-chick') + '</div>';
    else ava = '<div class="dlg-ava" style="background:' + esc(who.bg) + '" aria-hidden="true">' + esc(who.pic) + '</div>';
    var name = mine ? me.name : who.name;
    var role = !mine && who.role ? ' <span class="dlg-role">· ' + esc(who.role) + '</span>' : '';
    var speak = /[A-Za-z]/.test(en) ? '<button type="button" class="dlg-say" title="Послушать" aria-label="Послушать">' + ico('o-sound') + '</button>' : '';
    row.innerHTML = ava + '<div class="dlg-main"><div class="dlg-name">' + esc(name) + role + '</div><div class="dlg-bubble">' +
      esc(en) + speak + (ru ? '<div class="dlg-ru" hidden>' + esc(ru) + '</div>' : '') + '</div></div>';
    var b = row.querySelector('.dlg-say');
    if (b) b.onclick = function (e) { e.stopPropagation(); say(en); };
    var tr = row.querySelector('.dlg-ru');          // перевод — по нажатию на реплику (иначе подсказывал бы ответ)
    if (tr) { row.querySelector('.dlg-bubble').classList.add('sc-tap'); row.querySelector('.dlg-bubble').onclick = function () { tr.hidden = !tr.hidden; }; }
    show(row);
  }

  function noteRow(text) { show(el('div', 'sc-note', esc(text))); }

  /* ход ученицы: вопрос в панели под чатом; ответ — пузырь справа */
  function answerText(st) {
    if (st.type === 'choice') {
      for (var k = 0; k < st.options.length; k++) if (st.options[k][0] === st.answer) return st.options[k][1];
    }
    return String(st.answer);
  }
  function isRight(st, v) {
    if (st.type === 'choice') return +v === st.answer;
    if (!LT) return String(v).trim().toLowerCase() === String(st.answer).trim().toLowerCase();
    return LT.same(v, st.answer) || (st.type === 'type_in' && LT.near(v, st.answer));
  }

  function record(st, v) {                       // первый ответ — на сервер
    if (st.i in first) return;
    first[st.i] = v;
    hidden(st.type === 'order' ? 'q' + st.i + '_order' : 'q' + st.i, v);
  }

  function finishTurn(st, v, ok) {
    panel.innerHTML = '';
    var shown = ok && st.type === 'type_in' ? v : answerText(st);
    bubble(null, shown, '', true);
    if (!ok) noteRow('Правильно так: ' + answerText(st) + (st.explain ? ' — ' + st.explain.replace(/^[^—]*—\s*/, '') : ''));
    else if (st.type === 'type_in' && LT && !LT.same(v, st.answer)) noteRow('Засчитано! Только пишется так: ' + st.answer);
    pos++;
    changed();
    if (quiet) return;
    setTimeout(next, 450);
  }

  function attempt(st, v, fb, onWrong) {
    record(st, v);
    tries[st.i] = (tries[st.i] || 0) + 1;
    if (isRight(st, v)) { finishTurn(st, v, true); return; }
    changed();
    if (tries[st.i] >= 2) { finishTurn(st, v, false); return; }
    fb.className = 'rv-fb bad';
    fb.textContent = 'Почти! Попробуй ещё раз.';
    if (onWrong) onWrong();
  }

  function ask(st) {
    panel.innerHTML = '';
    var box = el('div', 'sc-turn');
    box.appendChild(el('p', 'sc-q', '<b>Твой ход.</b> ' + esc(st.q)));
    if (st.audio) {
      var row = el('p', 'sc-audio');
      row.innerHTML = '<button type="button" class="btn btn-small say-btn">' + ico('o-sound') + ' Слушать</button> ' +
        '<button type="button" class="btn btn-small say-btn">' + ico('o-turtle') + ' Медленно</button>';
      var bs = row.querySelectorAll('button');
      bs[0].onclick = function () { say(st.audio); };
      bs[1].onclick = function () { if (window.ttsSpeak) window.ttsSpeak(st.audio, { slow: true }); };
      box.appendChild(row);
      if (touched) say(st.audio);
    }
    var fb = el('div', 'rv-fb');
    if (st.type === 'choice') {
      var opts = el('div', 'rv-opts');
      st.options.forEach(function (o) {
        var b = el('button', 'rv-opt', esc(o[1])); b.type = 'button';
        b.onclick = function () {
          touched = true;
          attempt(st, String(o[0]), fb, function () { b.classList.add('is-wrong'); b.disabled = true; });
        };
        opts.appendChild(b);
      });
      box.appendChild(opts);
    } else if (st.type === 'order') {
      var bank = el('div', 'word-bank'), line = el('div', 'answer-line');
      function sync() { ok.disabled = !!bank.querySelector('.word-chip:not([hidden])'); }
      st.words.forEach(function (w) {
        var c = el('button', 'word-chip', esc(w)); c.type = 'button';
        c.onclick = function () {
          c.hidden = true;
          var t = el('button', 'word-chip chosen', esc(w)); t.type = 'button';
          t.onclick = function () { t.remove(); c.hidden = false; sync(); };
          line.appendChild(t); sync();
        };
        bank.appendChild(c);
      });
      var ok = el('button', 'btn sc-ok', 'Ответить'); ok.type = 'button'; ok.disabled = true;
      ok.onclick = function () {
        touched = true;
        var v = [].map.call(line.querySelectorAll('.word-chip'), function (c) { return c.textContent; }).join(' ');
        attempt(st, v, fb, function () {
          line.innerHTML = ''; bank.querySelectorAll('.word-chip').forEach(function (c) { c.hidden = false; }); sync();
        });
      };
      box.appendChild(bank); box.appendChild(line); box.appendChild(ok);
    } else {
      var inp = el('input', 'typein'); inp.type = 'text'; inp.autocomplete = 'off';
      inp.lang = st.ru ? 'ru' : 'en';
      inp.placeholder = st.ru ? 'Напиши по-русски' : 'Напиши по-английски';
      if (!(st.i in first)) inp.name = 'q' + st.i;      // для пометки «с подсказкой» (tiles.js → q<i>_help)
      inp.setAttribute('form', 'test-form');
      var send = el('button', 'btn sc-ok', 'Ответить'); send.type = 'button';
      send.onclick = function () {
        if (!inp.value.trim()) { inp.focus(); return; }
        touched = true;
        var v = inp.value;
        inp.removeAttribute('name');                     // первый ответ уже в скрытом поле
        attempt(st, v, fb, function () { inp.select(); });
      };
      inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); send.click(); } });
      box.appendChild(inp);
      if (st.tiles && LT) {
        var host = el('div', 'lt');
        box.appendChild(host);
        box.appendChild(send);
        panel.appendChild(box);
        LT.attach(host, inp, st.answer, tilesOpen);
      } else box.appendChild(send);
    }
    box.appendChild(fb);
    if (!box.parentNode) panel.appendChild(box);
    if (!quiet) box.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  function next() {
    while (pos < STEPS.length) {
      var st = STEPS[pos];
      if (st.t === 'say') { bubble(st.who, st.en, st.ru, false); if (touched && !quiet) say(st.en); pos++; continue; }
      if (st.t === 'note') { noteRow(st.text); pos++; continue; }
      if (st.done) { bubble(null, answerText(st), '', true); pos++; continue; }    // «Исправь ошибки»: уже засчитан
      if (quiet && st.i in first) {                       // восстановление: ход уже сделан
        var v = first[st.i], right = isRight(st, v);
        if (right || (tries[st.i] || 0) >= 2) {
          bubble(null, right && st.type === 'type_in' ? v : answerText(st), '', true);
          if (!right) noteRow('Правильно так: ' + answerText(st));
          pos++; continue;
        }                                                 // ошибся раз и ушёл — вторая попытка ещё есть
      }
      ask(st);
      return;
    }
    panel.innerHTML = '';
    endBox.hidden = false;
    if (!quiet) endBox.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  window.LessonScene = {
    get: function () { return { pos: pos, first: first, tries: tries }; },
    set: function (s) {
      if (!s || typeof s !== 'object') return;
      root.innerHTML = ''; panel.innerHTML = ''; endBox.hidden = true;
      pos = 0; first = {}; tries = s.tries || {};
      quiet = true;
      Object.keys(s.first || {}).forEach(function (i) {
        var st = STEPS.filter(function (x) { return x.t === 'q' && String(x.i) === i; })[0];
        if (st) record(st, s.first[i]);
      });
      next();
      quiet = false;
    }
  };

  next();
})();
