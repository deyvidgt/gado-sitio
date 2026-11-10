# -*- coding: utf-8 -*-


def test_dashboard_mostra_estoque_de_alimentacao_com_status_e_atalhos(cliente):
    html = cliente.get("/").get_data(as_text=True)

    assert "Estoque de alimentação" in html
    assert "Sal" in html
    assert "Proteinado" in html
    assert "Ração" in html
    assert "Sem informação" in html or "Normal" in html or "Atenção" in html or "Acabando" in html
    assert "Comparar preços" in html
    assert "Lançar compra" in html


def test_dashboard_informa_como_o_estoque_e_calculado(cliente):
    html = cliente.get("/insumos/estoque").get_data(as_text=True)

    assert "Estoque" in html or "saco" in html or "visitas" in html
