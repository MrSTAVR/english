/* PWA: регистрация service worker и подсказка «Установить на телефон». */
(function () {
  "use strict";
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () {});
    });
  }

  var box = document.getElementById("install-box");
  if (!box) return;
  var standalone = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  if (standalone) return;                                   // уже установлено
  try { if (localStorage.getItem("installHidden") === "1") return; } catch (e) {}

  var text = box.querySelector(".install-text");
  var btn = box.querySelector(".install-btn");
  var close = box.querySelector(".install-close");
  var deferred = null;

  function show() { box.hidden = false; }
  function hide(remember) {
    box.hidden = true;
    if (remember) { try { localStorage.setItem("installHidden", "1"); } catch (e) {} }
  }
  close.addEventListener("click", function () { hide(true); });

  // Android / Chrome: настоящая кнопка установки
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferred = e;
    text.textContent = "Поставь English Fun на экран телефона, как обычное приложение";
    btn.hidden = false;
    show();
  });
  btn.addEventListener("click", function () {
    if (!deferred) return;
    deferred.prompt();
    deferred.userChoice.finally(function () { deferred = null; hide(false); });
  });
  window.addEventListener("appinstalled", function () { hide(false); });

  // iPhone / iPad: установки кнопкой нет, показываем инструкцию
  var ua = navigator.userAgent || "";
  var isIOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  if (isIOS) {
    text.textContent = "Чтобы поставить приложение: нажми «Поделиться» ⬆️ и выбери «На экран Домой»";
    btn.hidden = true;
    show();
  }
})();
