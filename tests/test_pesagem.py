# -*- coding: utf-8 -*-
"""
v4.6 — Pesagem por animal e GMD. Peso vai na coluna "Pesos" da linha Pesagem
do Manejo; pesagens antigas da voz (peso só na Descrição) também são lidas.
"""
import pandas as pd
import pytest

import animais as A
import db
import pesagem as P
from config import COLUNAS_MANEJO
from extensions import _cache_invalidar


@pytest.fixture
def dois_animais(dados_restaurados):
    A._gravar(A.carregar().iloc[0:0])
    feitos = A.cadastrar([{"Dono": "Deyvid", "Categoria": "Garrote", "Brinco Nº": 21},
                          {"Dono": "Nilson", "Categoria": "Novilha", "Brinco Nº": 12}])
    _cache_invalidar()
    return [r["ID"] for r in feitos]


def _linha(**kw):
    return pd.Series({c: kw.get(c, "") for c in COLUNAS_MANEJO})


def test_pesos_coluna_e_legado():
    nova = _linha(Tipo="Pesagem", Pesos="Amarelo 21 #A0003: 320,5 kg; Azul 12 #A0007: 298 kg")
    assert P.pesos_da_linha(nova) == {"A0003": 320.5, "A0007": 298.0}
    voz = _linha(Tipo="Pesagem", Brincos="Amarelo 21 #A0003; Azul 12 #A0007",
                 **{"Descrição": "Amarelo 21: 320 kg; Azul 12: sem peso"})
    assert P.pesos_da_linha(voz) == {"A0003": 320.0}
    um = _linha(Tipo="Pesagem", Brincos="Amarelo 21 #A0003", **{"Descrição": "Peso: 410 kg"})
    assert P.pesos_da_linha(um) == {"A0003": 410.0}
    # Vacina que cita kg na descrição não vira peso
    assert P.pesos_da_linha(_linha(Tipo="Vermifugação", Brincos="Amarelo 21 #A0003",
                                   **{"Descrição": "Peso: 300 kg"})) == {}


def test_resumo_gmd():
    h = [(pd.Timestamp("2026-01-01"), 300.0), (pd.Timestamp("2026-04-11"), 360.0),
         (pd.Timestamp("2026-07-20"), 400.0)]
    r = P.resumo(h, rendimento=0.5)
    assert r["kg"] == 400 and r["n"] == 3 and r["dias"] == 100
    assert r["gmd"] == pytest.approx(0.4)
    assert r["gmd_total"] == pytest.approx(100 / 200)
    assert r["arrobas"] == pytest.approx(400 * 0.5 / 15)
    assert P.resumo(h[:1])["gmd"] is None
    assert P.resumo([]) is None


def test_validar_recusa_peso_absurdo(dois_animais):
    df = A.carregar()
    with pytest.raises(ValueError, match="parece errado"):
        P.validar({dois_animais[0]: "3200"}, df)
    with pytest.raises(ValueError, match="Nenhum peso"):
        P.validar({dois_animais[0]: ""}, df)
    assert P.validar({dois_animais[0]: "350,5", dois_animais[1]: ""}, df)[0][1] == 350.5


def test_pagina_pesagem_grava_uma_linha(cliente, dois_animais):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    a, b = dois_animais
    assert cliente.get("/animais/pesagem").status_code == 200
    antes = len(db.carregar_aba("Manejo"))
    r = cliente.post("/animais/pesagem", data={"csrf_token": "tok", "data": "2026-10-01",
                                               f"peso_{a}": "300", f"peso_{b}": "250,5"})
    assert r.status_code == 302
    man = db.carregar_aba("Manejo")
    assert len(man) == antes + 1
    ult = man.iloc[-1]
    assert ult["Tipo"] == "Pesagem" and int(ult["Qtd Cabeças"]) == 2
    assert P.pesos_da_linha(ult) == {a: 300.0, b: 250.5}
    # 2ª pesagem de um animal só → volta para a ficha, que mostra o GMD
    _cache_invalidar()
    r = cliente.post("/animais/pesagem", data={"csrf_token": "tok", "data": "2026-10-31",
                                               f"peso_{a}": "330"})
    assert r.headers["Location"].endswith(f"/animais/{a}")
    _cache_invalidar()
    hist = P.todas(db.carregar_aba("Manejo"))[a]
    assert P.resumo(hist)["gmd"] == pytest.approx(1.0)
    pagina = cliente.get(f"/animais/{a}").get_data(as_text=True)
    assert "1.00 kg/dia" in pagina and "chartPeso" in pagina


def test_voz_grava_coluna_pesos(monkeypatch):
    import comando_voz as V
    from datetime import datetime
    from test_comando_voz import CTX
    monkeypatch.setattr(A, "cores_brinco", lambda: {"Deyvid": "Amarelo", "Nilson": "Azul", "Mae": "Vermelho"})
    r = V.montar(V.analisar("pesagem amarelo 21 320 quilos, azul 12 280 quilos", datetime(2026, 10, 15)), CTX)
    linha = pd.Series({c: r["payload"]["linha"].get(c, "") for c in COLUNAS_MANEJO})
    assert sorted(P.pesos_da_linha(linha).values()) == [280.0, 320.0]
    assert "#A" in linha["Pesos"]
