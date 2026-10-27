# -*- coding: utf-8 -*-


def _csrf(cliente):
    cliente.get("/leite/ordenha")
    with cliente.session_transaction() as sessao:
        return sessao["csrf_token"]


def test_painel_leiteiro_abre(cliente):
    resposta = cliente.get("/leite")
    assert resposta.status_code == 200
    html = resposta.get_data(as_text=True)
    assert "Painel do leite" in html
    assert "Lançar ordenha" in html


def test_registra_ordenha_individual_e_impede_id_envio_duplicado(cliente, dados_restaurados):
    csrf = _csrf(cliente)
    dados = {
        "csrf_token": csrf,
        "data": "26/10/2026",
        "vaca_id": "A0001",
        "brinco": "Amarelo 01",
        "modo_registro": "individual",
        "ordenha": "Manhã",
        "litros": "12,5",
        "id_envio": "celular-ordenha-1",
    }
    primeira = cliente.post("/leite/ordenha", data=dados)
    segunda = cliente.post("/leite/ordenha", data=dados)
    assert primeira.status_code == 302
    assert segunda.status_code == 302

    from db import carregar_aba
    df = carregar_aba("Leite Produção")
    assert len(df[df["ID Envio"] == "celular-ordenha-1"]) == 1
    assert float(df.iloc[-1]["Litros"]) == 12.5


def test_registra_total_da_ordenha_sem_vaca(cliente, dados_restaurados):
    resposta = cliente.post("/leite/ordenha", data={
        "csrf_token": _csrf(cliente),
        "data": "26/10/2026",
        "modo_registro": "total",
        "ordenha": "Tarde",
        "litros": "30",
        "id_envio": "celular-total-1",
    })
    assert resposta.status_code == 302
    from db import carregar_aba
    df = carregar_aba("Leite Produção")
    linha = df[df["ID Envio"] == "celular-total-1"].iloc[0]
    assert linha["Modo Registro"] == "total"
    assert float(linha["Litros"]) == 30
