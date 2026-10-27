# -*- coding: utf-8 -*-
import json
import os


def test_configuracao_salva_coordenadas_do_tempo(cliente, dados_restaurados):
    with cliente.session_transaction() as sessao:
        sessao["csrf_token"] = "tok"
    resposta = cliente.post("/configuracoes/sitio", data={
        "csrf_token": "tok",
        "sitio_nome": "Sítio Teste",
        "sitio_donos": "Família",
        "latitude": "-18,9186",
        "longitude": "-48,2772",
    })
    assert resposta.status_code == 302
    with open(os.path.join(__import__("db").DATA_DIR, "sitio_config.json"), encoding="utf-8") as arquivo:
        cfg = json.load(arquivo)
    assert cfg["latitude"] == -18.9186
    assert cfg["longitude"] == -48.2772
