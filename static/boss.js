/* Босс недели: отвечай на вопросы, каждый верный ответ бьёт босса. */
(function () {
  'use strict';
  var root = document.getElementById('boss');
  if (!root) return;
  var words = [], distract = [];
  try { words = JSON.parse(root.dataset.words || '[]'); distract = JSON.parse(root.dataset.distract || '[]'); } catch (e) { /* noop */ }
  var lives = parseInt(root.dataset.lives, 10) || 3, maxLives = lives;
  var emoji = root.dataset.emoji, name = root.dataset.name;
  var hp = words.length, maxHp = hp, i = 0, locked = false;

  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ''; }
  function shuffle(a) { a = a.slice(); for (var k = a.length - 1; k > 0; k--) { var j = Math.floor(Math.random() * (k + 1)); var t = a[k]; a[k] = a[j]; a[j] = t; } return a; }

  var head = el('div', 'boss-head');
  var bossBox = el('div', 'boss-fighter', '<span class="boss-big">' + emoji + '</span>');
  var hpBar = el('div', 'goal-bar boss-hp'); var hpFill = el('i'); hpBar.appendChild(hpFill);
  var livesBox = el('div', 'boss-lives');
  head.appendChild(bossBox); head.appendChild(hpBar); head.appendChild(livesBox);
  var body = el('div', 'boss-body');
  root.appendChild(head); root.appendChild(body);

  function paint() {
    hpFill.style.width = (100 * hp / maxHp) + '%';
    livesBox.textContent = '❤️'.repeat(lives) + '🖤'.repeat(maxLives - lives);
  }

  function question() {
    if (hp <= 0) return finish(true);
    if (lives <= 0) return finish(false);
    locked = false;
    var w = words[i % words.length];
    var toRu = Math.random() < 0.5;
    var good = toRu ? w.ru : w.en;
    var pool = shuffle(distract.filter(function (d) { return d.key !== w.key && (toRu ? d.ru : d.en) !== good; }));
    var seen = {}; seen[good] = 1; var opts = [good];
    pool.forEach(function (d) { var t = toRu ? d.ru : d.en; if (opts.length < 4 && t && !seen[t]) { seen[t] = 1; opts.push(t); } });
    opts = shuffle(opts);
    body.innerHTML = '';
    body.appendChild(el('div', 'boss-q', (w.pic ? '<span class="boss-pic">' + esc(w.pic) + '</span> ' : '') + (toRu ? '<b>' + esc(w.en) + '</b>' : '<b>' + esc(w.ru) + '</b>')));
    var grid = el('div', 'boss-opts');
    opts.forEach(function (o) {
      var b = el('button', 'btn btn-secondary boss-opt', esc(o)); b.type = 'button';
      b.onclick = function () {
        if (locked) return; locked = true;
        if (o === good) { b.classList.add('ok'); hp--; bossBox.classList.add('hit'); }
        else { b.classList.add('bad'); lives--; bossBox.classList.add('laugh'); }
        paint();
        setTimeout(function () { bossBox.classList.remove('hit', 'laugh'); i++; question(); }, 700);
      };
      grid.appendChild(b);
    });
    body.appendChild(grid);
  }

  function finish(win) {
    body.innerHTML = '';
    var box = el('div', 'boss-end', '<div class="big-emoji">' + (win ? '🏆' : '💪') + '</div><h2>' + (win ? 'Победа! ' + esc(name) + ' повержен!' : 'Босс устоял...') + '</h2>');
    var msg = el('p', '', win ? 'Ты справился!' : 'Ничего, попробуй ещё раз — слова уже знакомые!');
    box.appendChild(msg);
    var again = el('a', 'btn btn-primary', win ? '⬅ К челленджу' : 'Ещё раз 🔁'); again.href = win ? '/student/weekly' : '/student/boss';
    box.appendChild(again);
    body.appendChild(box);
    if (win) document.dispatchEvent(new CustomEvent('game:end', { detail: { stars: 3 } }));
    fetch('/api/boss', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() },
      body: JSON.stringify({ win: win })
    }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      if (!j) return;
      var extra = [];
      if (j.coins) extra.push('+' + j.coins + ' монеток');
      (j.items || []).forEach(function (n) { extra.push('🎁 новый наряд: ' + n); });
      if (extra.length) msg.textContent = extra.join(' · ');
      if (j.newAchievements && j.newAchievements.length) {
        setTimeout(function () { document.dispatchEvent(new CustomEvent('ach:new', { detail: { list: j.newAchievements } })); }, 1200);
      }
    }).catch(function () { /* noop */ });
  }

  paint();
  question();
})();
