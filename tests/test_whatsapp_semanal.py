# -*- coding: utf-8 -*-
"""Resumo semanal sem ruído, valores por pessoa e brucelose por animal (Task 3).
Tudo offline: dados e animais simulados, Drive desligado."""
from datetime import datetime, timedelta

import pandas as pd
import pytest

import alertas_whatsapp as aw
import animais
import drive
from config import (COLUNAS_ANIMAIS, COLUNAS_COMPRAS, COLUNAS_GASTOS, COLUNAS_MANEJO,
                    COLUNAS_VENDAS, COLUNAS_VISITAS)

HOJE = datetime(2026, 10, 19, 7, 0)   # segunda


def _df(colunas, linhas=()):
    return pd.DataFrame(list(linhas), columns=colunas)


def _dados(compras=None):
    return {"Compras": compras if compras is not None else _df(COLUNAS_COMPRAS),
            "Gastos": _df(COLUNAS_GASTOS), "Vendas": _df(COLUNAS_VENDAS),
            "Manejo": _df(COLUNAS_MANEJO), "Visitas": _df(COLUNAS_VISITAS)}


def _animais(dias, sexo="F"):
    linha = {c: "" for c in COLUNAS_ANIMAIS}
    linha.update({"ID": "A0001", "Brinco Cor": "Amarelo", "Brinco Nº": 21, "Sexo": sexo,
                  "Status": "Vivo", "Nascimento": pd.Timestamp(HOJE) - timedelta(days=dias)})
    df = pd.DataFrame([linha], columns=COLUNAS_ANIMAIS)
    df["Brinco Nº"] = df["Brinco Nº"].astype("Int64")
    return df


@pytest.fixture
def ambiente(monkeypatch):
    monkeypatch.setattr(aw, "carregar_todas", lambda: _dados())
    monkeypatch.setattr(drive, "configurado", lambda: False)
    monkeypatch.setattr(animais, "carregar", lambda: _df(COLUNAS_ANIMAIS))
    return monkeypatch


def _brucelose(itens):
    return [i for i in itens if i["chave"].startswith("brucelose:")]


def test_semanal_sem_ruido(ambiente):
    itens = aw.montar_itens(HOJE)
    msg = aw.montar_msg_semanal(itens, HOJE)
    assert "nenhum registro ainda" not in msg
    assert "Resultado realizado" not in msg
    assert not [i for i in itens if i["chave"] == "fin:negativo"]


def test_semanal_sem_valores_tira_rs(ambiente):
    compras = _df(COLUNAS_COMPRAS, [[pd.Timestamp("2026-01-10"), 10, 20000, 2000,
                                     4, 3, 3, "lote", "Deyvid"]])
    ambiente.setattr(aw, "carregar_todas", lambda: _dados(compras))
    itens = aw.montar_itens(HOJE)
    assert "Rebanho:" in aw.montar_msg_semanal(itens, HOJE)
    assert "R$" not in aw.montar_msg_semanal(itens, HOJE, com_valores=False)
    assert "R$" not in aw.montar_msg_urgente(itens, HOJE, com_valores=False)


def test_brucelose_semanal_200_dias(ambiente):
    ambiente.setattr(animais, "carregar", lambda: _animais(200))
    b = _brucelose(aw.montar_itens(HOJE))
    assert len(b) == 1 and b[0]["chave"] == "brucelose:A0001"
    assert b[0]["urgente"] is False
    assert "Amarelo 21" in b[0]["texto"] and "vacinar até" in b[0]["texto"]


def test_brucelose_urgente_230_dias(ambiente):
    ambiente.setattr(animais, "carregar", lambda: _animais(230))
    b = _brucelose(aw.montar_itens(HOJE))
    assert b[0]["urgente"] is True and b[0]["repetir"] == 3


def test_brucelose_chegando(ambiente):
    ambiente.setattr(animais, "carregar", lambda: _animais(70))
    b = _brucelose(aw.montar_itens(HOJE))
    assert b[0]["urgente"] is False
    assert "entra na janela em 20 dias" in b[0]["texto"]


def test_itens_sem_animais_nao_quebra(ambiente):
    def quebra():
        raise Exception("aba Animais ilegível")
    ambiente.setattr(animais, "carregar", quebra)
    itens = aw.montar_itens(HOJE)
    assert itens and not _brucelose(itens)
