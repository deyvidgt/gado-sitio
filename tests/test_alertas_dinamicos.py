# -*- coding: utf-8 -*-
from datetime import date

import pandas as pd

import alertas


def test_alertas_detecta_ausencia_de_registro_para_vacas_em_lactacao():
    producao = pd.DataFrame([{"Data": "25/10/2026", "Litros": 18, "Modo Registro": "total"}])
    animais = pd.DataFrame([{"Status": "Vivo", "Sexo": "F", "Uso Produtivo": "leite", "Situação Leite": "lactação"}])

    itens = alertas.todos(producao=producao, animais=animais, referencia=date(2026, 10, 26))

    ausencia = next(item for item in itens if item["origem"] == "produção")
    assert ausencia["prioridade"] == "urgente"
    assert "sem registro" in ausencia["detalhe"].lower()


def test_alertas_detecta_tratamento_em_carencia():
    tratamentos = pd.DataFrame([{
        "Data": "25/10/2026", "Vaca ID": "A0001", "Descrição": "Mastite",
        "Período de Carência": "3", "Custo (R$)": "50",
    }])

    itens = alertas.todos(tratamentos=tratamentos, referencia=date(2026, 10, 26))

    carencia = next(item for item in itens if item["origem"] == "tratamento")
    assert carencia["prioridade"] == "urgente"
    assert "A0001" in carencia["detalhe"]


def test_alertas_detecta_colchao_vencido_e_ficha_nutricional_incompleta():
    colchao = pd.DataFrame([{
        "Data": "20/10/2026", "Local": "Baia", "Condição": "suja",
        "Próxima Troca": "25/10/2026",
    }])
    alimentacao = pd.DataFrame([{
        "Produto": "Ração", "Proteína Bruta (%)": "", "NDT/Energia (%)": "",
        "Fibra (%)": "", "Cálcio (%)": "", "Fósforo (%)": "", "Ativo": "Sim",
    }])

    itens = alertas.todos(colchao=colchao, alimentacao=alimentacao,
                          referencia=date(2026, 10, 26))

    assert any(item["origem"] == "colchão" and item["prioridade"] == "urgente" for item in itens)
    assert any(item["origem"] == "nutrição" and "incompleta" in item["detalhe"].lower() for item in itens)
