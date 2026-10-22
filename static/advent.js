/* Адвент-календарь: открытие окошек и озвучка слов */
(function () {
  'use strict';
  var grid = document.getElementById('advent'), msg = document.getElementById('adv-msg');
  if (!grid) return;
  function say(t) { if (window.ttsSpeak) window.ttsSpeak(t); }
  function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ''; }
  function esc(t) { var d = document.createElement('div'); d.textContent = t; return d.innerHTML; }

  grid.addEventListener('click', function (e) {
    var b = e.target.closest('.adv-door');
    if (!b) return;
    if (b.dataset.say) { say(b.dataset.say); return; }
    if (!b.dataset.day || b.disabled) return;
    b.disabled = true;
    fetch('/api/advent', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() },
      body: JSON.stringify({ day: parseInt(b.dataset.day, 10) })
    }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      if (!j) { b.disabled = false; msg.textContent = 'Не получилось открыть окошко — попробуй ещё раз.'; return; }
      var w = j.word;
      b.classList.add('adv-open', 'adv-pop');
      b.innerHTML = '<span class="adv-num">' + esc(b.dataset.day) + '</span><span class="adv-pic">' + esc(w.pic) + '</span><b>' +
        esc(w.en) + '</b><small>' + esc(w.ru) + '</small>';
      b.dataset.say = w.en;
      delete b.dataset.day;
      b.disabled = false;
      say(w.en);
      msg.textContent = j.coins ? 'Ура! +' + j.coins + ' монетка 🪙' : 'Окошко открыто!';
      if (j.newAchievements && j.newAchievements.length) {
        setTimeout(function () { document.dispatchEvent(new CustomEvent('ach:new', { detail: { list: j.newAchievements } })); }, 1200);
      }
    }).catch(function () { b.disabled = false; msg.textContent = 'Нет связи — окошко откроется, когда появится интернет.'; });
  });
})();
