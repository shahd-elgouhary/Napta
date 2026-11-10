// Service Worker for FieldWise AI (Napta) Farmer PWA
const CACHE_NAME = 'napta-farmer-v1';
const ASSETS = [
  '/farmer/',
  '/farmer/index.html',
  '/farmer/styles/main.css',
  '/farmer/src/app.js',
  '/farmer/manifest.json'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((k) => {
          if (k !== CACHE_NAME) return caches.delete(k);
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((res) => res || fetch(e.request).catch(() => caches.match('/farmer/index.html')))
  );
});
