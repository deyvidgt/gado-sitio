# -*- coding: utf-8 -*-


def _csrf(cliente):
    cliente.get("/leite/alimentacao")
    with cliente.session_transaction() as sessao:
        return sessao["csrf_token"]


def test_alimentacao_exibe_ficha_incompleta_com_nao_informado(cliente):
    resposta = cliente.get("/leite/alimentacao")
    assert resposta.status_code == 200
    html = resposta.get_data(as_text=True)
    assert "Alimentação leiteira" in html
    assert "não informado" in html
    assert "Necessidades diárias" in html


def test_cadastra_produto_e_necessidade_diaria(cliente, dados_restaurados):
    token = _csrf(cliente)
    produto = cliente.post("/leite/alimentacao", data={
        "csrf_token": token, "produto": "Ração Lactação", "fabricante": "Fábrica A",
        "categoria": "Ração de lactação", "proteina": "18", "preco": "120,00",
    })
    necessidade = cliente.post("/leite/necessidades", data={
        "csrf_token": token, "categoria": "lactação", "item": "Proteína bruta",
        "valor": "18", "unidade": "%", "fonte": "Rótulo", "data_revisao": "26/10/2026",
    })
    assert produto.status_code == 302
    assert necessidade.status_code == 302

    from db import carregar_aba
    alimentacao = carregar_aba("Leite Alimentação")
    necessidades = carregar_aba("Leite Necessidades")
    assert "Ração Lactação" in alimentacao["Produto"].tolist()
    assert "Proteína bruta" in necessidades["Nutriente ou Item"].tolist()
