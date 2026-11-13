#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_pastos_embrapa.py — Testes para Pastoreio Rotativo e Indicadores Embrapa
"""
import pytest
import pandas as pd


def test_pastos_rotativo_logica():
    import pastos_avancados as PAV
    
    df_p = pd.DataFrame([{"ID": "P01", "Nome": "Pasto 01", "Área (ha)": 10.0, "Ativo": "Sim"}])
    df_m = pd.DataFrame()
    
    analise = PAV.analise_rotativo_pasto("P01", df_p, df_m)
    assert analise["pasto_id"] == "P01"
    assert analise["area_ha"] == 10.0


def test_indicadores_embrapa_calculo():
    import indicadores_embrapa as IE
    
    df_a = pd.DataFrame([
        {"ID": "A001", "Sexo": "F", "Categoria": "Vaca", "Status": "Vivo"},
        {"ID": "A002", "Sexo": "F", "Categoria": "Vaca", "Status": "Vivo"},
    ])
    df_m = pd.DataFrame()
    
    nat = IE.calcular_taxa_natalidade(df_a, df_m)
    assert nat["matrizes"] == 2
    
    desm = IE.calcular_taxa_desmama(df_a, df_m)
    assert desm["matrizes"] == 2
