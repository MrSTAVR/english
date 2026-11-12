(function () {
  "use strict";
  const root = document.getElementById("pz");
  if (!root) return;
  const DATA = JSON.parse(document.getElementById("pz-data").textContent);
  const BASE = root.dataset.static || "/static/pizza/";
  const VER = root.dataset.ver || "";          // одна версия ассетов на страницу (pizza.html: PZ_V)
  const FARM = root.dataset.farm || "/student/farm";
  const withVer = (name) => BASE + name + (VER ? "?v=" + VER : "");
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const STEP_NAMES = ["Тесто", "Соус", "Начинки", "Сыр", "Печь", "Готово"];
  const BAKE_MS = 2600;
  // Кусков на рецепт: подобрано под пиццу на телефоне (75% стейджа), чтобы начинка не слипалась.
  // Сервер проверяет только рецепт, поэтому число кусков — дело оформления.
  const PIECES = {
    basil: 5, cherry_tomato: 6, pepperoni: 7, mushroom: 7,
    oregano: 4, chicken: 4, lettuce: 3, parmesan: 4,
  };

  const menu = $("pz-menu");
  const cook = $("pz-cook");
  const result = $("pz-result");
  const pizzaWrap = $("pz-pizza-wrap");
  const pizzaImg = $("pz-pizza");
  const piecesBox = $("pz-pieces");
  const title = $("pz-title");
  const hint = $("pz-hint");
  const stepLine = $("pz-step-line");
  const currentBox = $("pz-current");
  const action = $("pz-action");
  const switchBtn = $("pz-switch");
  const tools = $("pz-tools");
  const alertBox = $("pz-alert");
  const ingredientsBox = $("pz-ingredients");
  const intro = document.querySelector(".pz-intro");
  const steps = Array.from(document.querySelectorAll("#pz-steps li"));

  let current = null;
  let step = 0;
  let spots = [];          // [{x, y, key}|{x, y, key:null}] — точки на пицце
  let active = null;       // выбранная начинка
  let cooking = false;
  let serving = false;
  let bakeTimer = null;
  let bakeRaf = null;
  let drag = null;

  function csrf() {
    const m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.content : "";
  }

  function plural(n, one, few, many) {
    const m10 = n % 10, m100 = n % 100;
    if (m10 === 1 && m100 !== 11) return one;
    if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
    return many;
  }
  const coinsWord = (n) => plural(n, "монетка", "монетки", "монеток");
  const coinIcon = '<svg class="ico" aria-hidden="true"><use href="#i-coin"/></svg>';

  function setCoins(n) {
    const el = $("pz-coins");
    if (el && typeof n === "number") el.textContent = String(n);
  }

  // ── картинки ──────────────────────────────────────────────────────────────
  function imageFor(s, recipe) {
    if (s === 0) return withVer("pizza_dough_ball.png");
    if (s === 1) return withVer("pizza_dough_flat.png");
    // 0 начинок — это соус, а не «top0» (такого файла нет)
    if (s === 2) return withVer(recipe.key === "caesar" ? "pizza_dough_sauce_caesar.png" : "pizza_dough_sauce.png");
    if (s === 3 || s === 4) return withVer("pizza_" + recipe.key + "_cheese.png");
    return withVer("pizza_" + recipe.key + "_baked.png");
  }

  // ── точки на пицце ────────────────────────────────────────────────────────
  // Раскладка «подсолнухом»: точки равномерно расходятся от центра и всегда
  // попадают на лепёшку, сколько бы кусков ни было в рецепте.
  function spotsFor(n) {
    const out = [];
    for (let i = 0; i < n; i++) {
      const r = 0.34 * Math.sqrt((i + 0.5) / Math.max(n, 1));
      const a = i * 2.399963229728653;
      out.push({ x: 50 + r * Math.cos(a) * 100, y: 50 + r * Math.sin(a) * 100, key: null });
    }
    return out;
  }

  function planFor(recipe) {
    const left = {};
    const order = recipe.toppings.map(function (t) { return t.key; });
    order.forEach(function (k) { left[k] = PIECES[k] || 4; });
    const out = [];
    let more = order.length > 0;
    while (more) {
      more = false;
      order.forEach(function (k) {
        if (left[k] > 0) { out.push(k); left[k] -= 1; more = true; }
      });
    }
    return out;
  }

  const countOf = (key) => spots.filter(function (sp) { return sp.key === key; }).length;
  const totalOf = (key) => PIECES[key] || 4;

  function firstNeeded() {
    if (!current) return null;
    for (let i = 0; i < current.toppings.length; i++) {
      const key = current.toppings[i].key;
      if (countOf(key) < totalOf(key)) return key;
    }
    return null;
  }

  function allPlaced() {
    return spots.length > 0 && spots.every(function (sp) { return sp.key; });
  }

  function leftCount() {
    return spots.filter(function (sp) { return !sp.key; }).length;
  }

  function pieceWidth(n) {
    if (n <= 8) return 15;
    if (n <= 12) return 13;
    return 11;
  }

  // ── меню ──────────────────────────────────────────────────────────────────
  function renderMenu() {
    menu.innerHTML = "";
    DATA.recipes.forEach(function (r) {
      const done = DATA.completed.indexOf(r.key) !== -1;
      const can = r.can !== false;
      const missing = (r.need || []).filter(function (n) { return n.have < n.need; });
      const missText = missing.map(function (n) { return n.ru; }).join(", ");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "pz-card";
      btn.dataset.recipe = r.key;
      btn.disabled = !can;
      btn.setAttribute("aria-label", r.en + " — " + r.ru + (can ? "" : ". Не хватает: " + missText));
      btn.innerHTML =
        '<img src="' + withVer("pizza_" + r.key + "_baked.png") + '" alt="">' +
        (done && can
          ? '<span class="pz-done">готово</span>'
          : (can ? '<span class="pz-new">' + coinIcon + "+" + DATA.reward + "</span>" : "")) +
        (can ? "" : '<span class="pz-no">нет продуктов</span>') +
        '<span class="pz-card-title">' + esc(r.en) + '<span class="pz-card-ru">' + esc(r.ru) + "</span></span>" +
        '<span class="pz-card-ing">' +
          esc(r.ingredients.map(function (i) { return i.en; }).join(" · ")) + "</span>" +
        (can ? "" : '<span class="pz-card-miss">не хватает: ' + esc(missText) + "</span>");
      btn.addEventListener("click", function () { start(r); });
      menu.appendChild(btn);
    });
  }

  // После приготовления продукты списаны на сервере — обновляем наличие,
  // чтобы карточки не обещали то, чего уже нет.
  function spendLocally(recipe) {
    const spent = {};
    (recipe.need || []).forEach(function (n) { spent[n.key] = (spent[n.key] || 0) + n.need; });
    DATA.recipes.forEach(function (r) {
      (r.need || []).forEach(function (n) {
        n.have = Math.max(0, n.have - (spent[n.key] || 0));
      });
      r.can = (r.need || []).every(function (n) { return n.have >= n.need; });
    });
  }

  // ── начинки ───────────────────────────────────────────────────────────────
  function renderIngredients() {
    ingredientsBox.innerHTML = "";
    ingredientsBox.hidden = step !== 2;
    if (!current || step !== 2) return;
    current.toppings.forEach(function (t) {
      const total = totalOf(t.key);
      const done = countOf(t.key);
      const full = done >= total;
      const b = document.createElement("button");
      b.type = "button";
      b.className = "pz-ing" + (active === t.key ? " on" : "") + (full ? " full" : "");
      b.dataset.key = t.key;
      b.disabled = full;
      b.setAttribute("aria-pressed", active === t.key ? "true" : "false");
      b.setAttribute("aria-label", t.en + " — " + t.ru + ", " + done + " из " + total);
      b.innerHTML =
        '<img src="' + withVer(t.key + ".png") + '" alt="">' +
        '<span class="pz-ing-text"><b lang="en">' + esc(t.en) + "</b><small>" + esc(t.ru) + "</small></span>" +
        '<span class="pz-ing-count">' +
          (full ? '<svg class="ico" aria-hidden="true"><use href="#o-check"/></svg>' : "") +
          done + "/" + total + "</span>";
      bindChip(b, t.key);
      ingredientsBox.appendChild(b);
    });
  }

  function selectIngredient(key) {
    if (!current || step !== 2) return;
    if (countOf(key) >= totalOf(key)) return;
    if (active === key) return;
    active = key;
    // без перерисовки списка: не теряем фокус с кнопки
    ingredientsBox.querySelectorAll(".pz-ing").forEach(function (b) {
      const on = b.dataset.key === key;
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    renderCurrent();
  }

  // Подсказка на самой пицце: какая начинка сейчас «в руке» и сколько кусков уже на месте.
  function renderCurrent() {
    const t = (current && step === 2 && active)
      ? current.toppings.find(function (x) { return x.key === active; })
      : null;
    if (currentBox) currentBox.hidden = !t;
    if (!t) return;
    $("pz-current-img").src = withVer(t.key + ".png");
    $("pz-current-en").textContent = t.en;
    $("pz-current-ru").textContent = t.ru;
    $("pz-current-count").textContent = countOf(t.key) + "/" + totalOf(t.key);
  }

  // ── тап и перетаскивание ──────────────────────────────────────────────────
  function pointOnPizza(cx, cy) {
    const r = pizzaWrap.getBoundingClientRect();
    if (!r.width || !r.height) return null;
    if (cx < r.left || cx > r.right || cy < r.top || cy > r.bottom) return null;
    const x = ((cx - r.left) / r.width) * 100;
    const y = ((cy - r.top) / r.height) * 100;
    if (Math.hypot(x - 50, y - 50) > 44) return null;   // вне лепёшки
    return { x: x, y: y };
  }

  function place(x, y) {
    if (step !== 2 || !current) return;
    const key = (active && countOf(active) < totalOf(active)) ? active : firstNeeded();
    if (!key) return;
    const free = spots.filter(function (sp) { return !sp.key; });
    if (!free.length) return;
    let best = free[0], bestD = Infinity;
    free.forEach(function (sp) {
      const d = (sp.x - x) * (sp.x - x) + (sp.y - y) * (sp.y - y);
      if (d < bestD) { bestD = d; best = sp; }
    });
    best.key = key;
    if (countOf(key) >= totalOf(key)) active = firstNeeded();
    paint();
  }

  function fillAll() {
    if (step !== 2 || !current) return;
    let key = firstNeeded();
    while (key) {
      const sp = spots.find(function (s) { return !s.key; });
      if (!sp) break;
      sp.key = key;
      key = firstNeeded();
    }
    active = firstNeeded();
    paint();
  }

  function bindChip(btn, key) {
    btn.addEventListener("pointerdown", function (e) {
      if (step !== 2 || drag) return;
      if (e.pointerType === "mouse" && e.button !== 0) return;
      selectIngredient(key);
      drag = { x: e.clientX, y: e.clientY, moved: false };
      window.addEventListener("pointermove", onDragMove);
      window.addEventListener("pointerup", onDragEnd, { once: true });
      window.addEventListener("pointercancel", onDragEnd, { once: true });
    });
    // клавиатура и обычный тап: Enter/пробел на кнопке
    btn.addEventListener("click", function () { selectIngredient(key); });
  }

  function onDragMove(e) {
    if (!drag) return;
    if (!drag.moved && Math.hypot(e.clientX - drag.x, e.clientY - drag.y) > 10) {
      drag.moved = true;
      cook.classList.add("is-dragging");
    }
  }

  function onDragEnd(e) {
    window.removeEventListener("pointermove", onDragMove);
    cook.classList.remove("is-dragging");
    const d = drag;
    drag = null;
    if (!d || !d.moved || e.type === "pointercancel") return;
    const p = pointOnPizza(e.clientX, e.clientY);
    if (p) place(p.x, p.y);
  }

  // ── шаги ──────────────────────────────────────────────────────────────────
  function updateAction() {
    switchBtn.hidden = cooking || serving;
    tools.hidden = step !== 2 || allPlaced();
    action.disabled = false;
    if (step === 0) action.textContent = "Раскатать тесто";
    else if (step === 1) action.textContent = "Намазать соус";
    else if (step === 2) {
      const left = leftCount();
      action.textContent = left ? "Осталось: " + left + " " + plural(left, "кусок", "куска", "кусков")
        : "Посыпать сыром";
      action.disabled = left > 0;
    } else if (step === 3) action.textContent = "В печь!";
    else if (step === 4) {
      action.textContent = cooking ? "Печётся…" : "Ставим в печь";
      action.disabled = true;
    } else action.textContent = "Подать Тому";
    if (serving) {
      action.textContent = "Подаём…";
      action.disabled = true;
    }
  }

  function hintText() {
    if (step === 0) return "Перед тобой кусок теста. Раскатай его скалкой.";
    if (step === 1) return "Тесто готово. Теперь намажь соус.";
    if (step === 2) {
      if (allPlaced()) return "Все начинки на месте! Теперь посыпь сыром.";
      return "Нажми на картинку начинки, потом — на пиццу. Или перетащи картинку на пиццу.";
    }
    if (step === 3) return "Начинки разложены. Посыпь пиццу сыром.";
    if (step === 4) return cooking ? "Печётся… Подожди немного." : "Сыр сверху. Пора в печь!";
    return "Пицца готова. Подай её Тому!";
  }

  function paint() {
    pizzaImg.src = imageFor(step, current);
    pizzaImg.alt = step >= 5 ? "Готовая пицца «" + current.ru + "»" : "Пицца на кухне";
    pizzaWrap.classList.toggle("can-tap", step === 2);
    steps.forEach(function (li, i) {
      li.classList.toggle("on", i === step);
      li.classList.toggle("done", i < step);
      if (i === step) li.setAttribute("aria-current", "step");
      else li.removeAttribute("aria-current");
    });
    stepLine.textContent = "Шаг " + (step + 1) + " из " + STEP_NAMES.length + " · " + STEP_NAMES[step];
    hint.textContent = hintText();
    title.textContent = current.en + " — " + current.ru;
    renderPieces();
    renderIngredients();
    renderCurrent();
    updateAction();
  }

  function renderPieces() {
    piecesBox.innerHTML = "";
    if (!current || step !== 2) return;
    const w = pieceWidth(spots.length);
    spots.forEach(function (sp) {
      if (!sp.key) {
        const dot = document.createElement("span");
        dot.className = "pz-spot";
        dot.style.left = sp.x + "%";
        dot.style.top = sp.y + "%";
        piecesBox.appendChild(dot);
        return;
      }
      const el = document.createElement("span");
      el.className = "pz-piece";
      el.style.left = sp.x + "%";
      el.style.top = sp.y + "%";
      el.style.width = w + "%";
      el.innerHTML = '<img src="' + withVer(sp.key + ".png") + '" alt="">';
      piecesBox.appendChild(el);
    });
  }

  // ── печь ──────────────────────────────────────────────────────────────────
  function clearBake() {
    if (bakeTimer) { clearTimeout(bakeTimer); bakeTimer = null; }
    if (bakeRaf) { cancelAnimationFrame(bakeRaf); bakeRaf = null; }
    cooking = false;
    const oven = $("pz-oven");
    if (oven) oven.hidden = true;
  }

  function startBake() {
    const oven = $("pz-oven");
    const ring = $("pz-oven-fg");
    cooking = true;
    oven.hidden = false;
    const len = ring.getTotalLength ? ring.getTotalLength() : 0;
    if (len) {
      ring.style.strokeDasharray = String(len);
      ring.style.strokeDashoffset = String(len);
    }
    const t0 = performance.now();
    const tick = function (now) {
      const k = Math.min(1, (now - t0) / BAKE_MS);
      if (len) ring.style.strokeDashoffset = String(len * (1 - k));
      if (k < 1 && cooking) bakeRaf = requestAnimationFrame(tick);
    };
    bakeRaf = requestAnimationFrame(tick);
    bakeTimer = setTimeout(function () {
      bakeTimer = null;
      bakeRaf = null;
      cooking = false;
      oven.hidden = true;
      if (!current) return;
      step = 5;
      paint();
      if (window.ttsSpeak) window.ttsSpeak("Pizza is ready!", 0.9);
    }, BAKE_MS);
  }

  // ── запуск рецепта и возврат в меню ───────────────────────────────────────
  function start(recipe) {
    clearBake();
    current = recipe;
    step = 0;
    active = null;
    serving = false;
    drag = null;
    hideAlert();
    const plan = planFor(recipe);
    spots = spotsFor(plan.length);
    if (intro) intro.hidden = true;
    menu.hidden = true;
    cook.hidden = false;
    result.hidden = true;
    $("pz-order-en").textContent = "Can I have a " + recipe.en + " pizza, please?";
    $("pz-order-ru").textContent = "Можно мне пиццу «" + recipe.ru + "», пожалуйста?";
    paint();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function backToMenu() {
    clearBake();
    serving = false;
    current = null;
    step = 0;
    active = null;
    spots = [];
    hideAlert();
    piecesBox.innerHTML = "";
    ingredientsBox.innerHTML = "";
    ingredientsBox.hidden = true;
    if (currentBox) currentBox.hidden = true;
    tools.hidden = true;
    cook.hidden = true;
    result.hidden = true;
    menu.hidden = false;
    if (intro) intro.hidden = false;
    renderMenu();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ── подача ────────────────────────────────────────────────────────────────
  function next() {
    if (!current || serving) return;
    if (step === 0) { step = 1; paint(); return; }
    if (step === 1) { step = 2; active = firstNeeded(); paint(); return; }
    if (step === 2) { if (allPlaced()) { step = 3; paint(); } return; }
    if (step === 3) { step = 4; startBake(); paint(); return; }
    if (step === 4) return;
    if (step === 5) submit(current.key);
  }

  function hideAlert() {
    if (!alertBox) return;
    alertBox.hidden = true;
    alertBox.innerHTML = "";
  }

  function showAlert(html) {
    if (!alertBox) return;
    alertBox.innerHTML = html;
    alertBox.hidden = false;
  }

  function barnHtml(recipe) {
    const rows = (recipe.need || []).map(function (n) {
      const ok = n.have >= n.need;
      return '<li class="' + (ok ? "is-ok" : "") + '"><span>' + esc(n.ru) + "</span><b>" +
        n.have + "/" + n.need + "</b></li>";
    }).join("");
    return '<p class="pz-alert-title">В амбаре:</p><ul class="pz-barn">' + rows + "</ul>" +
      '<a class="btn btn-small btn-primary" href="' + FARM + '">На ферму</a>';
  }

  // key передаём в замыкание: current может обнулиться, пока ждём ответ
  function submit(key) {
    const recipe = current;
    if (!recipe) return;
    serving = true;
    hideAlert();
    updateAction();
    fetch("/api/pizza/finish", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() },
      body: JSON.stringify({ recipe: key }),
    }).then(function (r) {
      return r.json().catch(function () { return null; }).then(function (body) {
        if (!r.ok) {
          const err = body && typeof body === "object" ? body : {};
          err.status = r.status;
          throw err;
        }
        return body;
      });
    }).then(function (res) {
      serving = false;
      setCoins(res.coins);
      if (DATA.completed.indexOf(key) === -1) DATA.completed.push(key);
      // Сервер при повторе (already) ничего не списал — локально тоже не трогаем,
      // иначе амбар «сгорает» и карточки ложно блокируются «нет продуктов».
      if (!res.already) spendLocally(recipe);
      showResult(res.gained, res.already, recipe);
    }).catch(function (err) {
      serving = false;
      submitFailed(err, recipe);
    });
  }

  function submitFailed(err, recipe) {
    const status = err && err.status;
    serving = false;
    updateAction();                       // вернуть кнопку и «Выбрать другую пиццу»
    if (status === 403) {
      // пиццерию выключили (или сессия кончилась) — дорога на ферму
      hint.textContent = "Пиццерия сейчас закрыта. Вернись на ферму.";
      showAlert('<p class="pz-alert-title">Пиццерия закрыта.</p>' +
        '<a class="btn btn-small btn-primary" href="' + FARM + '">На ферму</a>');
      action.disabled = true;
      action.textContent = "Закрыто";
      return;
    }
    const missing = (err && err.missing) || [];
    if (status === 400 && missing.length) {
      const names = missing.map(function (k) {
        const n = (recipe.need || []).find(function (x) { return x.key === k; });
        return n ? n.ru : k;
      });
      hint.textContent = "Не хватает: " + names.join(", ") + ".";
      showAlert(barnHtml(recipe));
      return;
    }
    hint.textContent = "Не получилось подать пиццу. Проверь связь и попробуй ещё раз.";
  }

  function showResult(gained, already, recipe) {
    cook.hidden = true;
    result.hidden = false;
    const img = $("pz-result-img");
    img.src = withVer("pizza_" + recipe.key + "_baked.png");
    img.alt = "Пицца «" + recipe.ru + "»";
    $("pz-result-title").textContent = "Готово! " + recipe.en;
    let text;
    if (gained > 0) {
      text = "Пицца «" + esc(recipe.ru) + "» готова! Вот <b class=\"pz-gain\">" + coinIcon + "+" +
        gained + "</b> " + coinsWord(gained) + " за новый рецепт.";
    } else if (already) {
      text = "Пицца «" + esc(recipe.ru) + "» готова! Монетки дают за первый раз каждого рецепта.";
    } else {
      text = "Пицца «" + esc(recipe.ru) + "» готова!";
    }
    $("pz-result-text").innerHTML = text;
    renderMenu();
    try { result.focus({ preventScroll: false }); } catch (e) { result.focus(); }
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (window.ttsSpeak) window.ttsSpeak("Here you are!", 0.9);
  }

  // ── нажатия ───────────────────────────────────────────────────────────────
  action.addEventListener("click", function () {
    if (!action.disabled) next();
  });
  switchBtn.addEventListener("click", backToMenu);
  $("pz-more").addEventListener("click", backToMenu);
  $("pz-fill").addEventListener("click", fillAll);
  pizzaWrap.addEventListener("click", function (e) {
    if (step !== 2) return;
    const p = pointOnPizza(e.clientX, e.clientY);
    if (p) place(p.x, p.y);
  });
  $("pz-audio").addEventListener("click", function () {
    if (current && window.ttsSpeak) {
      window.ttsSpeak("Can I have a " + current.en + " pizza, please?", 0.9);
    }
  });

  $("pz-kitchen").src = withVer("kitchen.webp");
  renderMenu();
})();
