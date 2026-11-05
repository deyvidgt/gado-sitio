# -*- coding: utf-8 -*-
from datetime import timedelta

import pandas as pd
import pytest

import db
import config
import estoque_medicamentos as EM
import indicadores_v58
import cochos
import gastos
import pastos_ms
import agenda_manejo
from config import COLUNAS_ANIMAIS, COLUNAS_MANEJO
from extensions import _agora


def _post(cliente, **dados):
    with cliente.session_transaction() as sessao:
        sessao["csrf_token"] = "token-teste"
    return cliente.post("/medicamentos/estoque", data={"csrf_token": "token-teste", **dados})


def test_estoque_por_lote_impede_saldo_negativo_e_uso_vencido(cliente, dados_restaurados):
    hoje = _agora().date()
    validade = (hoje + timedelta(days=10)).strftime("%Y-%m-%d")
    data = hoje.strftime("%Y-%m-%d")

    resposta = _post(cliente, movimento="Entrada", data=data, produto="Antibiótico A",
                     principio="Princípio A", lote="L-01", validade=validade,
                     quantidade="10", unidade="mL", fornecedor="Fornecedor")
    assert resposta.status_code == 302
    entrada = db.carregar_aba(EM.ABA).iloc[-1]
    lote_id = entrada["ID Lote"]
    assert entrada["Lote"] == "L-01"

    falha = _post(cliente, movimento="Saída", data=data, lote_id=lote_id, quantidade="11")
    assert falha.status_code == 302
    assert EM.lotes_ativos(hoje)[0]["saldo"] == 10

    _post(cliente, movimento="Saída", data=data, lote_id=lote_id, quantidade="4")
    assert EM.lotes_ativos(hoje)[0]["saldo"] == 6

    validade_vencida = (hoje - timedelta(days=1)).strftime("%Y-%m-%d")
    data_entrada = (hoje - timedelta(days=5)).strftime("%Y-%m-%d")
    _post(cliente, movimento="Entrada", data=data_entrada, produto="Medicamento B",
          principio="Princípio B", lote="L-02", validade=validade_vencida,
          quantidade="2", unidade="frasco")
    lote_vencido = next(l for l in EM.lotes_ativos(hoje) if l["lote"] == "L-02")
    assert lote_vencido["vencido"]

    falha_vencido = _post(cliente, movimento="Saída", data=data, lote_id=lote_vencido["id"],
                          quantidade="1")
    assert falha_vencido.status_code == 302
    assert any(l["id"] == lote_vencido["id"] for l in EM.lotes_ativos(hoje))

    _post(cliente, movimento="Descarte", data=data, lote_id=lote_vencido["id"], quantidade="2")
    assert all(l["id"] != lote_vencido["id"] for l in EM.lotes_ativos(hoje))
    assert list(db.carregar_aba(EM.ABA).columns) == config.COLUNAS_ESTOQUE_MEDICAMENTOS


def test_estoque_rejeita_validade_anterior_a_entrada(cliente, dados_restaurados):
    hoje = _agora().date()
    data = hoje.strftime("%Y-%m-%d")
    resposta = _post(cliente, movimento="Entrada", data=data, produto="Medicamento",
                     principio="Ativo", lote="Vencido", validade=(hoje - timedelta(days=1)).strftime("%Y-%m-%d"),
                     quantidade="1", unidade="frasco")
    assert resposta.status_code == 302
    assert db.carregar_aba(EM.ABA).empty


def test_indicadores_aceitam_dataframes_em_cache():
    df = pd.DataFrame([{"GMD (kg/dia)": 0.85, "Pasto ID": "P01"}])
    resumo = indicadores_v58.engorda_pastagem_resumo({"Engorda Pastagem": df})
    assert resumo["lotes_ativos"] == 1
    assert resumo["ganho_medio"] == pytest.approx(0.85)


def test_novos_paineis_abrem(cliente):
    assert cliente.get("/evolucao").status_code == 200
    assert cliente.get("/indicadores").status_code == 200
    assert cliente.get("/medicamentos/estoque").status_code == 200
    assert cliente.get("/pastos/medicoes").status_code == 200


def test_data_iso_nao_e_trocada_por_dia_e_mes():
    assert EM._data("2026-11-04").strftime("%Y-%m-%d") == "2026-11-04"
    assert EM._data("04/11/2026").strftime("%Y-%m-%d") == "2026-11-04"


def test_categoria_gasto_legado():
    assert gastos.categoria_legada("Remédio/Vacina") == "Sanidade"
    assert gastos.categoria_legada("Sal/Proteínado") == "Nutrição"
    assert gastos.categoria_legada("Gasto sem detalhe") == "Outros"


def test_consumo_no_cocho_em_gramas_por_cabeca_dia():
    hoje = _agora().date()
    datas = [(hoje - timedelta(days=d)).strftime("%d/%m/%Y") for d in (3, 2, 1)]
    df_cochos = pd.DataFrame([{
        "ID": "C01", "Nome": "Cocho teste", "Tipo": "sal",
        "Capacidade (kg)": 100, "Volume Atual (kg)": 10,
        "Ativo": "Sim", "Última Salga": datas[1],
    }])
    movimentos = pd.DataFrame([
        {"Data": datas[0], "Cocho ID": "C01", "Tipo": "Leitura",
         "Quantidade (kg)": 10, "Cabeças": 10},
        {"Data": datas[1], "Cocho ID": "C01", "Tipo": "Reposição",
         "Quantidade (kg)": 5, "Cabeças": None},
        {"Data": datas[2], "Cocho ID": "C01", "Tipo": "Leitura",
         "Quantidade (kg)": 13, "Cabeças": 10},
    ])
    situacao = cochos.calcular_situacao_cochos(
        df_cochos, pd.DataFrame(), movimentos
    )["C01"]
    assert situacao["consumo_g_cab_dia"] == pytest.approx(100)
    assert situacao["volume_kg"] == 13


def test_estimativa_ms_usa_coeficiente_editavel(dados_restaurados):
    db.salvar_linha("Pastos", ["P99", "Pasto de teste", 1, "{}", "#000000", "Sim", "", "Teste"])
    resultado = pastos_ms.registrar(
        "P99", _agora().strftime("%Y-%m-%d"), "30", "320", "medição de teste", "Deyvid"
    )
    assert resultado["ms_kg_ha"] == 9600


def test_agenda_sugere_manejo_por_animal(monkeypatch):
    hoje = _agora().date()
    animal = {coluna: "" for coluna in COLUNAS_ANIMAIS}
    animal.update({
        "ID": "A0001", "Status": "Vivo", "Brinco Cor": "Amarelo",
        "Brinco Nº": 1, "Nascimento": pd.Timestamp(hoje - timedelta(days=500)),
    })
    data_ultimo = pd.Timestamp(hoje - timedelta(days=365))
    manejo = pd.DataFrame([{
        **{coluna: "" for coluna in COLUNAS_MANEJO},
        "Data": data_ultimo, "Tipo": "Vacina Raiva", "Brincos": "Amarelo 01 #A0001",
    }])
    monkeypatch.setattr("db.get_alertas_saude", lambda: {"Vacina Raiva": 365})
    sugestoes = agenda_manejo.sugestoes(manejo, pd.DataFrame([animal]), hoje)
    assert len(sugestoes) == 1
    assert sugestoes[0]["status"] == "hoje"
    assert sugestoes[0]["animais"] == ["Amarelo 01 #A0001"]
