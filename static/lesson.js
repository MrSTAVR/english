/* Урок (дизайн 4.0): подпись текущего шага, озвучка фраз в теории, колода «Новые слова»
   — одна большая карточка, перевод по нажатию, точки, список всех слов (на телефоне — шторка снизу). */
(function () {
  'use strict';
  var STEPS = { 'step-theory': ['Теория', 1], 'step-material': ['Слова', 2], 'step-exercises': ['Тренировка', 3], 'step-test': ['Тест', 4] };
  function say(text, slow) { if (window.ttsSpeak) window.ttsSpeak(text, slow ? 0.55 : null); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  var ICO = function (name) { return '<svg class="ico" aria-hidden="true"><use href="#o-' + name + '"/></svg>'; };

  /* ---------- шаг урока: подпись «Слова · 2/4» (на телефоне) ---------- */
  var now = document.getElementById('ls-now');
  window.lessonStepChanged = function (id) {
    var s = STEPS[id];
    if (now && s) now.textContent = s[0] + ' · ' + s[1] + '/4';
    if (id === 'step-material' && deck) deck.show();
  };

  /* ---------- теория: английские фразы (жирным) озвучиваются по нажатию ---------- */
  document.querySelectorAll('#step-theory .theory-block b, #step-theory .theory-intro b').forEach(function (b) {
    var text = b.textContent.trim();
    if (!/[A-Za-z]/.test(text) || /[А-Яа-яЁё]/.test(text)) return;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'th-say';
    btn.title = 'Послушать';
    btn.innerHTML = ICO('sound') + '<b lang="en">' + esc(text) + '</b>';
    btn.addEventListener('click', function () { say(text.replace(/…|\.\.\./g, '')); });
    b.replaceWith(btn);
  });

  /* ---------- колода слов ---------- */
  var deck = null;
  var dataEl = document.getElementById('wd-data');
  var W = [];
  try { W = JSON.parse(dataEl ? dataEl.textContent : '[]'); } catch (e) { W = []; }
  if (!W.length) return;

  var $ = function (id) { return document.getElementById(id); };
  var card = $('wd-card'), sheet = $('wd-sheet');
  var i = 0, flipped = false, seen = {};

  function picHtml(w) {
    return w.pic ? '<span class="wd-emoji">' + esc(w.pic) + '</span>' : ICO('chat');
  }
  function rowsHtml() {
    return W.map(function (w, k) {
      return '<button type="button" class="wd-row' + (k === i ? ' is-on' : '') + '" data-k="' + k + '">' +
        '<span class="wd-row-pic' + (w.pic ? '' : ' no-pic') + '">' + picHtml(w) + '</span>' +
        '<span class="wd-row-text"><b lang="en">' + esc(w.en) + '</b><small>' + esc(w.ru) + '</small></span>' +
        '<span class="wd-mark' + (seen[k] ? ' on' : '') + '">' + ICO('check') + '</span></button>';
    }).join('');
  }
  function countText() {
    var n = Object.keys(seen).length;
    return 'знаю ' + n + ' из ' + W.length;
  }
  function render() {
    var w = W[i];
    $('wd-num').textContent = (i + 1) + ' из ' + W.length;
    $('wd-know').hidden = !seen[i];
    var pic = $('wd-pic');
    pic.className = 'wd-pic' + (w.pic ? '' : ' no-pic');
    pic.innerHTML = picHtml(w);
    $('wd-en').textContent = w.en;
    $('wd-hint').textContent = w.hint ? '[' + w.hint + ']' : '';
    $('wd-ru').textContent = w.ru;
    $('wd-ru').hidden = !flipped;
    $('wd-tap').hidden = flipped;
    card.setAttribute('aria-label', flipped ? 'Спрятать перевод' : 'Показать перевод');
    $('wd-prev').disabled = i === 0;
    $('wd-next').textContent = i === W.length - 1 ? 'К тренировке →' : 'Дальше →';
    $('wd-dots').innerHTML = W.map(function (x, k) {
      return '<button type="button" class="wd-dot' + (k === i ? ' is-on' : seen[k] ? ' is-seen' : '') + '" data-k="' + k + '" aria-label="' + esc(x.en) + '"></button>';
    }).join('');
    $('wd-rows').innerHTML = $('wd-rows2').innerHTML = rowsHtml();
    $('wd-count').textContent = $('wd-count2').textContent = countText();
  }
  function go(k) {
    seen[i] = true;                                   // слово показали — оно «знакомое»
    i = Math.max(0, Math.min(W.length - 1, k));
    flipped = false;
    render();
    say(W[i].en);
  }
  function openSheet(open) {
    sheet.hidden = !open;
    document.body.classList.toggle('wd-sheet-open', open);
    if (open) { var on = sheet.querySelector('.wd-row.is-on'); if (on) on.scrollIntoView({ block: 'center' }); }
  }

  card.addEventListener('click', function () { flipped = !flipped; if (flipped) seen[i] = true; render(); });
  card.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); card.click(); } });
  $('wd-say').addEventListener('click', function () { say(W[i].en); });
  $('wd-slow').addEventListener('click', function () { say(W[i].en, true); });
  $('wd-prev').addEventListener('click', function () { go(i - 1); });
  $('wd-next').addEventListener('click', function () {
    if (i === W.length - 1) { seen[i] = true; if (window.goStep) window.goStep('step-exercises'); return; }
    go(i + 1);
  });
  $('wd-all').addEventListener('click', function () { openSheet(true); });
  [$('wd-dots'), $('wd-rows'), $('wd-rows2')].forEach(function (box) {
    box.addEventListener('click', function (e) {
      var b = e.target.closest('[data-k]');
      if (!b) return;
      go(+b.dataset.k);
      openSheet(false);
    });
  });
  sheet.addEventListener('click', function (e) { if (e.target.closest('[data-close]')) openSheet(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !sheet.hidden) openSheet(false); });

  deck = { show: function () { render(); } };
  render();
})();
