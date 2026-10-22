/* Письмо: «Собери предложение» (кубики-слова) и «Мини-диктант» (слушай и пиши). */
(function () {
  'use strict';
  var root = document.getElementById('write');
  if (!root) return;
  var mode = root.dataset.mode, items = [];
  try { items = JSON.parse(root.dataset.items || '[]'); } catch (e) { /* noop */ }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function say(t, r) { if (window.ttsSpeak) window.ttsSpeak(t, r); }
  function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ''; }
  function shuffle(a) { a = a.slice(); for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
  function norm(t) { return String(t).toLowerCase().replace(/[’`]/g, "'").replace(/[^a-z0-9' ]+/g, ' ').replace(/\s+/g, ' ').trim(); }
  function dist(a, b) {                                   // расстояние Левенштейна
    var m = a.length, n = b.length, d = [], i, j;
    for (i = 0; i <= m; i++) { d[i] = [i]; }
    for (j = 1; j <= n; j++) d[0][j] = j;
    for (i = 1; i <= m; i++) for (j = 1; j <= n; j++)
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    return d[m][n];
  }
  var finished = false, pos = 0, firstTry = 0, wrongWords = [];

  function end() {
    if (finished) return; finished = true;
    var n = items.length;
    var stars = firstTry >= n ? 3 : firstTry >= Math.ceil(n * 0.6) ? 2 : firstTry >= 1 ? 1 : 0;
    root.parentNode.classList.add('hidden');
    var box = document.getElementById('write-end'); box.classList.remove('hidden');
    document.getElementById('write-end-emoji').textContent = stars >= 3 ? '' : stars === 2 ? '' : stars === 1 ? '' : '';
    document.getElementById('write-end-text').textContent = (mode === 'build' ? 'Собрано с первой попытки: ' : 'Написано верно: ') + firstTry + ' из ' + n + '.';
    document.getElementById('write-end-stars').textContent = '★'.repeat(stars) + '☆'.repeat(3 - stars);
    var uniq = wrongWords.filter(function (w, i) { return wrongWords.indexOf(w) === i; });
    if (uniq.length) document.getElementById('write-end-wrong').innerHTML = '<p>Потренируем эти слова: <b>' + uniq.map(esc).join(', ') + '</b></p>';
    document.dispatchEvent(new CustomEvent('game:end', { detail: { stars: stars } }));
    fetch('/api/writing', { method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() },
      body: JSON.stringify({ mode: mode, stars: stars, wrong: uniq }) })
      .then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
        if (j && j.newAchievements && j.newAchievements.length) setTimeout(function () { document.dispatchEvent(new CustomEvent('ach:new', { detail: { list: j.newAchievements } })); }, 1500);
      }).catch(function () { /* noop */ });
  }

  /* ---------- 🧩 Собери предложение ---------- */
  function build() {
    var bar = el('div', 'g-bar'), pic = el('div', 'g-big'), ru = el('div', 'g-word'), line = el('div', 'wr-line'), bank = el('div', 'wr-bank'), fb = el('div', 'wr-fb'), acts = el('div', 'wr-acts');
    var check = el('button', 'btn btn-primary', 'Проверить'); check.type = 'button';
    var clear = el('button', 'btn btn-small', '↺ Сначала'); clear.type = 'button';
    var hear = el('button', 'btn btn-small', '<svg class="ico" aria-hidden="true"><use href="#o-sound"/></svg>'); hear.type = 'button'; hear.title = 'Послушать ответ';
    acts.appendChild(check); acts.appendChild(clear);
    [bar, pic, ru, line, bank, fb, acts].forEach(function (x) { root.appendChild(x); });
    var cur, words, placed, tries;
    function show() {
      bar.innerHTML = '<span>Фраза ' + (pos + 1) + ' из ' + items.length + '</span><span>С первой попытки: ' + firstTry + '</span>';
      pic.textContent = cur.pic || ''; ru.textContent = cur.ru; fb.textContent = '';
      words = shuffle(cur.en.split(/\s+/)); placed = [];
      if (words.join(' ') === cur.en.split(/\s+/).join(' ') && words.length > 2) words.reverse();
      render();
    }
    function render() {
      line.innerHTML = ''; bank.innerHTML = '';
      placed.forEach(function (i) {
        var b = el('button', 'wr-chip on', esc(words[i])); b.type = 'button';
        b.onclick = function () { placed.splice(placed.indexOf(i), 1); render(); };
        line.appendChild(b);
      });
      if (!placed.length) line.appendChild(el('span', 'wr-ph', 'Нажимай на слова ниже — они встанут сюда'));
      words.forEach(function (w, i) {
        if (placed.indexOf(i) !== -1) return;
        var b = el('button', 'wr-chip', esc(w)); b.type = 'button';
        b.onclick = function () { placed.push(i); render(); };
        bank.appendChild(b);
      });
    }
    function next() { pos++; if (pos >= items.length) { end(); return; } cur = items[pos]; tries = 0; show(); }
    clear.onclick = function () { placed = []; render(); };
    check.onclick = function () {
      if (check.disabled) return;
      var got = placed.map(function (i) { return words[i]; }).join(' ');
      if (placed.length < words.length) { fb.textContent = 'Поставь все слова'; return; }
      if (norm(got) === norm(cur.en)) {
        if (tries === 0) firstTry++;
        fb.innerHTML = '<b>' + esc(cur.en) + '</b>'; say(cur.en); check.disabled = true;
        setTimeout(function () { check.disabled = false; next(); }, 1500);
      } else {
        tries++; line.classList.add('shake'); setTimeout(function () { line.classList.remove('shake'); }, 400);
        if (tries >= 2) {
          fb.innerHTML = 'Правильно так: <b>' + esc(cur.en) + '</b>'; say(cur.en); check.disabled = true;
          cur.en.split(/\s+/).forEach(function (w) { wrongWords.push(norm(w)); });
          setTimeout(function () { check.disabled = false; next(); }, 2600);
        } else fb.textContent = 'Почти! Попробуй ещё раз';
      }
    };
    cur = items[0]; tries = 0; show();
  }

  /* ---------- ✍️ Мини-диктант ---------- */
  function dictation() {
    var bar = el('div', 'g-bar'), play = el('button', 'ls-play', '<svg class="ico" aria-hidden="true"><use href="#o-sound"/></svg>'), slow = el('label', 'st-slow', '<input type="checkbox"> Помедленнее');
    play.type = 'button';
    var ru = el('p', 'wr-ru'), input = el('input', 'wr-input'), fb = el('div', 'wr-fb'), acts = el('div', 'wr-acts');
    input.type = 'text'; input.autocomplete = 'off'; input.setAttribute('autocapitalize', 'off'); input.spellcheck = false; input.placeholder = 'Напиши предложение здесь';
    var check = el('button', 'btn btn-primary', 'Проверить'); check.type = 'button';
    acts.appendChild(check);
    var top = el('div', 'ls-box'); top.appendChild(play); top.appendChild(slow);
    [bar, top, ru, input, fb, acts].forEach(function (x) { root.appendChild(x); });
    var cur, attempt;
    function speak() { say(cur.en, slow.querySelector('input').checked ? 0.6 : 0.8); }
    play.onclick = speak;
    function show() {
      bar.innerHTML = '<span>Предложение ' + (pos + 1) + ' из ' + items.length + '</span><span>Верно: ' + firstTry + '</span>';
      ru.textContent = 'Подсказка по-русски: ' + cur.ru; input.value = ''; fb.textContent = ''; attempt = 0; input.disabled = false;
      setTimeout(function () { speak(); input.focus(); }, 300);
    }
    function next() { pos++; if (pos >= items.length) { end(); return; } cur = items[pos]; show(); }
    function diffHtml(want, got) {                          // слова из ответа: зелёные верные, красные ошибочные
      var g = norm(got).split(' '), pool = g.slice();
      return want.split(/\s+/).map(function (w) {
        var k = norm(w), i = pool.indexOf(k);
        if (i !== -1) { pool.splice(i, 1); return '<span class="wr-ok">' + esc(w) + '</span>'; }
        wrongWords.push(k); return '<span class="wr-bad">' + esc(w) + '</span>';
      }).join(' ');
    }
    function submit() {
      if (input.disabled) return;
      var got = input.value; if (!norm(got)) { fb.textContent = 'Напиши то, что услышал'; return; }
      var want = norm(cur.en), d = dist(norm(got), want);
      if (d === 0) { firstTry++; fb.innerHTML = 'Верно! <b>' + esc(cur.en) + '</b>'; done(1400); }
      else if (d <= 1 && want.length > 8) { firstTry++; fb.innerHTML = 'Почти без ошибок! Правильно: <b>' + esc(cur.en) + '</b>'; done(2200); }
      else {
        attempt++;
        if (attempt >= 2) { fb.innerHTML = 'Правильно так: ' + diffHtml(cur.en, got); done(3200); }
        else { fb.textContent = 'Не совсем. Послушай ещё раз и попробуй снова'; speak(); }
      }
    }
    function done(ms) { input.disabled = true; check.disabled = true; setTimeout(function () { check.disabled = false; next(); }, ms); }
    check.onclick = submit;
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') submit(); });
    cur = items[0]; show();
  }

  if (mode === 'build') build(); else dictation();
})();
