# -*- coding: utf-8 -*-
"""Testes de contagem, edição e remoção de cochos."""

import pandas as pd

import db
from config import COLUNAS_COCHOS


def test_resumo_cochos_ignora_inativos():
    import cochos as CO

    df = pd.DataFrame([
        ["C01", "Ativo", "sal", "Pasto", 100, 50, "", "", "Sim", "Deyvid"],
        ["C02", "Removido", "sal", "Pasto", 100, 50, "", "", "Não", "Deyvid"],
    ], columns=COLUNAS_COCHOS)

    resumo = CO.resumo_cochos(df, pd.DataFrame())

    assert resumo["total_cochos"] == 1
    assert sum(resumo[k] for k in ("cochos_cheios", "cochos_normais", "cochos_vazios")) == 1


def test_editar_e_remover_cocho_atualiza_pagina(cliente, dados_restaurados, monkeypatch):
    import routes_cochos

    monkeypatch.setattr(routes_cochos, "fazer_backup_seguro", lambda: None)
    db.salvar_linha("Cochos", ["C01", "Cocho 1", "sal", "Pasto", 100, 50, "", "", "Sim", "Deyvid"])
    db.salvar_linha("Cochos", ["C02", "Cocho 2", "sal", "Pasto", 100, 75, "", "", "Sim", "Deyvid"])
    with cliente.session_transaction() as sess:
        sess["csrf_token"] = "token-teste"

    resposta = cliente.post("/cochos/editar/C01", data={
        "csrf_token": "token-teste",
        "nome": "Cocho 1 editado",
        "tipo": "sal",
        "local": "Pasto",
        "capacidade": "100",
        "volume_atual": "20",
        "observacoes": "",
        "ativo": "Sim",
    }, follow_redirects=True)
    html = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "Cocho 1 editado" in html
    assert "20.0 / 100.0 kg" in html
    assert '<div class="resumo-valor">2</div>' in html

    resposta = cliente.post("/cochos/deletar/C01", data={
        "csrf_token": "token-teste",
    }, follow_redirects=True)
    html = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert '<div class="resumo-valor">1</div>' in html
    assert "Cocho 1 editado" not in html
    assert "Cocho 2" in html
