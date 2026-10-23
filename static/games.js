/* Игры со словами: пары на время, мемори, блиц, «услышь и выбери», бег с препятствиями. Слова приходят с сервера. */
(function () {
  'use strict';
  var root = document.getElementById('game');
  if (!root) return;
  var game = root.dataset.game, duel = root.dataset.duel ? parseInt(root.dataset.duel, 10) : null, words = [], distract = [];
  try { words = JSON.parse(root.dataset.words || '[]'); distract = JSON.parse(root.dataset.distract || '[]'); } catch (e) { /* noop */ }

  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function say(t) { if (window.ttsSpeak) window.ttsSpeak(t); }
  function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ''; }
  function shuffle(a) { a = a.slice(); for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
  var finished = false;

  /* Конец игры: показываем итог, сохраняем звёзды и счёт (для рекордов и дуэлей), зовём компаньона */
  function end(stars, text, score) {
    if (finished) return;
    finished = true;
    root.parentNode.classList.add('hidden');
    var box = document.getElementById('game-end');
    box.classList.remove('hidden');
    document.getElementById('game-end-emoji').textContent = stars >= 3 ? '' : stars === 2 ? '' : stars === 1 ? '' : '';
    document.getElementById('game-end-text').textContent = text;
    document.getElementById('game-end-stars').textContent = '★'.repeat(stars) + '☆'.repeat(3 - stars);
    document.dispatchEvent(new CustomEvent('game:end', { detail: { stars: stars } }));
    fetch('/api/game', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() },
      body: JSON.stringify({ game: game, stars: stars, score: score, duel: duel })
    }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      if (j && j.message) { var rec = document.getElementById('game-end-record'); rec.textContent = j.message; rec.classList.remove('hidden'); }
      if (j && j.newAchievements && j.newAchievements.length) {
        setTimeout(function () { document.dispatchEvent(new CustomEvent('ach:new', { detail: { list: j.newAchievements } })); }, 1500);
      }
    }).catch(function () { /* noop */ });
  }

  /* ---------- ⚡ Найди пару ---------- */
  function pairs() {
    var set = shuffle(words).slice(0, 6), t0 = Date.now(), left = set.length, picked = null, mistakes = 0;
    var bar = el('div', 'g-bar', '<span><b id="g-time">0</b> с</span><span>Ошибок: <b id="g-err">0</b></span>');
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
            setTimeout(function () { end(stars, 'Время: ' + sec + ' с, ошибок: ' + mistakes + '.', sec); }, 500);
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
            setTimeout(function () { end(stars, 'Ходов: ' + moves + '.', moves); }, 900);
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
    var bar = el('div', 'g-bar', '<span><b id="g-left">60</b> с</span><span>Верно: <b id="g-score">0</b></span><span id="g-streak"></span>');
    var qbox = el('div', 'g-q'), opts = el('div', 'rv-opts');
    root.appendChild(bar); root.appendChild(qbox); root.appendChild(opts);
    var timer = setInterval(function () {
      left--; document.getElementById('g-left').textContent = left;
      if (left <= 0) { clearInterval(timer); stars(); }
    }, 1000);
    function stars() {
      var s = score >= 12 ? 3 : score >= 7 ? 2 : score >= 1 ? 1 : 0;
      end(s, 'Правильных ответов: ' + score + ', лучшая серия: ' + best + '.', score);
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
          document.getElementById('g-streak').textContent = streak >= 3 ? '' + streak : '';
          setTimeout(ask, ok ? 250 : 700);
        };
        opts.appendChild(b);
      });
    }
    ask();
  }

  /* ---------- 👂 Услышь и выбери ---------- */
  function listen() {
    var rounds = shuffle(words).slice(0, 8), pos = 0, score = 0, cur = null;
    var pics = words.concat(distract).filter(function (w) { return w.pic; });
    var bar = el('div', 'g-bar'), box = el('div', 'ls-box'), opts = el('div', 'ls-opts');
    var play = el('button', 'ls-play', '<svg class="ico" aria-hidden="true"><use href="#o-sound"/></svg>'); play.type = 'button'; play.title = 'Послушать ещё раз';
    play.onclick = function () { if (cur) say(cur.en); };
    box.appendChild(play); box.appendChild(el('p', 'ls-hint', 'Что ты услышал?'));
    root.appendChild(bar); root.appendChild(box); root.appendChild(opts);

    function ask() {
      if (pos >= rounds.length) {
        var st = score >= rounds.length - 1 ? 3 : score >= Math.ceil(rounds.length * 0.6) ? 2 : score >= 1 ? 1 : 0;
        end(st, 'Угадано: ' + score + ' из ' + rounds.length + '.', score); return;
      }
      cur = rounds[pos++];
      bar.innerHTML = '<span>Слово ' + pos + ' из ' + rounds.length + '</span><span>Верно: ' + score + '</span>';
      var picMode = !!cur.pic && pics.filter(function (w) { return w.pic !== cur.pic && w.key !== cur.key; }).length >= 3;
      var field = picMode ? 'pic' : 'ru', seen = {}, wrong = [];
      seen[cur[field]] = 1;
      shuffle(picMode ? pics : words.concat(distract)).forEach(function (w) {
        if (wrong.length < 3 && w.key !== cur.key && !seen[w[field]] && (picMode || w.ru.length > 3)) { seen[w[field]] = 1; wrong.push(w); }
      });
      opts.innerHTML = ''; opts.className = 'ls-opts' + (picMode ? ' pics' : '');
      shuffle(wrong.concat([cur])).forEach(function (o) {
        var b = el('button', picMode ? 'ls-opt pic' : 'rv-opt', esc(o[field])); b.type = 'button';
        b.onclick = function () {
          if (b.classList.contains('lock')) return;
          var ok = o.key === cur.key;
          [].forEach.call(opts.children, function (x) { x.classList.add('lock'); });
          b.classList.add(ok ? 'is-right' : 'is-wrong');
          if (ok) score++;
          box.querySelector('.ls-hint').innerHTML = (ok ? '' : '') + '<b>' + esc(cur.en) + '</b> — ' + esc(cur.ru);
          if (!ok) { var right = [].filter.call(opts.children, function (x) { return x.textContent === cur[field]; })[0]; if (right) right.classList.add('is-right'); }
          setTimeout(function () { box.querySelector('.ls-hint').textContent = 'Что ты услышал?'; ask(); }, ok ? 900 : 1600);
        };
        opts.appendChild(b);
      });
      setTimeout(function () { say(cur.en); }, 250);
    }
    ask();
  }

  /* ---------- 🏃 Бег с препятствиями ---------- */
  function runner() {
    var total = Math.min(10, words.length), seq = shuffle(words).slice(0, total), pos = 0, lives = 3, busy = false, anim = null, cur = null;
    var OBJ = ['🪨', '🌵', '🚧', '🌳', '🪵', '🧱'];
    var bar = el('div', 'g-bar'), stage = el('div', 'rn-stage'), opts = el('div', 'rv-opts');
    var hero = el('div', 'rn-hero', '🐥'), obs = el('div', 'rn-obs'), ground = el('div', 'rn-ground');
    stage.appendChild(el('div', 'rn-cloud', '☁️')); stage.appendChild(hero); stage.appendChild(obs); stage.appendChild(ground);
    root.appendChild(bar); root.appendChild(stage); root.appendChild(opts);

    function head() { bar.innerHTML = '<span>Препятствие ' + Math.min(pos, total) + ' из ' + total + '</span><span>' + '❤️'.repeat(lives) + '🖤'.repeat(3 - lives) + '</span>'; }
    function finish() {
      if (lives <= 0) { end(0, 'Цыплёнок споткнулся. Пройдено препятствий: ' + Math.max(pos - 1, 0) + ' из ' + total + '.', Math.max(pos - 1, 0)); return; }
      end(lives, 'Дистанция пройдена! Осталось жизней: ' + lives + '.', total);
    }
    function flash(cls) { hero.classList.remove('jump', 'oops'); void hero.offsetWidth; hero.classList.add(cls); }
    function resolve(ok) {
      if (busy) return; busy = true;
      if (anim) anim.pause();
      [].forEach.call(opts.children, function (x) { x.classList.add('lock'); });
      if (ok) { flash('jump'); obs.classList.add('gone'); } else { lives--; flash('oops'); obs.classList.add('hit'); }
      head();
      setTimeout(function () { if (lives <= 0 || pos >= total) finish(); else next(); }, ok ? 800 : 1200);
    }
    function next() {
      busy = false; cur = seq[pos++]; head();
      var wrong = shuffle(words.concat(distract).filter(function (w) { return w.key !== cur.key && w.ru !== cur.ru; })).slice(0, 2);
      obs.className = 'rn-obs';
      obs.innerHTML = '<div class="rn-sign">' + (cur.pic ? esc(cur.pic) + ' ' : '') + esc(cur.en) + '</div><div class="rn-obj">' + OBJ[Math.floor(Math.random() * OBJ.length)] + '</div>';
      opts.innerHTML = '';
      shuffle(wrong.concat([cur])).forEach(function (o) {
        var b = el('button', 'rv-opt', esc(o.ru)); b.type = 'button';
        b.onclick = function () {
          if (busy) return;
          var ok = o.key === cur.key;
          b.classList.add(ok ? 'is-right' : 'is-wrong');
          if (!ok) { var r = [].filter.call(opts.children, function (x) { return x.textContent === cur.ru; })[0]; if (r) r.classList.add('is-right'); }
          resolve(ok);
        };
        opts.appendChild(b);
      });
      say(cur.en);
      var W = stage.clientWidth, hx = hero.offsetLeft + hero.offsetWidth - 6, dur = Math.max(4500, 8500 - pos * 400);
      anim = obs.animate([{ transform: 'translateX(' + W + 'px)' }, { transform: 'translateX(' + hx + 'px)' }], { duration: dur, easing: 'linear', fill: 'forwards' });
      anim.onfinish = function () { if (!busy) resolve(false); };
    }
    next();
  }

  ({ pairs: pairs, memory: memory, blitz: blitz, listen: listen, runner: runner }[game] || function () {})();
})();
