# -*- coding: utf-8 -*-
"""
Comparador de proteinado/ração (v5.3): custo por kg, por cabeça/dia e por mês.
"""
import pandas as pd
import pytest

import insumos as I


def test_comparar_ordena_pelo_custo_por_cabeca_dia():
    r = I.comparar([
        {"nome": "Caro",  "preco_saco": 120, "kg_saco": 30, "consumo_g": 300},
        {"nome": "Barato", "preco_saco": 90, "kg_saco": 30, "consumo_g": 300},
    ], cabecas=50)
    assert [o["nome"] for o in r] == ["Barato", "Caro"]
    assert r[0]["melhor"] and not r[1]["melhor"]
    assert r[0]["custo_kg"] == pytest.approx(3.0)
    assert r[0]["custo_cab_dia"] == pytest.approx(0.9)       # 3 R$/kg × 0,3 kg
    assert r[0]["custo_mes"] == pytest.approx(0.9 * 50 * 30)
    assert r[1]["diferenca_mes"] == pytest.approx(r[1]["custo_mes"] - r[0]["custo_mes"])
    assert r[0]["diferenca_mes"] == 0


def test_comparar_consumos_diferentes_podem_inverter_o_mais_barato():
    """Saco mais caro pode sair na frente se o consumo por cabeça é menor."""
    r = I.comparar([
        {"nome": "Barato no saco", "preco_saco": 90,  "kg_saco": 30, "consumo_g": 400},
        {"nome": "Caro no saco",   "preco_saco": 120, "kg_saco": 30, "consumo_g": 200},
    ], cabecas=10)
    assert r[0]["nome"] == "Caro no saco"


def test_comparar_ignora_linha_incompleta_ou_zerada():
    r = I.comparar([
        {"nome": "Ok", "preco_saco": 100, "kg_saco": 25, "consumo_g": 300},
        {"nome": "Sem preço", "preco_saco": 0, "kg_saco": 25, "consumo_g": 300},
        {"nome": "Sem kg", "preco_saco": 100, "kg_saco": 0, "consumo_g": 300},
        {"nome": "", "preco_saco": 100, "kg_saco": 25, "consumo_g": 300},
    ], cabecas=10)
    assert [o["nome"] for o in r] == ["Ok"]


def test_comparar_sem_cabecas_nao_tem_custo_mensal():
    r = I.comparar([{"nome": "A", "preco_saco": 100, "kg_saco": 25, "consumo_g": 300}],
                   cabecas=0)
    assert r[0]["custo_mes"] is None and r[0]["custo_kg"] == pytest.approx(4.0)


def test_ultimo_preco_saco_vem_dos_gastos():
    g = pd.DataFrame([
        {"Data": pd.Timestamp("2026-01-10"), "Produto": "Proteinado",
         "Qtd Sacos": 10, "Valor Total (R$)": 1200},
        {"Data": pd.Timestamp("2026-02-10"), "Produto": "Proteinado",
         "Qtd Sacos": 20, "Valor Total (R$)": 1800},
        {"Data": pd.Timestamp("2026-02-11"), "Produto": "Sal",
         "Qtd Sacos": 5, "Valor Total (R$)": 250},
    ])
    assert I.ultimo_preco_saco(g, "Proteinado") == (90.0, pd.Timestamp("2026-02-10"))
    assert I.ultimo_preco_saco(g, "Sal") == (50.0, pd.Timestamp("2026-02-11"))
    assert I.ultimo_preco_saco(g, "Ração") is None
    assert I.ultimo_preco_saco(pd.DataFrame(), "Sal") is None


def test_pagina_comparar_abre_e_calcula(cliente):
    html = cliente.get("/insumos/comparar").get_data(as_text=True)
    assert "Comparar" in html
    # Só calcula (GET com os valores na URL): não grava nada, não precisa de CSRF.
    html = cliente.get("/insumos/comparar?cabecas=40"
                       "&nome_0=Marca+A&preco_saco_0=120&kg_saco_0=30&consumo_g_0=300"
                       "&nome_1=Marca+B&preco_saco_1=90&kg_saco_1=30&consumo_g_1=300"
                       ).get_data(as_text=True)
    assert "Marca B" in html and "Marca A" in html
