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
