# -*- coding: utf-8 -*-
from db import carregar_aba


def _csrf(cliente):
    cliente.get("/leite/ordenha")
    with cliente.session_transaction() as sessao:
        return sessao["csrf_token"]


def _registro(cliente, dados_restaurados):
    cliente.post("/leite/ordenha", data={
        "csrf_token": _csrf(cliente), "data": "26/10/2026",
        "modo_registro": "total", "ordenha": "Manhã", "litros": "12",
        "id_envio": "editar-1",
    })
    return carregar_aba("Leite Produção")


def test_edita_ordenha_preservando_colunas(cliente, dados_restaurados, monkeypatch):
    _registro(cliente, dados_restaurados)
    import routes_leite
    monkeypatch.setattr(routes_leite, "fazer_backup", lambda: "backup.xlsx")
    indice = len(carregar_aba("Leite Produção")) - 1
    resposta = cliente.post(f"/leite/editar/{indice}", data={
        "csrf_token": _csrf(cliente), "data": "26/10/2026",
        "modo_registro": "total", "ordenha": "Tarde", "litros": "18",
        "id_envio": "editar-1",
    })
    assert resposta.status_code == 302
    linha = carregar_aba("Leite Produção").iloc[indice]
    assert float(linha["Litros"]) == 18
    assert linha["Ordenha"] == "Tarde"
    assert linha["ID Envio"] == "editar-1"


def test_exclui_ordenha_com_csrf_e_backup(cliente, dados_restaurados, monkeypatch):
    _registro(cliente, dados_restaurados)
    import routes_leite
    backups = []
    monkeypatch.setattr(routes_leite, "fazer_backup", lambda: backups.append(True))
    indice = len(carregar_aba("Leite Produção")) - 1
    resposta = cliente.post(f"/leite/excluir/{indice}", data={"csrf_token": _csrf(cliente)})
    assert resposta.status_code == 302
    assert backups == [True]
    assert "editar-1" not in carregar_aba("Leite Produção")["ID Envio"].astype(str).tolist()
