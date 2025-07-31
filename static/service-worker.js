self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open('oficina-cache-v1').then(function(cache) {
      return cache.addAll([
        '/',
        '/static/oficina-icon.png',
        '/static/manifest.json'
        // Adicione aqui outras rotas ou arquivos importantes que deseja cachear
      ]);
    })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request).then(function(response) {
      return response || fetch(event.request);
    })
  );
});