/* Мини-диалоги: партнёр говорит, ученик выбирает ответ. Завершённый диалог сохраняется на сервере. */
(function () {
  'use strict';
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function say(t) { if (window.ttsSpeak) window.ttsSpeak(t); }
  function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ''; }

  function save(key) {
    return fetch('/api/dialog', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() },
      body: JSON.stringify({ key: key })
    }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
  }

  function build(d) {
    var card = el('section', 'card dlg');
    card.appendChild(el('h2', null, '💬 ' + esc(d.title) + (d.done ? ' <span class="pill pill-soft">пройден ✅</span>' : '')));
    var chat = el('div', 'dlg-chat'), panel = el('div', 'dlg-panel');
    card.appendChild(chat); card.appendChild(panel);
    var idx = 0, mistakes = 0;

    function bubble(who, en, ru, mine) {
      var b = el('div', 'dlg-row ' + (mine ? 'me' : 'them'));
      b.innerHTML = '<div class="dlg-name">' + esc(who) + '</div><div class="dlg-bubble">' + esc(en) +
        '<button type="button" class="dlg-say" title="Послушать">🔊</button><div class="dlg-ru">' + esc(ru) + '</div></div>';
      b.querySelector('.dlg-say').onclick = function () { say(en); };
      chat.appendChild(b);
      b.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }

    function next() {
      panel.innerHTML = '';
      while (idx < d.lines.length && !d.lines[idx].options) {
        var ln = d.lines[idx++];
        bubble(d.partner, ln.en, ln.ru, false);
        if (idx === 1) say(ln.en);
      }
      if (idx >= d.lines.length) { finish(); return; }
      var turn = d.lines[idx];
      panel.appendChild(el('p', 'dlg-hint', 'Выбери свой ответ:'));
      var opts = el('div', 'rv-opts');
      var order = turn.options.map(function (o, i) { return i; });
      for (var k = order.length - 1; k > 0; k--) { var r = Math.floor(Math.random() * (k + 1)); var t = order[k]; order[k] = order[r]; order[r] = t; }
      order.forEach(function (i) {
        var o = turn.options[i];
        var b = el('button', 'rv-opt', esc(o)); b.type = 'button';
        b.onclick = function () {
          if (i !== turn.answer) { b.classList.add('is-wrong'); b.disabled = true; mistakes++; return; }
          bubble('Я', o, turn.ru, true);
          idx++;
          setTimeout(next, 450);
        };
        opts.appendChild(b);
      });
      panel.appendChild(opts);
    }

    function finish() {
      panel.innerHTML = '<div class="rv-fb ok">🎉 Диалог пройден!' + (mistakes ? ' Ошибок: ' + mistakes + '.' : ' Без единой ошибки!') + '</div>';
      var again = el('button', 'btn btn-small', 'Пройти ещё раз 🔁'); again.type = 'button';
      again.onclick = function () { chat.innerHTML = ''; idx = 0; mistakes = 0; next(); };
      panel.appendChild(again);
      document.dispatchEvent(new CustomEvent('game:end', { detail: { stars: mistakes === 0 ? 3 : 2, dialog: true } }));
      save(d.key).then(function (j) {
        if (j && j.newAchievements && j.newAchievements.length) {
          setTimeout(function () { document.dispatchEvent(new CustomEvent('ach:new', { detail: { list: j.newAchievements } })); }, 1200);
        }
      });
    }
    next();
    return card;
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('#dialogs, .lesson-dialogs').forEach(function (host) {
      var list = [];
      try { list = JSON.parse(host.dataset.dialogs || '[]'); } catch (e) { /* noop */ }
      list.forEach(function (d) { host.appendChild(build(d)); });
    });
  });
})();
