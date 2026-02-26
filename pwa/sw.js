/**
 * ERG PWA Service Worker
 * Cache strategy: cache-first for shell + air_monitoring_table.json.
 * Bump CACHE_VERSION when deploying to invalidate old caches.
 */
const CACHE_VERSION = 'erg-pwa-v3';
const CACHE_SHELL = `${CACHE_VERSION}-shell`;
const CACHE_TABLE = `${CACHE_VERSION}-table`;

const SHELL_URLS = [
  './',
  './index.html',
  './table.html',
  './hasp.html',
  './manifest.json'
];

const TABLE_URL = './air_monitoring_table.json';
const SENSOR_PART_URL = './sensor_part_numbers.json';

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_SHELL).then((cache) => cache.addAll(SHELL_URLS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k.startsWith('erg-pwa-') && k !== CACHE_SHELL && k !== CACHE_TABLE).map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.endsWith('air_monitoring_table.json') || url.pathname.endsWith('sensor_part_numbers.json') || url.pathname.endsWith('sensor_cross_sens.json')) {
    event.respondWith(
      caches.open(CACHE_TABLE).then((cache) =>
        cache.match(request).then((cached) => {
          const fetchPromise = fetch(request).then((res) => {
            if (res.ok) cache.put(request, res.clone());
            return res;
          });
          return cached || fetchPromise;
        })
      )
    );
    return;
  }

  const path = url.pathname;
  const shellMatch = path === '/' || path === '/index.html' || path === '/table.html' || path === '/hasp.html' ||
    SHELL_URLS.some((u) => path === new URL(u, self.location.origin).pathname);
  if (shellMatch) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request))
    );
  }
});
