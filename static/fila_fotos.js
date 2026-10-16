// ═══════════════════════════════════════════════════════════════════
//  fila_fotos.js — Sítio Santo Antonio (v4.4)
//  Fotos dos animais: reduz no celular (1600 px, JPEG) e tenta enviar na
//  hora; sem sinal (ou Drive fora), guarda no IndexedDB e envia sozinha
//  depois — ao abrir qualquer página, ao reconectar e a cada minuto.
//
//  Cada foto tem um id_envio: se o envio chegar mas a resposta se perder,
//  o reenvio não grava a foto duas vezes.
// ═══════════════════════════════════════════════════════════════════
(function () {
  const DB_NOME = "gado-offline", STORE = "fotos";
  const TEMPO_LIMITE_MS = 60000;   // foto pesa mais que visita: espera mais no 3G
  const LADO_MAX = 1600, QUALIDADE = 0.82;
  let rodada = Promise.resolve(0);   // rodadas de envio uma atrás da outra, nunca juntas

  function abrirDB() {
    return new Promise((ok, falha) => {
      // Mesma versão/upgrade de fila_visitas.js (banco compartilhado).
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

  const guardar = item => operar("readwrite", s => s.put(item));
  const remover = id   => operar("readwrite", s => s.delete(id));
  const listar  = ()   => operar("readonly",  s => s.getAll());

  function novoId() {
    if (crypto.randomUUID) return crypto.randomUUID();
    return Array.from(crypto.getRandomValues(new Uint8Array(16)),
                      b => b.toString(16).padStart(2, "0")).join("");
  }

  // Reduz para caber no 3G e no Drive; se o navegador não conseguir, vai a original.
  async function reduzir(arquivo) {
    try {
      const bmp = await createImageBitmap(arquivo, { imageOrientation: "from-image" });
      const esc = Math.min(1, LADO_MAX / Math.max(bmp.width, bmp.height));
      const cv = document.createElement("canvas");
      cv.width = Math.round(bmp.width * esc); cv.height = Math.round(bmp.height * esc);
      cv.getContext("2d").drawImage(bmp, 0, 0, cv.width, cv.height);
      const blob = await new Promise(ok => cv.toBlob(ok, "image/jpeg", QUALIDADE));
      return blob || arquivo;
    } catch (e) {
      return arquivo;
    }
  }

  async function tokenAtual() {
    const r = await fetch("/api/csrf", { credentials: "same-origin", cache: "no-store" });
    if (r.status === 401) return { erro: "login" };
    if (!r.ok) return { erro: "rede" };
    return { token: (await r.json()).csrf_token };
  }

  // Retorna {ok} | {ok:false, motivo: rede|login|csrf|drive|invalida, msg}
  async function enviarUma(item, token) {
    const fd = new FormData();
    fd.set("id_animal", item.id_animal);
    fd.set("tipo", item.tipo);
    fd.set("legenda", item.legenda);
    fd.set("data", item.data);
    fd.set("id_envio", item.id_envio);
    fd.set("csrf_token", token);
    fd.set("foto", item.blob, "foto.jpg");
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), TEMPO_LIMITE_MS);
    try {
      const r = await fetch("/api/fotos", { method: "POST", body: fd,
                                            credentials: "same-origin", signal: ctrl.signal });
      const d = await r.json().catch(() => ({}));
      if (r.ok && d.ok) return { ok: true };
      return { ok: false, motivo: d.erro || (r.status === 401 ? "login" : "drive"), msg: d.msg || "" };
    } catch (e) {
      return { ok: false, motivo: "rede" };
    } finally {
      clearTimeout(t);
    }
  }

  function avisar(texto, cor) {
    const alvo = document.querySelector(".content") || document.body;
    let faixa = document.getElementById("fila-fotos-aviso");
    if (!texto) { if (faixa) faixa.remove(); return; }
    if (!faixa) {
      faixa = document.createElement("div");
      faixa.id = "fila-fotos-aviso";
      faixa.style.cssText = "margin:0 0 14px;padding:10px 14px;border-radius:10px;font-size:13.5px";
      alvo.prepend(faixa);
    }
    faixa.style.background = cor === "erro" ? "rgba(192,57,43,.1)" : "var(--gold-lt)";
    faixa.style.border = cor === "erro" ? "1.5px solid var(--danger)" : "1.5px solid var(--gold)";
    faixa.textContent = texto;
  }

  async function atualizarAviso() {
    let n = 0;
    try { n = (await listar()).length; } catch (e) { return; }
    avisar(n ? `📷 ${n} foto(s) guardada(s) neste celular, aguardando sinal para enviar.` : "");
  }

  // Tentativa de envio de um item; 'invalida' sai da fila (nunca vai passar).
  async function processar(item, token) {
    const r = await enviarUma(item, token);
    if (r.ok) { await remover(item.id_envio).catch(() => {}); return "enviada"; }
    if (r.motivo === "invalida") {
      await remover(item.id_envio).catch(() => {});
      avisar(`❌ Foto recusada: ${r.msg}`, "erro");
      return "recusada";
    }
    return r.motivo;
  }

  async function enviar(idAnimal, arquivos, campos) {
    const itens = [];
    for (const arq of Array.from(arquivos || [])) {
      itens.push({ id_envio: novoId(), id_animal: idAnimal, blob: await reduzir(arq),
                   tipo: campos.tipo || "Evolução", legenda: campos.legenda || "",
                   data: campos.data || "", criado_em: Date.now() });
    }
    // Guarda ANTES de tentar: se a página fechar no meio, a foto não se perde.
    // Sem IndexedDB (aba anônima, celular sem espaço): tenta enviar direto e,
    // se não der, AVISA — nunca some calada.
    let naoGuardadas = 0, perdidas = 0;
    for (const it of itens) {
      try {
        if (!window.indexedDB) throw new Error("sem IndexedDB");
        await guardar(it);
      } catch (e) {
        naoGuardadas++;
        const tk = await tokenAtual().catch(() => ({ erro: "rede" }));
        const r = tk.token ? await enviarUma(it, tk.token) : { ok: false };
        if (!r.ok) perdidas++;
      }
    }
    if (perdidas) {
      avisar(`❌ ${perdidas} foto(s) NÃO foram enviadas e não puderam ser guardadas neste celular ` +
             "(sem sinal e sem espaço/modo anônimo). Tente de novo com internet.", "erro");
    }
    await enviarPendentes();
    return { perdidas, naoGuardadas };
  }

  // Espera a rodada em andamento (ex.: a do timer) e roda de novo: assim a foto
  // recém-tirada não fica para trás nem é enviada duas vezes ao mesmo tempo.
  function enviarPendentes() {
    rodada = rodada.then(rodar, rodar);
    return rodada;
  }

  async function rodar() {
    if (!window.indexedDB) return 0;
    let enviadas = 0;
    try {
      const itens = await listar();
      if (!itens.length) return 0;
      const tk = await tokenAtual().catch(() => ({ erro: "rede" }));
      if (!tk.token) return 0;
      for (const item of itens.sort((a, b) => a.criado_em - b.criado_em)) {
        const res = await processar(item, tk.token);
        if (res === "enviada") enviadas++;
        else if (res === "rede" || res === "login" || res === "drive") break;   // tenta mais tarde
      }
    } catch (e) {
      /* sem IndexedDB/rede: tenta na próxima vez */
    }
    await atualizarAviso();
    if (enviadas) document.dispatchEvent(new CustomEvent("fotos:atualizadas"));
    return enviadas;
  }

  async function pendentes(idAnimal) {
    const itens = await listar();
    return idAnimal ? itens.filter(i => i.id_animal === idAnimal) : itens;
  }

  window.FilaFotos = { enviar, pendentes, enviarPendentes };

  if (!window.indexedDB) return;
  window.addEventListener("online", enviarPendentes);
  document.addEventListener("DOMContentLoaded", () => { atualizarAviso(); enviarPendentes(); });
  setInterval(async () => {
    try { if ((await listar()).length) enviarPendentes(); } catch (e) {}
  }, 60000);
})();
