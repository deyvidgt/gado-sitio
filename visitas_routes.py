#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROTAS DE VISITAS — adicionar ao app.py antes de:
    if __name__ == "__main__":

Também atualizar os imports no topo do app.py:
    from config import (..., OPCOES_VISITA)
"""

# ════════════════════════════════════════════════════════════════════
#  VISITAS AO SÍTIO
# ════════════════════════════════════════════════════════════════════

def _gerar_sugestoes_visita(f: dict, estoque_esperado: int) -> str:
    """
    Gera sugestões automáticas com base nos dados preenchidos na visita.
    Retorna string com as sugestões separadas por " | ".
    """
    sug = []

    # ── Contagem de gado ────────────────────────────────────────────
    gado_contado = int(f.get("gado_contado") or 0)
    if gado_contado > 0 and estoque_esperado > 0:
        if gado_contado < estoque_esperado:
            faltando = estoque_esperado - gado_contado
            sug.append(
                f"⚠️ ALERTA: {faltando} cabeça(s) não localizada(s)! "
                f"Verificar pastagens vizinhas, cercas e comunicar a família."
            )
        elif gado_contado > estoque_esperado:
            a_mais = gado_contado - estoque_esperado
            sug.append(
                f"ℹ️ {a_mais} cabeça(s) a mais que o esperado — "
                f"possível animal de terceiro ou registro desatualizado no sistema."
            )

    # ── Sal/Ração ────────────────────────────────────────────────────
    sal = f.get("sal_racao", "OK")
    if sal == "Baixo":
        sug.append("🧂 Sal/Ração baixo — reabastecer nos próximos 2 a 3 dias.")
    elif sal == "Vazio":
        sug.append("🚨 Sal/Ração ESGOTADO — abastecer com urgência! Gado sem mineral compromete saúde e ganho de peso.")

    # ── Proteinado ───────────────────────────────────────────────────
    prot = f.get("proteinado", "OK")
    if prot == "Baixo":
        sug.append("🟡 Proteinado baixo — repor em breve para manter desempenho do rebanho.")
    elif prot == "Vazio":
        sug.append("🚨 Proteinado ESGOTADO — sem suplementação proteica o gado perde peso rapidamente. Comprar urgente!")

    # ── Mato / Vegetação ─────────────────────────────────────────────
    mato = f.get("mato", "Limpo")
    if mato == "Precisa Capinar":
        sug.append("🌿 Vegetação crescida — programar roçagem/capina nos próximos dias.")
    elif mato == "Muito Mato":
        sug.append(
            "🌿 Mato excessivo — roçagem urgente! Reduz área de pastagem, "
            "esconde cobras e pode danificar cercas."
        )

    # ── Grama / Pastagem ─────────────────────────────────────────────
    grama = f.get("grama", "Boa")
    if grama == "Regular":
        sug.append("🌱 Pastagem regular — considerar rotação de pasto ou adubação para recuperação.")
    elif grama == "Escassa":
        sug.append(
            "🚨 Pastagem escassa — rotacionar pasto IMEDIATAMENTE. "
            "Risco real de perda de peso. Avaliar suplementação volumosa (cana, silagem) se estiagem prolongada."
        )

    # ── Córrego / Água ───────────────────────────────────────────────
    corrego = f.get("corrego", "Normal")
    if corrego == "Baixo":
        sug.append("💧 Água no córrego/bebedouro baixa — monitorar e preparar alternativa de abastecimento.")
    elif corrego == "Seco":
        sug.append(
            "🚨 SEM ÁGUA no córrego — providenciar abastecimento alternativo urgente "
            "(bebedouro portátil, carro-pipa). Gado sem água é emergência!"
        )

    # ── Quintal ──────────────────────────────────────────────────────
    quintal = f.get("quintal", "OK")
    if quintal == "Precisa Atenção":
        sug.append("🏡 Quintal necessita atenção — verificar o que precisa ser feito e resolver na próxima visita.")

    # ── Cisterna ─────────────────────────────────────────────────────
    cisterna = f.get("cisterna", "OK")
    if cisterna == "Baixo":
        sug.append("🪣 Cisterna baixa — programar reabastecimento antes da próxima visita.")
    elif cisterna == "Vazia":
        sug.append("🚨 Cisterna VAZIA — abastecer imediatamente!")

    # ── Chuva ────────────────────────────────────────────────────────
    choveu = f.get("choveu", "nao") == "sim"
    mm_raw = f.get("chuva_mm", "") or ""
    try:
        mm = float(str(mm_raw).replace(",", "."))
    except Exception:
        mm = 0.0

    if choveu and mm >= 50:
        sug.append(
            f"🌧️ Chuva forte ({mm:.0f}mm) — verificar erosão, entupimento de valetas e estado das cercas."
        )
    elif choveu and mm >= 15:
        sug.append(f"🌦️ Boa chuva ({mm:.0f}mm) — pastagem deve se recuperar bem nos próximos dias.")
    elif choveu and mm > 0:
        sug.append(f"🌂 Chuva leve ({mm:.0f}mm) — impacto pequeno na pastagem, continuar monitorando.")
    elif choveu and mm == 0:
        sug.append("🌧️ Chuva registrada sem quantidade — anotar os mm na próxima vez para histórico.")
    else:
        sug.append("☀️ Sem chuva — acompanhar estiagem para ajustar suplementação se necessário.")

    if not sug:
        sug.append("✅ Visita sem pendências — sítio em boas condições!")

    return " | ".join(sug)


@app.route("/visitas")
@login_required
def visitas():
    df = carregar_aba("Visitas")
    ordem = request.args.get("ordem", "desc")
    if not df.empty and "Data" in df.columns:
        df = df.sort_values("Data", ascending=(ordem == "asc"), na_position="last")

    # Montar alertas para o topo da página (última visita)
    alertas = []
    if not df.empty:
        ultima = df.iloc[0] if ordem == "desc" else df.iloc[-1]
        # Verificar gado faltando
        falt = ultima.get("Gado Faltando", 0)
        try:
            falt = int(falt or 0)
        except Exception:
            falt = 0
        if falt > 0:
            alertas.append(("danger", f"⚠️ Na última visita, {falt} cabeça(s) estavam faltando!"))
        # Sal/Proteínado
        for campo, label in [("Sal/Ração", "Sal/Ração"), ("Proteinado", "Proteinado")]:
            v = str(ultima.get(campo, "OK") or "OK")
            if v == "Vazio":
                alertas.append(("danger", f"🚨 {label} ESGOTADO conforme última visita!"))
            elif v == "Baixo":
                alertas.append(("warning", f"⚠️ {label} está baixo — repor em breve."))
        # Água
        corrego = str(ultima.get("Córrego/Água", "Normal") or "Normal")
        if corrego == "Seco":
            alertas.append(("danger", "🚨 Córrego/bebedouro SECO na última visita!"))
        elif corrego == "Baixo":
            alertas.append(("warning", "💧 Água no córrego estava baixa — verificar."))

    rows = []
    for real_idx, row in (df.iterrows() if not df.empty else []):
        d = row.to_dict()
        d["Data"] = fmt_data(d.get("Data"))
        d["_idx"] = int(real_idx)
        # Calcular gado faltando como int para exibição
        try:
            d["Gado Faltando"] = int(d.get("Gado Faltando") or 0)
        except Exception:
            d["Gado Faltando"] = 0
        rows.append(d)

    return render_template(
        "lista_visitas.html",
        rows=rows, ordem=ordem, alertas=alertas,
    )


@app.route("/visitas/nova", methods=["GET", "POST"])
@login_required
def nova_visita():
    dados = carregar_todas()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])

    if request.method == "POST":
        f = request.form

        data        = f.get("data", datetime.now().strftime("%d/%m/%Y"))
        responsavel = f.get("responsavel", "")
        gado_cnt    = int(f.get("gado_contado") or 0)
        gado_esp    = estoque
        gado_falt   = max(0, gado_esp - gado_cnt) if gado_cnt > 0 else 0

        sal      = f.get("sal_racao", "OK")
        prot     = f.get("proteinado", "OK")
        mato     = f.get("mato", "Limpo")
        grama    = f.get("grama", "Boa")
        corrego  = f.get("corrego", "Normal")
        quintal  = f.get("quintal", "OK")
        cisterna = f.get("cisterna", "OK")

        choveu = "Sim" if f.get("choveu") == "sim" else "Não"
        try:
            chuva_mm = float(str(f.get("chuva_mm", "0") or "0").replace(",", "."))
        except Exception:
            chuva_mm = 0.0

        obs = f.get("observacoes", "").strip()

        # Gerar sugestões automáticas
        sugestoes = _gerar_sugestoes_visita(f, estoque)

        salvar_linha("Visitas", [
            data, responsavel,
            gado_cnt, gado_esp, gado_falt,
            sal, prot,
            mato, grama, corrego,
            quintal, cisterna,
            choveu, chuva_mm if chuva_mm > 0 else None,
            obs, sugestoes,
        ])

        # Alertas pós-salvamento se houver gado faltando
        if gado_falt > 0:
            flash(
                f"⚠️ Visita salva — mas {gado_falt} cabeça(s) estão faltando! "
                "Verificar com urgência.", "warning"
            )
        else:
            flash("✅ Visita registrada com sucesso!", "success")

        return redirect(url_for("visitas"))

    return render_template(
        "form_visita.html",
        estoque=estoque,
        MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
        hoje=datetime.now().strftime("%Y-%m-%d"),
    )


@app.route("/visitas/excluir/<int:idx>", methods=["POST"])
@login_required
def excluir_visita(idx):
    fazer_backup()
    _limpar_backups_antigos()
    df = carregar_aba("Visitas")
    if df.empty or idx >= len(df):
        flash("Registro não encontrado.", "error")
        return redirect(url_for("visitas"))
    df = df.drop(index=idx).reset_index(drop=True)
    reescrever_aba("Visitas", df)
    flash("Visita excluída.", "success")
    return redirect(url_for("visitas"))


# ── API: resumo da última visita (usado no dashboard) ────────────────────────
@app.route("/api/ultima-visita")
@login_required
def api_ultima_visita():
    df = carregar_aba("Visitas")
    if df.empty:
        return jsonify({"ok": False, "msg": "Nenhuma visita registrada."})

    df_sorted = df.sort_values("Data", ascending=False, na_position="last")
    row = df_sorted.iloc[0]

    def _str(v):
        return "" if (v is None or (isinstance(v, float) and pd.isna(v))) else str(v)

    return jsonify({
        "ok": True,
        "data":       fmt_data(row.get("Data")),
        "responsavel": _str(row.get("Responsável")),
        "gado_contado": int(row.get("Gado Contado") or 0),
        "gado_esperado": int(row.get("Gado Esperado") or 0),
        "gado_faltando": int(row.get("Gado Faltando") or 0),
        "sal":       _str(row.get("Sal/Ração")),
        "proteinado": _str(row.get("Proteinado")),
        "grama":     _str(row.get("Grama/Pastagem")),
        "corrego":   _str(row.get("Córrego/Água")),
        "choveu":    _str(row.get("Choveu")),
        "chuva_mm":  float(row.get("Chuva mm") or 0),
        "sugestoes": _str(row.get("Sugestões")),
    })
