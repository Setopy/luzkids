/* LuzKids Service Worker — offline-first for installed app experience */
const CACHE = "luzkids-v1";
const PRECACHE = [
  "/", "/library", "/static/css/style.css",
  "/static/js/lesson.js", "/static/js/games.js", "/static/js/main.js",
  "/static/icons/icon-192x192.png", "/static/icons/icon-512x512.png"
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ).then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  // Never intercept POST requests
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/series/") ||
      url.pathname.startsWith("/certificate/")) {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
  } else {
    e.respondWith(
      caches.match(e.request).then(cached => {
        const fresh = fetch(e.request).then(res => {
          if (res && res.status === 200) {
            const clone = res.clone();
            caches.open(CACHE).then(c => c.put(e.request, clone));
          }
          return res;
        });
        return cached || fresh;
      })
    );
  }
});
