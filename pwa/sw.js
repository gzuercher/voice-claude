// Minimal service worker. App responses (HTML/JS/CSS/API) stay
// pass-through so deploys are picked up immediately. The single
// exception is Google Fonts: the CSS and woff2 files are cache-first
// so the wordmark and body font keep rendering when the network is
// flaky and we don't pay a font fetch on every cold load.
const FONT_CACHE = 'voxgate-fonts-v1';
const FONT_HOSTS = new Set(['fonts.googleapis.com', 'fonts.gstatic.com']);

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(
      names.filter((n) => n !== FONT_CACHE).map((n) => caches.delete(n))
    );
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method === 'GET' && FONT_HOSTS.has(url.host)) {
    e.respondWith((async () => {
      const cache = await caches.open(FONT_CACHE);
      const hit = await cache.match(e.request);
      if (hit) return hit;
      const res = await fetch(e.request);
      if (res.ok) cache.put(e.request, res.clone());
      return res;
    })());
    return;
  }
  e.respondWith(fetch(e.request));
});
