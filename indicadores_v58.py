#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
indicadores_v58.py — Novos indicadores v5.8

- Engorda vs Pastagem
- GMD vs Lotação
- Ração Consumo
- Mortalidade de Bezerros
"""

import pandas as pd
from datetime import datetime, timedelta
from db import carregar_aba
from extensions import _agora


def engorda_pastagem_resumo(dados: dict = None) -> dict:
    """
    Retorna resumo de engorda vs pastagem do período atual.

    Returns:
        {
            "lotes_ativos": 5,
            "ganho_medio": 0.8,  # kg/dia
            "melhor_lote": {"pasto": "P01", "gmd": 1.2},
            "tabela": [...]
        }
    """
    try:
        abas = dados or {}
        engorda = abas.get("Engorda Pastagem") or carregar_aba("Engorda Pastagem")

        if engorda.empty:
            return {"lotes_ativos": 0, "ganho_medio": 0, "melhor_lote": {}, "tabela": []}

        # Calcular GMD médio
        engorda["GMD (kg/dia)"] = pd.to_numeric(engorda.get("GMD (kg/dia)", 0), errors="coerce")
        gmd_medio = engorda["GMD (kg/dia)"].mean() or 0

        # Encontrar melhor lote
        melhor = engorda.nlargest(1, "GMD (kg/dia)").iloc[0] if not engorda.empty else {}

        return {
            "lotes_ativos": len(engorda),
            "ganho_medio": round(gmd_medio, 2),
            "melhor_lote": {
                "pasto": melhor.get("Pasto ID", "—"),
                "gmd": float(melhor.get("GMD (kg/dia)", 0)),
            },
            "tabela": engorda.tail(10).to_dict('records'),
        }
    except Exception as e:
        return {"lotes_ativos": 0, "ganho_medio": 0, "melhor_lote": {}, "tabela": [], "erro": str(e)}


def gmd_lotacao_analise(dados: dict = None) -> dict:
    """
    Análise histórica de GMD vs lotação (densidade).

    Returns:
        {
            "periodos": [...],
            "correlacao": -0.45,  # GMD vs lotação (esperado negativo: menos densidade = melhor ganho)
            "recomendacao": "Reduzir lotação para melhorar GMD"
        }
    """
    try:
        abas = dados or {}
        historico = abas.get("GMD Lotação") or carregar_aba("GMD Lotação")

        if historico.empty:
            return {"periodos": [], "correlacao": 0, "recomendacao": ""}

        historico["GMD (kg/dia)"] = pd.to_numeric(historico.get("GMD (kg/dia)", 0), errors="coerce")
        historico["Lotação (UA/ha)"] = pd.to_numeric(historico.get("Lotação (UA/ha)", 0), errors="coerce")

        # Calcular correlação
        correlacao = historico["GMD (kg/dia)"].corr(historico["Lotação (UA/ha)"])

        # Recomendação baseada na correlação
        if correlacao < -0.3:
            rec = "Reduzir lotação para melhorar ganho de peso"
        elif correlacao > 0.3:
            rec = "Aumentar lotação (há espaço disponível)"
        else:
            rec = "Lotação está adequada ao ganho esperado"

        return {
            "periodos": historico.tail(12).to_dict('records'),
            "correlacao": round(float(correlacao) if not pd.isna(correlacao) else 0, 2),
            "recomendacao": rec,
        }
    except Exception as e:
        return {"periodos": [], "correlacao": 0, "recomendacao": f"Erro: {e}"}


def racao_consumo_analise(dados: dict = None) -> dict:
    """
    Análise de ração oferecida vs consumida (eficiência alimentar).

    Returns:
        {
            "consumo_medio": 85,  # %
            "desperdicio_medio": 15,  # %
            "custo_total_mes": 5000,
            "tabela": [...]
        }
    """
    try:
        abas = dados or {}
        racao = abas.get("Ração Consumo") or carregar_aba("Ração Consumo")

        if racao.empty:
            return {"consumo_medio": 0, "desperdicio_medio": 0, "custo_total_mes": 0, "tabela": []}

        racao["Taxa Consumo (%)"] = pd.to_numeric(racao.get("Taxa Consumo (%)", 0), errors="coerce")
        racao["Custo Total Oferecido (R$)"] = pd.to_numeric(racao.get("Custo Total Oferecido (R$)", 0), errors="coerce")

        consumo_medio = racao["Taxa Consumo (%)"].mean() or 0
        desperdicio = 100 - consumo_medio
        custo_mes = racao["Custo Total Oferecido (R$)"].sum() or 0

        return {
            "consumo_medio": round(consumo_medio, 1),
            "desperdicio_medio": round(desperdicio, 1),
            "custo_total_mes": round(custo_mes, 2),
            "tabela": racao.tail(10).to_dict('records'),
        }
    except Exception as e:
        return {
            "consumo_medio": 0, "desperdicio_medio": 0, "custo_total_mes": 0,
            "tabela": [], "erro": str(e)
        }


def mortalidade_bezerros_analise(dados: dict = None) -> dict:
    """
    Análise de mortalidade de bezerros.

    Returns:
        {
            "taxa_media": 5.2,  # %
            "total_nascidos": 150,
            "total_mortos": 8,
            "causas": {"diarreia": 3, "infecção": 2, "outro": 3},
            "tabela": [...]
        }
    """
    try:
        abas = dados or {}
        mortalidade = abas.get("Mortalidade Bezerros") or carregar_aba("Mortalidade Bezerros")

        if mortalidade.empty:
            return {
                "taxa_media": 0, "total_nascidos": 0, "total_mortos": 0,
                "causas": {}, "tabela": []
            }

        mortalidade["Taxa Mortalidade (%)"] = pd.to_numeric(
            mortalidade.get("Taxa Mortalidade (%)", 0), errors="coerce"
        )
        mortalidade["Bezerros Nascidos"] = pd.to_numeric(
            mortalidade.get("Bezerros Nascidos", 0), errors="coerce"
        )
        mortalidade["Bezerros Mortos"] = pd.to_numeric(
            mortalidade.get("Bezerros Mortos", 0), errors="coerce"
        )

        taxa_media = mortalidade["Taxa Mortalidade (%)"].mean() or 0
        total_nascidos = mortalidade["Bezerros Nascidos"].sum() or 0
        total_mortos = mortalidade["Bezerros Mortos"].sum() or 0

        # Contar causas
        causas = {}
        for col in ["Causa 1", "Causa 2", "Causa 3"]:
            if col in mortalidade.columns:
                causas.update(mortalidade[col].value_counts().to_dict())

        return {
            "taxa_media": round(taxa_media, 1),
            "total_nascidos": int(total_nascidos),
            "total_mortos": int(total_mortos),
            "causas": {str(k): int(v) for k, v in sorted(causas.items(), key=lambda x: x[1], reverse=True)[:5]},
            "tabela": mortalidade.tail(12).to_dict('records'),
        }
    except Exception as e:
        return {
            "taxa_media": 0, "total_nascidos": 0, "total_mortos": 0,
            "causas": {}, "tabela": [], "erro": str(e)
        }


def mortalidade_por_faixa_etaria(dados: dict = None) -> dict:
    """Mortalidade segmentada por faixa etária (v5.15).

    Usa o cadastro de animais: cada animal com Status "Morto" tem `Nascimento`
    e `Data Saída`; a idade na morte define a faixa. `%Part` = quanto aquela
    faixa representa do total de mortos. Só leitura — não mexe nas finanças.
    """
    abas = dados or {}
    df = abas.get("Animais")
    if df is None:
        try:
            df = carregar_aba("Animais")
        except Exception:
            df = None
    faixas_def = [
        ("0 a 4 meses", 0, 4),
        ("5 a 12 meses", 5, 12),
        ("13 a 24 meses", 13, 24),
        ("25 a 36 meses", 25, 36),
        ("> 36 meses", 37, 9999),
    ]
    contagem = {rot: 0 for rot, *_ in faixas_def}
    sem_data = 0
    total = 0
    if df is not None and not df.empty and "Status" in df.columns:
        mortos = df[df["Status"].astype(str).str.strip() == "Morto"]
        nasc = pd.to_datetime(mortos.get("Nascimento"), dayfirst=True, errors="coerce") \
            if "Nascimento" in mortos.columns else pd.Series([pd.NaT] * len(mortos), index=mortos.index)
        saida = pd.to_datetime(mortos.get("Data Saída"), dayfirst=True, errors="coerce") \
            if "Data Saída" in mortos.columns else pd.Series([pd.NaT] * len(mortos), index=mortos.index)
        for n, s in zip(nasc, saida):
            if pd.isna(n) or pd.isna(s):
                sem_data += 1
                continue
            meses = int((s - n).days / 30.44)
            for rot, lo, hi in faixas_def:
                if lo <= meses <= hi:
                    contagem[rot] += 1
                    total += 1
                    break
    lista = [{"faixa": rot, "n": contagem[rot],
              "pct": round(contagem[rot] * 100 / total, 1) if total else 0}
             for rot, *_ in faixas_def]
    return {"faixas": lista, "total": total, "sem_data": sem_data}
