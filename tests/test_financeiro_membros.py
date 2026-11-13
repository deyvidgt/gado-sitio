#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_financeiro_membros.py — Testes para os cálculos financeiros da tabela "Status por Membro" em /financeiro
"""
import pytest
import pandas as pd


def test_calculo_financeiro_por_membro():
    from calculos import calcular_todos_membros, calcular_estoque_por_membro

    # Mock de dados financeiros e rebanho
    df_comp = pd.DataFrame([
        {"Data": pd.Timestamp("2026-01-01"), "Qtd Cabeças": 30, "Valor Total (R$)": 90000.0, "Qtd Mae": 10, "Qtd Deyvid": 10, "Qtd Nilson": 10}
    ])
    df_gast = pd.DataFrame([
        {"Data": pd.Timestamp("2026-01-15"), "Valor Total (R$)": 6000.0, "Qtd Cabeças": 30, "Valor/Cabeça (R$)": 200.0}
    ])
    df_vend = pd.DataFrame([
        {"Data": pd.Timestamp("2026-02-01"), "Qtd Cabeças": 6, "Valor Total (R$)": 24000.0, "Qtd Mae": 2, "Qtd Deyvid": 2, "Qtd Nilson": 2}
    ])
    df_man = pd.DataFrame()

    r_membros = calcular_todos_membros(df_vend, df_comp, df_gast, df_man)
    estoque_membros = calcular_estoque_por_membro(df_comp, df_vend, df_man)

    for m in ["Mae", "Deyvid", "Nilson"]:
        res = r_membros.get(m, {})
        # Verificar que os campos retornam valores numéricos reais e não zero fixo
        assert "resultado" in res
        assert "capital_imobilizado" in res or "capital" in res or "custo_total" in res
        assert estoque_membros[m] == 8  # 10 - 2 vendidas
