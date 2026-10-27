/* Буквы-плитки и подсказка к заданиям «напиши по-английски» (урок: тренировка и тест, «Ещё потренируемся»).
   Разметка: <div class="lt" data-lt='{"t": [...плитки], "m": "f___", "w": false}' data-open="1"> рядом с input.typein.
   Нажал плитку — буква (или слово) встаёт в поле; набирать с клавиатуры тоже можно — плитки сами отмечаются.
   LetterTiles.near(given, answer) — ответ с маленькой опечаткой (как grading.near_miss на сервере). */
(function () {
  'use strict';

  function norm(s) { return String(s || '').toLowerCase().replace(/’/g, "'").replace(/\s+/g, ' ').trim().replace(/^[ .!?,;:]+|[ .!?,;:]+$/g, ''); }
  function dist(a, b) {                               // как grading._distance: соседние буквы местами — одна опечатка
    var d = [], i, j;
    for (i = 0; i <= a.length; i++) { d.push([]); for (j = 0; j <= b.length; j++) d[i].push(i * j === 0 ? i + j : 0); }
    for (i = 1; i <= a.length; i++) {
      for (j = 1; j <= b.length; j++) {
        d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
        if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
      }
    }
    return d[a.length][b.length];
  }
  function near(given, answer) {
    var g = norm(given), e = norm(answer);
    if (!g || g === e) return false;
    var lim = e.length < 4 ? 0 : e.length < 10 ? 1 : 2;
    return dist(g, e) <= lim;
  }

  /* плитки из ответа (для заданий, собранных в браузере) — как template_filters.letter_tiles */
  function tilesFor(answer) {
    var a = String(answer || '').toLowerCase().replace(/’/g, "'").replace(/[.!?,;:]+(\s|$)/g, ' ').replace(/\s+/g, ' ').trim();
    var words = a.split(' '), t, k, r, x;
    var mask = words.map(function (w) { return w.charAt(0) + new Array(w.length).join('_'); }).join(' ');
    if (words.length > 1) t = words.slice();
    else {
      t = a.split('');
      var spare = 'abcdefghijklmnoprstuwy'.split('').filter(function (c) { return a.indexOf(c) < 0; });
      for (k = 0; k < 2 && spare.length; k++) t.push(spare.splice(Math.floor(Math.random() * spare.length), 1)[0]);
    }
    for (k = t.length - 1; k > 0; k--) { r = Math.floor(Math.random() * (k + 1)); x = t[k]; t[k] = t[r]; t[r] = x; }
    return { t: t, m: mask, w: words.length > 1 };
  }

  function ico(name) { return '<svg class="ico" aria-hidden="true"><use href="#o-' + name + '"/></svg>'; }

  function build(host, inp, data, open) {
    if (host.dataset.ready) return;
    host.dataset.ready = '1';
    var tools = document.createElement('div'); tools.className = 'lt-tools';
    var hintBtn = document.createElement('button'); hintBtn.type = 'button'; hintBtn.className = 'btn btn-small btn-aux lt-hint-btn';
    hintBtn.innerHTML = ico('bulb') + ' Подсказка';
    var mask = document.createElement('span'); mask.className = 'lt-mask'; mask.hidden = true; mask.lang = 'en';
    mask.textContent = data.m.split('').join(' ').replace(/ {3}/g, '   ');
    var openBtn = document.createElement('button'); openBtn.type = 'button'; openBtn.className = 'btn btn-small btn-aux lt-open-btn';
    openBtn.innerHTML = ico('abc') + (data.w ? ' Собрать из слов' : ' Собрать из букв');
    tools.appendChild(hintBtn); tools.appendChild(openBtn); tools.appendChild(mask);
    var box = document.createElement('div'); box.className = 'lt-tiles'; box.hidden = !open;
    if (open) openBtn.hidden = true;
    var tiles = data.t.map(function (ch) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'lt-tile' + (data.w ? ' is-word' : '');
      b.textContent = ch === ' ' ? '␣' : ch; b.dataset.v = ch; b.lang = 'en';
      b.addEventListener('click', function () {
        var v = inp.value;
        if (data.w) v = v.replace(/\s+$/, '') + (v.trim() ? ' ' : '') + ch;
        else v += ch;
        set(v);
      });
      box.appendChild(b);
      return b;
    });
    var back = document.createElement('button'); back.type = 'button'; back.className = 'lt-tile lt-back'; back.title = 'Стереть последнее';
    back.setAttribute('aria-label', 'Стереть последнее'); back.innerHTML = ico('erase');
    back.addEventListener('click', function () {
      var v = inp.value.replace(/\s+$/, '');
      set(data.w ? v.replace(/\s*\S+$/, '') : v.slice(0, -1));
    });
    box.appendChild(back);
    host.appendChild(tools); host.appendChild(box);

    function set(v) {
      inp.value = v;
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      inp.dispatchEvent(new Event('change', { bubbles: true }));
    }
    function sync() {                                  // плитки, уже стоящие в поле, гаснут
      var left = data.w ? inp.value.toLowerCase().split(/\s+/).filter(Boolean) : inp.value.toLowerCase().split('');
      tiles.forEach(function (b) {
        var k = left.indexOf(b.dataset.v);
        b.classList.toggle('is-used', k >= 0);
        b.disabled = k >= 0;
        if (k >= 0) left.splice(k, 1);
      });
    }
    hintBtn.addEventListener('click', function () { mask.hidden = !mask.hidden; hintBtn.classList.toggle('is-on', !mask.hidden); });
    openBtn.addEventListener('click', function () { box.hidden = false; openBtn.hidden = true; sync(); });
    inp.addEventListener('input', sync);
    host._sync = sync;
    sync();
  }

  function attach(host, inp, answer, open) { build(host, inp, tilesFor(answer), open); }

  function initAll(root) {
    (root || document).querySelectorAll('.lt[data-lt]').forEach(function (host) {
      var box = host.closest('.exercise, .question');
      var inp = box && box.querySelector('input.typein');
      var data = null;
      try { data = JSON.parse(host.dataset.lt); } catch (e) { data = null; }
      if (inp && data && data.t && data.t.length) build(host, inp, data, host.dataset.open === '1');
    });
  }
  /* после восстановления ответов урока (lesson.js ставит значения без событий) — отметить использованные плитки */
  function resyncAll() { document.querySelectorAll('.lt').forEach(function (h) { if (h._sync) h._sync(); }); }

  window.LetterTiles = { near: near, attach: attach, resync: resyncAll };
  document.addEventListener('DOMContentLoaded', function () { initAll(); setTimeout(resyncAll, 0); });
})();
