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


def test_rota_financeiro(cliente):
    """GET /financeiro deve retornar 200."""
    rv = cliente.get("/financeiro")
    assert rv.status_code == 200
    assert b"Financeiro" in rv.data or b"financeiro" in rv.data.lower()


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
