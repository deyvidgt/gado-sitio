// ═══════════════════════════════════════════════════════════════════
//  voz_campos.js — Sítio Santo Antonio v4.3
//  1) Formulário preenchido pelo Comando de Voz: ?prefill=1&campo=valor
//     (o 🎤 monta o link "Corrigir no formulário" / "Abrir formulário").
//  2) Botão 🎤 de ditado nos campos de texto livre (descrição, observações,
//     sinais, produto, brincos…): o que for falado é acrescentado ao campo.
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
  const NOMES = /descr|obs|sugest|sinais|produto|pelagem|raca|brincos|mae|motivo/i;
  const campos = document.querySelectorAll(".content textarea, .content input[type='text']");
  let ativo = null;

  campos.forEach(el => {
    if (!NOMES.test(el.name || "") || el.readOnly || el.disabled || el.closest("[data-sem-mic]")) return;
    const wrap = document.createElement("span");
    wrap.style.cssText = "position:relative;display:block;width:100%";
    el.parentNode.insertBefore(wrap, el);
    wrap.appendChild(el);
    el.style.paddingRight = "40px";
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = "🎤";
    b.title = "Ditar";
    b.setAttribute("aria-label", "Ditar neste campo");
    b.style.cssText = "position:absolute;right:6px;top:6px;border:none;background:transparent;" +
                      "cursor:pointer;font-size:18px;line-height:1;padding:4px;border-radius:6px";
    wrap.appendChild(b);
    b.addEventListener("click", () => ditar(el, b));
  });

  function ditar(el, b) {
    if (ativo) { ativo.stop(); return; }
    const rec = new SR();
    rec.lang = "pt-BR";
    rec.interimResults = false;
    ativo = rec;
    b.textContent = "🔴";
    rec.onresult = ev => {
      const t = Array.from(ev.results).map(r => r[0].transcript).join(" ").trim();
      if (!t) return;
      el.value = el.value.trim() ? el.value.trim() + (el.tagName === "TEXTAREA" ? " " : ", ") + t : t;
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    };
    rec.onend = rec.onerror = () => { ativo = null; b.textContent = "🎤"; };
    try { rec.start(); } catch (e) { ativo = null; b.textContent = "🎤"; }
  }
})();
