#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pesagem.py — peso por animal e GMD (v4.6)

Uma pesagem é uma linha "Pesagem" no Manejo (como sempre foi, então o alerta
trimestral de saúde continua valendo). O peso de cada animal vai na coluna
"Pesos", legível na planilha e ligada ao ID:
    "Amarelo 21 #A0003: 320 kg; Azul 12 #A0007: 298,5 kg"
Pesagens antigas feitas pela voz só tinham o peso na Descrição
("Amarelo 21: 320 kg") — são lidas também, casando com a coluna "Brincos".

Não entra nas finanças: só informa (GMD, @ estimadas, peso médio do rebanho).
"""
from __future__ import annotations

import re

import pandas as pd

import animais as A
import db

PESO_MIN, PESO_MAX = 10, 1500   # kg — fora disso é erro de digitação
_RE_PESO_ID = re.compile(r"#(A\d+)\s*:\s*(\d+(?:[.,]\d+)?)\s*kg", re.I)


def _kg(v) -> float:
    return float(str(v).replace(",", "."))


def fmt_kg(kg: float) -> str:
    return f"{kg:g}".replace(".", ",")


def fmt_pesos(pares) -> str:
    """[(ref, kg)] → texto da coluna "Pesos"."""
    return "; ".join(f"{ref}: {fmt_kg(kg)} kg" for ref, kg in pares)


def pesos_da_linha(row) -> dict:
    """{ID: kg} de uma linha do Manejo (coluna Pesos; senão a Descrição antiga)."""
    pesos = {i: _kg(k) for i, k in _RE_PESO_ID.findall(str(row.get("Pesos") or ""))}
    if pesos or row.get("Tipo") != "Pesagem":
        return pesos
    desc = str(row.get("Descrição") or "")
    refs = [r.strip() for r in str(row.get("Brincos") or "").split(";") if "#" in r]
    for r in refs:
        rotulo, id_ = r.split(" #")[0], A.ids_de(r)[0]
        m = re.search(re.escape(rotulo) + r"\s*:\s*(\d+(?:[.,]\d+)?)\s*kg", desc, re.I)
        if m:
            pesos[id_] = _kg(m.group(1))
    if not pesos and len(refs) == 1:
        # voz com um animal só: "Peso: 320 kg"
        m = re.search(r"peso\s*:\s*(\d+(?:[.,]\d+)?)\s*kg", desc, re.I)
        if m:
            pesos[A.ids_de(refs[0])[0]] = _kg(m.group(1))
    return pesos


def todas(df_man: pd.DataFrame) -> dict:
    """{ID: [(data, kg), ...]} em ordem de data (sem data fica de fora)."""
    out: dict[str, list] = {}
    if df_man is None or df_man.empty:
        return out
    cols = df_man.columns
    if "Pesos" not in cols and "Brincos" not in cols:
        return out
    for _, r in df_man.iterrows():
        data = pd.to_datetime(r.get("Data"), dayfirst=True, errors="coerce")
        if pd.isna(data):
            continue
        for id_, kg in pesos_da_linha(r).items():
            out.setdefault(id_, []).append((data.normalize(), kg))
    for lista in out.values():
        lista.sort(key=lambda x: x[0])
    return out


def _gmd(a, b):
    dias = (b[0] - a[0]).days
    return (b[1] - a[1]) / dias if dias > 0 else None


def resumo(hist: list, rendimento: float = 0.52) -> dict | None:
    """Último peso, @ (carcaça) e GMD do último intervalo e desde a 1ª pesagem."""
    if not hist:
        return None
    ultimo = hist[-1]
    anteriores = [h for h in hist if h[0] < ultimo[0]]
    return {
        "kg": ultimo[1], "data": ultimo[0],
        "arrobas": ultimo[1] * rendimento / 15.0,
        "gmd": _gmd(anteriores[-1], ultimo) if anteriores else None,
        "gmd_total": _gmd(hist[0], ultimo) if anteriores else None,
        "dias": (ultimo[0] - anteriores[-1][0]).days if anteriores else None,
        "n": len(hist),
    }


def peso_medio_vivos(df_animais: pd.DataFrame, df_man: pd.DataFrame) -> tuple[float, int]:
    """(peso médio do último peso dos vivos pesados, quantos têm peso)."""
    hist = todas(df_man)
    pesos = [hist[i][-1][1] for i in A.vivos(df_animais)["ID"] if i in hist] if not df_animais.empty else []
    return (sum(pesos) / len(pesos), len(pesos)) if pesos else (0.0, 0)


def validar(pares_txt: dict, df_animais: pd.DataFrame) -> list[tuple[str, float]]:
    """{ID: '320,5'} do formulário → [(ref, kg)]; levanta ValueError com a mensagem."""
    pares = []
    for id_, txt in pares_txt.items():
        txt = str(txt or "").strip()
        if not txt:
            continue
        a = A.por_id(df_animais, id_)
        if a is None:
            raise ValueError(f"Animal #{id_} não existe.")
        try:
            kg = _kg(txt)
        except ValueError:
            raise ValueError(f"Peso inválido para {A.fmt_brinco(a['Brinco Cor'], a['Brinco Nº'])}: {txt}")
        if not PESO_MIN <= kg <= PESO_MAX:
            raise ValueError(f"{A.fmt_brinco(a['Brinco Cor'], a['Brinco Nº'])}: {fmt_kg(kg)} kg "
                             f"parece errado (aceito de {PESO_MIN} a {PESO_MAX} kg).")
        pares.append((A.ref(a), kg))
    if not pares:
        raise ValueError("Nenhum peso informado.")
    return pares


def registrar(pares: list[tuple[str, float]], data, responsavel: str = "", obs: str = ""):
    """Grava UMA linha Pesagem no Manejo com todos os animais pesados."""
    data_ts = A._data(data) if data else pd.NaT
    if pd.isna(data_ts):
        data_ts = pd.Timestamp.now().normalize()
    db.salvar_linha("Manejo", A._linha_manejo(
        data_ts, "Pesagem", len(pares),
        obs or f"{len(pares)} animal(is) · média {fmt_kg(round(sum(k for _, k in pares) / len(pares), 1))} kg",
        responsavel,
        brincos="; ".join(r for r, _ in pares), pesos=fmt_pesos(pares)))
