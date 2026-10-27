# -*- coding: utf-8 -*-


def test_painel_leiteiro_exibe_acumulados_e_medias(cliente):
    html = cliente.get("/leite").get_data(as_text=True)
    assert "Acumulado do dia" in html
    assert "Acumulado da semana" in html
    assert "Acumulado do mês" in html
    assert "Acumulado total" in html
    assert "Média por animal" in html
    assert "Animais ativos" in html
    assert "Vacas em lactação" in html


def test_lista_de_animais_leiteiros_abre(cliente):
    resposta = cliente.get("/leite/animais")
    assert resposta.status_code == 200
    html = resposta.get_data(as_text=True)
    assert "Vacas leiteiras" in html
    assert "Dias em lactação" in html
