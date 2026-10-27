# -*- coding: utf-8 -*-
import pytest

ROTAS = ["/leite", "/leite/ordenha", "/leite/animais", "/leite/alimentacao",
         "/leite/tratamentos", "/leite/conforto", "/leite/colchao",
         "/leite/relatorios", "/alertas", "/ajuda", "/"]


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
