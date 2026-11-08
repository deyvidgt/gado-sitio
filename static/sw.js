/**
 * Service Worker v5.7
 * Estratégias de cache: cache-first (assets), network-first (API),
 * stale-while-revalidate (HTML)
 *
 * Instalação em app.py:
 * @app.route('/sw.js')
 * def service_worker():
 *   return send_file('static/sw.js', mimetype='application/javascript')
 */

const CACHE_VERSION = 'v5.8';
const CACHE_ASSETS = `${CACHE_VERSION}-assets`;
const CACHE_PAGES = `${CACHE_VERSION}-pages`;
const CACHE_API = `${CACHE_VERSION}-api`;

/**
 * Assets críticos para pre-cache no install
 * Inclui CSS, JS, fonts necessários para funcionar offline
 */
const CRITICAL_ASSETS = [
  '/static/design-tokens.css',
  '/static/css/skeleton.css',
  '/static/js/lazy-images.js',
  '/manifest.json',
  '/_offline.html',
];

/**
 * INSTALL: Pre-cache assets críticos
 */
self.addEventListener('install', (event) => {
  console.log('[SW] Installing v5.8...');
  event.waitUntil(
    caches.open(CACHE_ASSETS).then((cache) => {
      console.log('[SW] Pre-caching critical assets');
      return cache.addAll(CRITICAL_ASSETS).catch((err) => {
        console.warn('[SW] Pre-cache failed (alguns assets podem estar indisponíveis):', err);
        // Não falhar o install se algum asset não estiver disponível
      });
    })
  );
  self.skipWaiting(); // Ativar imediatamente
});

/**
 * ACTIVATE: Limpar caches antigos
 */
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          // Deletar caches de versões antigas
          if (
            !cacheName.includes(CACHE_VERSION)
          ) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim(); // Tomar controle de abas abertas imediatamente
});

/**
 * FETCH: Estratégias de cache por tipo de requisição
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignorar requisições não-GET
  if (request.method !== 'GET') {
    return;
  }

  // ========== CACHE-FIRST: Assets (CSS, JS, fonts, imagens) ==========
  if (isAsset(request)) {
    event.respondWith(cacheFirst(request, CACHE_ASSETS));
    return;
  }

  // ========== NETWORK-FIRST: API calls ==========
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request, CACHE_API));
    return;
  }

  // ========== NETWORK-FIRST: Páginas HTML ==========
  // Sempre busca no servidor para evitar páginas obsoletas no telemóvel.
  if (request.destination === 'document' || request.destination === '') {
    event.respondWith(networkFirst(request, CACHE_PAGES));
    return;
  }

  // Default: network first com fallback offline
  event.respondWith(networkWithFallback(request));
});

/**
 * Detectar se é um asset (CSS, JS, font, imagem, etc)
 */
function isAsset(request) {
  const destination = request.destination;
  const url = new URL(request.url);

  return (
    destination === 'style' ||
    destination === 'script' ||
    destination === 'font' ||
    destination === 'image' ||
    url.pathname.match(/\.(css|js|woff|woff2|ttf|eot|svg|png|jpg|jpeg|gif|webp)$/i)
  );
}

/**
 * CACHE-FIRST: Procura no cache primeiro, depois faz fetch
 * Ideal para assets que mudam raramente
 */
function cacheFirst(request, cacheName) {
  return caches
    .match(request)
    .then((response) => {
      if (response) {
        console.log('[SW] Cache hit:', request.url);
        return response;
      }

      // Não está em cache, fazer fetch
      return fetch(request)
        .then((response) => {
          // Guardar no cache apenas se status OK
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(cacheName).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          // Offline: retornar placeholder ou nada
          console.log('[SW] Offline (fetch failed):', request.url);
          return new Response('Offline - recurso não disponível', {
            status: 503,
            statusText: 'Service Unavailable',
          });
        });
    });
}

/**
 * NETWORK-FIRST: Tenta fetch primeiro, depois cache
 * Ideal para API que precisa de dados frescos
 */
function networkFirst(request, cacheName) {
  return fetch(request)
    .then((response) => {
      // Guardar resposta bem-sucedida em cache
      if (response.status === 200) {
        const responseClone = response.clone();
        caches.open(cacheName).then((cache) => {
          cache.put(request, responseClone);
        });
      }
      console.log('[SW] Network fresh:', request.url);
      return response;
    })
    .catch(() => {
      // Offline: procurar no cache
      return caches
        .match(request)
        .then((response) => {
          if (response) {
            console.log('[SW] Cache fallback (offline):', request.url);
            return response;
          }
          // Nada em cache, retornar erro offline
          return new Response(
            JSON.stringify({ error: 'Offline', data: null }),
            {
              status: 503,
              headers: { 'Content-Type': 'application/json' },
            }
          );
        });
    });
}

/**
 * STALE-WHILE-REVALIDATE: Retorna cache imediatamente, faz fetch em background
 * Ideal para páginas HTML (rapidez + atualização eventual)
 */
function staleWhileRevalidate(request, cacheName) {
  return caches.match(request).then((cached) => {
    // Fazer fetch em background
    const fresh = fetch(request).then((response) => {
      // Atualizar cache se status OK
      if (response.status === 200) {
        const responseClone = response.clone();
        caches.open(cacheName).then((cache) => {
          cache.put(request, responseClone);
        });
      }
      return response;
    });

    // Retornar cache ou fetch (o que vier primeiro)
    return cached || fresh;
  });
}

/**
 * NETWORK WITH FALLBACK: Tenta network, se falhar tenta cache, senão offline
 */
function networkWithFallback(request) {
  return fetch(request)
    .then((response) => {
      // Guardar em cache
      if (response.status === 200) {
        const responseClone = response.clone();
        caches.open(CACHE_PAGES).then((cache) => {
          cache.put(request, responseClone);
        });
      }
      return response;
    })
    .catch(() => {
      return caches
        .match(request)
        .then((response) => {
          return response || caches.match('/_offline.html');
        });
    });
}

/**
 * MESSAGE: Comunicação com cliente (ex.: forçar update)
 */
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CLEAR_CACHE') {
    caches.keys().then((cacheNames) => {
      Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName.includes(CACHE_VERSION)) {
            return caches.delete(cacheName);
          }
        })
      );
    });
  }
});

/**
 * BACKGROUND SYNC: Sincronizar quando voltar online (futuro)
 */
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-api') {
    event.waitUntil(syncPendingRequests());
  }
});

async function syncPendingRequests() {
  // TODO: Implementar fila de requisições pendentes
  console.log('[SW] Background sync placeholder');
}

/**
 * PUSH: Notificações com ações (v5.9)
 */
self.addEventListener('push', (event) => {
  if (!event.data) {
    console.log('[SW] Push recebido sem dados');
    return;
  }

  try {
    const data = event.data.json();
    const options = {
      body: data.body || 'Nova notificação',
      icon: '/static/icon-192x192.png',
      badge: '/static/badge-72x72.png',
      tag: data.tag || 'notificacao',
      requireInteraction: data.urgencia === 'urgente',
      data: { url: data.url || '/', categoria: data.categoria },
      actions: data.actions || []
    };

    // Badge com número de itens
    if (data.badge) {
      options.badge = data.badge;
    }

    event.waitUntil(
      self.registration.showNotification(data.title || 'Gado - Sítio Santo Antonio', options)
    );
  } catch (err) {
    console.error('[SW] Erro ao processar push:', err);
  }
});

/**
 * NOTIFICATION CLICK: Ações nos botões (v5.9)
 */
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  // Ação dos botões
  if (event.action) {
    // POST para /api/notificacoes/acao com {id, acao}
    fetch('/api/notificacoes/acao', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        notification_id: event.notification.tag,
        action: event.action,
        timestamp: new Date().toISOString()
      })
    }).catch((err) => console.error('[SW] Erro ao registrar ação:', err));
  }

  // Abrir/focar na URL
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      // Se já há window aberta, focar nela
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      // Senão, abrir nova window
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});

console.log('[SW] Service Worker v5.8 loaded');
