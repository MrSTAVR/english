/* Игры со словами: пары на время, мемори, блиц, виселица. Слова приходят с сервера. */
(function () {
  'use strict';
  var root = document.getElementById('game');
  if (!root) return;
  var game = root.dataset.game, words = [], distract = [];
  try { words = JSON.parse(root.dataset.words || '[]'); distract = JSON.parse(root.dataset.distract || '[]'); } catch (e) { /* noop */ }

  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function say(t) { if (window.ttsSpeak) window.ttsSpeak(t); }
  function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ''; }
  function shuffle(a) { a = a.slice(); for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
  var finished = false;

  /* Конец игры: показываем итог, сохраняем звёзды, зовём компаньона */
  function end(stars, text) {
    if (finished) return;
    finished = true;
    root.parentNode.classList.add('hidden');
    var box = document.getElementById('game-end');
    box.classList.remove('hidden');
    document.getElementById('game-end-emoji').textContent = stars >= 3 ? '🏆' : stars === 2 ? '🏅' : stars === 1 ? '👍' : '💪';
    document.getElementById('game-end-text').textContent = text;
    document.getElementById('game-end-stars').textContent = '⭐'.repeat(stars) + '☆'.repeat(3 - stars);
    document.dispatchEvent(new CustomEvent('game:end', { detail: { stars: stars } }));
    fetch('/api/game', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() },
      body: JSON.stringify({ game: game, stars: stars })
    }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      if (j && j.newAchievements && j.newAchievements.length) {
        setTimeout(function () { document.dispatchEvent(new CustomEvent('ach:new', { detail: { list: j.newAchievements } })); }, 1500);
      }
    }).catch(function () { /* noop */ });
  }

  /* ---------- ⚡ Найди пару ---------- */
  function pairs() {
    var set = shuffle(words).slice(0, 6), t0 = Date.now(), left = set.length, picked = null, mistakes = 0;
    var bar = el('div', 'g-bar', '<span>⏱ <b id="g-time">0</b> с</span><span>Ошибок: <b id="g-err">0</b></span>');
    var cols = el('div', 'g-pairs');
    var colA = el('div', 'g-col'), colB = el('div', 'g-col');
    cols.appendChild(colA); cols.appendChild(colB);
    root.appendChild(bar); root.appendChild(cols);
    var timer = setInterval(function () { document.getElementById('g-time').textContent = Math.round((Date.now() - t0) / 1000); }, 500);

    function tile(w, side) {
      var b = el('button', 'g-tile', side === 'en' ? esc(w.en) : esc(w.ru)); b.type = 'button';
      b.dataset.key = w.key;
      b.onclick = function () {
        if (b.classList.contains('gone')) return;
        if (side === 'en') say(w.en);
        if (!picked) { picked = { b: b, side: side }; b.classList.add('sel'); return; }
        if (picked.b === b) { b.classList.remove('sel'); picked = null; return; }
        if (picked.side === side) { picked.b.classList.remove('sel'); picked = { b: b, side: side }; b.classList.add('sel'); return; }
        var a = picked.b; picked = null; a.classList.remove('sel');
        if (a.dataset.key === b.dataset.key) {
          a.classList.add('gone'); b.classList.add('gone'); left--;
          if (!left) {
            clearInterval(timer);
            var sec = Math.round((Date.now() - t0) / 1000), n = set.length;
            var stars = (sec <= n * 5 && mistakes <= 1) ? 3 : sec <= n * 9 ? 2 : 1;
            setTimeout(function () { end(stars, 'Время: ' + sec + ' с, ошибок: ' + mistakes + '.'); }, 500);
          }
        } else {
          mistakes++; document.getElementById('g-err').textContent = mistakes;
          [a, b].forEach(function (x) { x.classList.add('shake'); setTimeout(function () { x.classList.remove('shake'); }, 400); });
        }
      };
      return b;
    }
    shuffle(set).forEach(function (w) { colA.appendChild(tile(w, 'en')); });
    shuffle(set).forEach(function (w) { colB.appendChild(tile(w, 'ru')); });
  }

  /* ---------- 🃏 Мемори ---------- */
  function memory() {
    var withPic = words.filter(function (w) { return w.pic; });
    var usePic = withPic.length >= 4;
    var set = shuffle(usePic ? withPic : words).slice(0, 6), moves = 0, open = [], left = set.length, lock = false;
    var cards = [];
    set.forEach(function (w) {
      cards.push({ key: w.key, w: w, face: usePic ? '<span class="g-big">' + esc(w.pic) + '</span>' : esc(w.ru) });
      cards.push({ key: w.key, w: w, face: '<b>' + esc(w.en) + '</b>' });
    });
    root.appendChild(el('div', 'g-bar', '<span>Ходов: <b id="g-moves">0</b></span><span>' + (usePic ? 'Картинка ↔ слово' : 'Слово ↔ перевод') + '</span>'));
    var grid = el('div', 'g-mem');
    shuffle(cards).forEach(function (c) {
      var b = el('button', 'g-card', '<span class="g-back">?</span><span class="g-face">' + c.face + '</span>'); b.type = 'button';
      b.onclick = function () {
        if (lock || b.classList.contains('open') || b.classList.contains('gone')) return;
        b.classList.add('open'); open.push({ b: b, c: c });
        if (open.length < 2) return;
        moves++; document.getElementById('g-moves').textContent = moves;
        var x = open[0], y = open[1]; open = [];
        if (x.c.key === y.c.key) {
          say(x.c.w.en);
          setTimeout(function () { x.b.classList.add('gone'); y.b.classList.add('gone'); }, 350);
          left--;
          if (!left) {
            var n = set.length, stars = moves <= n * 1.6 ? 3 : moves <= n * 2.6 ? 2 : 1;
            setTimeout(function () { end(stars, 'Ходов: ' + moves + '.'); }, 900);
          }
        } else {
          lock = true;
          setTimeout(function () { x.b.classList.remove('open'); y.b.classList.remove('open'); lock = false; }, 900);
        }
      };
      grid.appendChild(b);
    });
    root.appendChild(grid);
  }

  /* ---------- ⏱️ Блиц 60 секунд ---------- */
  function blitz() {
    var left = 60, score = 0, streak = 0, best = 0, cur = null, order = shuffle(words), pos = 0;
    var bar = el('div', 'g-bar', '<span>⏱ <b id="g-left">60</b> с</span><span>Верно: <b id="g-score">0</b></span><span id="g-streak"></span>');
    var qbox = el('div', 'g-q'), opts = el('div', 'rv-opts');
    root.appendChild(bar); root.appendChild(qbox); root.appendChild(opts);
    var timer = setInterval(function () {
      left--; document.getElementById('g-left').textContent = left;
      if (left <= 0) { clearInterval(timer); stars(); }
    }, 1000);
    function stars() {
      var s = score >= 12 ? 3 : score >= 7 ? 2 : score >= 1 ? 1 : 0;
      end(s, 'Правильных ответов: ' + score + ', лучшая серия: ' + best + '.');
    }
    function ask() {
      if (finished) return;
      if (pos >= order.length) { order = shuffle(words); pos = 0; }
      cur = order[pos++];
      var toRu = Math.random() < 0.6, pool = words.concat(distract);
      var field = toRu ? 'ru' : 'en';
      var wrong = shuffle(pool.filter(function (w) { return w.key !== cur.key && w[field] !== cur[field]; })).slice(0, 3);
      var options = shuffle(wrong.concat([cur]));
      qbox.innerHTML = (cur.pic && toRu ? '<div class="g-big">' + esc(cur.pic) + '</div>' : '') +
        '<div class="g-word">' + esc(toRu ? cur.en : cur.ru) + '</div>';
      if (toRu) say(cur.en);
      opts.innerHTML = '';
      options.forEach(function (o) {
        var b = el('button', 'rv-opt', esc(o[field])); b.type = 'button';
        b.onclick = function () {
          if (finished || b.classList.contains('lock')) return;
          var ok = o.key === cur.key;
          [].forEach.call(opts.children, function (x) { x.classList.add('lock'); });
          b.classList.add(ok ? 'is-right' : 'is-wrong');
          if (ok) { score++; streak++; best = Math.max(best, streak); } else { streak = 0; }
          document.getElementById('g-score').textContent = score;
          document.getElementById('g-streak').textContent = streak >= 3 ? '🔥 ' + streak : '';
          setTimeout(ask, ok ? 250 : 700);
        };
        opts.appendChild(b);
      });
    }
    ask();
  }

  /* ---------- 🔤 Виселица ---------- */
  function hangman() {
    var cand = shuffle(words.filter(function (w) { return /^[a-z]{3,9}$/i.test(w.en); })).slice(0, 5);
    if (cand.length < 2) { root.innerHTML = '<p>Для этой игры в твоих словах мало подходящих слов — пройди ещё уроки 🌱</p>'; return; }
    var round = 0, won = 0, lives, word, shown, used;
    var ALPHA = 'abcdefghijklmnopqrstuvwxyz'.split('');
    var head = el('div', 'g-bar'), pic = el('div', 'g-big'), ruEl = el('div', 'g-word'), mask = el('div', 'g-mask'), kb = el('div', 'g-kb');
    root.appendChild(head); root.appendChild(pic); root.appendChild(ruEl); root.appendChild(mask); root.appendChild(kb);

    function start() {
      if (round >= cand.length) { var s = won >= cand.length ? 3 : won >= Math.ceil(cand.length / 2) ? 2 : won >= 1 ? 1 : 0; end(s, 'Угадано слов: ' + won + ' из ' + cand.length + '.'); return; }
      var w = cand[round]; word = w.en.toLowerCase(); lives = 6; used = {};
      pic.textContent = w.pic || '❓'; ruEl.textContent = w.ru;
      draw(); keys();
    }
    function draw() {
      head.innerHTML = '<span>Слово ' + (round + 1) + ' из ' + cand.length + '</span><span>' + '❤️'.repeat(lives) + '🖤'.repeat(6 - lives) + '</span>';
      mask.textContent = word.split('').map(function (c) { return used[c] ? c.toUpperCase() : '_'; }).join(' ');
    }
    function keys() {
      kb.innerHTML = '';
      ALPHA.forEach(function (c) {
        var b = el('button', 'g-key', c.toUpperCase()); b.type = 'button';
        b.onclick = function () {
          if (used[c] || finished) return;
          used[c] = true; b.disabled = true;
          if (word.indexOf(c) === -1) { lives--; b.classList.add('bad'); } else b.classList.add('good');
          draw();
          var all = word.split('').every(function (x) { return used[x]; });
          if (all || lives <= 0) {
            if (all) { won++; say(word); } else { mask.textContent = word.toUpperCase().split('').join(' '); }
            [].forEach.call(kb.children, function (x) { x.disabled = true; });
            setTimeout(function () { round++; start(); }, all ? 1100 : 1800);
          }
        };
        kb.appendChild(b);
      });
    }
    start();
  }

  ({ pairs: pairs, memory: memory, blitz: blitz, hangman: hangman }[game] || function () {})();
})();
