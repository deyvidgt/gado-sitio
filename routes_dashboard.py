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
from calculos import calcular_todos_membros, calcular_estoque_por_membro
from config import MEMBROS, NOMES_MEMBROS, EMOJIS_MEMBROS, ALERTAS_SAUDE
from extensions import (
    app, _agora, login_required,
    _get_dados_cache, _get_resumo_cache,
    _carregar_usuarios, fmt_brl,
    _ultimo_alerta_wpp, _ALERTA_INTERVALO,
    _gerar_alertas, fmt_data,
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
    return render_template("dashboard.html", r=r, membros=membros_r,
                           estoque_membro=estoque_membro, recentes=recentes[:6],
                           alertas=_gerar_alertas(dados),
                           NOMES=NOMES_MEMBROS, EMOJIS=EMOJIS_MEMBROS, MEMBROS=MEMBROS)


# ══════════════════════════════════════════════════════════════════════════════
