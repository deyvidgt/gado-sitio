# -*- coding: utf-8 -*-
from datetime import date, datetime

import pandas as pd


def test_painel_leiteiro_exibe_acumulados_e_medias(cliente):
    html = cliente.get("/leite").get_data(as_text=True)
    assert "Acumulado do dia" in html
    assert "Acumulado da semana" in html
    assert "Acumulado do mês" in html
    assert "Acumulado total" in html
    assert "Média por animal" in html
    assert "Animais ativos" in html
    assert "Vacas em lactação" in html


def test_painel_leite_exibe_acumulados_reais_da_planilha(cliente, monkeypatch):
    import routes_leite

    hoje = date(2026, 11, 3)
    df = pd.DataFrame([
        {
            "Data": datetime(2026, 11, 3),
            "Vaca ID": "A1",
            "Modo Registro": "individual",
            "Ordenha": "Manhã",
            "Litros": 8.5,
            "CCS (células/mL)": 120000,
            "CPP (UFC/mL)": 50000,
        },
        {
            "Data": datetime(2026, 11, 2),
            "Vaca ID": "A1",
            "Modo Registro": "individual",
            "Ordenha": "Manhã",
            "Litros": 7.5,
            "CCS (células/mL)": 110000,
            "CPP (UFC/mL)": 45000,
        },
    ])
    monkeypatch.setattr(routes_leite, "_agora", lambda: datetime.combine(hoje, datetime.min.time()))
    monkeypatch.setattr(
        routes_leite,
        "carregar_aba",
        lambda aba: df if aba == "Leite Produção" else pd.DataFrame(),
    )
    monkeypatch.setattr(routes_leite.A, "carregar", lambda: pd.DataFrame())

    html = cliente.get("/leite").get_data(as_text=True)

    assert "Acumulado do dia" in html and "8,5" in html
    assert "Acumulado total" in html and "16,0" in html
    assert "Média / dia no mês" in html and "8,0" in html


def test_lista_de_animais_leiteiros_abre(cliente):
    resposta = cliente.get("/leite/animais")
    assert resposta.status_code == 200
    html = resposta.get_data(as_text=True)
    assert "Vacas leiteiras" in html
    assert "Dias em lactação" in html
