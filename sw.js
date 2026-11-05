// Čeština obrazem: offline support. The app files come from the cache at once and are refreshed in the background;
// photos and fonts are kept after the first view so they also work offline.
const APP = 'cz-app-v11';
const CORE = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(APP).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== APP && k !== 'cz-photos' && k !== 'cz-fonts').map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    e.respondWith(caches.open(APP).then(async c => {
      const hit = await c.match(req, { ignoreSearch: true }) || (req.mode === 'navigate' ? await c.match('./index.html') : null);
      const net = fetch(req).then(res => { if (res.ok) c.put(req, res.clone()); return res; }).catch(() => null);
      return hit || (await net) || new Response('Offline', { status: 503 });
    }));
    return;
  }
  const isPhoto = /(^|\.)wikimedia\.org$/.test(url.hostname) && !url.pathname.includes('/api.php');
  const isFont = /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname);
  if (isPhoto || isFont) {
    e.respondWith(caches.open(isPhoto ? 'cz-photos' : 'cz-fonts').then(async c => {
      const hit = await c.match(req);
      if (hit) return hit;
      try { const res = await fetch(req); c.put(req, res.clone()); return res; } catch (err) { return Response.error(); }
    }));
  }
});
