(function () {
  "use strict";
  const root = document.getElementById("pz");
  if (!root) return;
  const DATA = JSON.parse(document.getElementById("pz-data").textContent);
  const BASE = root.dataset.static || "/static/pizza/";
  const withVer = (name) => BASE + name + "?v=2";
  const $ = (id) => document.getElementById(id);

  const menu = $("pz-menu");
  const cook = $("pz-cook");
  const result = $("pz-result");
  const pizzaImg = $("pz-pizza");
  const title = $("pz-title");
  const hint = $("pz-hint");
  const action = $("pz-action");
  const switchBtn = $("pz-switch");
  const ingredientsBox = $("pz-ingredients");
  const intro = document.querySelector(".pz-intro");
  const steps = Array.from(document.querySelectorAll("#pz-steps li"));

  let current = null;
  let step = 0;
  let picked = new Set();
  let cooking = false;
  let bakeTimer = null;

  const STAGE_IMAGES = {
    0: "pizza_dough_ball.png",
    1: "pizza_dough_flat.png",
    2: "pizza_dough_sauce.png",
  };

  function csrf() {
    const m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.content : "";
  }

  function setCoins(n) {
    const el = $("pz-coins");
    if (el && typeof n === "number") el.textContent = String(n);
  }

  function imageFor(s, recipe) {
    if (s <= 2) {
      if (s === 2 && recipe.key === "caesar") return withVer("pizza_dough_sauce_caesar.png");
      return withVer(STAGE_IMAGES[s]);
    }
    if (s === 3) return withVer("pizza_" + recipe.key + "_top" + picked.size + ".png");
    if (s === 4) return withVer("pizza_" + recipe.key + "_cheese.png");
    return withVer("pizza_" + recipe.key + "_baked.png");
  }

  function clearBake() {
    if (bakeTimer) {
      clearTimeout(bakeTimer);
      bakeTimer = null;
    }
    cooking = false;
  }

  function renderMenu() {
    menu.innerHTML = "";
    DATA.recipes.forEach(function (r) {
      const done = DATA.completed.indexOf(r.key) !== -1;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "pz-card";
      btn.dataset.recipe = r.key;
      const ing = r.ingredients.map(function (i) { return i.en; }).join(" · ");
      const can = r.can !== false;
      const missing = (r.need || []).filter(function (n) { return n.have < n.need; })
        .map(function (n) { return n.ru; }).join(", ");
      btn.disabled = !can;
      btn.title = can ? "" : "Не хватает: " + missing;
      btn.innerHTML =
        '<img src="' + withVer("pizza_" + r.key + "_baked.png") + '" alt="">' +
        (done ? '<span class="pz-done">готово</span>' : (can ? '<span class="pz-new">+ ' + DATA.reward + '</span>' : '')) +
        (can ? '' : '<span class="pz-no">нет продуктов</span>') +
        "<h3>" + r.en + '<span class="pz-card-ru">' + r.ru + "</span></h3>" +
        '<span class="pz-card-ing">' + ing + "</span>" +
        (can ? "" : '<span class="pz-card-ing">нужно: ' + missing + "</span>");
      btn.addEventListener("click", function () { start(r); });
      menu.appendChild(btn);
    });
  }

  function renderIngredients() {
    ingredientsBox.innerHTML = "";
    if (step !== 2 && step !== 3) return;
    current.toppings.forEach(function (i) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "pz-ing" + (picked.has(i.key) ? " on" : "");
      b.dataset.key = i.key;
      b.setAttribute("aria-pressed", picked.has(i.key) ? "true" : "false");
      b.title = i.en + " — " + i.ru;
      b.innerHTML = '<img src="' + withVer(i.key + ".png") + '" alt=""><span>' + i.en + '</span><small>' + i.ru + "</small>";
      b.addEventListener("click", function () {
        if (!current) return;
        if (step === 2) { step = 3; picked.add(i.key); paint(); return; }
        if (picked.has(i.key)) picked.delete(i.key); else picked.add(i.key);
        paint();
      });
      ingredientsBox.appendChild(b);
    });
  }

  function allPicked() {
    return current && picked.size >= current.toppings.length;
  }

  function updateAction() {
    action.disabled = false;
    switchBtn.hidden = cooking;
    if (step === 0) action.textContent = "Раскатать тесто";
    else if (step === 1) action.textContent = "Добавить соус";
    else if (step === 2) {
      action.textContent = "Выбери продукты";
      action.disabled = true;
    } else if (step === 3) {
      action.textContent = allPicked() ? "Посыпать сыром" : "Выбери все продукты";
      action.disabled = !allPicked();
    } else if (step === 4) {
      action.textContent = cooking ? "Печётся…" : "Поставить в печь";
      action.disabled = cooking;
    } else if (step === 5) action.textContent = "Подать Тому";
  }

  function hintText() {
    if (step === 2) return "Нажми на каждый продукт из рецепта — это начинка.";
    if (step === 3) return "Начинки: " + picked.size + " из " + current.toppings.length + ". " + (allPicked() ? "Всё на месте!" : "Нажми на оставшиеся продукты.");
    if (step === 4) return cooking ? "Печётся… Подожди немного." : "Сыр сверху. Пора в печь!";
    if (step === 5) return "Пицца готова. Подай её Тому!";
    if (step === 0) return "Перед тобой кусок теста. Раскатай его скалкой.";
    return "Тесто готово. Теперь намажь соус.";
  }

  function paint() {
    pizzaImg.src = imageFor(step, current);
    pizzaImg.alt = step >= 5 ? "Готовая пицца " + current.ru : "Пицца на кухне";
    steps.forEach(function (li, i) {
      li.classList.toggle("on", i === step);
      li.classList.toggle("done", i < step);
      if (i === step) li.setAttribute("aria-current", "step");
      else li.removeAttribute("aria-current");
    });
    hint.textContent = hintText();
    title.textContent = current.en + " — " + current.ru;
    renderIngredients();
    updateAction();
  }

  function start(recipe) {
    clearBake();
    current = recipe;
    step = 0;
    picked = new Set();
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
    if (intro) intro.hidden = false;
    menu.hidden = false;
    cook.hidden = true;
    result.hidden = true;
    current = null;
  }

  function next() {
    if (!current) return;
    if (step === 0) { step = 1; paint(); return; }
    if (step === 1) { step = 2; paint(); return; }
    if (step === 2 && allPicked()) { step = 3; paint(); return; }
    if (step === 3) { step = 4; paint(); return; }
    if (step === 4) {
      if (cooking) return;
      cooking = true;
      paint();
      bakeTimer = setTimeout(function () {
        bakeTimer = null;
        if (!current) return;
        cooking = false;
        step = 5;
        paint();
      }, 3200);
      return;
    }
    if (step === 5) submit();
  }

  function submit() {
    action.disabled = true;
    action.textContent = "Подаём…";
    fetch("/api/pizza/finish", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() },
      body: JSON.stringify({ recipe: current.key })
    }).then(function (r) {
      return r.json().catch(function () { return null; }).then(function (body) {
        if (!r.ok) throw body || { missing: [] };
        return body;
      });
    }).then(function (res) {
      setCoins(res.coins);
      const key = current.key;
      if (DATA.completed.indexOf(key) === -1) DATA.completed.push(key);
      showResult(res.gained, res.already);
    }).catch(function (err) {
      action.disabled = false;
      action.textContent = "Подать Тому";
      const miss = err && err.missing && err.missing.length
        ? err.missing.map(function (k) {
          const n = (current.need || []).find(function (x) { return x.key === k; });
          return n ? n.ru : k;
        }).join(", ")
        : "";
      hint.textContent = miss
        ? "Не хватает продуктов: " + miss + ". Собери их на ферме."
        : "Не получилось подать пиццу. Попробуй ещё раз.";
    });
  }

  function showResult(gained, already) {
    cook.hidden = true;
    result.hidden = false;
    $("pz-result-img").src = withVer("pizza_" + current.key + "_baked.png");
    $("pz-result-title").textContent = "Готово! " + current.en;
    let text;
    if (gained > 0) {
      text = "Пицца «" + current.ru + "» готова! Вот " + gained + " монетки за новый рецепт.";
    } else if (already) {
      text = "Пицца «" + current.ru + "» готова! Монетки дают за первый раз каждого рецепта.";
    } else {
      text = "Пицца «" + current.ru + "» готова!";
    }
    $("pz-result-text").textContent = text;
    renderMenu();
  }

  action.addEventListener("click", function () {
    if (!action.disabled) next();
  });
  switchBtn.addEventListener("click", backToMenu);
  $("pz-more").addEventListener("click", function () { location.reload(); });
  $("pz-audio").addEventListener("click", function () {
    if (current && window.ttsSpeak) {
      window.ttsSpeak("Can I have a " + current.en + " pizza, please?", 0.9);
    }
  });

  $("pz-kitchen").src = withVer("kitchen.webp");
  renderMenu();
})();
