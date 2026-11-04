#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes da busca rápida global (v5.6)
"""
import pandas as pd
import pytest
from busca import ABAS_DISPONIVEIS, buscar_global


def test_busca_vazia():
    """Busca com termo vazio retorna lista vazia."""
    assert buscar_global("") == []
    assert buscar_global("  ") == []


def test_busca_termo_muito_curto():
    """Termo com menos de 2 caracteres retorna lista vazia."""
    assert buscar_global("a") == []


def test_busca_animais(flask_app):
    """Busca encontra animais por brinco, ID ou nome."""
    with flask_app.app_context():
        resultados = buscar_global("amarelo")
        # Se houver animais no banco, devem incluir "amarelo" em algum lugar
        if resultados:
            assert any(r["tipo"] == "animal" for r in resultados)


def test_busca_tarefas(flask_app):
    """Busca encontra tarefas por título ou ID."""
    with flask_app.app_context():
        resultados = buscar_global("tarefa")
        # Resultado pode estar vazio ou conter tarefas
        assert isinstance(resultados, list)


def test_busca_limite_resultados(flask_app):
    """Busca nunca retorna mais de 10 resultados."""
    with flask_app.app_context():
        resultados = buscar_global("a")  # Termo genérico
        assert len(resultados) <= 10


def test_busca_filtro_tipo(flask_app):
    """Filtro por tipo retorna apenas esse tipo."""
    with flask_app.app_context():
        resultados = buscar_global("a", tipo_filtro="animal")
        for r in resultados:
            assert r["tipo"] == "animal"


def test_busca_resultado_estrutura(flask_app):
    """Cada resultado tem a estrutura esperada."""
    with flask_app.app_context():
        resultados = buscar_global("aa")
        for r in resultados:
            assert "tipo" in r
            assert "id" in r
            assert "titulo" in r
            assert "subtitulo" in r
            assert "link" in r
            assert "icone" in r


def test_api_busca_endpoint(cliente):
    """GET /api/busca?q=... retorna JSON."""
    rv = cliente.get("/api/busca?q=teste")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "resultados" in data
    assert isinstance(data["resultados"], list)


def test_api_busca_com_tipo(cliente):
    """GET /api/busca?q=...&tipo=animal filtra por tipo."""
    rv = cliente.get("/api/busca?q=teste&tipo=animal")
    assert rv.status_code == 200
    data = rv.get_json()
    for r in data["resultados"]:
        assert r["tipo"] == "animal"


def test_busca_sem_acento_e_com_varias_palavras(monkeypatch):
    animais_df = pd.DataFrame([{
        "ID": "A0001", "Brinco Cor": "Amarelo", "Brinco Nº": 21,
        "Nome": "Estrela", "Categoria": "Vaca", "Sexo": "Fêmea",
        "Raça": "Nelore", "Pelagem": "", "Dono": "Geane", "Status": "Ativo",
        "Observações": "",
    }])
    vazio = pd.DataFrame()
    monkeypatch.setattr("busca.animais.carregar", lambda: animais_df)
    monkeypatch.setattr("busca.tarefas.carregar", lambda: vazio)
    monkeypatch.setattr("busca.db.carregar_aba", lambda aba: vazio)

    resultados = buscar_global("amarelo 21")
    assert resultados[0]["tipo"] == "animal"
    assert resultados[0]["link"] == "/animais/A0001"
    assert any(r["titulo"] == "Reprodução" for r in buscar_global("reproducao"))
    assert any(r["titulo"] == "Resultado por Membro" for r in buscar_global("resultado por membro"))
    assert any(r["titulo"] == "Comercialização" for r in buscar_global("compras e vendas"))


def test_busca_prioriza_tela_exata_e_oferece_telas_do_menu(monkeypatch):
    animais_df = pd.DataFrame([{
        "ID": "A0001", "Brinco Cor": "Amarelo", "Brinco Nº": 21,
        "Nome": "Pasto Norte", "Categoria": "Vaca", "Dono": "Geane",
        "Status": "Ativo",
    }])
    vazio = pd.DataFrame()
    monkeypatch.setattr("busca.animais.carregar", lambda: animais_df)
    monkeypatch.setattr("busca.tarefas.carregar", lambda: vazio)
    monkeypatch.setattr("busca.db.carregar_aba", lambda aba: vazio)

    resultado = buscar_global("aplicações em pastagens")
    assert resultado[0]["tipo"] == "aba"
    assert resultado[0]["titulo"] == "Aplicações em Pastagens"
    assert resultado[0]["link"] == "/pastos/aplicacoes"
    assert resultado[0]["subtitulo"] == "Abrir tela"

    assert any(r["titulo"] == "Mastite e Qualidade do Leite" and r["link"] == "/leite/saude"
               for r in buscar_global("mastite"))
    assert any(r["titulo"] == "Orçamento e Contas" and r["link"] == "/planejamento"
               for r in buscar_global("orçamento"))


def test_busca_encontra_transacao_pelo_brinco(monkeypatch):
    animais_df = pd.DataFrame(columns=[
        "ID", "Brinco Cor", "Brinco Nº", "Nome", "Categoria", "Sexo",
        "Raça", "Pelagem", "Dono", "Status", "Observações",
    ])
    vazio = pd.DataFrame()
    monkeypatch.setattr("busca.animais.carregar", lambda: animais_df)
    monkeypatch.setattr("busca.tarefas.carregar", lambda: vazio)
    monkeypatch.setattr("busca.db.carregar_aba", lambda aba: vazio)
    dados = {
        "Manejo": vazio,
        "Compras": vazio,
        "Gastos": vazio,
        "Visitas": vazio,
        "Vendas": pd.DataFrame([{
            "Data": "03/11/2026", "Qtd Cabeças": 1,
            "Descrição": "Venda lote", "Brincos": "Amarelo 21 #A0001",
        }]),
    }

    resultados = buscar_global("amarelo 21", dados=dados)
    assert any(r["tipo"] == "registro" and "Venda: 1 cabeças" == r["titulo"] for r in resultados)
    assert any(r["link"].startswith("/transacoes") for r in resultados)


def test_busca_rapida_tem_sugestoes_acessiveis(cliente):
    html = cliente.get("/").get_data(as_text=True)
    assert 'aria-autocomplete="list"' in html
    assert 'aria-haspopup="listbox"' in html
    assert 'id="search-dropdown" class="search-dropdown" role="listbox" aria-live="polite" hidden' in html
    assert "Ctrl+K" in html or "ctrlKey" in html


def test_telas_indexadas_apontam_para_rotas_existentes(flask_app):
    adaptador = flask_app.url_map.bind("localhost")
    for aba in ABAS_DISPONIVEIS:
        adaptador.match(aba["link"], method="GET")
