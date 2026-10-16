// ═══════════════════════════════════════════════════════════════════
//  fila_visitas.js — Sítio Santo Antonio (v4.2)
//  Visitas registradas SEM INTERNET ficam guardadas no celular (IndexedDB)
//  e são enviadas sozinhas quando o sinal volta: ao abrir
//  qualquer página do sistema, ao reconectar e a cada minuto com pendências.
//
//  Cada visita tem um código único (id_envio): se o envio chegar ao servidor
//  mas a confirmação se perder, o reenvio não grava a visita duas vezes.
// ═══════════════════════════════════════════════════════════════════
(function () {
  const DB_NOME = "gado-offline", STORE = "visitas";
  const TEMPO_LIMITE_MS = 25000;
  let enviando = false;

  function abrirDB() {
    return new Promise((ok, falha) => {
      // v2 (v4.4): o mesmo banco guarda também as fotos (fila_fotos.js abre igual).
      const req = indexedDB.open(DB_NOME, 2);
      req.onupgradeneeded = () => {
        for (const nome of ["visitas", "fotos"]) {
          if (!req.result.objectStoreNames.contains(nome)) req.result.createObjectStore(nome, { keyPath: "id_envio" });
        }
      };
      req.onsuccess = () => ok(req.result);
      req.onerror = () => falha(req.error);
    });
  }

  async function operar(modo, fn) {
    const db = await abrirDB();
    return new Promise((ok, falha) => {
      const tx = db.transaction(STORE, modo);
      const req = fn(tx.objectStore(STORE));
      tx.oncomplete = () => { db.close(); ok(req && req.result); };
      tx.onerror = () => { db.close(); falha(tx.error); };
    });
  }

  const guardar  = item => operar("readwrite", s => s.put(item));
  const remover  = id   => operar("readwrite", s => s.delete(id));
  const listar   = ()   => operar("readonly",  s => s.getAll());

  function novoId() {
    if (crypto.randomUUID) return crypto.randomUUID();
    return Array.from(crypto.getRandomValues(new Uint8Array(16)),
                      b => b.toString(16).padStart(2, "0")).join("");
  }

  // Token CSRF da sessão ATUAL (a página guardada no celular pode ter um antigo).
  async function tokenAtual() {
    const r = await fetch("/api/csrf", { credentials: "same-origin", cache: "no-store" });
    if (r.status === 401) return { erro: "login" };
    if (!r.ok) return { erro: "rede" };
    return { token: (await r.json()).csrf_token };
  }

  // Envia uma visita. Retorna {ok, motivo, gado_faltando}.
  async function enviar(item, token) {
    const fd = new FormData();
    for (const [k, v] of item.campos) fd.append(k, v);
    fd.set("id_envio", item.id_envio);
    fd.set("csrf_token", token);

    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), TEMPO_LIMITE_MS);
    try {
      const r = await fetch("/api/visitas", { method: "POST", body: fd,
                                              credentials: "same-origin", signal: ctrl.signal });
      if (r.status === 401) return { ok: false, motivo: "login" };
      if (r.status === 403) return { ok: false, motivo: "csrf" };
      if (!r.ok) return { ok: false, motivo: "servidor" };
      const d = await r.json();
      return { ok: !!d.ok, gado_faltando: d.gado_faltando || 0 };
    } catch (e) {
      return { ok: false, motivo: "rede" };
    } finally {
      clearTimeout(t);
    }
  }

  // Usado pelo formulário: tenta enviar já; sem sucesso, guarda no celular.
  async function enviarOuGuardar(item) {
    if (navigator.onLine) {
      const tk = await tokenAtual().catch(() => ({ erro: "rede" }));
      if (tk.token) {
        const r = await enviar(item, tk.token);
        if (r.ok) return { enviada: true, gado_faltando: r.gado_faltando };
        if (r.motivo === "servidor") {
          // Erro do servidor (não de rede): guarda também, para não perder a visita.
          try { await guardar(item); atualizarAviso(); return { guardada: true, motivo: "servidor" }; }
          catch (e) { return {}; }
        }
      }
      if (tk.erro === "login") {
        try { await guardar(item); atualizarAviso(); return { guardada: true, motivo: "login" }; }
        catch (e) { return {}; }
      }
    }
    try { await guardar(item); atualizarAviso(); return { guardada: true, motivo: "rede" }; }
    catch (e) { return {}; }
  }

  // Envia tudo o que está guardado. Retorna quantas foram enviadas.
  async function enviarPendentes() {
    // Sem checar navigator.onLine: logo após o sinal voltar ele ainda diz "offline"
    // (e às vezes diz "online" sem internet). Tentar e falhar não custa nada.
    if (enviando || !window.indexedDB) return 0;
    enviando = true;
    let enviadas = 0;
    try {
      const itens = await listar();
      if (!itens.length) return 0;
      const tk = await tokenAtual();
      if (!tk.token) return 0;
      for (const item of itens.sort((a, b) => a.criado_em - b.criado_em)) {
        const r = await enviar(item, tk.token);
        if (r.ok) { await remover(item.id_envio); enviadas++; }
        else if (r.motivo === "rede" || r.motivo === "login") break;   // tenta mais tarde
      }
    } catch (e) {
      /* sem IndexedDB/rede: tenta na próxima vez */
    } finally {
      enviando = false;
    }
    await atualizarAviso(enviadas);
    return enviadas;
  }

  // Faixa no topo das páginas: "N visita(s) aguardando envio".
  async function atualizarAviso(enviadas = 0) {
    const alvo = document.querySelector(".content") || document.body;
    let faixa = document.getElementById("fila-visitas-aviso");
    let pendentes = 0;
    try { pendentes = (await listar()).length; } catch (e) { return; }
    if (!pendentes && !enviadas) { if (faixa) faixa.remove(); return; }
    if (!faixa) {
      faixa = document.createElement("div");
      faixa.id = "fila-visitas-aviso";
      faixa.style.cssText = "margin:0 0 14px;padding:10px 14px;border-radius:10px;font-size:13.5px;" +
                            "display:flex;align-items:center;gap:10px;flex-wrap:wrap";
      alvo.prepend(faixa);
    }
    if (pendentes) {
      faixa.style.background = "var(--gold-lt)"; faixa.style.border = "1.5px solid var(--gold)";
      faixa.style.color = "var(--text)";
      faixa.innerHTML = `📴 <span><strong>${pendentes} visita(s)</strong> guardada(s) neste celular, aguardando internet para enviar.</span>`;
      const b = document.createElement("button");
      b.type = "button"; b.className = "btn btn-outline btn-sm"; b.textContent = "📤 Enviar agora";
      b.onclick = () => { b.disabled = true; b.textContent = "⏳ Enviando..."; enviarPendentes(); };
      faixa.append(b);
    } else {
      faixa.style.background = "var(--green-50)"; faixa.style.border = "1.5px solid var(--green-200)";
      faixa.style.color = "var(--green-700)";
      faixa.textContent = `✅ ${enviadas} visita(s) guardada(s) no celular foram enviadas.`;
      setTimeout(() => faixa.remove(), 8000);
    }
  }

  // Deixa o formulário de visita guardado no celular para abrir sem internet
  // (o service worker guarda a página). No máximo a cada 6 horas.
  function prepararFormularioOffline() {
    // Só quem guarda a página é o service worker: se ele ainda não controla esta
    // aba (1ª abertura do app), buscar agora não guardaria nada — e o intervalo
    // de 6 h impediria nova tentativa. Tenta quando ele assumir.
    if (!navigator.serviceWorker || !navigator.serviceWorker.controller) {
      if (navigator.serviceWorker) {
        navigator.serviceWorker.addEventListener("controllerchange", prepararFormularioOffline, { once: true });
      }
      return;
    }
    try {
      const ult = +localStorage.getItem("gado-form-visita-ts") || 0;
      if (Date.now() - ult < 6 * 3600 * 1000) return;
      fetch("/visitas/nova", { credentials: "same-origin" }).then(r => {
        if (r.ok && !r.redirected) localStorage.setItem("gado-form-visita-ts", String(Date.now()));
      }).catch(() => {});
    } catch (e) { /* sem localStorage: ignora */ }
  }

  window.FilaVisitas = { novoId, enviarOuGuardar, enviarPendentes, listar };

  if (!window.indexedDB) return;
  window.addEventListener("online", enviarPendentes);
  document.addEventListener("DOMContentLoaded", () => {
    atualizarAviso();
    enviarPendentes();
    prepararFormularioOffline();
  });
  setInterval(async () => {
    try { if ((await listar()).length) enviarPendentes(); } catch (e) {}
  }, 30000);
})();
