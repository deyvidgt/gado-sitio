# -*- coding: utf-8 -*-


def test_central_de_alertas_abre(cliente):
    resposta = cliente.get("/alertas")
    assert resposta.status_code == 200
    html = resposta.get_data(as_text=True)
    assert "Central de alertas" in html
    assert "Nutrição e consumo" in html
    assert "Conforto térmico" in html
    assert "Previsão do tempo" in html


def test_api_alertas_retorna_lista(cliente):
    resposta = cliente.get("/api/alertas")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert "alertas" in dados
    assert "tempo" in dados
