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
    """A carência vem de doencas_carencia (fonte única das 3 abas)."""
    from datetime import date as _date

    from doencas_carencia import _status_de

    linha = {
        "animal_id": "A0001", "brinco": "Amarelo 21 #A0001",
        "data": _date(2026, 10, 25), "medicamento": "Ceftiofur",
        "descricao": "Mastite", "dias_leite": 3, "dias_carne": 4,
        "conhecida_leite": True, "conhecida_carne": True,
    }
    carencias = [dict(_status_de([linha], "leite", _date(2026, 10, 26)), animal_id="A0001")]

    itens = alertas.todos(carencias=carencias, referencia=date(2026, 10, 26))

    carencia = next(item for item in itens if item["origem"] == "tratamento")
    assert carencia["prioridade"] == "urgente"
    assert "A0001" in carencia["detalhe"]
    assert carencia["rota"] == "/doencas"


def test_alertas_detecta_qualidade_do_leite_por_ccs_e_cpp():
    """CLAUDE.md documenta _qualidade_leite_alertas (CCS 200k/400k, CPP 100k/500k)."""
    casos = [
        ({"CCS (células/mL)": "450000"}, "urgente"),
        ({"CCS (células/mL)": "250000"}, "aviso"),
        ({"CCS (células/mL)": "100000"}, None),
        ({"CPP (UFC/mL)": "600000"}, "urgente"),
        ({"CPP (UFC/mL)": "200000"}, "aviso"),
    ]
    for campos, esperado in casos:
        producao = pd.DataFrame([dict(campos, Data="25/10/2026", Litros=18,
                                      **{"Modo Registro": "total"})])
        itens = alertas.todos(producao=producao, referencia=date(2026, 10, 26))
        achou = [i for i in itens if i["origem"] == "qualidade"]
        if esperado is None:
            assert not achou, campos
        else:
            assert achou and achou[0]["prioridade"] == esperado, campos


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
