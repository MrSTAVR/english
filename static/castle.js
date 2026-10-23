/* Замок Чик-чика: выбор комнаты (карточка с действием), Чик-чик в своём наряде в спальне, озвучка слов комнаты. */
(function () {
  'use strict';
  /* Чик-чик в спальне — тот же рисунок и наряд, что в гардеробе */
  document.querySelectorAll('.cs-chick').forEach(function (el) {
    var o = {};
    try { o = JSON.parse(el.dataset.outfit || '{}'); } catch (e) { o = {}; }
    if (window.Chick) el.innerHTML = window.Chick.svg(o);
  });

  /* слова комнаты: нажал — услышал */
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.cs-word[data-say]');
    if (b && window.ttsSpeak) window.ttsSpeak(b.dataset.say);
  });

  /* комната: метки слов на рисунке и игра «Find the…!» */
  var scene = document.getElementById('cs-scene');
  if (scene) roomScene(scene);

  /* выбор комнаты на странице замка */
  var card = document.getElementById('cs-card');
  if (!card) return;
  var name = document.getElementById('cs-card-name'), info = document.getElementById('cs-card-info');
  var open = document.getElementById('cs-open'), lesson = document.getElementById('cs-lesson'), form = document.getElementById('cs-build-form');
  function words(n) { n = +n; var m10 = n % 10, m100 = n % 100; return n + ' ' + (m10 === 1 && m100 !== 11 ? 'слово' : m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14) ? 'слова' : 'слов'); }
  function pick(room) {
    var d = room.dataset;
    document.querySelectorAll('.cs-room.is-sel').forEach(function (r) { r.classList.remove('is-sel'); });
    room.classList.add('is-sel');
    open.hidden = lesson.hidden = form.hidden = true;
    if (d.state === 'built') {
      name.textContent = d.name + ' · уровень ' + d.level;
      info.textContent = (d.who ? 'Живёт ' + d.who + ' · ' : '') + words(d.words);
      open.href = '/student/castle/' + d.room; open.hidden = false;
    } else if (d.state === 'build') {
      name.textContent = d.name + ' — можно построить';
      info.textContent = 'Нужно ' + d.costB + ' кирпичиков и ' + d.costC + ' монеток';
      form.action = '/student/castle/' + d.room + '/build'; form.hidden = false;
    } else {
      name.textContent = d.name + ' — пока закрыта';
      info.textContent = d.lock;
      if (d.lesson) { lesson.href = d.lesson; lesson.hidden = false; }
    }
  }
  document.querySelectorAll('.cs-castle .cs-room').forEach(function (r) {
    r.addEventListener('click', function () { pick(r); });
  });
  var first = document.querySelector('.cs-room.is-sel') || document.querySelector('.cs-room');
  if (first) pick(first);

  function roomScene(scene) {
    var pins = Array.prototype.slice.call(scene.querySelectorAll('.cs-pin'));
    var tip = document.getElementById('cs-tip'), tipEn = document.getElementById('cs-tip-en'), tipRu = document.getElementById('cs-tip-ru');
    var labels = document.getElementById('cs-labels');
    var title = document.getElementById('cs-find-title'), info = document.getElementById('cs-find-info');
    var go = document.getElementById('cs-find-go'), again = document.getElementById('cs-find-say'), box = document.getElementById('cs-find');
    var ROUNDS = Math.min(5, pins.length), game = null;
    function say(t) { if (window.ttsSpeak) window.ttsSpeak(t); }
    function showTip(pin) {
      pins.forEach(function (p) { p.classList.toggle('is-tip', p === pin); });
      tipEn.textContent = pin.dataset.en; tipRu.textContent = pin.dataset.ru; tip.hidden = false;
    }
    document.getElementById('cs-tip-say').addEventListener('click', function () { say(tipEn.textContent); });

    try { labels.checked = localStorage.getItem('cs-labels') === '1'; } catch (e) { /* без хранилища — подписи скрыты */ }
    scene.classList.toggle('show-labels', labels.checked);
    labels.addEventListener('change', function () {
      scene.classList.toggle('show-labels', labels.checked);
      try { localStorage.setItem('cs-labels', labels.checked ? '1' : '0'); } catch (e) { /* не страшно */ }
    });

    function ask() {
      var w = game.order[game.i];
      pins.forEach(function (p) { p.classList.remove('is-no'); });
      title.textContent = 'Find the ' + w + '!';
      info.textContent = 'Найди предмет · ' + game.found + ' из ' + ROUNDS;
      say('Find the ' + w);
    }
    function finish() {
      scene.classList.remove('is-finding'); box.classList.add('is-win'); again.hidden = true;
      title.textContent = 'Well done!';
      info.textContent = 'Все предметы найдены: ' + ROUNDS + ' из ' + ROUNDS + '!';
      go.textContent = 'Ещё раз'; go.hidden = false; say('Well done!');
      var meta = document.querySelector('meta[name="csrf-token"]');
      fetch(scene.dataset.findUrl, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': meta ? meta.content : '' }, body: '{}' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) {
          if (d && d.bricks) info.textContent += ' +' + d.bricks + ' кирпичик для замка.';
          if (d && d.task) {   /* поручение соседа выполнено — показать кнопку награды */
            info.textContent += ' Сосед ждёт тебя — забери награду!';
            setTimeout(function () { location.hash = 'cs-task'; location.reload(); }, 2200);
          }
        })
        .catch(function () { /* офлайн — без кирпичика */ });
      game = null;
    }
    go.addEventListener('click', function () {
      var order = pins.map(function (p) { return p.dataset.en; });
      for (var i = order.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)), t = order[i]; order[i] = order[j]; order[j] = t; }
      game = { order: order.slice(0, ROUNDS), i: 0, found: 0, miss: false };
      pins.forEach(function (p) { p.classList.remove('is-ok', 'is-no', 'is-tip'); });
      tip.hidden = true; box.classList.remove('is-win');
      scene.classList.add('is-finding'); go.hidden = true; again.hidden = false;
      ask();
    });
    again.addEventListener('click', function () { if (game) say('Find the ' + game.order[game.i]); });

    pins.forEach(function (pin) {
      pin.addEventListener('click', function () {
        if (!game) { showTip(pin); say(pin.dataset.en); return; }
        if (pin.classList.contains('is-ok')) return;
        if (pin.dataset.en === game.order[game.i]) {
          pin.classList.add('is-ok'); game.found++; game.i++;
          if (game.i >= game.order.length) { finish(); return; }
          info.textContent = 'Yes! Это ' + pin.dataset.ru + '. ' + game.found + ' из ' + ROUNDS;
          setTimeout(function () { if (game) ask(); }, 900);
        } else {
          pin.classList.remove('is-no'); void pin.offsetWidth; pin.classList.add('is-no');
          info.textContent = 'Это ' + pin.dataset.en + ' — ' + pin.dataset.ru + '. Попробуй ещё!';
          say(pin.dataset.en);
        }
      });
    });
  }
})();
