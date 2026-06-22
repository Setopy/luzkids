/* LuzKids Service Worker — minimal and bulletproof.
   Only static assets (css/js/icons) are cached.
   Every dynamic request (pages, API calls) bypasses the service worker
   completely and goes straight to the network, exactly as if there were
   no service worker at all. This is deliberate: a content-heavy, frequently
   updated site gains far more from "always fresh" than from offline caching
   of dynamic pages, and this approach eliminates an entire class of bugs
   (stale cache, undefined Response, rejected fetch events) that come from
   trying to be clever about caching dynamic content. */

const CACHE = "luzkids-static-v4";
const PRECACHE = [
  "/static/css/style.css",
  "/static/js/lesson.js",
  "/static/js/games.js",
  "/static/js/main.js",
  "/static/icons/icon-192x192.png",
  "/static/icons/icon-512x512.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(PRECACHE))
      .catch(() => {}) // never let a precache failure block install
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;

  // Only ever intervene for GET requests to our own static assets.
  // Everything else — every page, every POST, every API call —
  // is left completely alone and handled natively by the browser.
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (!url.pathname.startsWith("/static/")) return;

  // Cache-first for static assets, with a safe network fallback.
  e.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req).then((res) => {
        if (res && res.ok) {
          const clone = res.clone();
          caches.open(CACHE).then((c) => c.put(req, clone)).catch(() => {});
        }
        return res;
      });
    }).catch(() => fetch(req)) // absolute last resort: just go to network
  );
});
