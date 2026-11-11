// ═══════════════════════════════════════════════════════════════════
//  sync_offline.js — Sítio Santo Antonio (v5.16)
//  Sincronização offline total: guarda requisições POST (Manejo, Compras,
//  Vendas, Gastos, Visitas, Pastos) no IndexedDB quando sem internet
//  e sincroniza automaticamente ao recuperar o sinal.
// ═══════════════════════════════════════════════════════════════════
(function () {
  const DB_NOME = "gado-offline", STORE = "fila_geral";
  let enviando = false;

  function abrirDB() {
    return new Promise((ok, falha) => {
      const req = indexedDB.open(DB_NOME, 3);
      req.onupgradeneeded = e => {
        const db = e.target.result;
        for (const nome of ["visitas", "fotos", "fila_geral"]) {
          if (!db.objectStoreNames.contains(nome)) {
            db.createObjectStore(nome, { keyPath: "id_envio" });
          }
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

  const guardar = item => operar("readwrite", s => s.put(item));
  const remover = id => operar("readwrite", s => s.delete(id));
  const listar = () => operar("readonly", s => s.getAll());

  function novoId() {
    if (crypto.randomUUID) return crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  function criarBanner() {
    if (document.getElementById("offline-sync-banner")) return;
    const banner = document.createElement("div");
    banner.id = "offline-sync-banner";
    banner.style.cssText = "display:none;position:fixed;bottom:0;left:0;width:100%;background:#e67e22;color:#fff;text-align:center;padding:10px;font-size:13px;font-weight:700;z-index:99999;box-shadow:0 -2px 10px rgba(0,0,0,0.2);";
    document.body.appendChild(banner);
  }

  async function atualizarBanner() {
    criarBanner();
    const banner = document.getElementById("offline-sync-banner");
    if (!banner) return;
    try {
      const itens = await listar();
      if (itens.length > 0) {
        banner.style.display = "block";
        banner.textContent = `📶 Modo Offline: ${itens.length} alteração(ões) guardada(s) localmente. Sincronizará ao voltar o sinal.`;
      } else {
        banner.style.display = "none";
      }
    } catch (e) {
      banner.style.display = "none";
    }
  }

  async function sincronizarFila() {
    if (enviando || !navigator.onLine) return;
    enviando = true;
    try {
      const itens = await listar();
      if (!itens.length) { enviando = false; atualizarBanner(); return; }

      for (const item of itens.sort((a, b) => a.criado_em - b.criado_em)) {
        const fd = new FormData();
        for (const [k, v] of Object.entries(item.dados)) {
          fd.append(k, v);
        }
        const r = await fetch(item.url, {
          method: "POST",
          body: fd,
          credentials: "same-origin"
        });
        if (r.ok || r.status === 302 || r.status === 200) {
          await remover(item.id_envio);
        } else {
          break; // Se falhar por servidor, tenta mais tarde
        }
      }
    } catch (e) {
      console.error("Erro na sincronização offline:", e);
    } finally {
      enviando = false;
      atualizarBanner();
    }
  }

  // Intercepta submissões de formulários POST críticos quando offline
  document.addEventListener("submit", async e => {
    const form = e.target;
    if (form.tagName !== "FORM" || form.method.toUpperCase() !== "POST") return;
    if (!navigator.onLine) {
      e.preventDefault();
      const formData = new FormData(form);
      const dados = {};
      for (const [k, v] of formData.entries()) {
        if (typeof v === "string") dados[k] = v;
      }
      const item = {
        id_envio: novoId(),
        url: form.action || window.location.href,
        dados: dados,
        criado_em: Date.now()
      };
      await guardar(item);
      await atualizarBanner();
      alert("📶 Sem internet: seu registro foi guardado com segurança no telemóvel e será enviado assim que o sinal voltar!");
      if (form.dataset.redirecionar) {
        window.location.href = form.dataset.redirecionar;
      } else {
        window.location.reload();
      }
    }
  });

  window.addEventListener("online", () => {
    sincronizarFila();
  });

  document.addEventListener("DOMContentLoaded", () => {
    criarBanner();
    atualizarBanner();
    if (navigator.onLine) {
      sincronizarFila();
    }
    setInterval(sincronizarFila, 30000); // Tenta sincronizar a cada 30 segundos
  });
})();
