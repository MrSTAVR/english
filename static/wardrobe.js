/* Гардероб: рисуем Чик-чика в наряде и превью каждого предмета */
(function () {
  'use strict';
  var host = document.getElementById('wardrobe');
  if (!host || !window.Chick) return;
  var worn = {}, items = [];
  try { worn = JSON.parse(host.dataset.worn || '{}'); items = JSON.parse(host.dataset.items || '[]'); } catch (e) { /* noop */ }
  var prev = document.getElementById('wd-preview');
  if (prev) prev.innerHTML = window.Chick.svg(worn);
  [].forEach.call(host.querySelectorAll('.wd-thumb'), function (t) {
    var slot = t.dataset.slot, o = {};
    if (slot === 'color') o.color = t.dataset.key; else o[slot] = t.dataset.key;
    if (slot !== 'color' && worn.color) o.color = worn.color;   // примеряем на своём цвете
    t.innerHTML = window.Chick.svg(o);
  });
})();
