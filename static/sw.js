/* Service worker English Fun. __VERSION__ подставляет сервер: при изменении статики кэш обновляется. */
const VERSION = "__VERSION__";
const CACHE = "english-" + VERSION;
const OFFLINE_URL = "/offline";
const PAGES = "english-pages";   // страницы, посещённые ребёнком: доступны без сети
// Что можно открыть офлайн: уроки, игры, истории, письмо, повторение, слова, теория, главная ученика.
const OFFLINE_OK = [/^\/student$/, /^\/lesson\/\d+$/, /^\/student\/(games|dialogs|stories|writing|review|words|theory|wardrobe|weekly|boss|halloween|newyear|advent|house|stickers|map)(\/.*)?$/];
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

  // Статика: сначала кэш, в фоне обновляем.
  if (url.pathname.startsWith("/static/")) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE);
      const cached = await cache.match(req, { ignoreSearch: true });
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
