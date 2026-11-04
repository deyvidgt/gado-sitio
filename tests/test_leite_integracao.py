# -*- coding: utf-8 -*-
import pytest

ROTAS = ["/leite", "/leite/ordenha", "/leite/animais", "/leite/alimentacao",
         "/leite/tratamentos", "/leite/conforto", "/leite/colchao",
         "/leite/relatorios", "/leite/consumo", "/alertas", "/ajuda", "/"]


@pytest.mark.parametrize("rota", ROTAS)
def test_paginas_do_leite_abrem(cliente, rota):
    assert cliente.get(rota).status_code == 200


def test_leite_nao_altera_resultado_do_corte(cliente, flask_app):
    import calculos
    from db import carregar_todas
    d = carregar_todas()
    antes = calculos.calcular_resumo_financeiro(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"])
    cliente.get("/leite")
    d = carregar_todas()
    depois = calculos.calcular_resumo_financeiro(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"])
    assert antes == depois


def test_gravar_leite_exige_csrf(cliente):
    r = cliente.post("/leite/ordenha", data={"data": "26/10/2026", "litros": "10"})
    assert r.status_code in (400, 403)


def test_navegacao_do_painel_leiteiro(cliente):
    resposta = cliente.get("/leite")
    html = resposta.get_data(as_text=True)
    assert 'class="leite-nav"' in html
    assert 'class="leite-nav-menu"' in html
    assert 'class="leite-nav-links"' in html
    assert "flex-wrap:wrap" in html
    assert 'data-leite-back-url="/leite"' not in html
    assert "static/leite_nav.js" in html
    assert 'href="/leite/ordenha"' in html
    assert 'href="/leite/alimentacao"' in html


def test_navegacao_contextual_da_alimentacao(cliente):
    html = cliente.get("/leite/alimentacao").get_data(as_text=True)
    assert 'data-leite-back-url="/leite"' in html
    assert "← Painel do leite" in html


def test_navegacao_contextual_do_consumo(cliente):
    html = cliente.get("/leite/consumo").get_data(as_text=True)
    assert 'data-leite-back-url="/leite/alimentacao"' in html
    assert "← Alimentação" in html


def test_navegacao_contextual_de_subpaginas(cliente):
    casos = {
        "/leite/animais": "/leite",
        "/leite/relatorios": "/leite",
        "/leite/saude": "/leite",
        "/leite/nutricao": "/leite/alimentacao",
        "/leite/calculador": "/leite/alimentacao",
        "/leite/tratamentos": "/leite",
        "/leite/conforto": "/leite",
        "/leite/colchao": "/leite",
        "/leite/comparativo": "/leite",
    }
    for rota, destino in casos.items():
        resposta = cliente.get(rota)
        assert resposta.status_code == 200, rota
        assert f'data-leite-back-url="{destino}"' in resposta.get_data(as_text=True)


def test_botoes_de_ordenha_e_medicao_com_css_visivel_e_elevado(cliente):
    leite = cliente.get("/leite/saude").get_data(as_text=True)
    assert 'class="btn btn-registrar-ordenha"' in leite
    assert "background: #28a745" in leite
    assert "color: #fff" in leite
    assert "font-weight: 700" in leite

    medicacoes = cliente.get("/medicacoes").get_data(as_text=True)
    assert "bottom: calc(72px + env(safe-area-inset-bottom, 0px))" in medicacoes
    assert "z-index: 1050" in medicacoes
    assert ".fab-container { position: fixed; bottom: calc(72px + env(safe-area-inset-bottom, 0px))" in leite


def test_script_de_gesto_tem_regras_de_segurança():
    from pathlib import Path
    script = Path("static/leite_nav.js").read_text(encoding="utf-8")
    for trecho in ("768", "24", "72", "pointerdown", "pointermove", "pointerup",
                   "form", "contenteditable", "scrollWidth", "location.href"):
        assert trecho in script
