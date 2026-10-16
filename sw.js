// ═══════════════════════════════════════════════════════════════════
//  sw.js — Sítio Santo Antonio v4.1
//  Estratégia:
//  • Assets estáticos (CSS, JS, fontes) → cache-first
//  • Páginas HTML                       → network-first
//  • APIs /api/*                        → SEMPRE network, sem cache
//    (evita o bug "body is locked" e garante dados sempre frescos)
// ═══════════════════════════════════════════════════════════════════

const CACHE_VERSION = "gado-v5";   // troca de versão limpa o cache antigo dos celulares
const CACHE_STATIC  = `${CACHE_VERSION}-static`;
const CACHE_PAGES   = `${CACHE_VERSION}-pages`;

const STATIC_ASSETS = [
  "/static/icon.svg",
  "/static/icon-192.png",
  "/static/icon-512.png",
  "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;700&family=DM+Sans:wght@300;400;500;600&display=swap",
  "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js",
];

// ── Instalação ────────────────────────────────────────────────────
self.addEventListener("install", evt => {
  self.skipWaiting();
  evt.waitUntil(
    caches.open(CACHE_STATIC).then(cache =>
      cache.addAll(STATIC_ASSETS).catch(() => {})
    )
  );
});

// ── Ativação: limpar caches antigos ──────────────────────────────
self.addEventListener("activate", evt => {
  evt.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k.startsWith("gado-") && k !== CACHE_STATIC && k !== CACHE_PAGES)
          .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch ─────────────────────────────────────────────────────────
self.addEventListener("fetch", evt => {
  const url = new URL(evt.request.url);

  // Só tratar GET
  if (evt.request.method !== "GET") return;

  // ── APIs: NUNCA cachear — passa direto para a rede ────────────
  // Isso elimina o bug "body is locked" e garante dados frescos.
  // Fotos (v4.4): o navegador já guarda pelo Cache-Control; não misturar no cache de páginas.
  if (url.pathname.startsWith("/fotos/")) return;

  if (url.pathname.startsWith("/api/")) {
    // Deixa o browser lidar normalmente (não chama evt.respondWith)
    return;
  }

  // Ignorar cross-origin exceto CDN e fontes conhecidas
  if (url.origin !== location.origin &&
      !url.hostname.includes("fonts.googleapis.com") &&
      !url.hostname.includes("fonts.gstatic.com") &&
      !url.hostname.includes("cdn.jsdelivr.net")) return;

  // ── Assets estáticos → cache-first ───────────────────────────
  if (url.pathname.startsWith("/static/") ||
      url.hostname.includes("fonts.") ||
      url.hostname.includes("cdn.jsdelivr.net")) {
    evt.respondWith(cacheFirst(evt.request));
    return;
  }

  // ── Páginas HTML → network-first com fallback ─────────────────
  evt.respondWith(networkFirstPage(evt.request));
});

// ── Estratégia: cache-first ───────────────────────────────────────
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_STATIC);
      cache.put(request, response.clone());  // clone antes de usar
    }
    return response;
  } catch {
    return new Response("Offline — recurso não disponível", { status: 503 });
  }
}

// ── Estratégia: network-first para páginas ────────────────────────
async function networkFirstPage(request) {
  try {
    const response = await fetch(request);
    // Só guarda PÁGINAS (HTML) que não sejam a de login. Antes guardava também os
    // downloads (planilha de dados, PDF, backups) no celular.
    const tipo = response.headers.get("Content-Type") || "";
    if (response.ok && tipo.includes("text/html") && !new URL(response.url).pathname.startsWith("/login")) {
      const cache = await caches.open(CACHE_PAGES);
      cache.put(request, response.clone());  // clone antes de usar
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    const dashboard = await caches.match("/");
    if (dashboard) return dashboard;
    return offlinePage();
  }
}

// ── Página offline ────────────────────────────────────────────────
function offlinePage() {
  const html = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Sem conexão — Sítio Santo Antonio</title>
  <style>
    body { font-family: sans-serif; background: #f8f4ee;
           display: flex; align-items: center; justify-content: center;
           min-height: 100vh; margin: 0; text-align: center; padding: 20px; }
    .box { max-width: 360px; }
    .icon { font-size: 64px; margin-bottom: 16px; }
    h1 { font-size: 22px; color: #1a3a1f; margin-bottom: 8px; }
    p { font-size: 14px; color: #666; margin-bottom: 24px; line-height: 1.6; }
    a { background: #3d7a34; color: #fff; padding: 10px 24px;
        border-radius: 8px; text-decoration: none; font-weight: 600; }
  </style>
</head>
<body>
  <div class="box">
    <div class="icon">🐄</div>
    <h1>Sem conexão com a internet</h1>
    <p>O sistema do Sítio Santo Antonio precisa de conexão para carregar dados.
       Verifique o Wi-Fi ou dados móveis e tente novamente.</p>
    <a href="/" onclick="location.reload()">Tentar novamente</a>
  </div>
</body>
</html>`;
  return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
}
