# -*- coding: utf-8 -*-
"""
Reprodução sem sensor (v5.3): cobertura → toque → parto, só com calendário.
"""
import pandas as pd
import pytest

import reproducao as R
from config import COLUNAS_ANIMAIS, COLUNAS_MANEJO

HOJE = pd.Timestamp("2026-11-10")


def _man(*linhas):
    """Manejo só com as colunas que a reprodução lê."""
    df = pd.DataFrame(linhas, columns=["Data", "Tipo", "Descrição", "Produto", "Brincos"])
    for c in COLUNAS_MANEJO:
        if c not in df.columns:
            df[c] = ""
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True)
    return df


def _animais(*linhas):
    df = pd.DataFrame(linhas, columns=["ID", "Brinco Cor", "Brinco Nº", "Sexo",
                                       "Status", "Mãe", "Nascimento"])
    for c in COLUNAS_ANIMAIS:
        if c not in df.columns:
            df[c] = ""
    return df


VACA = _animais(("A0001", "Amarelo", 21, "F", "Vivo", "", ""))


def test_cobertura_vira_coberta_com_previsao_de_parto():
    df = _man(("01/02/2026", "Cobertura", "Cobertura — Touro Zebu", "Touro Zebu",
               "Amarelo 21 #A0001"))
    v = R.situacao(df, VACA, HOJE)[0]
    assert v["status"] == "coberta" and v["touro"] == "Touro Zebu"
    assert v["parto_previsto"] == pd.Timestamp("2026-11-13")   # 01/02 + 285
    assert v["diagnostico_a_partir"] == pd.Timestamp("2026-03-08")
    assert v["secagem_em"] == pd.Timestamp("2026-09-14")
    assert v["dias_para_parto"] == 3


def test_toque_prenha_e_vazia():
    base = ("01/02/2026", "Cobertura", "", "", "Amarelo 21 #A0001")
    prenha = R.situacao(_man(base, ("10/03/2026", R.TIPO_DIAGNOSTICO, "Prenha", "",
                                    "Amarelo 21 #A0001")), VACA, HOJE)[0]
    vazia = R.situacao(_man(base, ("10/03/2026", R.TIPO_DIAGNOSTICO, "Vazia", "",
                                   "Amarelo 21 #A0001")), VACA, HOJE)[0]
    assert prenha["status"] == "prenha" and vazia["status"] == "vazia"


def test_bezerro_com_mae_fecha_o_ciclo():
    rebanho = _animais(("A0001", "Amarelo", 21, "F", "Vivo", "", ""),
                       ("A0002", "Verde", 1, "M", "Vivo", "Amarelo 21 #A0001", "05/11/2026"))
    v = R.situacao(_man(("01/02/2026", "Cobertura", "", "", "Amarelo 21 #A0001")),
                   rebanho, HOJE)[0]
    assert v["status"] == "pariu" and v["pariu_em"] == pd.Timestamp("2026-11-05")


def test_sem_noticia_muito_depois_do_parto_fica_atrasada():
    v = R.situacao(_man(("01/02/2026", "Cobertura", "", "", "Amarelo 21 #A0001")),
                   VACA, pd.Timestamp("2027-01-10"))[0]
    assert v["status"] == "atrasada"


def test_cobertura_nova_substitui_a_anterior():
    df = _man(("01/02/2026", "Cobertura", "", "Touro A", "Amarelo 21 #A0001"),
              ("20/02/2026", R.TIPO_DIAGNOSTICO, "Vazia", "", "Amarelo 21 #A0001"),
              ("01/03/2026", "Cobertura", "", "Touro B", "Amarelo 21 #A0001"))
    sit = R.situacao(df, VACA, HOJE)
    assert len(sit) == 1
    assert sit[0]["touro"] == "Touro B" and sit[0]["status"] == "coberta"
    assert sit[0]["coberta_em"] == pd.Timestamp("2026-03-01")


def test_indicadores_taxa_e_iep():
    rebanho = _animais(("A0001", "Amarelo", 21, "F", "Vivo", "", ""),
                       ("A0002", "Azul", 5, "F", "Vivo", "", ""),
                       ("A0003", "Verde", 1, "M", "Vivo", "Amarelo 21 #A0001", "01/01/2025"),
                       ("A0004", "Verde", 2, "M", "Vivo", "Amarelo 21 #A0001", "11/01/2026"))
    df = _man(("01/02/2026", "Cobertura", "", "", "Amarelo 21 #A0001"),
              ("10/03/2026", R.TIPO_DIAGNOSTICO, "Prenha", "", "Amarelo 21 #A0001"),
              ("01/02/2026", "Cobertura", "", "", "Azul 05 #A0002"),
              ("10/03/2026", R.TIPO_DIAGNOSTICO, "Vazia", "", "Azul 05 #A0002"))
    ind = R.indicadores(R.situacao(df, rebanho, HOJE), rebanho)
    assert ind["coberturas"] == 2 and ind["taxa_prenhez"] == 50.0
    assert ind["iep_dias"] == 375


def test_parto_em_poucos_dias_vira_aviso_urgente():
    sit = R.situacao(_man(("01/02/2026", "Cobertura", "", "", "Amarelo 21 #A0001")),
                     VACA, HOJE)
    a = R.alertas(sit, HOJE)
    assert len(a) == 1 and a[0]["urgente"] and "Amarelo 21" in a[0]["texto"]


def test_vaca_vazia_nao_gera_aviso():
    df = _man(("01/02/2026", "Cobertura", "", "", "Amarelo 21 #A0001"),
              ("10/03/2026", R.TIPO_DIAGNOSTICO, "Vazia", "", "Amarelo 21 #A0001"))
    assert R.alertas(R.situacao(df, VACA, HOJE), HOJE) == []


def test_pagina_reproducao_abre_e_grava(cliente, dados_restaurados):
    import animais as A
    A.cadastrar([{"Brinco Cor": "Amarelo", "Brinco Nº": 21, "Dono": "Deyvid",
                  "Categoria": "Vaca", "Origem": "Já no sítio"}],
                registrado_por="Deyvid")
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    cliente.post("/reproducao/registrar",
                 data={"csrf_token": "tok", "tipo": "cobertura", "vaca": "Amarelo 21",
                       "data": "2026-02-01", "touro": "Touro Zebu"},
                 follow_redirects=True)
    html = cliente.get("/reproducao").get_data(as_text=True)
    assert "Touro Zebu" in html and "Amarelo 21" in html


def test_registrar_toque_sem_resultado_recusa():
    with pytest.raises(ValueError):
        R.registrar(R.TIPO_DIAGNOSTICO, "Amarelo 21", "2026-03-10")
