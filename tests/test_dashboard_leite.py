# -*- coding: utf-8 -*-
import pandas as pd


def test_dashboard_exibe_resumo_leiteiro(cliente, monkeypatch):
    import routes_dashboard

    monkeypatch.setattr(routes_dashboard, "carregar_aba", lambda aba: {
        "Leite Produção": pd.DataFrame([{"Data": "26/10/2026", "Litros": 24, "Modo Registro": "total"}]),
        "Compras": pd.DataFrame(), "Gastos": pd.DataFrame(), "Vendas": pd.DataFrame(),
        "Manejo": pd.DataFrame(), "Visitas": pd.DataFrame(),
    }.get(aba, pd.DataFrame()))
    html = cliente.get("/").get_data(as_text=True)
    assert "Resumo Leiteiro" in html
    assert "24,0 L" in html
