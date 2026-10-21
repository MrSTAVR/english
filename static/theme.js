/* Переключатель тёмной/светлой темы. Начальное значение ставит скрипт в <head> (без «вспышки»). */
(function () {
  'use strict';
  var root = document.documentElement;
  var btn = document.getElementById('theme-toggle');
  var meta = document.querySelector('meta[name=theme-color]');
  function apply(t) {
    root.setAttribute('data-theme', t);
    if (meta) meta.setAttribute('content', t === 'dark' ? '#14112a' : '#7c5cff');
    if (btn) btn.setAttribute('aria-pressed', t === 'dark' ? 'true' : 'false');
  }
  function saved() { try { var t = localStorage.getItem('theme'); return t === 'dark' || t === 'light' ? t : null; } catch (e) { return null; } }
  apply(root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light');
  if (btn) btn.addEventListener('click', function () {
    var t = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    apply(t);
    try { localStorage.setItem('theme', t); } catch (e) {}
  });
  /* если выбор не сохранён — следуем за настройкой устройства */
  if (window.matchMedia) {
    var mq = matchMedia('(prefers-color-scheme: dark)');
    var onChange = function (e) { if (!saved()) apply(e.matches ? 'dark' : 'light'); };
    if (mq.addEventListener) mq.addEventListener('change', onChange);
  }
})();
