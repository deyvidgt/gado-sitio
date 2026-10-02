#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_dashboard.py — Sítio Santo Antonio
Rota principal do dashboard e lógica de alertas WhatsApp automáticos.
"""
import threading
from flask import render_template, session
import pandas as pd
from datetime import datetime, timedelta
from db import carregar_aba
from calculos import (
    calcular_todos_membros, calcular_estoque_por_membro,
    calcular_indicadores_extras, estimar_rebanho_arroba, PRECO_ARROBA_REF,
)
from config import MEMBROS, NOMES_MEMBROS, EMOJIS_MEMBROS, ALERTAS_SAUDE
from extensions import (
    app, _agora, login_required,
    _get_dados_cache, _get_resumo_cache,
    _carregar_usuarios, fmt_brl,
    _gerar_alertas, fmt_data, _ler_sitio_config_disco,
)


@app.route("/")
@login_required
def dashboard():
    dados = _get_dados_cache()
    r = _get_resumo_cache()
    membros_r      = calcular_todos_membros(dados["Vendas"], dados["Compras"], dados["Gastos"], dados["Manejo"])
    estoque_membro = calcular_estoque_por_membro(dados["Compras"], dados["Vendas"], dados["Manejo"])
    recentes = []
    for _, row in dados["Compras"].tail(3).iterrows():
        ts = row.get("Data")
        recentes.append({"tipo": "Compra", "cor": "compra", "data": fmt_data(ts),
                          "_ts": ts if pd.notna(ts) else pd.Timestamp.min,
                          "desc": row.get("Descrição", ""), "val": fmt_brl(row.get("Valor Total (R$)", 0))})
    for _, row in dados["Gastos"].tail(2).iterrows():
        ts = row.get("Data")
        recentes.append({"tipo": "Gasto", "cor": "gasto", "data": fmt_data(ts),
                          "_ts": ts if pd.notna(ts) else pd.Timestamp.min,
                          "desc": row.get("Descrição", ""), "val": fmt_brl(row.get("Valor Total (R$)", 0))})
    for _, row in dados["Vendas"].tail(3).iterrows():
        ts = row.get("Data")
        recentes.append({"tipo": "Venda", "cor": "venda", "data": fmt_data(ts),
                          "_ts": ts if pd.notna(ts) else pd.Timestamp.min,
                          "desc": row.get("Descrição", ""), "val": fmt_brl(row.get("Valor Total (R$)", 0))})
    recentes.sort(key=lambda x: x["_ts"], reverse=True)
    for rec in recentes:
        rec.pop("_ts", None)

    # Indicadores extras de gestão (custo/dia, arrobas mínimas, TMP, % gasto)
    indicadores = calcular_indicadores_extras(
        dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"],
        r.get("ctcab", 0.0),
    )

    # Estimativa de valor do rebanho (peso médio + rendimento das Configurações)
    cfg = _ler_sitio_config_disco()
    try:
        peso_medio = float(cfg.get("peso_medio", 0) or 0)
    except (TypeError, ValueError):
        peso_medio = 0.0
    try:
        rendimento = float(cfg.get("rendimento", 52) or 52)
    except (TypeError, ValueError):
        rendimento = 52.0
    rebanho_est = None
    if peso_medio > 0 and r.get("estoque", 0) > 0:
        rebanho_est = estimar_rebanho_arroba(
            r["estoque"], peso_medio, PRECO_ARROBA_REF, r.get("ctcab", 0.0),
            rendimento / 100.0,
        )
        rebanho_est["peso_medio"]   = peso_medio
        rebanho_est["rendimento"]   = rendimento
        rebanho_est["preco_arroba"] = PRECO_ARROBA_REF

    return render_template("dashboard.html", r=r, membros=membros_r,
                           estoque_membro=estoque_membro, recentes=recentes[:6],
                           alertas=_gerar_alertas(dados),
                           indicadores=indicadores, rebanho_est=rebanho_est,
                           NOMES=NOMES_MEMBROS, EMOJIS=EMOJIS_MEMBROS, MEMBROS=MEMBROS)


# ══════════════════════════════════════════════════════════════════════════════
