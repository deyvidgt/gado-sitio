#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_rotas_novas_v510.py — Testes das rotas novas v5.10

Testa:
- /financeiro
- /resultado
- /fluxo-caixa
- /fluxo-animais
- /lembretes-whatsapp
- /confinamento
- /confinamento/novo
- /genetica
- /genetica/compatibilidade
"""

import pytest


def test_rotulos_mensais_do_fluxo_de_caixa_em_portugues():
    import routes_financeiro_novo
    from datetime import datetime

    assert [
        routes_financeiro_novo._rotulo_mes_pt(datetime(2025, mes, 1))
        for mes in range(1, 13)
    ] == [
        "Jan/25", "Fev/25", "Mar/25", "Abr/25", "Mai/25", "Jun/25",
        "Jul/25", "Ago/25", "Set/25", "Out/25", "Nov/25", "Dez/25",
    ]


def test_graficos_do_fluxo_de_caixa_usam_rotulos_traduzidos(cliente, monkeypatch):
    import routes_financeiro_novo

    monkeypatch.setattr(
        routes_financeiro_novo,
        "_calcular_fluxo_mensal",
        lambda vendas, compras, gastos: [{
            "mes": "Fev/26",
            "receita": 100,
            "despesa": 50,
            "saldo_mes": 50,
            "saldo_acumulado": 50,
        }],
    )

    html = cliente.get("/fluxo-caixa").get_data(as_text=True)

    assert html.count('"Fev/26"') == 2
    assert "Feb/26" not in html


def test_conversao_media_sem_animais_usa_zero(monkeypatch, cliente):
    import pandas as pd
    import conversao_alimentar

    monkeypatch.setattr(conversao_alimentar.animais, "carregar", lambda: pd.DataFrame())

    resumo = conversao_alimentar.resumo_conversao_alimentar()
    resposta = cliente.get("/nutrição/conversão")

    assert resumo["conversao_media"] == 0.0
    assert resposta.status_code == 200
    assert "Conversao Media</div>" in resposta.get_data(as_text=True)
    assert ">0.0</div>" in resposta.get_data(as_text=True)
    assert ">None</div>" not in resposta.get_data(as_text=True)


def test_conversao_media_ignora_none_nan_e_infinito(monkeypatch):
    import math
    import pandas as pd
    import conversao_alimentar

    monkeypatch.setattr(
        conversao_alimentar.animais,
        "carregar",
        lambda: pd.DataFrame([{"ID": "A1"}, {"ID": "A2"}, {"ID": "A3"}, {"ID": "A4"}]),
    )
    valores = iter([None, float("nan"), float("inf"), 4.25])
    monkeypatch.setattr(
        conversao_alimentar,
        "calcular_conversao_alimentar",
        lambda animal_id: {
            "conversao_alimentar": next(valores),
            "consumo_total_kg": 0,
            "ganho_total_kg": 0,
        },
    )
    monkeypatch.setattr(conversao_alimentar, "gerar_alertas_conversao", lambda: [])

    resumo = conversao_alimentar.resumo_conversao_alimentar()

    assert math.isfinite(resumo["conversao_media"])
    assert resumo["conversao_media"] == 4.25


def test_rota_financeiro(cliente):
    """GET /financeiro deve retornar 200."""
    rv = cliente.get("/financeiro")
    assert rv.status_code == 200
    assert b"Financeiro" in rv.data or b"financeiro" in rv.data.lower()


def test_financeiro_usa_estoque_calculado_por_membro(cliente, monkeypatch):
    import pandas as pd
    import routes_financeiro_novo as financeiro
    import calculos
    from flask import jsonify

    dados = {
        "Compras": pd.DataFrame(),
        "Gastos": pd.DataFrame(),
        "Vendas": pd.DataFrame(),
        "Manejo": pd.DataFrame(),
    }
    resultado_membros = {
        membro: {"resultado_realizado": 0, "capital_imobilizado": 0, "ctcab": 0}
        for membro in financeiro.MEMBROS
    }
    estoque = dict(zip(financeiro.MEMBROS, (13, 12, 11)))

    monkeypatch.setattr(financeiro, "_get_dados_cache", lambda: dados)
    monkeypatch.setattr(financeiro, "_get_resumo_cache", lambda: {})
    monkeypatch.setattr(financeiro, "_get_membros_cache", lambda: {})
    monkeypatch.setattr(calculos, "calcular_todos_membros", lambda *args: resultado_membros)
    monkeypatch.setattr(financeiro, "calcular_estoque_por_membro", lambda *args: estoque)
    monkeypatch.setattr(financeiro, "_grafico_receita_vs_custo", lambda *args: None)
    monkeypatch.setattr(financeiro, "_grafico_resultado_por_membro", lambda *args: None)
    monkeypatch.setattr(
        financeiro,
        "render_template",
        lambda template, **context: jsonify(context["tabela_membros"]),
    )

    resposta = cliente.get("/financeiro")

    assert resposta.status_code == 200
    tabela = resposta.get_json()
    assert [linha["estoque"] for linha in tabela] == [13, 12, 11]


def test_rota_resultado(cliente):
    """GET /resultado deve retornar 200."""
    rv = cliente.get("/resultado")
    assert rv.status_code == 200
    assert b"Resultado" in rv.data or b"resultado" in rv.data.lower()


def test_rota_fluxo_caixa(cliente):
    """GET /fluxo-caixa deve retornar 200."""
    rv = cliente.get("/fluxo-caixa")
    assert rv.status_code == 200
    assert b"Fluxo" in rv.data or b"fluxo" in rv.data.lower()


def test_rota_fluxo_animais(cliente):
    """GET /fluxo-animais deve retornar 200."""
    rv = cliente.get("/fluxo-animais")
    assert rv.status_code == 200
    assert b"Fluxo" in rv.data or b"fluxo" in rv.data.lower()


def test_rota_lembretes_whatsapp(cliente):
    """GET /lembretes-whatsapp deve retornar 200."""
    rv = cliente.get("/lembretes-whatsapp")
    assert rv.status_code == 200
    assert b"WhatsApp" in rv.data or b"whatsapp" in rv.data.lower()


def test_rota_confinamento(cliente):
    """GET /confinamento deve retornar 200."""
    rv = cliente.get("/confinamento")
    assert rv.status_code == 200
    assert b"Confinamento" in rv.data or b"confinamento" in rv.data.lower()


def test_rota_novo_lote(cliente):
    """GET /confinamento/novo deve retornar 200."""
    rv = cliente.get("/confinamento/novo")
    assert rv.status_code == 200
    assert b"Lote" in rv.data or b"lote" in rv.data.lower()


def test_rota_genetica(cliente):
    """GET /genetica deve retornar 200."""
    rv = cliente.get("/genetica")
    assert rv.status_code == 200
    assert b"Genetica" in rv.data or b"genetica" in rv.data.lower()


def test_rota_compatibilidade_acasalamento(cliente):
    """GET /genetica/compatibilidade deve retornar 200."""
    rv = cliente.get("/genetica/compatibilidade")
    assert rv.status_code == 200
    assert b"Compatibilidade" in rv.data or b"compatibilidade" in rv.data.lower()


def test_novo_lote_post(cliente, dados_restaurados):
    """POST /confinamento/novo com dados válidos deve criar lote."""
    data = {
        "data_entrada": "2026-10-28",
        "lote_id": "L2026-TEST-001",
        "brincos": "Amarelo 01 #A0001",
        "quantidade": "10",
        "peso_inicial": "300",
        "observacao": "Teste",
    }
    rv = cliente.post("/confinamento/novo", data=data, follow_redirects=True)
    # Pode ser 200 (sucesso) ou 302 (redirect para /confinamento)
    assert rv.status_code in (200, 302)


def test_compatibilidade_post(cliente):
    """POST /genetica/compatibilidade com dados válidos deve processar."""
    data = {
        "touro_id": "A0001",
        "vaca_id": "A0002",
    }
    rv = cliente.post("/genetica/compatibilidade", data=data)
    assert rv.status_code == 200
    # POST processa e retorna o template com o resultado
    assert b"html" in rv.data  # template renderizada
