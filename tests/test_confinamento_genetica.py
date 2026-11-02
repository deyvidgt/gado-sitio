#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_confinamento_genetica.py — Testes de confinamento e genética

Testa funções:
- confinamento.py: lotes_ativos, resumo_lote, ganho_total, custo_por_lote, alertas
- genetica.py: genealogia_animal, calcular_endogamia_simples, compatibilidade_acasalamento, avisos_genetica
"""

import pytest
import pandas as pd
from datetime import datetime


def test_confinamento_lotes_ativos_vazio():
    """lotes_ativos() com dados vazios deve retornar DataFrame vazio."""
    import confinamento as CONF

    dados = {"Confinamento Lotes": pd.DataFrame()}
    ativos = CONF.lotes_ativos(dados)

    assert ativos.empty


def test_confinamento_resumo_lote_vazio():
    """resumo_lote() com lote inexistente deve retornar dict vazio."""
    import confinamento as CONF

    dados = {"Confinamento Lotes": pd.DataFrame()}
    resumo = CONF.resumo_lote("L001", dados)

    assert resumo == {}


def test_confinamento_ganho_total():
    """ganho_total() deve calcular peso_final - peso_inicial."""
    import confinamento as CONF

    # Mock de um lote
    conf_df = pd.DataFrame({
        "Lote ID": ["L001"],
        "Quantidade": [10],
        "Peso Inicial (kg)": [300],
        "Peso Final (kg)": [450],
        "Dias Confinado": [150],
        "GMD (kg/dia)": [1.0],
        "Status": ["Ativo"],
    })
    dados = {"Confinamento Lotes": conf_df}

    ganho = CONF.ganho_total("L001", dados)

    assert ganho == 150  # 450 - 300


def test_confinamento_custo_por_lote():
    """custo_por_lote() deve calcular custo/cabeça e resultado."""
    import confinamento as CONF

    conf_df = pd.DataFrame({
        "Lote ID": ["L001"],
        "Quantidade": [10],
        "Peso Inicial (kg)": [300],
        "Peso Final (kg)": [450],
        "Dias Confinado": [150],
        "GMD (kg/dia)": [1.0],
        "Status": ["Ativo"],
    })
    dados = {"Confinamento Lotes": conf_df}

    # Custo total R$5000, preço de venda R$300/arroba
    resultado = CONF.custo_por_lote("L001", custo_total=5000, preco_venda_arroba=300, dados=dados)

    assert resultado["custo_total"] == 5000
    assert resultado["custo_por_cab"] == 500  # 5000 / 10
    assert resultado["custo_por_dia"] == 33.33  # ~5000 / 150
    # 1 @ = 15 kg de carcaça: 450 kg × 0,58 = 261 kg → 17,4 @ → R$5.220/cab.
    assert resultado["receita_por_cab"] == 5220.0
    assert "resultado" in resultado
    assert "margem" in resultado


def test_confinamento_alertas_gmd_baixo():
    """alertas_confinamento() deve retornar alerta se GMD < 0.5."""
    import confinamento as CONF

    conf_df = pd.DataFrame({
        "Lote ID": ["L001"],
        "Quantidade": [10],
        "Peso Inicial (kg)": [300],
        "Peso Final (kg)": [305],
        "Dias Confinado": [30],
        "GMD (kg/dia)": [0.17],  # Baixo!
        "Status": ["Ativo"],
    })
    dados = {"Confinamento Lotes": conf_df}

    alertas = CONF.alertas_confinamento(dados)

    assert len(alertas) > 0
    assert alertas[0]["urgente"] == True
    assert "GMD baixo" in alertas[0]["texto"]


def test_confinamento_alertas_dias_altos():
    """alertas_confinamento() deve retornar aviso se dias > 120."""
    import confinamento as CONF

    conf_df = pd.DataFrame({
        "Lote ID": ["L001"],
        "Quantidade": [10],
        "Peso Inicial (kg)": [300],
        "Peso Final (kg)": [450],
        "Dias Confinado": [150],  # > 120!
        "GMD (kg/dia)": [1.0],
        "Status": ["Ativo"],
    })
    dados = {"Confinamento Lotes": conf_df}

    alertas = CONF.alertas_confinamento(dados)

    assert len(alertas) > 0
    assert alertas[0]["urgente"] == False  # Aviso, não urgente
    assert "150" in alertas[0]["texto"]


def test_genetica_genealogia_vazia():
    """genealogia_animal() com animal inexistente deve retornar dict vazio."""
    import genetica as GEN

    dados = {"Animais": pd.DataFrame()}
    gen = GEN.genealogia_animal("A0001", dados)

    assert gen == {}


def test_genetica_endogamia_simples_diferente():
    """calcular_endogamia_simples() com pai != mãe deve retornar "nenhum"."""
    import genetica as GEN

    resultado = GEN.calcular_endogamia_simples("T0001", "V0001")

    assert resultado["risco"] == "nenhum"
    assert resultado["coeficiente"] == 0


def test_genetica_endogamia_simples_igual():
    """calcular_endogamia_simples() com pai == mãe deve retornar "urgente"."""
    import genetica as GEN

    resultado = GEN.calcular_endogamia_simples("T0001", "T0001")

    assert resultado["risco"] == "urgente"
    assert resultado["coeficiente"] == 100
    assert "CONSANGUINIDADE" in resultado["msg"]


def test_genetica_compatibilidade_mesmo_animal():
    """compatibilidade_acasalamento() com touro == vaca deve retornar False."""
    import genetica as GEN

    resultado = GEN.compatibilidade_acasalamento("A0001", "A0001")

    assert resultado["compativel"] == False
    assert "mesmo animal" in resultado["motivo"].lower()


def test_genetica_compatibilidade_diferente():
    """compatibilidade_acasalamento() com animais diferentes deve retornar compatível."""
    import genetica as GEN

    # Com dados de genealogia, animais diferentes podem cruzar
    animais_df = pd.DataFrame({
        "ID": ["T0001", "V0001"],
        "Pai": ["T9999", "T8888"],
        "Mãe": ["V9999", "V8888"],
    })
    dados = {"Animais": animais_df}

    resultado = GEN.compatibilidade_acasalamento("T0001", "V0001", dados)

    assert resultado["compativel"] == True


def test_genetica_avisos_vazio():
    """avisos_genetica() com dados vazios deve retornar lista vazia."""
    import genetica as GEN

    dados = {"Animais": pd.DataFrame()}
    avisos = GEN.avisos_genetica(dados)

    assert avisos == []


def test_confinamento_resumo_mensal():
    """resumo_mensal_confinamento() deve retornar dict com num_lotes, cabecas, gmd."""
    import confinamento as CONF

    conf_df = pd.DataFrame({
        "Lote ID": ["L001", "L002"],
        "Quantidade": [10, 15],
        "Peso Inicial (kg)": [300, 280],
        "Peso Final (kg)": [450, 400],
        "Dias Confinado": [150, 120],
        "GMD (kg/dia)": [1.0, 0.8],
        "Status": ["Ativo", "Ativo"],
    })
    dados = {"Confinamento Lotes": conf_df}

    resumo = CONF.resumo_mensal_confinamento(dados)

    assert resumo["num_lotes"] == 2
    assert resumo["total_cabecas"] == 25
    assert resumo["gmd_medio"] == 0.9  # (1.0 + 0.8) / 2
    assert "mensagem" in resumo


def test_genetica_resumo_mensal_sem_avisos():
    """resumo_mensal_genetica() sem avisos deve retornar num_avisos=0."""
    import genetica as GEN

    dados = {"Animais": pd.DataFrame()}
    resumo = GEN.resumo_mensal_genetica(dados)

    assert resumo["num_avisos"] == 0
    assert "ok" in resumo["mensagem"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
