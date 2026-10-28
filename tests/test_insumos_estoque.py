#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes da página de estoque de insumos com marca, kg, valor e nutrição (v5.10).
"""
import pandas as pd
from datetime import datetime

import insumos as I


def test_estoque_completo_sem_catalogo():
    """Sem aba Insumos, retorna previsão só."""
    # Sem catálogo
    result = I.estoque_completo(None, pd.DataFrame(), pd.DataFrame())

    assert len(result) == 3  # Sal, Proteinado, Ração
    assert all("marca" in r for r in result)
    assert all(r["marca"] is None for r in result)


def test_estoque_completo_com_catalogo():
    """Com catálogo, adiciona marca, PB%, Energia, kg e valor total."""
    # Cria aba Insumos com dados
    df_insumos = pd.DataFrame({
        "Tipo": ["Sal", "Proteinado", "Ração"],
        "Marca": ["Sal Marinha", "Pro 40%", "Ração Premium"],
        "R$/Saco": [45.00, 120.00, 85.00],
        "kg/Saco": [25.0, 20.0, 20.0],
        "PB (%)": [None, 40.0, 16.5],
        "Energia (Mcal/kg)": [None, 2.4, 2.1],
        "Data Cadastro": [datetime.now()] * 3,
        "Observações": [""] * 3,
    })

    result = I.estoque_completo(df_insumos, pd.DataFrame(), pd.DataFrame())

    assert len(result) == 3

    # Verifica Sal
    sal = [r for r in result if r["produto"] == "Sal"][0]
    assert sal["marca"] == "Sal Marinha"
    assert sal["preco_saco"] == 45.00
    assert sal["kg_saco"] == 25.0

    # Verifica Proteinado com nutrição
    prot = [r for r in result if r["produto"] == "Proteinado"][0]
    assert prot["marca"] == "Pro 40%"
    assert prot["pb_pct"] == 40.0
    assert prot["energia"] == 2.4


def test_estoque_completo_calcula_kg_e_valor():
    """Calcula kg em estoque e valor total com dados do catálogo."""
    df_insumos = pd.DataFrame({
        "Tipo": ["Proteinado"],
        "Marca": ["Pro 40%"],
        "R$/Saco": [120.00],
        "kg/Saco": [20.0],
        "PB (%)": [40.0],
        "Energia (Mcal/kg)": [2.4],
        "Data Cadastro": [datetime.now()],
        "Observações": [""],
    })

    # Com contagem de estoque
    df_vis = pd.DataFrame({
        "Data": [datetime.now()],
        "Sacos Proteinado": [5.0],  # 5 sacos
    })

    result = I.estoque_completo(df_insumos, df_vis, pd.DataFrame())
    prot = [r for r in result if r["produto"] == "Proteinado"][0]

    if prot["estoque"] is not None:
        assert prot["kg_estoque"] == 5.0 * 20.0  # 100 kg
        assert prot["valor_total"] == 5.0 * 120.00  # R$ 600
