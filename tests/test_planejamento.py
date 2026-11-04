# -*- coding: utf-8 -*-
"""Testes de aplicações de pastagem, orçamento e contas futuras."""

import json
from datetime import date, timedelta

import pandas as pd

import db
import planejamento as PL
import pastos as PA
from config import COLUNAS_GASTOS


def _quadrado():
    return json.dumps({
        "type": "Polygon",
        "coordinates": [[[0, 0], [0.0089832, 0], [0.0089832, 0.0089832],
                         [0, 0.0089832], [0, 0]]],
    })


def test_comparativo_orcamento_por_mes_categoria():
    orcamento = pd.DataFrame([
        ["ORC-1", "2026-11", "Despesa", "Calcário/Adubação", "Adubo", 500, "Deyvid"],
    ], columns=["ID", "Mês", "Tipo", "Categoria", "Descrição", "Valor Previsto (R$)", "Membro"])
    gastos = pd.DataFrame([
        {"Data": pd.Timestamp("2026-11-03"), "Tipo": "Calcário/Adubação", "Valor Total (R$)": 650},
        {"Data": pd.Timestamp("2026-10-30"), "Tipo": "Calcário/Adubação", "Valor Total (R$)": 900},
    ])

    linhas = PL.comparar_orcamento(orcamento, pd.DataFrame(), gastos, pd.DataFrame(), 2026)

    novembro = next(linha for linha in linhas if linha["mes"] == "2026-11")
    outubro = next(linha for linha in linhas if linha["mes"] == "2026-10")
    assert novembro == {
        "mes": "2026-11", "tipo": "Despesa", "categoria": "Calcário/Adubação",
        "previsto": 500.0, "realizado": 650.0, "diferenca": 150.0,
    }
    assert outubro["previsto"] == 0
    assert outubro["realizado"] == 900


def test_contas_proximas_inclui_atrasadas_e_pendentes():
    contas = pd.DataFrame([
        {"ID": "1", "Data Vencimento": "02/11/2026", "Tipo": "Pagar", "Status": "Pendente"},
        {"ID": "2", "Data Vencimento": "08/11/2026", "Tipo": "Receber", "Status": "Pendente"},
        {"ID": "3", "Data Vencimento": "05/11/2026", "Tipo": "Pagar", "Status": "Pago"},
        {"ID": "4", "Data Vencimento": "20/11/2026", "Tipo": "Pagar", "Status": "Pendente"},
    ])

    proximas = PL.contas_proximas(contas, pd.Timestamp("2026-11-03").date())

    assert [c["ID"] for c in proximas] == ["1", "2"]
    assert proximas[0]["atrasada"] is True


def test_aplicacao_cria_gasto_vinculado_em_uma_gravacao(
    cliente, dados_restaurados, monkeypatch
):
    import routes_pastos

    monkeypatch.setattr(routes_pastos, "fazer_backup_seguro", lambda: None)
    pasto_id = PA.criar("Pasto Aplicacao", _quadrado(), "Deyvid")
    with cliente.session_transaction() as sess:
        sess["csrf_token"] = "csrf-planejamento"

    resposta = cliente.post("/pastos/aplicacoes", data={
        "csrf_token": "csrf-planejamento",
        "pasto_id": pasto_id,
        "data": "2026-11-03",
        "tipo_insumo": "Ureia",
        "produto": "Ureia 45%",
        "quantidade": "50",
        "unidade": "kg",
        "custo": "250,00",
        "responsavel": "Deyvid",
    })
    assert resposta.status_code == 302

    aplicacoes = db.carregar_aba("Pastos Aplicações")
    gastos = db.carregar_aba("Gastos")
    aplicacao = aplicacoes.iloc[-1]
    assert aplicacao["Pasto ID"] == pasto_id
    assert float(aplicacao["Custo Total (R$)"]) == 250
    gasto = gastos[gastos["Aplicação ID"].astype(str) == str(aplicacao["ID"])]
    assert len(gasto) == 1
    assert gasto.iloc[0]["Tipo"] == "Calcário/Adubação"
    assert gasto.iloc[0]["Pasto ID"] == pasto_id
    html = cliente.get("/pastos/aplicacoes").get_data(as_text=True)
    assert "Pasto Aplicacao" in html
    assert "R$ 250,00" in html
    assert "R$ 2,50" in html


def test_conta_futura_marcada_paga_nao_cria_realizado(
    cliente, dados_restaurados, monkeypatch
):
    import routes_financeiro_novo

    monkeypatch.setattr(routes_financeiro_novo, "_backup_planejamento", lambda: None)
    with cliente.session_transaction() as sess:
        sess["csrf_token"] = "csrf-planejamento"
    resposta = cliente.post("/contas-futuras/nova", data={
        "csrf_token": "csrf-planejamento",
        "vencimento": (date.today() + timedelta(days=2)).isoformat(),
        "tipo": "Pagar",
        "categoria": "Calcário/Adubação",
        "descricao": "Adubo planejado",
        "valor": "300",
        "membro": "Deyvid",
    })
    assert resposta.status_code == 302
    conta = db.carregar_aba("Contas Futuras").iloc[-1]
    assert "Adubo planejado" in cliente.get("/transacoes").get_data(as_text=True)

    resposta = cliente.post(f"/contas-futuras/{conta['ID']}/status", data={
        "csrf_token": "csrf-planejamento", "status": "Pago",
    })
    assert resposta.status_code == 302
    contas = db.carregar_aba("Contas Futuras")
    assert contas.iloc[-1]["Status"] == "Pago"
    assert db.carregar_aba("Gastos").empty or not (
        db.carregar_aba("Gastos")["Descrição"].astype(str) == "Adubo planejado"
    ).any()
    assert "Adubo planejado" not in cliente.get("/transacoes").get_data(as_text=True)


def test_orcamento_cria_previsao_e_aparece_na_comparacao(
    cliente, dados_restaurados, monkeypatch
):
    import routes_financeiro_novo

    monkeypatch.setattr(routes_financeiro_novo, "_backup_planejamento", lambda: None)
    with cliente.session_transaction() as sess:
        sess["csrf_token"] = "csrf-planejamento"
    mes = date.today().strftime("%Y-%m")
    ano = date.today().year
    resposta = cliente.post("/orcamento/novo", data={
        "csrf_token": "csrf-planejamento",
        "mes": mes,
        "tipo": "Despesa",
        "categoria": "Calcário/Adubação",
        "descricao": "Adubação do pasto",
        "valor": "500",
        "membro": "Deyvid",
    })
    assert resposta.status_code == 302
    previsoes = db.carregar_aba("Orçamento Previsto")
    assert previsoes.iloc[-1]["Categoria"] == "Calcário/Adubação"
    pagina = cliente.get(f"/planejamento?ano={ano}").get_data(as_text=True)
    assert "Adubação do pasto" in pagina
    assert "R$ 500,00" in pagina


def test_rotas_de_planejamento_exigem_csrf(cliente):
    assert cliente.post("/orcamento/novo").status_code == 403
    assert cliente.post("/contas-futuras/nova").status_code == 403
    assert cliente.post("/pastos/aplicacoes").status_code == 403


def test_gastos_esquema_preserva_colunas_anteriores():
    assert COLUNAS_GASTOS[-2:] == ["Pasto ID", "Aplicação ID"]
