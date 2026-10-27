# -*- coding: utf-8 -*-

from datetime import date

import pandas as pd

from leite import (
    acumulados,
    contagens_rebanho,
    dias_em_lactacao,
    medias_periodo,
    producao_por_animal,
    resumo_periodo,
    validar_producao,
)


def _producao():
    return pd.DataFrame([
        {"Data": "20/10/2026", "Vaca ID": "A0001", "Modo Registro": "individual", "Ordenha": "Manhã", "Litros": 10},
        {"Data": "20/10/2026", "Vaca ID": "A0002", "Modo Registro": "individual", "Ordenha": "Manhã", "Litros": 8},
        {"Data": "21/10/2026", "Vaca ID": "A0001", "Modo Registro": "individual", "Ordenha": "Manhã", "Litros": 11},
        {"Data": "22/10/2026", "Vaca ID": "", "Modo Registro": "total", "Ordenha": "Manhã", "Litros": 25},
    ])


def test_validacao_rejeita_litros_negativos():
    erro = validar_producao({"Vaca ID": "A0001", "Modo Registro": "individual", "Litros": "-1"})
    assert "Litros" in erro


def test_resumo_separa_individual_e_total_sem_duplicar():
    resultado = resumo_periodo(_producao(), date(2026, 10, 20), date(2026, 10, 22), animais_lactacao=2)
    assert resultado["litros"] == 54
    assert resultado["litros_individuais"] == 29
    assert resultado["litros_totais"] == 25
    assert resultado["media_por_animal"] == 14.5


def test_acumulados_dia_semana_mes_total():
    resultado = acumulados(_producao(), date(2026, 10, 22))
    assert resultado == {"dia": 25, "semana": 54, "mes": 54, "total": 54}


def test_producao_por_animal_e_dias_em_lactacao():
    por_animal = producao_por_animal(_producao(), date(2026, 10, 20), date(2026, 10, 22))
    assert por_animal["A0001"] == 21
    assert por_animal["A0002"] == 8
    assert dias_em_lactacao("15/10/2026", date(2026, 10, 22)) == 7
    assert dias_em_lactacao("", date(2026, 10, 22)) is None
