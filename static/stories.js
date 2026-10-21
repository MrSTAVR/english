/* Истории: чтение с кликабельными словами, прослушивание и вопросы. */
(function () {
  'use strict';
  var root = document.getElementById('story');
  if (!root) return;
  var S = JSON.parse(root.dataset.story);
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function say(t, r) { if (window.ttsSpeak) window.ttsSpeak(t, r); }
  function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ''; }
  var listen = S.mode === 'listen', slow = false, playing = false;

  /* ---------- плеер ---------- */
  var player = el('div', 'card st-player');
  var playBtn = el('button', 'btn btn-primary', listen ? '▶ Слушать историю' : '🔊 Прочитать вслух'); playBtn.type = 'button';
  var slowLbl = el('label', 'st-slow', '<input type="checkbox"> 🐢 Помедленнее');
  slowLbl.querySelector('input').onchange = function (e) { slow = e.target.checked; };
  player.appendChild(playBtn); player.appendChild(slowLbl);
  if (listen) player.appendChild(el('p', 'st-hint', 'Текст спрятан — слушай внимательно, потом ответь на вопросы. Можно слушать сколько хочешь раз!'));
  else player.appendChild(el('p', 'st-hint', 'Нажми на любое слово, чтобы узнать перевод. Значок 🇷🇺 показывает перевод предложения.'));
  root.appendChild(player);

  /* ---------- текст ---------- */
  var text = el('div', 'card st-text' + (listen ? ' masked' : ''));
  var rows = [];
  S.sentences.forEach(function (sen, i) {
    var row = el('p', 'st-sen');
    sen.en.split(/(\s+)/).forEach(function (tok) {
      if (/^\s+$/.test(tok) || !tok) { row.appendChild(document.createTextNode(tok)); return; }
      var key = tok.toLowerCase().replace(/[^a-zé']/g, '');
      var w = el('span', 'st-w', esc(tok)); w.dataset.w = key;
      row.appendChild(w);
    });
    var tr = el('button', 'st-tr', '🇷🇺'); tr.type = 'button'; tr.title = 'Перевод предложения';
    var ru = el('span', 'st-ru hidden', esc(sen.ru));
    tr.onclick = function () { ru.classList.toggle('hidden'); };
    var sp = el('button', 'st-sp', '🔊'); sp.type = 'button'; sp.title = 'Послушать предложение';
    sp.onclick = function () { stop(); say(sen.en, slow ? 0.65 : 0.85); };
    row.appendChild(sp); row.appendChild(tr); row.appendChild(ru);
    text.appendChild(row); rows.push(row);
  });
  var pop = el('div', 'st-pop hidden');
  text.appendChild(pop);
  root.appendChild(text);
  if (listen) {
    var peek = el('button', 'btn btn-small', '👀 Показать текст'); peek.type = 'button';
    peek.onclick = function () { text.classList.remove('masked'); peek.remove(); };
    root.insertBefore(peek, text);
  }
  text.addEventListener('click', function (e) {
    var w = e.target.closest ? e.target.closest('.st-w') : null;
    if (!w || text.classList.contains('masked')) return;
    [].forEach.call(text.querySelectorAll('.st-w.on'), function (x) { x.classList.remove('on'); });
    w.classList.add('on');
    var key = w.dataset.w, tr = S.gloss[key] || '';
    pop.innerHTML = '<b>' + esc(w.textContent.replace(/[.,!?:;]/g, '')) + '</b> — ' + (tr ? esc(tr) : '<i>перевода нет</i>') + ' <button type="button" class="st-sp">🔊</button>';
    pop.querySelector('.st-sp').onclick = function () { say(w.textContent.replace(/[.,!?:;]/g, '')); };
    pop.classList.remove('hidden');
    say(w.textContent.replace(/[.,!?:;]/g, ''));
  });

  /* ---------- чтение вслух по предложениям ---------- */
  function stop() {
    if (window.ttsStop) window.ttsStop();
    playing = false; playBtn.textContent = listen ? '▶ Слушать историю' : '🔊 Прочитать вслух';
    rows.forEach(function (r) { r.classList.remove('now'); });
  }
  playBtn.onclick = function () {
    if (playing) { stop(); return; }
    playing = true; playBtn.textContent = '⏸ Стоп';
    window.ttsSpeakSeq(S.sentences.map(function (s) { return s.en; }), {
      rate: slow ? 0.65 : 0.85,
      onSentence: function (i) { rows.forEach(function (r, j) { r.classList.toggle('now', j === i && !listen); }); },
      onDone: stop
    });
  };

  /* ---------- вопросы ---------- */
  var box = el('div', 'card st-quiz');
  box.appendChild(el('h2', null, '❓ Проверь себя'));
  var qi = 0, correct = 0, saved = false;
  var area = el('div'); box.appendChild(area); root.appendChild(box);
  function ask() {
    area.innerHTML = '';
    if (qi >= S.questions.length) { finish(); return; }
    var q = S.questions[qi];
    area.appendChild(el('p', 'st-q', '<b>' + (qi + 1) + ' из ' + S.questions.length + '.</b> ' + esc(q.q)));
    var opts = el('div', 'rv-opts');
    var order = q.options.map(function (o, i) { return i; });
    for (var k = order.length - 1; k > 0; k--) { var r = Math.floor(Math.random() * (k + 1)); var t = order[k]; order[k] = order[r]; order[r] = t; }
    order.forEach(function (i) {
      var b = el('button', 'rv-opt', esc(q.options[i])); b.type = 'button';
      b.onclick = function () {
        if (b.classList.contains('lock')) return;
        [].forEach.call(opts.children, function (x) { x.classList.add('lock'); });
        var ok = i === q.answer;
        b.classList.add(ok ? 'is-right' : 'is-wrong');
        if (ok) correct++; else [].forEach.call(opts.children, function (x) { if (x.textContent === q.options[q.answer]) x.classList.add('is-right'); });
        setTimeout(function () { qi++; ask(); }, ok ? 700 : 1500);
      };
      opts.appendChild(b);
    });
    area.appendChild(opts);
  }
  function finish() {
    text.classList.remove('masked'); if (typeof peek !== 'undefined' && peek.parentNode) peek.remove();
    var total = S.questions.length;
    area.innerHTML = '<div class="rv-fb ok">🎉 Готово! Верных ответов: ' + correct + ' из ' + total + '.' + (correct === total ? ' Идеально!' : '') + '</div>';
    var again = el('a', 'btn btn-small btn-secondary', '🔁 Ещё раз'); again.href = location.href;
    var other = el('a', 'btn btn-small', listen ? '📖 Прочитать текст' : '🎧 Послушать на слух'); other.href = '?mode=' + (listen ? 'read' : 'listen');
    var back = el('a', 'btn btn-small btn-primary', 'Все истории ▶'); back.href = '/student/stories';
    area.appendChild(again); area.appendChild(document.createTextNode(' ')); area.appendChild(other); area.appendChild(document.createTextNode(' ')); area.appendChild(back);
    document.dispatchEvent(new CustomEvent('game:end', { detail: { stars: correct, story: true } }));
    if (saved) return; saved = true;
    fetch('/api/story', { method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() },
      body: JSON.stringify({ key: S.key, mode: S.mode, correct: correct }) })
      .then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
        if (!j) return;
        if (j.coins) area.insertBefore(el('p', 'st-coins', '+' + j.coins + ' 🪙 за первое прохождение!'), area.children[1]);
        if (j.newAchievements && j.newAchievements.length) {
          setTimeout(function () { document.dispatchEvent(new CustomEvent('ach:new', { detail: { list: j.newAchievements } })); }, 1200);
        }
      }).catch(function () { /* noop */ });
  }
  ask();
  window.addEventListener('pagehide', function () { if (window.ttsStop) window.ttsStop(); });
})();
