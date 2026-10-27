# -*- coding: utf-8 -*-


def _csrf(cliente):
    cliente.get("/leite/alimentacao")
    with cliente.session_transaction() as sessao:
        return sessao["csrf_token"]


def test_telas_operacionais_leiteiras_abrem(cliente):
    for rota, titulo in (("/leite/tratamentos", "Tratamentos"), ("/leite/conforto", "Conforto"), ("/leite/colchao", "Colchão")):
        resposta = cliente.get(rota)
        assert resposta.status_code == 200
        assert titulo in resposta.get_data(as_text=True)


def test_registra_tratamento_conforto_e_colchao(cliente, dados_restaurados):
    token = _csrf(cliente)
    respostas = [
        cliente.post("/leite/tratamentos", data={"csrf_token": token, "data": "26/10/2026", "tipo": "medicamento", "descricao": "Mastite", "custo": "50,00"}),
        cliente.post("/leite/conforto", data={"csrf_token": token, "data": "26/10/2026", "local": "Baia", "sombra": "boa", "agua": "disponível", "descanso": "adequado"}),
        cliente.post("/leite/colchao", data={"csrf_token": token, "data": "26/10/2026", "local": "Baia", "material": "Casca de arroz", "condicao": "boa"}),
    ]
    assert all(resposta.status_code == 302 for resposta in respostas)

    from db import carregar_aba
    assert carregar_aba("Leite Tratamentos")["Descrição"].iloc[-1] == "Mastite"
    assert carregar_aba("Leite Conforto")["Local"].iloc[-1] == "Baia"
    assert carregar_aba("Leite Colchão")["Material"].iloc[-1] == "Casca de arroz"
