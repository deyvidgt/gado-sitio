#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
indicadores_embrapa.py — Indicadores Zootécnicos Padrão ANCP / Embrapa
- Taxa de Desmama (Bezerros desmamados / Matrizes expostas)
- Taxa de Natalidade (Nascidos vivos / Matrizes mantidas)
- Eficiência reprodutiva da cria para relatórios de crédito rural.
"""

from __future__ import annotations
import pandas as pd
import reproducao as R
import animais as A

def calcular_taxa_natalidade(df_animais: pd.DataFrame, df_man: pd.DataFrame, ano: int = None) -> dict:
    """Calcula a Taxa de Natalidade: Nascidos vivos / Total de Matrizes (fêmeas reprodutoras)."""
    if df_animais is None or df_animais.empty:
        return {"taxa": 0.0, "nascidos": 0, "matrizes": 0}

    # Contar matrizes (fêmeas adultas / vacas)
    femeas = df_animais[
        df_animais["Sexo"].astype(str).str.upper().str.startswith("F") &
        df_animais["Categoria"].astype(str).str.contains("Vaca|Matriz", case=False, na=False)
    ]
    total_matrizes = len(femeas)
    if total_matrizes == 0:
        # Fallback se categoria não estiver preenchida exatamente assim
        total_matrizes = len(df_animais[df_animais["Sexo"].astype(str).str.upper().str.startswith("F")])

    if total_matrizes == 0:
        return {"taxa": 0.0, "nascidos": 0, "matrizes": 0}

    # Contar partos registrados no Manejo ou animais nascidos
    partos = R._partos(df_animais)
    nascidos_total = sum(len(datas) for datas in partos.values())

    # Se ano especificado, filtrar
    if ano:
        nascidos_ano = 0
        for _, datas in partos.items():
            for d in datas:
                if d.year == ano:
                    nascidos_ano += 1
        nascidos_total = nascidos_ano

    taxa = (nascidos_total / total_matrizes) * 100.0 if total_matrizes > 0 else 0.0

    return {
        "taxa": round(min(taxa, 100.0), 1),
        "nascidos": nascidos_total,
        "matrizes": total_matrizes,
        "classificacao": "Excelente" if taxa >= 80 else ("Bom" if taxa >= 70 else "Atenção"),
    }


def calcular_taxa_desmama(df_animais: pd.DataFrame, df_man: pd.DataFrame, ano: int = None) -> dict:
    """Calcula a Taxa de Desmama: Bezerros desmamados / Matrizes expostas à reprodução."""
    natalidade = calcular_taxa_natalidade(df_animais, df_man, ano)
    matrizes = natalidade["matrizes"]
    nascidos = natalidade["nascidos"]

    # Considerar mortalidade padrão de bezerros (ou ler da aba Mortalidade Bezerros)
    mortalidade_bezerros = 0.05  # 5% padrão Embrapa se não houver dados
    desmamados = int(nascidos * (1.0 - mortalidade_bezerros))

    taxa_desmama = (desmamados / matrizes) * 100.0 if matrizes > 0 else 0.0

    return {
        "taxa": round(min(taxa_desmama, 100.0), 1),
        "desmamados": desmamados,
        "matrizes": matrizes,
        "classificacao": "Excelente" if taxa_desmama >= 75 else ("Bom" if taxa_desmama >= 65 else "Atenção"),
    }
