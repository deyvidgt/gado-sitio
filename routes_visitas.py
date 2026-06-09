#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas de Visitas ao Sítio — Sítio Santo Antonio
"""
from flask import render_template, request, redirect, url_for, flash
from db import carregar_aba, fazer_backup
from calculos import calcular_estoque
from config import MEMBROS, NOMES_MEMBROS
from extensions import (
    app, _agora, _validar_csrf, login_required,
    _get_dados_cache, salvar_linha, reescrever_aba,
    _limpar_backups_antigos, fmt_data,
)


# ── Sugestões automáticas ─────────────────────────────────────────────────────

def _gerar_sugestoes_visita(f, estoque_esperado):
    sug = []
    gado_contado = int(f.get("gado_contado") or 0)
    if gado_contado > 0 and estoque_esperado > 0:
        if gado_contado < estoque_esperado:
            falt = estoque_esperado - gado_contado
            sug.append(f"⚠️ ALERTA: {falt} cabeça(s) não localizada(s)! Verificar pastagens vizinhas e cercas.")
        elif gado_contado > estoque_esperado:
            sug.append(f"ℹ️ {gado_contado - estoque_esperado} cabeça(s) a mais — possível animal de terceiro.")

    sal = f.get("sal_racao", "OK")
    if sal == "Baixo":       sug.append("🧂 Sal/Ração baixo — reabastecer nos próximos 2 a 3 dias.")
    elif sal in ("Vazio", "Meio Saco"):
        msg = "🚨 Sal/Ração ESGOTADO — abastecer com urgência!" if sal == "Vazio" else "🧂 Sal/Ração no fim — reabastecer em breve."
        sug.append(msg)

    prot = f.get("proteinado", "OK")
    if prot == "Baixo":      sug.append("🟡 Proteinado baixo — repor em breve.")
    elif prot in ("Vazio", "Meio Saco"):
        sug.append("🚨 Proteinado ESGOTADO — comprar urgente!" if prot == "Vazio" else "🟡 Proteinado no fim — repor em breve.")

    mato = f.get("mato", "Limpo")
    if mato == "Precisa Capinar": sug.append("🌿 Vegetação crescida — programar roçagem.")
    elif mato == "Muito Mato":    sug.append("🌿 Mato excessivo — roçagem urgente!")

    grama = f.get("grama", "Boa")
    if grama in ("Amarelando/Secando",): sug.append("🌾 Pastagem amarelando — monitorar.")
    elif grama == "Regular":  sug.append("🌱 Pastagem regular — considerar rotação ou adubação.")
    elif grama == "Escassa":  sug.append("🚨 Pastagem escassa — rotacionar IMEDIATAMENTE.")

    corrego = f.get("corrego", "Normal")
    if corrego == "Baixo":    sug.append("💧 Água baixa — monitorar e preparar alternativa.")
    elif corrego == "Seco":   sug.append("🚨 SEM ÁGUA — providenciar abastecimento urgente!")

    quintal = f.get("quintal", "OK")
    if quintal == "Precisa Atenção": sug.append("🏡 Quintal necessita atenção.")

    cisterna = f.get("cisterna", "OK")
    if cisterna in ("Baixo/Secando",): sug.append("🪣 Cisterna baixa — programar reabastecimento.")
    elif cisterna == "Vazia": sug.append("🚨 Cisterna VAZIA — abastecer imediatamente!")

    choveu = f.get("choveu", "nao") == "sim"
    try:
        mm = float(str(f.get("chuva_mm", "0") or "0").replace(",", "."))
    except Exception:
        mm = 0.0

    if choveu and mm >= 50:   sug.append(f"🌧️ Chuva forte ({mm:.0f}mm) — verificar erosão e cercas.")
    elif choveu and mm >= 15: sug.append(f"🌦️ Boa chuva ({mm:.0f}mm) — pastagem deve se recuperar.")
    elif choveu and mm > 0:   sug.append(f"🌂 Chuva leve ({mm:.0f}mm).")
    elif choveu:              sug.append("🌧️ Chuva registrada — anotar os mm na próxima vez.")
    else:                     sug.append("☀️ Sem chuva — acompanhar estiagem.")

    if not sug:
        sug.append("✅ Visita sem pendências — sítio em boas condições!")
    return " | ".join(sug)


# ── Listar visitas ────────────────────────────────────────────────────────────

@app.route("/visitas")
@login_required
def visitas():
    df = carregar_aba("Visitas")
    ordem = request.args.get("ordem", "desc")
    if not df.empty and "Data" in df.columns:
        df = df.sort_values("Data", ascending=(ordem == "asc"), na_position="last")

    alertas = []
    if not df.empty:
        ultima = df.iloc[0] if ordem == "desc" else df.iloc[-1]
        try:
            falt = int(ultima.get("Gado Faltando") or 0)
        except Exception:
            falt = 0
        if falt > 0:
            alertas.append(("danger", f"⚠️ Na última visita, {falt} cabeça(s) estavam faltando!"))
        for campo, label in [("Sal/Ração", "Sal/Ração"), ("Proteinado", "Proteinado")]:
            v = str(ultima.get(campo, "OK") or "OK")
            if v == "Vazio":   alertas.append(("danger",  f"🚨 {label} ESGOTADO conforme última visita!"))
            elif v == "Baixo": alertas.append(("warning", f"⚠️ {label} está baixo — repor em breve."))
        corrego = str(ultima.get("Córrego/Água", "Normal") or "Normal")
        if corrego == "Seco":   alertas.append(("danger",  "🚨 Córrego/bebedouro SECO na última visita!"))
        elif corrego == "Baixo": alertas.append(("warning", "💧 Água no córrego estava baixa — verificar."))

    rows = []
    for real_idx, row in (df.iterrows() if not df.empty else []):
        d = row.to_dict()
        d["Data"] = fmt_data(d.get("Data"))
        d["_idx"] = int(real_idx)
        try:
            d["Gado Faltando"] = int(d.get("Gado Faltando") or 0)
        except Exception:
            d["Gado Faltando"] = 0
        rows.append(d)

    return render_template("lista_visitas.html", rows=rows, ordem=ordem, alertas=alertas)


# ── Nova visita ───────────────────────────────────────────────────────────────

@app.route("/visitas/nova", methods=["GET", "POST"])
@login_required
def nova_visita():
    dados   = _get_dados_cache()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])

    if request.method == "POST":
        _validar_csrf()
        f = request.form

        data        = f.get("data", _agora().strftime("%d/%m/%Y"))
        responsavel = f.get("responsavel", "")
        gado_cnt    = int(f.get("gado_contado") or 0)
        gado_esp    = estoque
        gado_falt   = max(0, gado_esp - gado_cnt) if gado_cnt > 0 else 0

        sal      = f.get("sal_racao",  "OK")
        prot     = f.get("proteinado", "OK")
        mato     = f.get("mato",       "Limpo")
        grama    = f.get("grama",      "Boa")
        corrego  = f.get("corrego",    "Normal")
        quintal  = f.get("quintal",    "OK")
        cisterna = f.get("cisterna",   "OK")
        choveu   = "Sim" if f.get("choveu") == "sim" else "Não"

        try:
            chuva_mm = float(str(f.get("chuva_mm", "0") or "0").replace(",", "."))
        except Exception:
            chuva_mm = 0.0

        obs       = f.get("observacoes", "").strip()
        sugestoes = _gerar_sugestoes_visita(f, estoque)

        # Campos de sacos (BUG CORRIGIDO: antes eram silenciosamente descartados)
        def _int_safe(v):
            try:
                return int(str(v).strip()) if v and str(v).strip() else None
            except Exception:
                return None

        sacos_sal  = _int_safe(f.get("sacos_sal"))
        sacos_racao = _int_safe(f.get("sacos_racao"))
        sacos_prot = _int_safe(f.get("sacos_prot"))

        # COLUNAS_VISITAS tem 18 colunas — salvar todas na ordem correta:
        # Data, Responsável, Gado Contado, Gado Esperado, Gado Faltando,
        # Sal/Ração, Proteinado, Mato/Vegetação, Grama/Pastagem, Córrego/Água,
        # Quintal, Cisterna, Choveu, Chuva mm, Observações, Sugestões,
        # Sacos Sal/Ração, Sacos Proteinado
        salvar_linha("Visitas", [
            data, responsavel,
            gado_cnt, gado_esp, gado_falt,
            sal, prot, mato, grama, corrego,
            quintal, cisterna,
            choveu, chuva_mm if chuva_mm > 0 else None,
            obs, sugestoes,
            sacos_sal, sacos_prot,
        ])

        if gado_falt > 0:
            flash(f"⚠️ Visita salva — mas {gado_falt} cabeça(s) estão faltando!", "warning")
        else:
            flash("✅ Visita registrada com sucesso!", "success")
        return redirect(url_for("visitas"))

    return render_template("form_visita.html", estoque=estoque,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))


# ── Excluir visita ────────────────────────────────────────────────────────────

@app.route("/visitas/excluir/<int:idx>", methods=["POST"])
@login_required
def excluir_visita(idx):
    _validar_csrf()
    fazer_backup()
    _limpar_backups_antigos()
    df = carregar_aba("Visitas")
    if df.empty or idx not in df.index:
        flash("Registro não encontrado.", "error")
        return redirect(url_for("visitas"))
    df = df.drop(index=idx).reset_index(drop=True)
    reescrever_aba("Visitas", df)
    flash("Visita excluída.", "success")
    return redirect(url_for("visitas"))
