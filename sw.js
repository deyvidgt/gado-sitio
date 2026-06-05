// ═══════════════════════════════════════════════════════════════════
//  service-worker.js — Sítio Santo Antonio v3.3
//  Estratégia:
//  • Assets estáticos (CSS, JS, fontes) → cache-first
//  • Páginas HTML → network-first (sempre tenta buscar fresco)
//  • APIs /api/* → network-first com fallback de cache (30 min)
//  • Offline fallback: exibe dashboard em cache se não tiver rede
// ═══════════════════════════════════════════════════════════════════

const CACHE_VERSION  = "gado-v1";
const CACHE_STATIC   = `${CACHE_VERSION}-static`;
const CACHE_PAGES    = `${CACHE_VERSION}-pages`;
const CACHE_API      = `${CACHE_VERSION}-api`;

// Assets que vão pro cache estático na instalação
const STATIC_ASSETS = [
  "/static/icon.svg",
  "/static/manifest.json",
  "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;700&family=DM+Sans:wght@300;400;500;600&display=swap",
  "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js",
];

// Páginas pré-cacheadas para uso offline
const PAGES_PRECACHE = ["/"];

// ── Instalação ────────────────────────────────────────────────────
self.addEventListener("install", evt => {
  self.skipWaiting();
  evt.waitUntil(
    caches.open(CACHE_STATIC).then(cache =>
      cache.addAll(STATIC_ASSETS).catch(() => {})  // ignora falhas individuais
    )
  );
});

// ── Ativação: limpar caches antigos ──────────────────────────────
self.addEventListener("activate", evt => {
  evt.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k.startsWith("gado-") && k !== CACHE_STATIC
                    && k !== CACHE_PAGES && k !== CACHE_API)
          .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch: roteamento por tipo de request ─────────────────────────
self.addEventListener("fetch", evt => {
  const url = new URL(evt.request.url);

  // Ignorar requests não-GET e cross-origin (exceto CDN e fontes)
  if (evt.request.method !== "GET") return;
  if (url.origin !== location.origin &&
      !url.hostname.includes("fonts.googleapis.com") &&
      !url.hostname.includes("fonts.gstatic.com") &&
      !url.hostname.includes("cdn.jsdelivr.net")) return;

  // Assets estáticos → cache-first
  if (url.pathname.startsWith("/static/") ||
      url.hostname.includes("fonts.") ||
      url.hostname.includes("cdn.jsdelivr.net")) {
    evt.respondWith(cacheFirst(CACHE_STATIC, evt.request));
    return;
  }

  // APIs → network-first, fallback cache 30 min
  if (url.pathname.startsWith("/api/")) {
    evt.respondWith(networkFirstApi(CACHE_API, evt.request, 30 * 60));
    return;
  }

  // Páginas HTML → network-first, fallback cache
  evt.respondWith(networkFirstPage(CACHE_PAGES, evt.request));
});

// ── Estratégias ───────────────────────────────────────────────────

async function cacheFirst(cacheName, request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response("Offline — recurso não disponível", { status: 503 });
  }
}

async function networkFirstPage(cacheName, request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    // Fallback: dashboard em cache
    const dashboard = await caches.match("/");
    if (dashboard) return dashboard;
    return offlinePage();
  }
}

async function networkFirstApi(cacheName, request, maxAgeSeconds) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      // Salvar com timestamp no header para controle de validade
      const headers = new Headers(response.headers);
      headers.append("sw-cached-at", Date.now().toString());
      const modified = new Response(await response.blob(), {
        status: response.status,
        statusText: response.statusText,
        headers,
      });
      cache.put(request, modified);
      return response;
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) {
      const cachedAt = parseInt(cached.headers.get("sw-cached-at") || "0");
      if (Date.now() - cachedAt < maxAgeSeconds * 1000) {
        return cached;
      }
    }
    return new Response(
      JSON.stringify({ ok: false, erro: "Sem conexão — dados em cache indisponíveis" }),
      { status: 503, headers: { "Content-Type": "application/json" } }
    );
  }
}

function offlinePage() {
  const html = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Sem conexão — Sítio Santo Antonio</title>
  <style>
    body { font-family: 'DM Sans', sans-serif; background: #f8f4ee;
           display: flex; align-items: center; justify-content: center;
           min-height: 100vh; margin: 0; text-align: center; padding: 20px; }
    .box { max-width: 360px; }
    .icon { font-size: 64px; margin-bottom: 16px; }
    h1 { font-size: 22px; color: #1a3a1f; margin-bottom: 8px; }
    p { font-size: 14px; color: #666; margin-bottom: 24px; line-height: 1.6; }
    a { background: #3d7a34; color: #fff; padding: 10px 24px;
        border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 600; }
  </style>
</head>
<body>
  <div class="box">
    <div class="icon">🐄</div>
    <h1>Sem conexão com a internet</h1>
    <p>O sistema de gestão do Sítio Santo Antonio precisa de conexão para carregar dados atualizados.
       Verifique o Wi-Fi ou dados móveis e tente novamente.</p>
    <a href="/" onclick="location.reload()">Tentar novamente</a>
  </div>
</body>
</html>`;
  return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
}
