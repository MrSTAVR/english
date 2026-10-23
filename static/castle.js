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
})();
