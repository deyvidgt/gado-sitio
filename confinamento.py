#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
confinamento.py — Rastreamento de lotes em confinamento (v5.10)

Funções simples:
- lotes_ativos() — retorna lotes abertos
- novo_lote() — cria entrada na aba
- encerrar_lote() — calcula GMD e fecha
"""

import pandas as pd
from db import carregar_aba, salvar_linha
from datetime import datetime


def lotes_ativos(dados: dict = None) -> pd.DataFrame:
    """Retorna lotes ainda em confinamento (Status == 'Ativo')."""
    if dados is None:
        conf = carregar_aba("Confinamento Lotes")
    else:
        conf = dados.get("Confinamento Lotes", pd.DataFrame())

    if conf.empty:
        return pd.DataFrame()

    return conf[conf.get("Status", "") == "Ativo"].copy()


def resumo_lote(lote_id: str, dados: dict = None) -> dict:
    """Retorna resumo de um lote: cabeças, GMD, dias confinado, status."""
    if dados is None:
        conf = carregar_aba("Confinamento Lotes")
    else:
        conf = dados.get("Confinamento Lotes", pd.DataFrame())

    if conf.empty:
        return {}

    linha = conf[conf.get("Lote ID", "") == lote_id]
    if linha.empty:
        return {}

    row = linha.iloc[0]
    qtd = pd.to_numeric(row.get("Quantidade", 0), errors="coerce") or 0
    peso_ini = pd.to_numeric(row.get("Peso Inicial (kg)", 0), errors="coerce") or 0
    peso_fim = pd.to_numeric(row.get("Peso Final (kg)", 0), errors="coerce") or 0
    gmd = pd.to_numeric(row.get("GMD (kg/dia)", 0), errors="coerce") or 0

    return {
        "lote_id": lote_id,
        "quantidade": int(qtd),
        "peso_inicial": peso_ini,
        "peso_final": peso_fim,
        "gmd": round(gmd, 2),
        "dias": int(pd.to_numeric(row.get("Dias Confinado", 0), errors="coerce") or 0),
        "status": row.get("Status", "—"),
        "observacao": row.get("Observação", ""),
    }


def ganho_total(lote_id: str, dados: dict = None) -> float:
    """Ganho total de peso do lote (Peso Final - Peso Inicial)."""
    resumo = resumo_lote(lote_id, dados)
    if not resumo:
        return 0
    return resumo["peso_final"] - resumo["peso_inicial"]


def custo_por_lote(lote_id: str, custo_total: float = 0, preco_venda_arroba: float = 0, dados: dict = None) -> dict:
    """Calcula custo por cabeça, resultado financeiro do lote."""
    resumo = resumo_lote(lote_id, dados)
    if not resumo or not resumo["quantidade"]:
        return {"custo_total": custo_total, "custo_por_cab": 0, "custo_por_dia": 0, "resultado": 0}

    qtd = resumo["quantidade"]
    dias = resumo["dias"] or 1
    peso_final = resumo["peso_final"]

    # Receita (estimada): peso_final × rendimento × preco_arroba / 30kg
    # Assumir rendimento 58% padrão se não informado
    rendimento = 0.58
    arrobas_por_cab = (peso_final * rendimento) / 30 if peso_final > 0 else 0
    receita_por_cab = arrobas_por_cab * preco_venda_arroba if preco_venda_arroba > 0 else 0
    receita_total = receita_por_cab * qtd

    custo_por_cab = custo_total / qtd if qtd > 0 else 0
    resultado = receita_total - custo_total

    return {
        "custo_total": round(custo_total, 2),
        "custo_por_cab": round(custo_por_cab, 2),
        "custo_por_dia": round(custo_total / dias, 2),
        "receita_total": round(receita_total, 2),
        "receita_por_cab": round(receita_por_cab, 2),
        "resultado": round(resultado, 2),
        "margem": round((resultado / receita_total * 100), 1) if receita_total > 0 else 0,
    }


def alertas_confinamento(dados: dict = None) -> list:
    """Retorna lista de alertas (lotes com problemas)."""
    alertas = []
    ativos = lotes_ativos(dados)

    if ativos.empty:
        return alertas

    for _, lote in ativos.iterrows():
        gmd = pd.to_numeric(lote.get("GMD (kg/dia)", 0), errors="coerce") or 0

        # Alerta: GMD muito baixo
        if 0 < gmd < 0.5:
            alertas.append({
                "urgente": True,
                "texto": f"Lote {lote.get('Lote ID', '—')} com GMD baixo ({gmd} kg/dia)"
            })

        # Aviso: próximo de encerrar (dias > 120)
        dias = pd.to_numeric(lote.get("Dias Confinado", 0), errors="coerce") or 0
        if dias > 120:
            alertas.append({
                "urgente": False,
                "texto": f"Lote {lote.get('Lote ID', '—')} há {int(dias)} dias em confinamento"
            })

    return alertas


def resumo_mensal_confinamento(dados: dict = None) -> dict:
    """Retorna resumo mensal para relatório/WhatsApp."""
    ativos = lotes_ativos(dados)

    if ativos.empty:
        return {"num_lotes": 0, "total_cabecas": 0, "gmd_medio": 0}

    total_cab = pd.to_numeric(ativos.get("Quantidade", 0), errors="coerce").sum() or 0
    gmd_med = pd.to_numeric(ativos.get("GMD (kg/dia)", 0), errors="coerce").mean() or 0

    return {
        "num_lotes": len(ativos),
        "total_cabecas": int(total_cab),
        "gmd_medio": round(gmd_med, 2),
        "mensagem": f"📊 Confinamento: {len(ativos)} lotes, {int(total_cab)} cabeças, GMD médio {gmd_med:.2f} kg/dia"
    }
