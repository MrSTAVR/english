/* Праздничный сезон (Хэллоуин, Новый год): озвучка карточек и викторина */
(function () {
  'use strict';
  function say(t) { if (window.ttsSpeak) window.ttsSpeak(t); }
  [].forEach.call(document.querySelectorAll('[data-say]'), function (b) { b.addEventListener('click', function () { say(b.dataset.say); }); });
  var root = document.getElementById('season-quiz'), host = document.getElementById('hw-quiz');
  if (!root || !host) return;
  var words = JSON.parse(root.dataset.words || '[]'), len = parseInt(root.dataset.len, 10) || 8, need = parseInt(root.dataset.pass, 10) || 6;
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ''; }
  function shuffle(a) { a = a.slice(); for (var k = a.length - 1; k > 0; k--) { var j = Math.floor(Math.random() * (k + 1)); var t = a[k]; a[k] = a[j]; a[j] = t; } return a; }
  var order = shuffle(words).slice(0, len), n = 0, ok = 0, locked = false;

  function next() {
    host.innerHTML = '';
    if (n >= order.length) return end();
    locked = false;
    var w = order[n], toRu = n % 2 === 0, good = toRu ? w.ru : w.en;
    var opts = [good];
    shuffle(words).forEach(function (d) { var t = toRu ? d.ru : d.en; if (opts.length < 4 && t !== good) opts.push(t); });
    host.appendChild(el('p', 'boss-q', '<span class="boss-pic">' + w.pic + '</span> <b>' + (toRu ? w.en : w.ru) + '</b> <small>(' + (n + 1) + '/' + order.length + ')</small>'));
    var grid = el('div', 'boss-opts');
    shuffle(opts).forEach(function (o) {
      var b = el('button', 'btn btn-secondary boss-opt', o); b.type = 'button';
      b.onclick = function () {
        if (locked) return; locked = true;
        if (o === good) { ok++; b.classList.add('ok'); } else { b.classList.add('bad'); }
        say(w.en);
        setTimeout(function () { n++; next(); }, 800);
      };
      grid.appendChild(b);
    });
    host.appendChild(grid);
  }

  function end() {
    var win = ok >= need;
    var msg = el('p', '', win ? root.dataset.win : 'Почти! Нужно ' + need + ' верных — попробуй ещё раз.');
    host.appendChild(el('div', 'big-emoji', win ? root.dataset.winEmoji : root.dataset.loseEmoji));
    host.appendChild(el('h3', '', 'Верно: ' + ok + ' из ' + order.length));
    host.appendChild(msg);
    var again = el('button', 'btn btn-primary', 'Ещё раз 🔁'); again.type = 'button'; again.onclick = function () { location.reload(); };
    host.appendChild(again);
    fetch(root.dataset.api, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() },
      body: JSON.stringify({ correct: ok })
    }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      if (!j) return;
      if (j.coins) msg.textContent += ' +' + j.coins + ' монетки!';
      if (j.newAchievements && j.newAchievements.length) {
        setTimeout(function () { document.dispatchEvent(new CustomEvent('ach:new', { detail: { list: j.newAchievements } })); }, 1200);
      }
    }).catch(function () { /* noop */ });
  }
  next();
})();
