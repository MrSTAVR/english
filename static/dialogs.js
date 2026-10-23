/* Мини-диалоги: партнёр говорит, ученик выбирает ответ. Завершённый диалог сохраняется на сервере.
   window.LessonDialogs.get()/set() — место в каждом диалоге (для «продолжить урок с того же места»). */
(function () {
  'use strict';
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function say(t) { if (window.ttsSpeak) window.ttsSpeak(t); }
  function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ''; }

  var REG = {};                                         // key → {get, set}
  function changed() { document.dispatchEvent(new CustomEvent('lesson:changed')); }
  window.LessonDialogs = {
    get: function () { var o = {}; Object.keys(REG).forEach(function (k) { var s = REG[k].get(); if (s.idx > 0) o[k] = s; }); return o; },
    set: function (all) { Object.keys(all || {}).forEach(function (k) { if (REG[k]) REG[k].set(all[k]); }); }
  };

  function save(key) {
    return fetch('/api/dialog', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() },
      body: JSON.stringify({ key: key })
    }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
  }

  function build(d, me) {
    var card = el('section', 'card dlg');
    card.appendChild(el('h2', 'dlg-title', '<span class="dlg-ava big" style="background:' + d.who.bg + '">' + esc(d.who.pic) + '</span> ' + esc(d.title) + (d.done ? ' <span class="pill pill-soft">пройден</span>' : '')));
    var chat = el('div', 'dlg-chat'), panel = el('div', 'dlg-panel');
    card.appendChild(chat); card.appendChild(panel);
    var idx = 0, mistakes = 0, touched = false, finished = false;

    function bubble(who, en, ru, mine, quiet) {
      var b = el('div', 'dlg-row ' + (mine ? 'me' : 'them'));
      var pic = mine ? me.emoji : d.who.pic, bg = mine ? '#e3d9ff' : d.who.bg;
      var role = !mine && d.who.role ? ' <span class="dlg-role">· ' + esc(d.who.role) + '</span>' : '';
      b.innerHTML = '<div class="dlg-ava' + '" style="background:' + bg + '" aria-hidden="true">' + esc(pic) + '</div>' +
        '<div class="dlg-main"><div class="dlg-name">' + esc(who) + role + '</div><div class="dlg-bubble">' + esc(en) +
        '<button type="button" class="dlg-say" title="Послушать" aria-label="Послушать"><svg class="ico" aria-hidden="true"><use href="#o-sound"/></svg></button><div class="dlg-ru">' + esc(ru) + '</div></div></div>';
      b.querySelector('.dlg-say').onclick = function () { say(en); };
      chat.appendChild(b);
      if (!quiet) b.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }

    function next(quiet) {
      panel.innerHTML = '';
      while (idx < d.lines.length && !d.lines[idx].options) {
        var ln = d.lines[idx++];
        bubble(d.partner, ln.en, ln.ru, false, quiet);
        if (touched && !quiet) say(ln.en);
      }
      if (idx >= d.lines.length) { finish(quiet); return; }
      var turn = d.lines[idx];
      panel.appendChild(el('p', 'dlg-hint', 'Выбери свой ответ:'));
      var opts = el('div', 'rv-opts');
      var order = turn.options.map(function (o, i) { return i; });
      for (var k = order.length - 1; k > 0; k--) { var r = Math.floor(Math.random() * (k + 1)); var t = order[k]; order[k] = order[r]; order[r] = t; }
      order.forEach(function (i) {
        var o = turn.options[i];
        var b = el('button', 'rv-opt', esc(o)); b.type = 'button';
        b.onclick = function () {
          if (i !== turn.answer) { b.classList.add('is-wrong'); b.disabled = true; mistakes++; changed(); return; }
          touched = true; bubble(me.name, o, turn.ru, true);
          idx++;
          changed();
          setTimeout(function () { next(); changed(); }, 450);
        };
        opts.appendChild(b);
      });
      panel.appendChild(opts);
    }

    function finish(quiet) {
      finished = true;
      panel.innerHTML = '<div class="rv-fb ok">Диалог пройден!' + (mistakes ? ' Ошибок: ' + mistakes + '.' : ' Без единой ошибки!') + '</div>';
      var again = el('button', 'btn btn-small btn-aux', '<svg class="ico" aria-hidden="true"><use href="#o-repeat"/></svg> Пройти ещё раз'); again.type = 'button';
      again.onclick = function () { chat.innerHTML = ''; idx = 0; mistakes = 0; touched = true; finished = false; next(); changed(); };
      panel.appendChild(again);
      if (quiet) return;                                // восстановление: награды и сохранение уже были
      document.dispatchEvent(new CustomEvent('game:end', { detail: { stars: mistakes === 0 ? 3 : 2, dialog: true } }));
      save(d.key).then(function (j) {
        if (j && j.newAchievements && j.newAchievements.length) {
          setTimeout(function () { document.dispatchEvent(new CustomEvent('ach:new', { detail: { list: j.newAchievements } })); }, 1200);
        }
      });
    }
    REG[d.key] = {
      get: function () { return { idx: idx, mistakes: mistakes, fin: finished }; },
      set: function (s) {                                 // проигрываем пройденные реплики без звука и прокрутки
        if (!s || !(s.idx > 0)) return;
        chat.innerHTML = ''; idx = 0; mistakes = s.mistakes | 0; touched = true; finished = false;
        var upto = Math.min(s.idx | 0, d.lines.length);
        while (idx < upto) {
          var ln = d.lines[idx];
          if (ln.options) bubble(me.name, ln.options[ln.answer], ln.ru, true, true);
          else bubble(d.partner, ln.en, ln.ru, false, true);
          idx++;
        }
        next(true);
      }
    };
    next();
    return card;
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('#dialogs, .lesson-dialogs').forEach(function (host) {
      var list = [];
      try { list = JSON.parse(host.dataset.dialogs || '[]'); } catch (e) { /* noop */ }
      var me = { emoji: host.dataset.meEmoji || '🎒', name: host.dataset.meName || 'Я' };
      list.forEach(function (d) { host.appendChild(build(d, me)); });
    });
  });
})();
