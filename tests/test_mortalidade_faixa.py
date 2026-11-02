# -*- coding: utf-8 -*-
"""v5.15 — Mortalidade segmentada por faixa etária (idade na Data Saída)."""
import pandas as pd

import indicadores_v58 as I


def test_mortalidade_por_faixa_etaria():
    df = pd.DataFrame([
        {"Status": "Morto", "Nascimento": "01/01/2025", "Data Saída": "01/03/2025"},  # 2 m
        {"Status": "Morto", "Nascimento": "01/01/2024", "Data Saída": "01/09/2024"},  # 8 m
        {"Status": "Morto", "Nascimento": "01/01/2020", "Data Saída": "01/06/2024"},  # 53 m
        {"Status": "Morto", "Nascimento": "", "Data Saída": ""},                      # sem data
        {"Status": "Vivo", "Nascimento": "01/01/2020", "Data Saída": ""},             # vivo
    ])
    r = I.mortalidade_por_faixa_etaria({"Animais": df})
    assert r["total"] == 3
    assert r["sem_data"] == 1
    fx = {f["faixa"]: f for f in r["faixas"]}
    assert fx["0 a 4 meses"]["n"] == 1
    assert fx["5 a 12 meses"]["n"] == 1
    assert fx["> 36 meses"]["n"] == 1
    # Cada % é arredondado a 1 casa (33.3 × 3 = 99.9) — tolera o arredondamento.
    assert abs(sum(f["pct"] for f in r["faixas"]) - 100.0) < 0.5


def test_mortalidade_por_faixa_sem_dados():
    r = I.mortalidade_por_faixa_etaria({"Animais": pd.DataFrame()})
    assert r["total"] == 0
    assert all(f["n"] == 0 for f in r["faixas"])
