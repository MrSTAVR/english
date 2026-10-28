/* Напоминания от Чик-чика (Web Push, push.py): карточка «Включить» на главной ученика.
   Показываем, только если браузер умеет push (Android Chrome; iPhone — если сайт на экране «Домой»)
   и разрешение ещё не дано. Уже подписанное устройство тихо обновляет подписку на сервере. */
(function () {
  'use strict';
  var card = document.getElementById('push-card');
  if (!card || !('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) return;
  var btn = document.getElementById('push-on'), msg = document.getElementById('push-msg');

  function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ''; }
  function post(url, body) {
    return fetch(url, { method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf() }, body: JSON.stringify(body) });
  }
  function withTimeout(p, ms) {                 // подписка может повиснуть без сервиса уведомлений
    return Promise.race([p, new Promise(function (_, no) { setTimeout(function () { no(new Error('timeout')); }, ms); })]);
  }
  function keyBytes(b64) {
    var s = (b64 + '===='.slice(b64.length % 4)).replace(/-/g, '+').replace(/_/g, '/');
    var raw = atob(s), out = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
    return out;
  }

  navigator.serviceWorker.ready.then(function (reg) {
    return reg.pushManager.getSubscription().then(function (sub) {
      if (sub && Notification.permission === 'granted') {
        post('/api/push/subscribe', { sub: sub.toJSON() }).catch(function () {});   // освежаем на сервере
        return;
      }
      if (Notification.permission === 'denied') return;     // отказались — не пристаём
      card.hidden = false;
      btn.addEventListener('click', function () {
        btn.disabled = true;
        Notification.requestPermission().then(function (perm) {
          if (perm !== 'granted') { msg.textContent = 'Хорошо, без напоминаний. Включить можно потом в настройках браузера.'; return null; }
          return fetch('/api/push/key', { credentials: 'same-origin' }).then(function (r) { return r.json(); })
            .then(function (d) {
              if (!d.key) throw new Error('no key');
              return withTimeout(reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(d.key) }), 20000);
            })
            .then(function (s) { return post('/api/push/subscribe', { sub: s.toJSON() }); })
            .then(function (r) {
              if (!r.ok) throw new Error('save');
              msg.textContent = 'Готово! Чик-чик напомнит вечером, если ты забудешь.';
              btn.hidden = true;
            });
        }).catch(function () {
          msg.textContent = 'Не получилось включить. Попробуй ещё раз чуть позже.';
          btn.disabled = false;
        });
      });
    });
  }).catch(function () {});
})();
