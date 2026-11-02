# -*- coding: utf-8 -*-
import pandas as pd


def test_ficha_leiteira_mostra_historico_e_dias_em_lactacao(cliente, monkeypatch):
    import doencas_carencia
    import routes_leite

    monkeypatch.setattr(routes_leite.A, "carregar", lambda: pd.DataFrame([{
        "ID": "A0001", "Status": "Vivo", "Sexo": "F", "Uso Produtivo": "leite",
        "Brinco Cor": "Amarelo", "Brinco Nº": "21", "Situação Leite": "lactação",
        "Último Parto": "20/10/2026",
    }]))
    abas = {
        "Leite Produção": pd.DataFrame([
            {"Data": "25/10/2026", "Vaca ID": "A0001", "Modo Registro": "individual", "Litros": 18},
            {"Data": "26/10/2026", "Vaca ID": "A0001", "Modo Registro": "individual", "Litros": 20},
        ]),
        "Leite Tratamentos": pd.DataFrame([{
            "Data": "26/10/2026", "Vaca ID": "A0001", "Descrição": "Mastite",
            "Período de Carência": "2",
        }]),
    }
    monkeypatch.setattr(routes_leite, "carregar_aba", lambda aba: abas.get(aba, pd.DataFrame()))
    # A carência agora vem da fonte única (3 abas) — não só de Leite Tratamentos.
    monkeypatch.setattr(doencas_carencia, "carregar_aba", lambda aba: abas.get(aba, pd.DataFrame()))
    monkeypatch.setattr(routes_leite, "_agora", lambda: pd.Timestamp("2026-10-26"))

    resposta = cliente.get("/leite/animal/A0001")
    html = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert "Amarelo 21" in html
    assert "38,0" in html
    assert "6 dias" in html
    assert "Mastite" in html
    assert "carência" in html.lower()


def test_ficha_leiteira_recusa_animal_inexistente(cliente, monkeypatch):
    import routes_leite
    monkeypatch.setattr(routes_leite.A, "carregar", lambda: pd.DataFrame([{"ID": "A0001", "Status": "Vivo"}]))
    resposta = cliente.get("/leite/animal/NAOEXISTE")
    assert resposta.status_code == 404
