/* ============================================================
   NutriTrack Service Worker
   Cache name: nutritrack-v1
   Strategy:
     - /static/* → cache-first (CSS, JS, images, manifest)
     - /api/*    → network-first (always try live, fall back to cache)
     - pages     → network-first
   ============================================================ */

var CACHE_NAME = 'nutritrack-v1';

var STATIC_SHELL = [
  '/',
  '/offline',
  '/static/css/style.css',
  '/static/js/i18n.js',
  '/static/js/app.js',
  '/static/js/dashboard.js',
  '/static/js/history.js',
  '/static/js/foods.js',
  '/static/js/meal_templates.js',
  '/static/js/chat.js',
  '/static/js/settings.js',
  '/static/manifest.json',
  '/static/icon.svg',
];

/* ---- Install: pre-cache static shell ---- */
self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(STATIC_SHELL);
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

/* ---- Activate: remove old caches ---- */
self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (k) { return k !== CACHE_NAME; })
            .map(function (k) { return caches.delete(k); })
      );
    }).then(function () {
      return self.clients.claim();
    })
  );
});

/* ---- Fetch handler ---- */
self.addEventListener('fetch', function (event) {
  var url = new URL(event.request.url);

  /* Only handle GET requests on the same origin */
  if (event.request.method !== 'GET' || url.origin !== location.origin) {
    return;
  }

  /* API routes: network-first, fall back to cache */
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(event.request));
    return;
  }

  /* Static assets: cache-first */
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  /* HTML pages: network-first */
  event.respondWith(networkFirst(event.request));
});

function cacheFirst(request) {
  return caches.open(CACHE_NAME).then(function (cache) {
    return cache.match(request).then(function (cached) {
      if (cached) return cached;
      return fetch(request).then(function (response) {
        if (response && response.status === 200) {
          cache.put(request, response.clone());
        }
        return response;
      });
    });
  });
}

function networkFirst(request) {
  return caches.open(CACHE_NAME).then(function (cache) {
    return fetch(request).then(function (response) {
      if (response && response.status === 200) {
        cache.put(request, response.clone());
      }
      return response;
    }).catch(function () {
      var cached = cache.match(request);
      if (cached) return cached;

      /* For navigation requests (HTML pages), fall back to offline page */
      if (request.mode === 'navigate') {
        return cache.match('/offline');
      }

      /* For other requests, return a basic offline response */
      return new Response('Offline - resource not available', {
        status: 503,
        statusText: 'Service Unavailable',
        headers: new Headers({
          'Content-Type': 'text/plain'
        })
      });
    });
  });
}
