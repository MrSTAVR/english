/* Service worker English Fun. __VERSION__ подставляет сервер: при изменении статики кэш обновляется. */
const VERSION = "__VERSION__";
const CACHE = "english-" + VERSION;
const OFFLINE_URL = "/offline";
const PAGES = "english-pages";   // страницы, посещённые ребёнком: доступны без сети
// Что можно открыть офлайн: уроки, игры, истории, письмо, повторение, слова, теория, главная ученика.
const OFFLINE_OK = [/^\/student$/, /^\/lesson\/\d+$/, /^\/student\/(games|dialogs|stories|writing|review|words|theory|wardrobe|weekly|boss|halloween|newyear|march8|easter|birthday|advent|stickers|map)(\/.*)?$/];
const okOffline = (path) => OFFLINE_OK.some((re) => re.test(path));
const PRECACHE = __PRECACHE__;

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    // по одному: отсутствие одного файла не должно ломать установку
    await Promise.all(PRECACHE.concat([OFFLINE_URL]).map(async (url) => {
      try { await cache.add(new Request(url, { cache: "reload" })); } catch (e) { /* пропускаем */ }
    }));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k.startsWith("english-") && k !== CACHE && k !== PAGES).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;                       // формы (POST) всегда идут в сеть
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Страницы: сначала сеть (свежие данные и CSRF-токены). Страницы уроков/игр запоминаем,
  // и при обрыве сети открываем последнюю версию; иначе — офлайн-страница.
  if (req.mode === "navigate") {
    event.respondWith((async () => {
      try {
        const resp = await fetch(req);
        if (resp && resp.ok && !resp.redirected && okOffline(url.pathname)) {
          const pages = await caches.open(PAGES);
          pages.put(url.pathname, resp.clone());
        }
        return resp;
      } catch (e) {
        if (okOffline(url.pathname)) {
          const pages = await caches.open(PAGES);
          const hit = await pages.match(url.pathname);
          if (hit) return hit;
        }
        return (await caches.match(OFFLINE_URL)) || Response.error();
      }
    })());
    return;
  }

  // Статика: сначала кэш, в фоне обновляем. Строку запроса учитываем: ?v=N — это новая версия файла,
  // иначе подменённый js/css/модель остаются старыми в кэше телефона после выкатки.
  if (url.pathname.startsWith("/static/")) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE);
      const cached = await cache.match(req);
      const network = fetch(req).then((resp) => {
        if (resp && resp.ok) cache.put(req, resp.clone());
        return resp;
      }).catch(() => null);
      return cached || (await network) || Response.error();
    })());
  }
  // остальное (API, healthz и т.п.) — без вмешательства
});

// При выходе из аккаунта стираем запомненные страницы (на общем устройстве).
self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "clear-pages") event.waitUntil(caches.delete(PAGES));
});

// Уведомления от Чик-чика (push.py): показываем и по нажатию открываем приложение.
self.addEventListener("push", (event) => {
  let d = {};
  try { d = event.data ? event.data.json() : {}; } catch (e) { d = { body: event.data && event.data.text() }; }
  event.waitUntil(self.registration.showNotification(d.title || "English Fun", {
    body: d.body || "Чик-чик ждёт тебя!",
    icon: "/static/icons/icon-192.png",
    badge: "/static/icons/favicon-32.png",
    tag: "chick-reminder",          // новое напоминание заменяет старое, а не копится
    data: { url: d.url || "/student" },
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/student";
  event.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of all) {
      if ("focus" in c) { await c.focus(); if ("navigate" in c) await c.navigate(url); return; }
    }
    await self.clients.openWindow(url);
  })());
});
