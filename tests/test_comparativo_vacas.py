# -*- coding: utf-8 -*-
"""Testes do comparativo de vacas leiteiras."""

import pytest
from comparativo import comparar_vacas


def test_comparativo_get_abre(cliente):
    """GET /leite/comparativo abre sem erro."""
    assert cliente.get("/leite/comparativo").status_code == 200


def test_comparativo_post_sem_vacas(cliente):
    """POST /leite/comparativo sem vacas selecionadas abre normalmente."""
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    resp = cliente.post("/leite/comparativo", data={
        "csrf_token": "tok",
        "vaca_1": "", "vaca_2": "", "vaca_3": ""
    })
    assert resp.status_code == 200


def test_comparativo_post_com_vacas(cliente):
    """POST /leite/comparativo com vacas selecionadas mostra tabela."""
    from db import carregar_aba
    df_animais = carregar_aba("Animais")
    if df_animais.empty:
        pytest.skip("Nenhum animal cadastrado")

    # Procura uma vaca em lactação
    vaca_id = None
    for _, animal in df_animais.iterrows():
        situacao = str(animal.get("Situação Leite", "")).lower()
        if situacao in {"lactação", "lactacao"}:
            vaca_id = str(animal.get("ID", "")).strip()
            if vaca_id:
                break

    if not vaca_id:
        pytest.skip("Nenhuma vaca em lactação")

    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    resp = cliente.post("/leite/comparativo", data={
        "csrf_token": "tok",
        "vaca_1": vaca_id, "vaca_2": "", "vaca_3": ""
    })
    assert resp.status_code == 200
    assert vaca_id.encode() in resp.data or b"Producao" in resp.data or b"Producci" in resp.data


def test_api_comparativo_sem_parametro(cliente):
    """API sem IDs retorna erro 400."""
    resp = cliente.get("/api/leite/comparativo")
    assert resp.status_code == 400


def test_api_comparativo_com_vacas(cliente):
    """API com IDs de vacas retorna JSON válido."""
    from db import carregar_aba
    df_animais = carregar_aba("Animais")
    if df_animais.empty:
        pytest.skip("Nenhum animal cadastrado")

    # Procura uma vaca em lactação
    vaca_id = None
    for _, animal in df_animais.iterrows():
        situacao = str(animal.get("Situação Leite", "")).lower()
        if situacao in {"lactação", "lactacao"}:
            vaca_id = str(animal.get("ID", "")).strip()
            if vaca_id:
                break

    if not vaca_id:
        pytest.skip("Nenhuma vaca em lactação")

    resp = cliente.get(f"/api/leite/comparativo?ids={vaca_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert vaca_id in data
    assert "producao_litros_dia" in data[vaca_id]
    assert "margem_diario" in data[vaca_id]


def test_funcao_comparar_vacas_basica():
    """Função comparar_vacas retorna dict com chaves esperadas."""
    resultado = comparar_vacas(["A0001"])
    assert isinstance(resultado, dict)
    if "A0001" in resultado:
        dados = resultado["A0001"]
        assert "producao_litros_dia" in dados
        assert "custo_diario" in dados
        assert "receita_diario" in dados
        assert "margem_diario" in dados
        assert "ccs_ultimo" in dados
        assert "cpp_ultimo" in dados
        assert "ultimos_eventos" in dados
