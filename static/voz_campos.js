// ═══════════════════════════════════════════════════════════════════
//  voz_campos.js — Sítio Santo Antonio v4.3
//  1) Formulário preenchido pelo Comando de Voz: ?prefill=1&campo=valor
//     (o 🎤 monta o link "Corrigir no formulário" / "Abrir formulário").
//  2) Ditado em campos de texto, números, datas, listas e opções dos formulários.
// ═══════════════════════════════════════════════════════════════════
(function () {
  // ── 1) Prefill ─────────────────────────────────────────────────────
  const params = new URLSearchParams(location.search);
  if (params.get("prefill") === "1") {
    const form = document.querySelector(".content form[method='post']:not([action*='logout'])");
    const tocados = [];
    if (form) {
      params.forEach((valor, nome) => {
        if (nome === "prefill" || nome === "csrf_token" || valor === "") return;
        const els = form.querySelectorAll(`[name="${CSS.escape(nome)}"]`);
        els.forEach(el => {
          if (el.type === "radio") el.checked = el.value === valor;
          else if (el.type === "checkbox") el.checked = ["1", "on", "sim", "true"].includes(valor);
          else if (el.type === "date" && /^\d{2}\/\d{2}\/\d{4}$/.test(valor)) {
            const [d, m, a] = valor.split("/"); el.value = `${a}-${m}-${d}`;
          } else el.value = valor;
          tocados.push(el);
        });
      });
      // Avisa os scripts da página (mostrar campos, recalcular prévia…) depois
      // que eles registraram os ouvintes. Eventos sintéticos têm isTrusted=false.
      document.addEventListener("DOMContentLoaded", () => {
        tocados.forEach(el => {
          if (el.type === "radio" && !el.checked) return;
          el.dispatchEvent(new Event("input", { bubbles: true }));
          el.dispatchEvent(new Event("change", { bubbles: true }));
        });
      });
      const aviso = document.createElement("div");
      aviso.className = "flash info";
      aviso.textContent = "🎤 Preenchido pelo comando de voz — confira e salve.";
      const wrap = document.querySelector(".content");
      if (wrap) wrap.insertBefore(aviso, wrap.firstChild);
    }
  }

  // ── 2) Ditado nos campos de texto ──────────────────────────────────
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;
  const campos = document.querySelectorAll(
    ".content form textarea, .content form input:not([type]), " +
    ".content form input[type='text'], .content form input[type='number'], " +
    ".content form input[type='date'], .content form input[type='checkbox'], " +
    ".content form input[type='radio'], .content form select"
  );
  const gruposRadio = new Set();
  let ativo = null;

  campos.forEach(el => {
    if (!el.name || ["csrf_token", "id_envio"].includes(el.name) || el.readOnly || el.disabled
        || el.type === "hidden" || el.closest("[data-sem-mic]")) return;
    if (el.type === "radio") {
      if (gruposRadio.has(el.name)) return;
      gruposRadio.add(el.name);
    }
    const escolha = el.type === "checkbox" || el.type === "radio";
    const wrap = document.createElement("span");
    wrap.style.cssText = escolha
      ? "position:relative;display:inline-flex;align-items:center;vertical-align:middle;gap:3px"
      : "position:relative;display:block;width:100%";
    el.parentNode.insertBefore(wrap, el);
    wrap.appendChild(el);
    if (el.type !== "checkbox" && el.type !== "radio") el.style.paddingRight = "40px";
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = "🎤";
    b.title = "Ditar";
    b.setAttribute("aria-label", "Preencher " + nomeCampo(el));
    b.style.cssText = escolha
      ? "border:none;background:transparent;cursor:pointer;font-size:16px;line-height:1;padding:2px;border-radius:6px"
      : "position:absolute;right:6px;top:6px;border:none;background:transparent;" +
        "cursor:pointer;font-size:18px;line-height:1;padding:4px;border-radius:6px";
    wrap.appendChild(b);
    const status = document.createElement("span");
    status.className = "voz-campo-status";
    status.setAttribute("role", "status");
    status.style.cssText = "position:absolute;left:0;top:100%;font-size:11px;color:var(--text-3)";
    wrap.appendChild(status);
    b.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      ditar(el, b, status);
    });
  });

  function nomeCampo(el) {
    const label = el.labels && el.labels[0];
    return (label && label.textContent.trim()) || el.name;
  }

  function normalizar(s) {
    return String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("pt-BR").replace(/[^\p{L}\p{N} ]/gu, " ").replace(/\s+/g, " ").trim();
  }

  function numeroFalado(frase) {
    const texto = normalizar(frase);
    const digitado = String(frase).match(/-?\d[\d.,]*/);
    if (digitado) {
      let n = digitado[0];
      if (n.includes(",") && n.includes(".")) n = n.replace(/\./g, "").replace(",", ".");
      else if (n.includes(",")) n = n.replace(",", ".");
      else if (/^\d{1,3}(?:\.\d{3})+$/.test(n)) n = n.replace(/\./g, "");
      return Number.isFinite(Number(n)) ? String(Number(n)) : null;
    }
    const unidades = {
      zero: 0, um: 1, uma: 1, dois: 2, duas: 2, tres: 3, quatro: 4, cinco: 5,
      seis: 6, sete: 7, oito: 8, nove: 9, dez: 10, onze: 11, doze: 12, treze: 13,
      quatorze: 14, catorze: 14, quinze: 15, dezesseis: 16, dezessete: 17,
      dezoito: 18, dezenove: 19, vinte: 20, trinta: 30, quarenta: 40,
      cinquenta: 50, sessenta: 60, setenta: 70, oitenta: 80, noventa: 90,
      cem: 100, cento: 100, duzentos: 200, trezentos: 300, quatrocentos: 400,
      quinhentos: 500, seiscentos: 600, setecentos: 700, oitocentos: 800, novecentos: 900
    };
    const palavras = texto.split(" ").filter(p => p !== "e" && ![
      "de",
      "kg", "quilo", "quilos", "litro", "litros", "reais", "real", "sacos", "saco",
      "cabecas", "cabeca", "dias", "dia", "porcento"
    ].includes(p));
    if (!palavras.length || palavras.some(p => !(p in unidades))) return null;
    return String(palavras.reduce((total, palavra) => total + unidades[palavra], 0));
  }

  function dataFalado(frase) {
    const texto = normalizar(frase);
    const hoje = new Date();
    if (/\bhoje\b/.test(texto)) return dataISO(hoje);
    if (/\bontem\b/.test(texto)) { hoje.setDate(hoje.getDate() - 1); return dataISO(hoje); }
    if (/\banteontem\b/.test(texto)) { hoje.setDate(hoje.getDate() - 2); return dataISO(hoje); }
    const meses = {
      janeiro: 1, fevereiro: 2, marco: 3, abril: 4, maio: 5, junho: 6,
      julho: 7, agosto: 8, setembro: 9, outubro: 10, novembro: 11, dezembro: 12
    };
    const nomeado = texto.match(/\b(.+?) de (janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)(?: de (\d{4}))?\b/);
    if (nomeado) {
      const dia = Number(numeroFalado(nomeado[1]));
      const mes = meses[nomeado[2]];
      const ano = Number(nomeado[3] || new Date().getFullYear());
      const validada = new Date(ano, mes - 1, dia);
      if (dia && validada.getFullYear() === ano && validada.getMonth() === mes - 1
          && validada.getDate() === dia) return dataISO(validada);
      return null;
    }
    const data = texto.match(/\b(\d{1,2})[ /-](\d{1,2})(?:[ /-](\d{4}))?\b/);
    if (!data) return null;
    const ano = Number(data[3] || new Date().getFullYear());
    const mes = Number(data[2]);
    const dia = Number(data[1]);
    const validada = new Date(ano, mes - 1, dia);
    if (validada.getFullYear() !== ano || validada.getMonth() !== mes - 1 || validada.getDate() !== dia) return null;
    return `${ano}-${String(mes).padStart(2, "0")}-${String(dia).padStart(2, "0")}`;
  }

  function dataISO(data) {
    return `${data.getFullYear()}-${String(data.getMonth() + 1).padStart(2, "0")}-${String(data.getDate()).padStart(2, "0")}`;
  }

  function aplicarDitado(el, frase) {
    const tipo = el.type;
    if (tipo === "checkbox") {
      const resposta = normalizar(frase);
      if (/^(nao|negativo|desmarcar)$/.test(resposta)) el.checked = false;
      else if (/^(sim|positivo|marcar|ok)$/.test(resposta)) el.checked = true;
      else return "Diga “sim” ou “não” para marcar esta opção.";
    } else if (tipo === "radio") {
      const formulario = el.form;
      const opcoes = formulario
        ? Array.from(formulario.elements).filter(opcao => opcao.type === "radio" && opcao.name === el.name)
        : [];
      const termo = normalizar(frase);
      const escolha = Array.from(opcoes).find(opcao => {
        const label = opcao.labels && opcao.labels[0];
        const texto = normalizar((label && label.textContent) || opcao.value);
        return texto === termo || texto.includes(termo) || termo.includes(texto);
      });
      if (!escolha) return `Não encontrei a opção “${frase}” neste campo.`;
      escolha.checked = true;
      escolha.dispatchEvent(new Event("change", { bubbles: true }));
    } else if (el.tagName === "SELECT") {
      const termo = normalizar(frase);
      const opcoes = Array.from(el.options).filter(opcao => !opcao.disabled && opcao.value);
      const exatas = opcoes.filter(opcao => normalizar(opcao.textContent) === termo
        || normalizar(opcao.value) === termo);
      const parciais = opcoes.filter(opcao => normalizar(opcao.textContent).includes(termo));
      const escolha = exatas[0] || (parciais.length === 1 ? parciais[0] : null);
      if (!escolha) return `Não encontrei uma opção correspondente a “${frase}”.`;
      el.value = escolha.value;
    } else if (tipo === "number") {
      const valor = numeroFalado(frase);
      if (valor === null) return "Não consegui reconhecer um número neste campo.";
      el.value = valor;
    } else if (tipo === "date") {
      const valor = dataFalado(frase);
      if (!valor) return "Diga uma data como “hoje”, “ontem” ou “25/12/2026”.";
      el.value = valor;
    } else {
      el.value = el.value.trim()
        ? el.value.trim() + (el.tagName === "TEXTAREA" ? " " : ", ") + frase
        : frase;
    }
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return "";
  }

  function ditar(el, b, status) {
    if (ativo) {
      ativo.stop();
      return;
    }
    const rec = new SR();
    rec.lang = "pt-BR";
    rec.interimResults = false;
    ativo = rec;
    b.textContent = "🔴";
    rec.onresult = ev => {
      const t = Array.from(ev.results).map(r => r[0].transcript).join(" ").trim();
      if (!t) return;
      status.textContent = aplicarDitado(el, t);
    };
    rec.onerror = ev => { status.textContent = `Microfone indisponível (${ev.error}).`; };
    rec.onend = () => { ativo = null; b.textContent = "🎤"; };
    try { rec.start(); } catch (e) {
      ativo = null;
      b.textContent = "🎤";
      status.textContent = "Não foi possível iniciar o microfone. Tente novamente.";
    }
  }
})();
