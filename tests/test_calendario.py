# -*- coding: utf-8 -*-
import pandas as pd
from datetime import date

import calendario


def _manejo(**kw):
    base = {"Data": "", "Tipo": "", "Descrição": "", "Produto": "", "Brincos": ""}
    base.update(kw)
    return base


def test_eventos_normaliza_fontes_e_ignora_data_invalida():
    dados = {
        "Manejo": pd.DataFrame([
            _manejo(Data="10/10/2026", Tipo="Pesagem", Descrição="Curral"),
            _manejo(Data="não é data", Tipo="Pesagem"),
            _manejo(Data="05/10/2026", Tipo="Movimentação de Pasto", Descrição="P01"),
        ]),
        "Visitas": pd.DataFrame([{"Data": "08/10/2026", "Responsável": "Deyvid"}]),
    }
    eventos = calendario.eventos(dados, inicio="01/10/2026", fim="31/10/2026")
    assert [e["data"].strftime("%d/%m") for e in eventos] == ["05/10", "08/10", "10/10"]
    assert all(e["origem"] in {"Manejo", "Visitas"} for e in eventos)


def test_eventos_filtra_por_tipo_e_mantem_vazio():
    assert calendario.eventos({}, tipo="saude") == []
    dados = {"Manejo": pd.DataFrame([_manejo(Data="10/10/2026", Tipo="Vacina Raiva")])}
    assert calendario.eventos(dados, tipo="saude")[0]["tipo"] == "saude"


def test_eventos_mes_retorna_dict_por_data():
    """eventos_mes retorna { data: [eventos] } para o mês especificado."""
    dados = {
        "Manejo": pd.DataFrame([
            _manejo(Data="05/11/2026", Tipo="Pesagem"),
            _manejo(Data="10/11/2026", Tipo="Vacinação"),
            _manejo(Data="05/10/2026", Tipo="Pesagem"),  # Outro mês, não deve entrar
        ]),
        "Visitas": pd.DataFrame([{"Data": "08/11/2026", "Responsável": "Deyvid"}]),
    }
    resultado = calendario.eventos_mes(dados, mes=11, ano=2026)

    # Deve retornar dict
    assert isinstance(resultado, dict)

    # Deve ter eventos em 5, 8 e 10 de novembro (não 5 de outubro)
    assert date(2026, 11, 5) in resultado
    assert date(2026, 11, 8) in resultado
    assert date(2026, 11, 10) in resultado
    assert date(2026, 10, 5) not in resultado

    # Cada data tem lista de eventos
    assert len(resultado[date(2026, 11, 5)]) == 1
    assert resultado[date(2026, 11, 5)][0]["titulo"] == "Pesagem"
    assert len(resultado[date(2026, 11, 8)]) == 1
    assert resultado[date(2026, 11, 8)][0]["titulo"] == "Visita"


def test_eventos_mes_calcula_urgencia():
    """eventos_mes marca urgência por dias até o evento."""
    hoje = date(2026, 11, 15)
    dados = {
        "Tarefas": pd.DataFrame([
            {"Data": "15/11/2026", "Título": "Hoje", "Feito Em": "", "Responsável": ""},
            {"Data": "17/11/2026", "Título": "Em 2 dias", "Feito Em": "", "Responsável": ""},
            {"Data": "22/11/2026", "Título": "Em 7 dias", "Feito Em": "", "Responsável": ""},
            {"Data": "25/11/2026", "Título": "Em 10 dias", "Feito Em": "", "Responsável": ""},
        ])
    }
    resultado = calendario.eventos_mes(dados, mes=11, ano=2026, hoje=hoje)

    # Verificar urgências
    assert resultado[date(2026, 11, 17)][0]["urgencia"] == "urgente"  # 2 dias
    assert resultado[date(2026, 11, 22)][0]["urgencia"] == "aviso"    # 7 dias
    assert resultado[date(2026, 11, 25)][0]["urgencia"] == "normal"   # 10 dias
