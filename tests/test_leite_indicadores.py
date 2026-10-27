# -*- coding: utf-8 -*-

from datetime import date

import pandas as pd

from leite import contagens_rebanho, medias_periodo


def test_medias_periodo_separam_media_diaria_mensal_e_por_animal():
    producao = pd.DataFrame([
        {"Data": "01/10/2026", "Vaca ID": "A1", "Modo Registro": "individual", "Litros": 10},
        {"Data": "02/10/2026", "Vaca ID": "A1", "Modo Registro": "individual", "Litros": 14},
        {"Data": "02/10/2026", "Vaca ID": "A2", "Modo Registro": "individual", "Litros": 6},
    ])
    resultado = medias_periodo(producao, date(2026, 10, 1), date(2026, 10, 2), animais_lactacao=2)
    assert resultado["media_diaria"] == 15
    assert resultado["media_mensal"] == 30
    assert resultado["media_por_animal"] == 15
    assert resultado["media_por_animal_lactacao"] == 15


def test_contagens_rebanho_separam_ativos_de_lactacao():
    animais = pd.DataFrame([
        {"ID": "A1", "Status": "Vivo", "Sexo": "F", "Uso Produtivo": "leite", "Situação Leite": "lactação"},
        {"ID": "A2", "Status": "Vivo", "Sexo": "F", "Uso Produtivo": "leite", "Situação Leite": "seca"},
        {"ID": "A3", "Status": "Vivo", "Sexo": "M", "Uso Produtivo": "corte", "Situação Leite": ""},
        {"ID": "A4", "Status": "Morto", "Sexo": "F", "Uso Produtivo": "leite", "Situação Leite": "lactação"},
    ])
    assert contagens_rebanho(animais) == {
        "animais_ativos": 3,
        "vacas_leiteiras_ativas": 2,
        "vacas_lactacao": 1,
    }
