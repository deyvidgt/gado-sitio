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
    db.reescrever_aba("Cochos", pd.DataFrame(columns=COLUNAS_COCHOS))
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
    cochos_salvos = db.carregar_aba("Cochos")
    assert "C01" not in cochos_salvos["ID"].astype(str).tolist()
    assert "C02" in cochos_salvos["ID"].astype(str).tolist()


def test_novo_cocho_rejeita_id_duplicado_e_limpa_planilha(cliente, dados_restaurados, monkeypatch):
    import routes_cochos

    monkeypatch.setattr(routes_cochos, "fazer_backup_seguro", lambda: None)
    db.reescrever_aba("Cochos", pd.DataFrame(columns=COLUNAS_COCHOS))
    db.salvar_linha("Cochos", ["C01", "Cocho antigo", "sal", "Pasto", 100, 25, "", "", "Sim", "Deyvid"])
    db.salvar_linha("Cochos", ["C01", "Cocho atual", "sal", "Pasto", 100, 50, "", "", "Sim", "Deyvid"])
    with cliente.session_transaction() as sess:
        sess["csrf_token"] = "token-teste"

    html_antes = cliente.get("/cochos").get_data(as_text=True)
    assert "Cocho atual" in html_antes
    assert "Cocho antigo" not in html_antes

    resposta = cliente.post("/cochos/novo", data={
        "csrf_token": "token-teste",
        "id": "C01",
        "nome": "Cadastro duplicado",
        "tipo": "sal",
        "local": "Pasto",
        "capacidade": "100",
        "volume_atual": "80",
    }, follow_redirects=True)

    salvos = db.carregar_aba("Cochos")
    assert resposta.status_code == 200
    assert "Já existe um cocho com o ID C01" in resposta.get_data(as_text=True)
    assert salvos["ID"].astype(str).tolist() == ["C01"]
    assert salvos.iloc[0]["Nome"] == "Cocho atual"
    assert salvos.iloc[0]["Volume Atual (kg)"] == 50


def test_botao_adicionar_cocho_fica_acima_da_navegacao(cliente, dados_restaurados):
    html = cliente.get("/cochos").get_data(as_text=True)

    assert 'id="btn-novo-cocho"' in html
    assert "bottom: 30px" in html
    assert "right: 30px" in html
    assert "z-index: 1050" in html


def test_datas_de_salga_sao_exibidas_no_formato_brasileiro(cliente, dados_restaurados):
    db.salvar_linha("Cochos", [
        "C01", "Cocho 1", "sal", "Pasto", 100, 50, "2026-11-03", "", "Sim", "Deyvid"
    ])

    html = cliente.get("/cochos").get_data(as_text=True)

    assert "03/11/2026" in html
    assert "2026-11-03" not in html
