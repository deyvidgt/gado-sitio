# -*- coding: utf-8 -*-
"""
Testes de integração cruzada entre módulos (conveniências textuais e parsers).
Garante que tipos de manejo, IDs de animais e colunas cruzadas não quebram silenciosamente.
"""
from datetime import date

import pandas as pd
import pytest

import reproducao
import pastos
import animais
import cochos

def test_convencoes_manejo_reproducao():
    assert reproducao.TIPO_DIAGNOSTICO == "Diagnóstico de Gestação"
    df = pd.DataFrame([
        {"Data": "01/01/2026", "Tipo": "Cobertura", "Descrição": "", "Produto": "Touro 1", "Brincos": "Amarelo 01 #A0001"}
    ], columns=["Data", "Tipo", "Descrição", "Produto", "Brincos"])
    anim = pd.DataFrame([
        {"ID": "A0001", "Brinco Cor": "Amarelo", "Brinco Nº": 1, "Sexo": "F", "Status": "Vivo", "Mãe": "", "Nascimento": ""}
    ])
    sit = reproducao.situacao(df, anim, pd.Timestamp("2026-06-01"))
    assert len(sit) == 1
    assert sit[0]["status"] == "coberta"

def test_convencoes_manejo_pastos():
    assert pastos.TIPO_MOV == "Movimentação de Pasto"
    df_pasto = pd.DataFrame([
        {"ID": "P01", "Nome": "Pasto 1", "Área (ha)": 10.0, "Ativo": "Sim", "Contorno": "{}", "Criado Por": "Deyvid"}
    ])
    assert not pastos.ativos(df_pasto).empty

def test_formatos_brincos_animais():
    linha = "Amarelo 21 #A0005"
    ids = animais.ids_de(linha)
    assert ids == ["A0005"]

def test_cochos_extracao_visitas():
    df_vazio = pd.DataFrame(columns=["Data", "Sacos Proteinado", "Sacos Sal/Ração", "Sacos Ração"])
    assert cochos.extrair_consumo_visitas(df_vazio) == {}

    df = pd.DataFrame([{
        "Data": date.today().strftime("%d/%m/%Y"),
        "Sacos Proteinado": 2,
        "Sacos Sal/Ração": 1,
        "Sacos Ração": 3,
    }])
    consumo = cochos.extrair_consumo_visitas(df, dias=60)
    assert consumo["proteinado"]["kg"] == 50
    assert consumo["racao"]["kg"] == 75
