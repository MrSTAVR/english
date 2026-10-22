/* Дополнительные задания: «послушай», диктант, собери слово, перевод.
   Здесь ошибки не считаются — это просто тренировка. */
(function () {
  'use strict';

  function say(text, slow) { if (window.ttsSpeak) window.ttsSpeak(text, slow ? 0.5 : undefined); }
  function norm(s) { return String(s || '').toLowerCase().replace(/’/g, "'").replace(/\s+/g, ' ').trim().replace(/^[ .!?,;:]+|[ .!?,;:]+$/g, ''); }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  document.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('.say-btn') : null;
    if (b) say(b.dataset.say, !!b.dataset.slow);
  });

  function verdict(box, ok, item) {
    var r = box.querySelector('.ex-result');
    r.textContent = ok ? ' Правильно!' : ' Пока нет, попробуй ещё!';
    r.className = 'ex-result ' + (ok ? 'ok' : 'bad');
    if (ok) {
      box.classList.add('done');
      var ex = box.querySelector('.explain');
      if (ex) ex.classList.remove('hidden');
    }
    document.dispatchEvent(new CustomEvent('practice:checked', { detail: { ok: ok } }));
  }

  function build(item, idx) {
    var box = el('div', 'exercise card-inner pr-item');
    box.appendChild(el('p', 'q', '<b>Задание ' + (idx + 1) + '.</b> ' + esc(item.q)));
    if (item.audio) {
      box.appendChild(el('p', null, '<button type="button" class="btn btn-small say-btn" data-say="' + esc(item.audio) + '"><svg class="ico" aria-hidden="true"><use href="#o-sound"/></svg> Слушать</button> ' +
        '<button type="button" class="btn btn-small say-btn" data-say="' + esc(item.audio) + '" data-slow="1">Медленно</button>'));
    }
    var check;
    if (item.type === 'choice') {
      var opts = el('div', 'options');
      item.options.forEach(function (o, i) {
        var l = el('label', 'opt');
        l.innerHTML = '<input type="radio" name="pr' + idx + '" value="' + i + '"> ' + esc(o);
        opts.appendChild(l);
      });
      box.appendChild(opts);
      check = function () {
        var s = box.querySelector('input:checked');
        return !!s && parseInt(s.value, 10) === item.answer;
      };
    } else if (item.type === 'type_in') {
      var inp = el('input', 'typein'); inp.type = 'text'; inp.autocomplete = 'off'; inp.placeholder = 'Напиши по-английски';
      box.appendChild(inp);
      check = function () { return norm(inp.value) === norm(item.answer); };
    } else if (item.type === 'scramble') {
      var line = el('div', 'answer-line pr-line'), bank = el('div', 'word-bank pr-bank');
      item.letters.forEach(function (ch) {
        var b = el('button', 'word-chip'); b.type = 'button'; b.textContent = ch;
        b.onclick = function () {
          if (b.parentNode === bank) line.appendChild(b); else bank.appendChild(b);
        };
        bank.appendChild(b);
      });
      var reset = el('button', 'btn btn-small', 'Сбросить'); reset.type = 'button';
      reset.onclick = function () { [].slice.call(line.children).forEach(function (c) { bank.appendChild(c); }); };
      box.appendChild(bank); box.appendChild(line); box.appendChild(reset);
      check = function () { return [].map.call(line.children, function (c) { return c.textContent; }).join('') === item.answer; };
    }
    var btn = el('button', 'btn btn-small', 'Проверить'); btn.type = 'button';
    btn.onclick = function () { verdict(box, check(), item); };
    box.appendChild(btn);
    box.appendChild(el('span', 'ex-result'));
    box.appendChild(el('div', 'explain hidden', '' + esc(item.explain || '')));
    return box;
  }

  document.addEventListener('DOMContentLoaded', function () {
    var host = document.getElementById('practice');
    if (!host) return;
    var items = [];
    try { items = JSON.parse(host.dataset.items || '[]'); } catch (e) { /* noop */ }
    items.forEach(function (it, i) { host.appendChild(build(it, i)); });
  });
})();
