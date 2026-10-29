/* Сцена истории вместо теста (scenes.py): реплики героев появляются по очереди и озвучиваются,
   ученица отвечает за себя. Новые слова урока — карточки под репликой (перевод по нажатию).
   Ход проверяется сразу: герой реагирует на ответ (ok / no), можно попробовать ещё раз, после двух ошибок
   показываем верный ответ и идём дальше. На сервер уходят первый ответ (q<i> / q<i>_order) и второй
   (q<i>_2 / q<i>_order_2 — полбалла). pick — выбор без правильного ответа ({ключ} в следующих репликах),
   speak — «скажи вслух» по желанию.
   window.LessonScene.get()/set() — место в сцене и ответы (для «продолжить урок с того же места»). */
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

  var pos = 0, first = {}, second = {}, tries = {}, picks = {}, touched = false, quiet = false, run = 0;

  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function say(t, slow) { if (window.ttsSpeak) window.ttsSpeak(t, slow ? 0.55 : null); }
  function changed() { document.dispatchEvent(new CustomEvent('lesson:changed')); }
  function ico(id) { return '<svg class="ico" aria-hidden="true"><use href="#' + id + '"/></svg>'; }
  function show(node) { root.appendChild(node); if (!quiet) node.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
  function pic(p) { return window.picHtml ? window.picHtml(p) : esc(p); }

  /* {ключ} — выбор ученицы из pick (в английском — v, в переводе — v_ru) */
  function fill(text, ru) {
    return String(text || '').replace(/\{(\w+)\}/g, function (m, k) {
      var st = STEPS.filter(function (x) { return x.t === 'pick' && x.key === k; })[0];
      var o = st && picks[k] != null ? st.options[picks[k]] : null;
      return o ? (ru ? o.v_ru : o.v) : m;
    });
  }

  function hidden(name, value) {
    var h = form.querySelector('input[type=hidden][name="' + name + '"]');
    if (!h) { h = el('input'); h.type = 'hidden'; h.name = name; form.appendChild(h); }
    h.value = value;
  }

  /* слова урока в реплике — жирным (одним проходом, длинные фразы первыми) */
  function highlight(text, hl) {
    var h = esc(text);
    if (!hl || !hl.length) return h;
    var alts = hl.slice().sort(function (a, b) { return b.length - a.length; }).map(function (k) {
      return esc(k).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    });
    return h.replace(new RegExp("(^|[^A-Za-z'])(" + alts.join('|') + ")(?![A-Za-z'])", 'gi'), '$1<b class="sc-w">$2</b>');
  }

  function bubble(who, en, ru, mine, opt) {
    opt = opt || {};
    var row = el('div', 'dlg-row ' + (mine ? 'me' : 'them') + (opt.wrong ? ' sc-wrong' : ''));
    var ava;
    if (mine) ava = '<div class="dlg-ava" aria-hidden="true">' + esc(me.emoji) + '</div>';
    else if (who.chick) ava = '<div class="dlg-ava sc-chick" aria-hidden="true">' + ico('i-chick') + '</div>';
    else ava = '<div class="dlg-ava" style="background:' + esc(who.bg) + '" aria-hidden="true">' + esc(who.pic) + '</div>';
    var name = mine ? me.name : who.name;
    var role = !mine && who.role ? ' <span class="dlg-role">· ' + esc(who.role) + '</span>' : '';
    var speak = /[A-Za-z]/.test(en) ? '<button type="button" class="dlg-say" title="Послушать" aria-label="Послушать">' + ico('o-sound') + '</button>' : '';
    var tr = ru ? '<button type="button" class="sc-tr" aria-expanded="false">перевод</button>' : '';
    var body = (opt.pic ? '<span class="sc-bpic">' + pic(opt.pic) + '</span> ' : '') + (mine ? esc(en) : highlight(en, opt.hl));
    row.innerHTML = ava + '<div class="dlg-main"><div class="dlg-name">' + esc(name) + role + '</div><div class="dlg-bubble">' +
      body + speak + tr + (ru ? '<div class="dlg-ru" hidden>' + esc(ru) + '</div>' : '') + '</div>' +
      (opt.words && opt.words.length ? wordsHtml(opt.words) : '') + '</div>';
    var b = row.querySelector('.dlg-say');
    if (b) b.onclick = function (e) { e.stopPropagation(); say(en); };
    var t = row.querySelector('.sc-tr');
    if (t) t.onclick = function () {
      var r = row.querySelector('.dlg-ru'); r.hidden = !r.hidden;
      t.setAttribute('aria-expanded', String(!r.hidden));
    };
    row.querySelectorAll('.sc-word').forEach(function (w) {
      w.onclick = function () { w.classList.add('is-open'); w.querySelector('.sc-word-ru').hidden = false; say(w.dataset.en); };
    });
    show(row);
  }

  /* знакомство с новыми словами урока: карточки под репликой, перевод по нажатию */
  function wordsHtml(words) {
    return '<div class="sc-words"><span class="sc-words-h">Новое слово — нажми:</span>' + words.map(function (w) {
      return '<button type="button" class="sc-word" data-en="' + esc(w.en) + '">' +
        (w.pic ? '<span class="sc-word-pic" aria-hidden="true">' + pic(w.pic) + '</span>' : '') +
        '<b lang="en">' + esc(w.en) + '</b><span class="sc-word-ru" hidden>' + esc(w.ru) + '</span></button>';
    }).join('') + '</div>';
  }

  function noteRow(text) { show(el('div', 'sc-note', esc(text))); }

  function heroLine(ln) { if (ln) bubble(ln.who, fill(ln.en), fill(ln.ru, true), false, { hl: ln.hl, words: ln.new }); }

  /* реплика прозвучала — идём дальше (без озвучки — пауза по длине) */
  function after(en, cb) {
    var token = run, done = false;
    function go() { if (!done && token === run) { done = true; cb(); } }
    if (touched && en && window.ttsSpeakSeq && window.ttsSpeakSeq([en], { onDone: function () { setTimeout(go, 200); } })) {
      setTimeout(go, 1500 + en.length * 110);            // страховка: голос мог не ответить
    } else setTimeout(go, Math.min(2200, 700 + (en || '').length * 25));
  }

  /* ---------- ход ученицы ---------- */
  function optText(st, k) {
    for (var j = 0; j < st.options.length; j++) if (+st.options[j][0] === +k) return st.options[j][1];
    return '';
  }
  function answerText(st) { return st.type === 'choice' ? optText(st, st.answer) : String(st.answer); }
  function shownText(st, v) { return st.type === 'choice' ? optText(st, v) : String(v); }
  function optPic(st, k) { return st.pics ? st.pics[String(k)] : ''; }
  function isRight(st, v) {
    if (st.type === 'choice') return +v === st.answer;
    if (!LT) return String(v).trim().toLowerCase() === String(st.answer).trim().toLowerCase();
    return LT.same(v, st.answer) || (st.type === 'type_in' && LT.near(v, st.answer));
  }
  function field(st, n) { return (st.type === 'order' ? 'q' + st.i + '_order' : 'q' + st.i) + (n === 2 ? '_2' : ''); }

  function record(st, v) {                       // первый ответ — на балл, второй — на полбалла
    if (!(st.i in first)) { first[st.i] = v; hidden(field(st, 1), v); }
    else if (!(st.i in second)) { second[st.i] = v; hidden(field(st, 2), v); }
  }

  function noReaction(st, v) {
    if (!st.no) return null;
    return st.no[String(v)] || st.no['*'] || null;
  }

  /* итог хода: ответ — пузырь справа, реакция героя, дальше по сюжету */
  function finishTurn(st, v, ok) {
    panel.innerHTML = '';
    var k = ok ? v : st.answer;
    bubble(null, ok && st.type !== 'choice' ? String(v) : answerText(st), '', true, { pic: st.type === 'choice' ? optPic(st, k) : '' });
    if (!ok) noteRow('Правильно так: ' + answerText(st) + (st.explain ? ' — ' + st.explain.replace(/^[^—]*—\s*/, '') : ''));
    else if (st.type === 'type_in' && LT && !LT.same(v, st.answer)) noteRow('Засчитано! Только пишется так: ' + st.answer);
    pos++;
    changed();
    if (quiet) { heroLine(st.ok); return; }
    if (st.ok) { heroLine(st.ok); after(fill(st.ok.en), next); } else setTimeout(next, 450);
  }

  function attempt(st, v, fb, onWrong) {
    record(st, v);
    tries[st.i] = (tries[st.i] || 0) + 1;
    if (isRight(st, v)) { finishTurn(st, v, true); return; }
    changed();
    if (tries[st.i] >= 2) { finishTurn(st, v, false); return; }
    var r = noReaction(st, v);
    if (onWrong) onWrong();
    if (r) {                                       // герой слышит неверный ответ и отвечает на него
      bubble(null, shownText(st, v), '', true, { wrong: true, pic: st.type === 'choice' ? optPic(st, v) : '' });
      heroLine(r);
      fb.className = 'rv-fb';
      fb.textContent = 'Попробуй ещё раз!';
      after(fill(r.en), function () { panel.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); });
    } else {
      fb.className = 'rv-fb bad';
      fb.textContent = 'Почти! Попробуй ещё раз.';
    }
  }

  function turnBox(text, review) {
    panel.innerHTML = '';
    var box = el('div', 'sc-turn');
    if (review) box.appendChild(el('p', 'sc-rev', ico('o-repeat') + ' Вспомни! Это из прошлых уроков'));
    box.appendChild(el('p', 'sc-q', '<b>Твой ход.</b> ' + esc(text)));
    return box;
  }
  function place(box) {
    if (!box.parentNode) panel.appendChild(box);
    if (!quiet) box.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  function ask(st) {
    var box = turnBox(st.q, st.review);
    if (st.audio) {
      var row = el('p', 'sc-audio');
      row.innerHTML = '<button type="button" class="btn btn-small say-btn">' + ico('o-sound') + ' Слушать</button> ' +
        '<button type="button" class="btn btn-small say-btn">' + ico('o-turtle') + ' Медленно</button>';
      var bs = row.querySelectorAll('button');
      bs[0].onclick = function () { say(st.audio); };
      bs[1].onclick = function () { say(st.audio, true); };
      box.appendChild(row);
      if (touched && !quiet) setTimeout(function () { say(st.audio); }, 300);
    }
    var fb = el('div', 'rv-fb');
    var wrongBefore = st.i in first && !(st.i in second) ? String(first[st.i]) : null;   // восстановление: одна ошибка уже была
    if (st.type === 'choice') {
      var opts = el('div', 'rv-opts' + (st.pics ? ' sc-pics' : ''));
      st.options.forEach(function (o) {
        var p = optPic(st, o[0]);
        var b = el('button', 'rv-opt' + (p ? ' sc-pic' : ''), p ? '<span aria-hidden="true">' + pic(p) + '</span>' : esc(o[1]));
        b.type = 'button';
        if (p) b.setAttribute('aria-label', 'Вариант');
        if (wrongBefore === String(o[0])) { b.classList.add('is-wrong'); b.disabled = true; }
        b.onclick = function () {
          touched = true;
          attempt(st, String(o[0]), fb, function () { b.classList.add('is-wrong'); b.disabled = true; });
        };
        opts.appendChild(b);
      });
      box.appendChild(opts);
    } else if (st.type === 'order') {
      var bank = el('div', 'word-bank'), line = el('div', 'answer-line');
      var ok = el('button', 'btn sc-ok', 'Ответить'); ok.type = 'button'; ok.disabled = true;
      var sync = function () { ok.disabled = !!bank.querySelector('.word-chip:not([hidden])'); };
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
        inp.removeAttribute('name');                     // ответ уже в скрытом поле
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
    if (wrongBefore !== null) { fb.className = 'rv-fb bad'; fb.textContent = 'Почти! Попробуй ещё раз.'; }
    box.appendChild(fb);
    place(box);
  }

  /* выбор без правильного ответа — дальше герои говорят о том, что выбрала ученица */
  function choose(st) {
    var box = turnBox(st.q), opts = el('div', 'rv-opts');
    st.options.forEach(function (o, k) {
      var b = el('button', 'rv-opt', '<b lang="en">' + esc(o.en) + '</b><small class="sc-opt-ru">' + esc(o.ru) + '</small>');
      b.type = 'button';
      b.onclick = function () {
        touched = true;
        picks[st.key] = k;
        panel.innerHTML = '';
        bubble(null, o.en, '', true);
        pos++;
        changed();
        after(o.en, next);
      };
      opts.appendChild(b);
    });
    box.appendChild(opts);
    place(box);
  }

  /* «скажи вслух» — по желанию, без оценки */
  function speakTurn(st) {
    var box = turnBox('Скажи вслух — Чик-чик слушает! Можно сначала послушать.');
    box.appendChild(el('p', 'sc-phrase', '<b lang="en">' + esc(st.en) + '</b><small>' + esc(st.ru) + '</small>'));
    var row = el('div', 'sc-speak-btns');
    row.innerHTML = '<button type="button" class="btn btn-small say-btn">' + ico('o-sound') + ' Послушать</button>' +
      '<button type="button" class="btn btn-primary">Я сказал(а)!</button>' +
      '<button type="button" class="btn btn-small btn-aux">Пропустить</button>';
    var bs = row.querySelectorAll('button');
    bs[0].onclick = function () { touched = true; say(st.en); };
    function done(said) {
      touched = true;
      panel.innerHTML = '';
      if (said) bubble(null, st.en, '', true);
      pos++;
      changed();
      setTimeout(next, 350);
    }
    bs[1].onclick = function () { done(true); };
    bs[2].onclick = function () { done(false); };
    box.appendChild(row);
    place(box);
  }

  /* ---------- ход истории ---------- */
  function next() {
    run++;
    while (pos < STEPS.length) {
      var st = STEPS[pos];
      if (st.t === 'say' || st.t === 'note') {
        if (st.t === 'say') bubble(st.who, fill(st.en), fill(st.ru, true), false, { hl: st.hl, words: st.new });
        else noteRow(fill(st.text, true));
        pos++;
        if (quiet) continue;
        changed();
        after(st.t === 'say' ? fill(st.en) : '', next);   // следующая реплика — когда прозвучит эта
        return;
      }
      if (st.t === 'pick') {
        if (quiet && picks[st.key] != null) { bubble(null, st.options[picks[st.key]].en, '', true); pos++; continue; }
        choose(st); return;
      }
      if (st.t === 'speak') { speakTurn(st); return; }
      if (st.done) { bubble(null, answerText(st), '', true); heroLine(st.ok); pos++; continue; }   // «Исправь ошибки»: уже засчитан
      ask(st);
      return;
    }
    panel.innerHTML = '';
    endBox.hidden = false;
    if (!quiet) endBox.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  /* восстановление: всё до сохранённого места показываем сразу, без озвучки */
  function replay(upto) {
    quiet = true;
    while (pos < upto && pos < STEPS.length) {
      var st = STEPS[pos];
      if (st.t === 'say') { bubble(st.who, fill(st.en), fill(st.ru, true), false, { hl: st.hl, words: st.new }); pos++; }
      else if (st.t === 'note') { noteRow(fill(st.text, true)); pos++; }
      else if (st.t === 'speak') pos++;
      else if (st.t === 'pick') {
        if (picks[st.key] == null) break;
        bubble(null, st.options[picks[st.key]].en, '', true); pos++;
      } else if (st.done) { bubble(null, answerText(st), '', true); heroLine(st.ok); pos++; }
      else {
        if (!(st.i in first) || (!isRight(st, first[st.i]) && !(st.i in second))) break;   // ход ещё не закончен
        var v = st.i in second ? second[st.i] : first[st.i];
        finishTurn(st, v, isRight(st, v));
      }
    }
    next();
    quiet = false;
  }

  function start() {
    panel.innerHTML = '';
    var b = el('button', 'btn btn-primary btn-big sc-start', ico('o-sound') + ' Начать историю');
    b.type = 'button';
    b.onclick = function () { touched = true; next(); };
    panel.appendChild(b);
  }

  window.LessonScene = {
    get: function () { return { pos: pos, first: first, second: second, tries: tries, picks: picks }; },
    set: function (s) {
      if (!s || typeof s !== 'object') return;
      run++;
      root.innerHTML = ''; panel.innerHTML = ''; endBox.hidden = true;
      pos = 0; first = {}; second = {}; tries = s.tries || {}; picks = s.picks || {};
      Object.keys(s.first || {}).forEach(function (i) {
        var st = STEPS.filter(function (x) { return x.t === 'q' && String(x.i) === i; })[0];
        if (!st) return;
        record(st, s.first[i]);
        if (s.second && i in s.second) record(st, s.second[i]);
      });
      if (!(+s.pos) && !Object.keys(first).length) { start(); return; }   // историю ещё не начинали
      replay(+s.pos || 0);
    }
  };

  start();
})();
