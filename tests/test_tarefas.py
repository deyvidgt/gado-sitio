# -*- coding: utf-8 -*-
"""
Agenda de tarefas (v5.3): o que fazer no sítio, com repetição e aviso.
"""
import pandas as pd
import pytest

import tarefas as T


@pytest.fixture
def limpa(dados_restaurados):
    """Começa sem tarefa nenhuma (a aba existe mas pode ter lixo de outro teste)."""
    T._gravar(T.carregar().iloc[0:0])
    yield


def test_criar_e_listar(limpa):
    id_ = T.criar("Consertar a cerca do fundo", "10/11/2026", "Deyvid", criado_por="Deyvid")
    assert id_ == "T0001"
    df = T.carregar()
    assert len(df) == 1 and df.at[0, "Título"] == "Consertar a cerca do fundo"
    assert df.at[0, "Feito Em"] == ""


def test_criar_sem_titulo_recusa(limpa):
    with pytest.raises(ValueError):
        T.criar("   ", "10/11/2026", "Deyvid")


def test_criar_com_repeticao_invalida_recusa(limpa):
    with pytest.raises(ValueError):
        T.criar("Alguma coisa", "10/11/2026", "Deyvid", repetir="De vez em quando")


def test_pendentes_separa_atrasada_hoje_e_proxima(limpa):
    T.criar("Atrasada", "01/11/2026", "Mae")
    T.criar("É hoje", "10/11/2026", "Mae")
    T.criar("Semana que vem", "17/11/2026", "Mae")
    p = T.pendentes(T.carregar(), hoje=pd.Timestamp("2026-11-10"))
    assert [t["titulo"] for t in p] == ["Atrasada", "É hoje", "Semana que vem"]
    assert [t["situacao"] for t in p] == ["atrasada", "hoje", "proxima"]
    assert p[0]["dias"] == -9 and p[1]["dias"] == 0 and p[2]["dias"] == 7


def test_concluir_tira_da_lista(limpa):
    id_ = T.criar("Comprar sal", "10/11/2026", "Nilson")
    T.concluir(id_, hoje=pd.Timestamp("2026-11-11"))
    df = T.carregar()
    assert df.at[0, "Feito Em"] == "11/11/2026"
    assert T.pendentes(df, hoje=pd.Timestamp("2026-11-11")) == []


def test_concluir_tarefa_mensal_cria_a_proxima(limpa):
    id_ = T.criar("Trocar o sal do cocho", "10/11/2026", "Mae", repetir="Mensal")
    T.concluir(id_, hoje=pd.Timestamp("2026-11-10"))
    df = T.carregar()
    assert len(df) == 2
    nova = df[df["Feito Em"] == ""].iloc[0]
    assert nova["Data"] == "10/12/2026" and nova["Repetir"] == "Mensal"
    assert nova["Título"] == "Trocar o sal do cocho" and nova["ID"] != id_


def test_concluir_duas_vezes_nao_duplica(limpa):
    id_ = T.criar("Uma vez só", "10/11/2026", "Mae", repetir="Semanal")
    T.concluir(id_, hoje=pd.Timestamp("2026-11-10"))
    T.concluir(id_, hoje=pd.Timestamp("2026-11-10"))
    assert len(T.carregar()) == 2


def test_excluir(limpa):
    id_ = T.criar("Errada", "10/11/2026", "Mae")
    T.excluir(id_)
    assert T.carregar().empty


def test_pagina_tarefas_lista_e_cria(cliente, limpa):
    html = cliente.get("/tarefas").get_data(as_text=True)
    assert "Tarefas" in html
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    cliente.post("/tarefas/nova", data={"csrf_token": "tok", "titulo": "Roçar o curral",
                                        "data": "2026-11-20", "responsavel": "Deyvid",
                                        "repetir": "Não"}, follow_redirects=True)
    assert "Roçar o curral" in cliente.get("/tarefas").get_data(as_text=True)


def test_painel_mostra_tarefas(cliente, limpa):
    assert "Tarefas" in cliente.get("/").get_data(as_text=True)


def test_tarefa_atrasada_vira_aviso_urgente(limpa):
    from datetime import datetime
    import alertas_whatsapp as W
    T.criar("Consertar o bebedouro", "01/11/2026", "Nilson")
    itens = W.montar_itens(datetime(2026, 11, 10))
    urg = [i for i in itens if i["chave"].startswith("tarefa:") and i["urgente"]]
    assert len(urg) == 1 and "Consertar o bebedouro" in urg[0]["texto"]
