/* Раунд повторения: по одному заданию, сразу проверка, ответ уходит на сервер (Лейтнер). */
(function () {
  'use strict';
  var stage = document.getElementById('rv-stage');
  if (!stage) return;
  var items = [];
  try { items = JSON.parse(stage.dataset.items || '[]'); } catch (e) { /* noop */ }
  var idx = 0, okCount = 0, learned = 0;

  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function norm(s) { return String(s || '').toLowerCase().replace(/’/g, "'").replace(/\s+/g, ' ').trim().replace(/^[ .!?,;:]+|[ .!?,;:]+$/g, ''); }
  function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ''; }
  function say(t, slow) { if (window.ttsSpeak) window.ttsSpeak(t, slow ? 0.5 : undefined); }

  function send(item, ok) {
    return fetch('/api/review', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() },
      body: JSON.stringify({ key: item.key, ok: ok })
    }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
  }

  function finishAnswer(box, item, ok, correctText) {
    if (ok) okCount++;
    box.classList.add('answered', ok ? 'right' : 'wrong');
    var fb = el('div', 'rv-fb ' + (ok ? 'ok' : 'bad'),
      (ok ? 'Верно!' : 'Правильно: <b>' + esc(correctText) + '</b>') +
      '<div class="rv-explain">' + esc(item.explain || '') + '</div>');
    box.appendChild(fb);
    // после ответа всегда можно услышать английское слово (и оно озвучивается само)
    var hearEn = el('div', 'rv-sayline', '<span class="rv-pic">' + picHtml(item.pic) + '</span><button type="button" class="btn btn-small"><svg class="ico" aria-hidden="true"><use href="#o-sound"/></svg> ' + esc(item.en) + '</button><span class="rv-hint">[' + esc(item.hint || '') + ']</span>');
    hearEn.querySelector('button').onclick = function () { say(item.en); };
    box.appendChild(hearEn);
    setTimeout(function () { say(item.en); }, 350);
    document.dispatchEvent(new CustomEvent('review:answer', { detail: { ok: ok } }));
    send(item, ok).then(function (j) {
      if (!j) return;
      if (j.learned && ok && item.box < 4) learned++;
      if (j.goalDone) document.dispatchEvent(new CustomEvent('review:goal', { detail: { coins: j.goalCoins } }));
      if (j.newAchievements && j.newAchievements.length) {
        setTimeout(function () {
          document.dispatchEvent(new CustomEvent('review:achievements', { detail: { list: j.newAchievements } }));
        }, 1200);
      }
    });
    var next = el('button', 'btn btn-primary', idx + 1 < items.length ? 'Дальше ▶' : 'Результат');
    next.type = 'button';
    next.onclick = function () { idx++; show(); };
    box.appendChild(next);
    next.focus();
  }

  function show() {
    stage.innerHTML = '';
    document.getElementById('rv-fill').style.width = (100 * idx / items.length) + '%';
    document.getElementById('rv-count').textContent = Math.min(idx + 1, items.length) + ' / ' + items.length;
    if (idx >= items.length) { summary(); return; }
    var it = items[idx];
    var box = el('div', 'rv-q');
    box.appendChild(el('p', 'q', '<b>' + esc(it.q) + '</b>'));
    if (it.pic && it.q.indexOf('Что значит') === 0) box.appendChild(el('div', 'rv-pic-big', picHtml(it.pic)));
    if (!it.audio && it.type === 'choice' && it.q.indexOf('Что значит') === 0) {   // английское слово в вопросе — можно послушать
      var hear = el('p', null, '<button type="button" class="btn btn-small say-btn"><svg class="ico" aria-hidden="true"><use href="#o-sound"/></svg> Послушать слово</button>');
      hear.querySelector('button').onclick = function () { say(it.en); };
      box.appendChild(hear);
    }
    if (it.audio) {
      var play = el('p', null, '<button type="button" class="btn btn-small say-btn"><svg class="ico" aria-hidden="true"><use href="#o-sound"/></svg> Слушать</button> <button type="button" class="btn btn-small say-btn slow">Медленно</button>');
      play.querySelector('.say-btn').onclick = function () { say(it.audio); };
      play.querySelector('.slow').onclick = function () { say(it.audio, true); };
      box.appendChild(play);
      setTimeout(function () { say(it.audio); }, 250);
    }
    if (it.type === 'choice') {
      var opts = el('div', 'rv-opts');
      it.options.forEach(function (o, i) {
        var b = el('button', 'rv-opt', esc(o)); b.type = 'button';
        b.onclick = function () {
          if (box.classList.contains('answered')) return;
          [].forEach.call(opts.children, function (x, k) { if (k === it.answer) x.classList.add('is-right'); });
          if (i !== it.answer) b.classList.add('is-wrong');
          finishAnswer(box, it, i === it.answer, it.options[it.answer]);
        };
        opts.appendChild(b);
      });
      box.appendChild(opts);
    } else if (it.type === 'type_in') {
      var inp = el('input', 'typein'); inp.type = 'text'; inp.autocomplete = 'off'; inp.lang = 'en'; inp.placeholder = 'Напиши по-английски';
      var go = el('button', 'btn btn-small', 'Проверить'); go.type = 'button';
      var done = function () {
        if (box.classList.contains('answered') || !inp.value.trim()) return;
        inp.disabled = true; go.disabled = true;
        finishAnswer(box, it, norm(inp.value) === norm(it.answer), it.answer);
      };
      go.onclick = done;
      inp.onkeydown = function (e) { if (e.key === 'Enter') done(); };
      box.appendChild(inp); box.appendChild(go);
      setTimeout(function () { inp.focus(); }, 300);
    } else {
      var line = el('div', 'answer-line pr-line'), bank = el('div', 'word-bank pr-bank');
      it.letters.forEach(function (ch) {
        var b = el('button', 'word-chip'); b.type = 'button'; b.textContent = ch;
        b.onclick = function () { if (!box.classList.contains('answered')) (b.parentNode === bank ? line : bank).appendChild(b); };
        bank.appendChild(b);
      });
      var chk = el('button', 'btn btn-small', 'Проверить'); chk.type = 'button';
      chk.onclick = function () {
        if (box.classList.contains('answered')) return;
        var got = [].map.call(line.children, function (c) { return c.textContent; }).join('');
        if (!got) return;
        finishAnswer(box, it, got === it.answer, it.answer);
      };
      box.appendChild(bank); box.appendChild(line); box.appendChild(chk);
    }
    stage.appendChild(box);
  }

  function summary() {
    document.getElementById('rv-card').classList.add('hidden');
    var s = document.getElementById('rv-summary');
    s.classList.remove('hidden');
    document.getElementById('rv-ok').textContent = okCount;
    document.getElementById('rv-total').textContent = items.length;
    document.getElementById('rv-emoji').textContent = okCount === items.length ? '' : okCount >= items.length * 0.7 ? '' : '';
    if (learned) document.getElementById('rv-learned').textContent = 'Ещё ' + learned + ' слов(а) выучено надолго!';
    document.dispatchEvent(new CustomEvent('review:done', { detail: { ok: okCount, total: items.length } }));
  }

  show();
})();
