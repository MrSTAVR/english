/* Таблицы на телефоне показываются карточками: подписи полей берём из заголовков столбцов. */
(function () {
  "use strict";
  document.querySelectorAll("table.tbl").forEach(function (table) {
    var heads = Array.prototype.map.call(table.querySelectorAll("thead th"), function (th) {
      return th.textContent.trim();
    });
    if (!heads.length) return;
    table.querySelectorAll("tbody tr").forEach(function (tr) {
      Array.prototype.forEach.call(tr.children, function (td, i) {
        if (heads[i] && !td.hasAttribute("data-label")) td.setAttribute("data-label", heads[i]);
      });
    });
  });
})();

/* Телефон в режиме «Версия для ПК»: страница рисуется шириной ~1000px и выглядит мелко.
   Определяем это и подсказываем, как выключить. */
(function () {
  "use strict";
  var small = Math.min(window.screen.width, window.screen.height) <= 700;
  var touch = window.matchMedia("(pointer: coarse)").matches || "ontouchstart" in window;
  if (!(small && touch && window.innerWidth > 800)) return;
  try { if (sessionStorage.getItem("desktopWarnHidden") === "1") return; } catch (e) {}
  var box = document.createElement("div");
  box.className = "desktop-warn";
  box.innerHTML = "<b>Страница открыта как «Версия для ПК», поэтому всё мелкое.</b> " +
    "Открой меню браузера (⋮) и выключи галочку «Версия для ПК» / «Desktop site», затем обнови страницу. " +
    "<button type=\"button\">Понятно</button>";
  box.querySelector("button").addEventListener("click", function () {
    box.remove();
    try { sessionStorage.setItem("desktopWarnHidden", "1"); } catch (e) {}
  });
  document.body.insertBefore(box, document.body.firstChild);
})();
