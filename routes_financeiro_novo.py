#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_financeiro_novo.py — Rotas de reorganização do dashboard (v5.10)

Novas páginas para dashboard mobile-first:
- /financeiro — Indicadores financeiros completos
- /resultado — Resultado por membro + período
- /fluxo-caixa — Gráfico entrada/saída + saldo acumulado
- /fluxo-animais — Compras/vendas com gráfico
- /lembretes-whatsapp — Preferências + fila de avisos
"""

from flask import render_template, session, jsonify
import pandas as pd
from datetime import datetime, timedelta
from db import carregar_aba, RAIZ
from calculos import calcular_todos_membros, calcular_estoque_por_membro
from config import MEMBROS, NOMES_MEMBROS, EMOJIS_MEMBROS
from extensions import app, _agora, login_required, _get_dados_cache, _get_membros_cache, _get_resumo_cache, fmt_brl, fmt_data
import os
import json


@app.route("/financeiro")
@login_required
def financeiro():
    """Página de indicadores financeiros completos."""
    dados = _get_dados_cache()
    r = _get_resumo_cache()  # resumo geral

    return render_template("financeiro.html", r=r)


@app.route("/resultado")
@login_required
def resultado():
    """Página de resultado por membro e período."""
    from calculos import calcular_resumo_financeiro
    dados = _get_dados_cache()
    membros_dict = _get_membros_cache()
    resumo_geral = calcular_resumo_financeiro(dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"])

    return render_template(
        "resultado.html",
        resumo_geral=resumo_geral,
        membros=membros_dict,
        MEMBROS=MEMBROS,
        NOMES_MEMBROS=NOMES_MEMBROS,
        EMOJIS_MEMBROS=EMOJIS_MEMBROS,
    )


@app.route("/fluxo-caixa")
@login_required
def fluxo_caixa():
    """Página de fluxo de caixa (entrada/saída/saldo acumulado)."""
    dados = _get_dados_cache()
    vendas = dados.get("Vendas", pd.DataFrame())
    compras = dados.get("Compras", pd.DataFrame())
    gastos = dados.get("Gastos", pd.DataFrame())

    # Agrupar por mês
    fluxo = _calcular_fluxo_mensal(vendas, compras, gastos)

    return render_template("fluxo_caixa.html", fluxo=fluxo)


@app.route("/fluxo-animais")
@login_required
def fluxo_animais():
    """Página de fluxo de animais (entrada de compras/nascimento, saída de vendas/morte)."""
    dados = _get_dados_cache()
    compras = dados.get("Compras", pd.DataFrame())
    vendas = dados.get("Vendas", pd.DataFrame())
    manejo = dados.get("Manejo", pd.DataFrame())

    fluxo = _calcular_fluxo_animais(compras, vendas, manejo)

    return render_template("fluxo_animais.html", fluxo=fluxo)


@app.route("/lembretes-whatsapp")
@login_required
def lembretes_whatsapp():
    """Página de preferências WhatsApp e fila de avisos pendentes."""
    usuarios = _carregar_usuarios_disco()
    user_id = session.get("user_id")
    user_prefs = usuarios.get(user_id, {}).get("whatsapp_prefs", {})

    # Ler fila de avisos pendentes
    avisos_pendentes = _ler_avisos_pendentes()

    return render_template(
        "lembretes_whatsapp.html",
        user_prefs=user_prefs,
        avisos_pendentes=avisos_pendentes,
    )


# ── Funções auxiliares ────────────────────────────────────────────────────────

def _calcular_fluxo_mensal(vendas, compras, gastos, meses=12):
    """Calcula fluxo de caixa mensal: receita (vendas), despesa (compras+gastos), saldo."""
    agora = _agora()
    fluxo_list = []
    saldo_acum = 0

    for i in range(meses, 0, -1):
        data_inicio = agora - timedelta(days=30*i)
        data_fim = agora - timedelta(days=30*(i-1))

        # Receita (vendas)
        receita = 0
        if not vendas.empty:
            v = vendas[(pd.to_datetime(vendas["Data"], format="%d/%m/%Y", errors="coerce") >= data_inicio) &
                      (pd.to_datetime(vendas["Data"], format="%d/%m/%Y", errors="coerce") < data_fim)]
            if not v.empty:
                receita = float(pd.to_numeric(v["Valor Total (R$)"], errors="coerce").sum())

        # Despesa (compras + gastos)
        despesa = 0
        if not compras.empty:
            c = compras[(pd.to_datetime(compras["Data"], format="%d/%m/%Y", errors="coerce") >= data_inicio) &
                       (pd.to_datetime(compras["Data"], format="%d/%m/%Y", errors="coerce") < data_fim)]
            if not c.empty:
                despesa += float(pd.to_numeric(c["Valor Total (R$)"], errors="coerce").sum())
        if not gastos.empty:
            g = gastos[(pd.to_datetime(gastos["Data"], format="%d/%m/%Y", errors="coerce") >= data_inicio) &
                      (pd.to_datetime(gastos["Data"], format="%d/%m/%Y", errors="coerce") < data_fim)]
            if not g.empty:
                despesa += float(pd.to_numeric(g["Valor Total (R$)"], errors="coerce").sum())

        saldo_mes = receita - despesa
        saldo_acum += saldo_mes

        fluxo_list.append({
            "mes": data_fim.strftime("%b/%y"),
            "receita": receita,
            "despesa": despesa,
            "saldo_mes": saldo_mes,
            "saldo_acumulado": saldo_acum,
        })

    return fluxo_list


def _calcular_fluxo_animais(compras, vendas, manejo, dias=90):
    """Calcula fluxo de animais (entrada/saída) nos últimos dias."""
    agora = _agora()
    data_inicio = agora - timedelta(days=dias)

    fluxo_list = []
    entrada_total = 0
    saida_total = 0

    for i in range(dias):
        data = data_inicio + timedelta(days=i)

        # Entrada: compras + nascimentos
        entrada = 0
        if not compras.empty:
            c = compras[pd.to_datetime(compras["Data"], format="%d/%m/%Y", errors="coerce").dt.date == data.date()]
            entrada += len(c)
        if not manejo.empty:
            n = manejo[(manejo["Tipo"] == "Nascimento") &
                      (pd.to_datetime(manejo["Data"], format="%d/%m/%Y", errors="coerce").dt.date == data.date())]
            entrada += len(n)

        # Saída: vendas + mortes + perdas
        saida = 0
        if not vendas.empty:
            v = vendas[pd.to_datetime(vendas["Data"], format="%d/%m/%Y", errors="coerce").dt.date == data.date()]
            if not v.empty:
                saida += int(pd.to_numeric(v["Qtd Cabeças"], errors="coerce").sum())
        if not manejo.empty:
            m = manejo[(manejo["Tipo"].isin(["Morte", "Perda"])) &
                      (pd.to_datetime(manejo["Data"], format="%d/%m/%Y", errors="coerce").dt.date == data.date())]
            saida += len(m)

        entrada_total += entrada
        saida_total += saida

        if (i % 7 == 0) or (i == dias - 1):  # Mostrar a cada semana
            fluxo_list.append({
                "data": data.strftime("%d/%m"),
                "entrada": entrada_total,
                "saida": saida_total,
            })

    return {
        "datas": [f["data"] for f in fluxo_list],
        "entrada": [f["entrada"] for f in fluxo_list],
        "saida": [f["saida"] for f in fluxo_list],
        "entrada_total": entrada_total,
        "saida_total": saida_total,
        "saldo": entrada_total - saida_total,
    }


def _carregar_usuarios_disco():
    """Carrega usuários.json da raiz."""
    try:
        path = os.path.join(RAIZ, "usuarios.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def _ler_avisos_pendentes():
    """Lê fila de avisos pendentes de WhatsApp."""
    try:
        from db import DATA_DIR
        path = os.path.join(DATA_DIR, "avisos_pendentes.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f) or []
    except Exception:
        pass
    return []
