# -*- coding: utf-8 -*-
"""
Peso estimado por foto (v5.1): medidas da foto → Schaeffer → calibração com a balança.
A estimativa nunca entra no GMD.
"""
import pandas as pd
import pytest

import animais as A
import db
import pesagem as P
import peso_foto as F
from config import COLUNAS_MANEJO
from extensions import _cache_invalidar


def _linha(data, tipo, pesos, brincos="Amarelo 21 #A0001"):
    return {**{c: "" for c in COLUNAS_MANEJO}, "Data": pd.Timestamp(data), "Tipo": tipo,
            "Qtd Cabeças": 1, "Brincos": brincos, "Pesos": pesos}


def test_formula_schaeffer():
    # perímetro = 2,6 × 70 = 182 cm; 182² × 160 / 10838 = 489 kg
    assert F.estimar_bruto(160, 70) == pytest.approx(182 ** 2 * 160 / 10838)
    assert 480 < F.estimar_bruto(160, 70) < 500


@pytest.mark.parametrize("comp,prof,ref", [(40, 70, 100), (160, 10, 100), (300, 70, 100),
                                            (160, 70, 5), ("abc", 70, 100), (160, 200, 100)])
def test_medidas_absurdas_recusadas(comp, prof, ref):
    with pytest.raises(ValueError):
        F.validar(comp, prof, ref)


def test_validar_aceita_virgula():
    assert F.validar("158,5", "71", "100") == (158.5, 71.0, 100.0)


def _df(*linhas):
    return pd.DataFrame(list(linhas), columns=COLUNAS_MANEJO)


def test_calibracao_precisa_de_3_pares():
    df = _df(_linha("2026-01-01", "Peso Estimado", "Amarelo 21 #A0001: 400 kg"),
             _linha("2026-01-05", "Pesagem", "Amarelo 21 #A0001: 440 kg"),
             _linha("2026-02-01", "Peso Estimado", "Azul 02 #A0002: 300 kg", "Azul 02 #A0002"),
             _linha("2026-02-03", "Pesagem", "Azul 02 #A0002: 330 kg", "Azul 02 #A0002"))
    assert F.fator_calibracao(df) == (1.0, 2)


def test_calibracao_mediana_e_limite():
    linhas = []
    for i, (est, real) in enumerate([(400, 440), (300, 330), (500, 560), (200, 900)]):
        ref = f"Azul {i:02d} #A00{i + 10}"
        linhas += [_linha("2026-03-01", "Peso Estimado", f"{ref}: {est} kg", ref),
                   _linha("2026-03-10", "Pesagem", f"{ref}: {real} kg", ref)]
    # par a mais de 15 dias não conta
    linhas += [_linha("2026-01-01", "Peso Estimado", "Azul 50 #A0050: 100 kg", "Azul 50 #A0050"),
               _linha("2026-03-01", "Pesagem", "Azul 50 #A0050: 500 kg", "Azul 50 #A0050")]
    fator, n = F.fator_calibracao(_df(*linhas))
    assert n == 4
    # razões 1,10 · 1,10 · 1,12 · 4,5 → a mediana ignora o par errado
    assert fator == pytest.approx((1.10 + 1.12) / 2)


def test_calibracao_limitada():
    linhas = []
    for i in range(3):
        ref = f"Azul {i:02d} #A00{i + 10}"
        linhas += [_linha("2026-03-01", "Peso Estimado", f"{ref}: 200 kg", ref),
                   _linha("2026-03-02", "Pesagem", f"{ref}: 400 kg", ref)]
    assert F.fator_calibracao(_df(*linhas)) == (1.3, 3)


def test_estimado_fora_do_gmd():
    df = _df(_linha("2026-01-01", "Pesagem", "Amarelo 21 #A0001: 300 kg"),
             _linha("2026-02-01", "Peso Estimado", "Amarelo 21 #A0001: 999 kg"))
    assert [kg for _, kg in P.todas(df)["A0001"]] == [300.0]
    assert [kg for _, kg in P.todas(df, estimados=True)["A0001"]] == [999.0]


@pytest.fixture
def um_animal(dados_restaurados):
    A._gravar(A.carregar().iloc[0:0])
    reg = A.cadastrar([{"Dono": "Deyvid", "Categoria": "Garrote", "Brinco Nº": 21}])[0]
    _cache_invalidar()
    return reg["ID"]


def test_registrar_e_ultima_estimativa(um_animal):
    bruto = F.registrar(um_animal, 160, 70, 100, "2026-10-01", "Deyvid")
    man = db.carregar_aba("Manejo")
    ult = man.iloc[-1]
    assert ult["Tipo"] == "Peso Estimado" and int(ult["Qtd Cabeças"]) == 1
    assert "comprimento 160 cm" in ult["Descrição"]
    est = F.ultima_estimativa(um_animal, man)
    assert est["bruto"] == pytest.approx(bruto, abs=0.5) and est["fator"] == 1.0
    assert est["faixa_pct"] == 15
