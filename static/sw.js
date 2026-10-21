/* Service worker English Fun. __VERSION__ подставляет сервер: при изменении статики кэш обновляется. */
const VERSION = "__VERSION__";
const CACHE = "english-" + VERSION;
const OFFLINE_URL = "/offline";
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
    await Promise.all(keys.filter((k) => k.startsWith("english-") && k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;                       // формы (POST) всегда идут в сеть
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Страницы: только сеть (там личные данные и CSRF-токены), при обрыве — офлайн-страница.
  if (req.mode === "navigate") {
    event.respondWith(fetch(req).catch(async () => (await caches.match(OFFLINE_URL)) || Response.error()));
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
