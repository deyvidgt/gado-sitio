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


# ── Task 4: seção "Na semana" ────────────────────────────────────────────────

HOJE_SEMANA = datetime(2026, 10, 26, 7, 0)   # segunda


def _linhas(colunas, registros):
    """DataFrame a partir de dicts (colunas não citadas ficam vazias)."""
    return pd.DataFrame([{c: r.get(c, "") for c in colunas} for r in registros],
                        columns=colunas)


def _dados_semana(**abas):
    dados = _dados()
    dados.update(abas)
    return dados


def _linha_com(linhas, trecho):
    achadas = [x["texto"] for x in linhas if trecho in x["texto"]]
    assert achadas, f"sem linha com {trecho!r}"
    return achadas[0]


def test_semana_conta_so_7_dias():
    gastos = _linhas(COLUNAS_GASTOS, [
        {"Data": pd.Timestamp("2026-10-19"), "Valor Total (R$)": 500},   # fora (exclusivo)
        {"Data": pd.Timestamp("2026-10-20"), "Valor Total (R$)": 100},
    ])
    linhas = aw.resumo_semana(_dados_semana(Gastos=gastos), HOJE_SEMANA)
    assert "1 lançamentos — R$ 100,00" in _linha_com(linhas, "Gastos")


def test_semana_vazia():
    assert aw.resumo_semana(_dados_semana(), HOJE_SEMANA) == []
    msg = aw.montar_msg_semanal([], HOJE_SEMANA, semana=[])
    assert "Semana sem registros." in msg


def test_semana_none_nao_mostra_secao():
    assert "Na semana" not in aw.montar_msg_semanal([], HOJE_SEMANA)


def test_semana_sem_valores():
    compras = _linhas(COLUNAS_COMPRAS, [
        {"Data": pd.Timestamp("2026-10-22"), "Qtd Cabeças": 5, "Valor Total (R$)": 15000}])
    semana = aw.resumo_semana(_dados_semana(Compras=compras), HOJE_SEMANA)
    com = aw.montar_msg_semanal([], HOJE_SEMANA, semana=semana)
    sem = aw.montar_msg_semanal([], HOJE_SEMANA, com_valores=False, semana=semana)
    assert "📆 *Na semana*" in com and "🛒 Compras: 5 cab. — R$ 15.000,00" in com
    assert "🛒 Compras: 5 cab." in sem and "R$" not in sem


def test_semana_manejo_e_nascimento():
    manejo = _linhas(COLUNAS_MANEJO, [
        {"Data": pd.Timestamp("2026-10-21"), "Tipo": "Vacina Aftosa", "Qtd Cabeças": 28},
        {"Data": pd.Timestamp("2026-10-21"), "Tipo": "Nascimento", "Qtd Cabeças": 1},
    ])
    semana = aw.resumo_semana(_dados_semana(Manejo=manejo), HOJE_SEMANA)
    assert "Vacina Aftosa (28 cab.)" in _linha_com(semana, "Manejos")
    assert "Nascimento" not in _linha_com(semana, "Manejos")
    assert "🍼 Nascimentos: 1" in _linha_com(semana, "Nascimentos")


def test_semana_visitas_e_chuva():
    visitas = _linhas(COLUNAS_VISITAS, [
        {"Data": pd.Timestamp("2026-10-21"), "Responsável": "Deyvid", "Chuva mm": 20},
        {"Data": pd.Timestamp("2026-10-23"), "Responsável": "Nilson", "Chuva mm": 15},
        {"Data": pd.NaT, "Responsável": "Mae", "Chuva mm": 99},
    ])
    semana = aw.resumo_semana(_dados_semana(Visitas=visitas), HOJE_SEMANA)
    assert _linha_com(semana, "Visitas") == "🏡 Visitas: 2 (Deyvid, Nilson) · 🌧️ chuva 35 mm"


def test_main_semanal_falha_no_resumo_nao_bloqueia(monkeypatch, capsys):
    monkeypatch.setattr(aw, "montar_itens", lambda hoje=None: [])
    def quebra(*a, **k):
        raise RuntimeError("xlsx ilegível")
    monkeypatch.setattr(aw, "resumo_semana", quebra)
    assert aw.main(["--teste", "--semanal"]) == 0
    assert "Resumo semanal" in capsys.readouterr().out
