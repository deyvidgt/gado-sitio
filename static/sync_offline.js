// Fila offline única para formulários e leituras IoT.
(function () {
  const DB_NOME = "gado-offline", STORE = "fila_geral", DB_VERSAO = 4;
  let enviando = false;

  function contexto() {
    const meta = (nome) => document.querySelector(`meta[name="${nome}"]`)?.content || "";
    return {usuario: meta("offline-usuario"), sitio: meta("offline-sitio")};
  }

  function abrirDB() {
    return new Promise((ok, falha) => {
      const req = indexedDB.open(DB_NOME, DB_VERSAO);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, {keyPath: "id_envio"});
        }
        if (e.oldVersion < 4) migrarFilaIoT(db);
      };
      req.onsuccess = () => ok(req.result);
      req.onerror = () => falha(req.error);
    });
  }

  function migrarFilaIoT(db) {
    const antiga = localStorage.getItem("iot_fila_offline");
    if (!antiga || !db.objectStoreNames.contains(STORE)) return;
    let itens;
    try { itens = JSON.parse(antiga); } catch (_) { return; }
    const store = db.transaction(STORE, "readwrite").objectStore(STORE);
    for (const item of Array.isArray(itens) ? itens : []) {
      const id = String(item.id_envio || crypto.randomUUID());
      store.put({
        id_envio: id, url: "/api/iot/sync", metodo: "POST",
        tipo: item.tipo || "", dados: item.dados || {},
        usuario: contexto().usuario, sitio: contexto().sitio,
        criado_em: item.criado_em || Date.parse(item.timestamp) || Date.now(),
        tentativas: 0, ultimo_erro: ""
      });
    }
    // Mantém a fila legada para recuperação manual; o versionamento impede nova importação.
    localStorage.setItem("iot_fila_offline_migrated_v4", "1");
  }

  async function operar(modo, fn) {
    const db = await abrirDB();
    return new Promise((ok, falha) => {
      const tx = db.transaction(STORE, modo), req = fn(tx.objectStore(STORE));
      tx.oncomplete = () => { db.close(); ok(req?.result); };
      tx.onerror = () => { db.close(); falha(tx.error); };
    });
  }

  function novoId() { return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`; }
  const listar = () => operar("readonly", s => s.getAll());
  const guardar = (item) => operar("readwrite", s => s.put(item));
  const remover = (id) => operar("readwrite", s => s.delete(id));
  const atualizar = (item) => guardar(item);

  async function enqueue({url, metodo = "POST", dados = {}, tipo = "formulario"}) {
    const ctx = contexto();
    if (!ctx.usuario || !ctx.sitio) throw new Error("Sessão ou sítio ausente; registro bloqueado");
    const item = {id_envio: novoId(), url, metodo, dados, tipo, ...ctx,
      criado_em: Date.now(), tentativas: 0, ultimo_erro: ""};
    await guardar(item); atualizarBanner(); return item.id_envio;
  }

  async function sincronizar() {
    if (enviando || !navigator.onLine) return;
    const itens = (await listar()).sort((a, b) => a.criado_em - b.criado_em);
    if (!itens.length) { atualizarBanner(); return; }
    enviando = true;
    try {
      const response = await fetch("/api/sync", {
        method: "POST", headers: {"Content-Type": "application/json"},
        credentials: "same-origin", body: JSON.stringify({itens})
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const resultados = (await response.json()).resultados || [];
      for (const resultado of resultados) {
        if (["processado", "duplicado"].includes(resultado.status)) await remover(resultado.id_envio);
        else if (["erro_transitorio", "invalido"].includes(resultado.status)) {
          const item = itens.find((i) => i.id_envio === resultado.id_envio);
          if (item) { item.tentativas++; item.ultimo_erro = resultado.msg || resultado.status; await atualizar(item); }
        }
      }
    } catch (e) {
      for (const item of itens) { item.tentativas++; item.ultimo_erro = e.message; await atualizar(item); }
      console.error("Erro na sincronização offline:", e);
    } finally { enviando = false; atualizarBanner(); }
  }

  function criarBanner() {
    if (document.getElementById("offline-sync-banner")) return;
    const banner = document.createElement("div"); banner.id = "offline-sync-banner";
    banner.style.cssText = "display:none;position:fixed;bottom:0;left:0;width:100%;background:#e67e22;color:#fff;text-align:center;padding:10px;font-size:13px;font-weight:700;z-index:99999";
    document.body.appendChild(banner);
  }
  async function atualizarBanner() {
    criarBanner(); const banner = document.getElementById("offline-sync-banner");
    try { const n = (await listar()).length; banner.style.display = n ? "block" : "none";
      if (n) banner.textContent = `📶 Modo Offline: ${n} alteração(ões) pendente(s).`;
    } catch (_) { banner.style.display = "none"; }
  }

  document.addEventListener("submit", async (e) => {
    const form = e.target;
    if (form.tagName !== "FORM" || form.method.toUpperCase() !== "POST" || navigator.onLine) return;
    e.preventDefault();
    const dados = Object.fromEntries([...new FormData(form)].filter(([, v]) => typeof v === "string"));
    await enqueue({url: form.action || location.href, dados});
    alert("📶 Sem internet: registro guardado neste dispositivo e será sincronizado ao voltar o sinal.");
    window.location.reload();
  });

  window.offlineSync = {enqueue, sync: sincronizar, pendingCount: async () => (await listar()).length};
  window.addEventListener("online", sincronizar);
  document.addEventListener("DOMContentLoaded", () => { criarBanner(); atualizarBanner(); sincronizar(); setInterval(sincronizar, 30000); });
})();
