/* DS単語 — Service Worker for offline support */

const CACHE_VERSION = 'ds-tango-v2';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const AUDIO_CACHE = `${CACHE_VERSION}-audio`;

// Files cached on install (shell) — small, must always be available offline.
const STATIC_ASSETS = [
  './',
  './index.html',
  './style.css',
  './app.js',
  './manifest.json',
  './i18n/ja.json',
  './data/vocabulary.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => Promise.all(
        // cache:'reload' forces bypassing the HTTP cache so an updated SW
        // always sees the newest static assets.
        STATIC_ASSETS.map((url) =>
          fetch(url, { cache: 'reload' }).then((resp) => {
            if (resp.ok) return cache.put(url, resp);
          })
        )
      ))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys
        .filter((k) => !k.startsWith(CACHE_VERSION))
        .map((k) => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // ignore cross-origin

  // Audio files: cache on first play (lazy)
  if (url.pathname.startsWith('/audio/') || url.pathname.includes('/audio/')) {
    event.respondWith(
      caches.open(AUDIO_CACHE).then(async (cache) => {
        const hit = await cache.match(req);
        if (hit) return hit;
        try {
          const resp = await fetch(req);
          if (resp.ok) cache.put(req, resp.clone());
          return resp;
        } catch (e) {
          return new Response('', { status: 504 });
        }
      })
    );
    return;
  }

  // Everything else: cache-first, then network, then cache
  event.respondWith(
    caches.match(req).then((hit) => {
      if (hit) return hit;
      return fetch(req).then((resp) => {
        if (resp.ok) {
          caches.open(STATIC_CACHE).then((c) => c.put(req, resp.clone()));
        }
        return resp;
      }).catch(() => caches.match('./index.html'));
    })
  );
});
