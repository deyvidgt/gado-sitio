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


TIPO_ESTIMADO = "Peso Estimado"   # peso pela foto (peso_foto.py) — nunca entra no GMD


def todas(df_man: pd.DataFrame, estimados: bool = False) -> dict:
    """{ID: [(data, kg), ...]} em ordem de data (sem data fica de fora).
    Só balança; com estimados=True, só as estimativas por foto (peso bruto)."""
    out: dict[str, list] = {}
    if df_man is None or df_man.empty:
        return out
    cols = df_man.columns
    if "Pesos" not in cols and "Brincos" not in cols:
        return out
    for _, r in df_man.iterrows():
        if (r.get("Tipo") == TIPO_ESTIMADO) != estimados:
            continue
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


def faixas_arrobas(df_animais: pd.DataFrame, df_man: pd.DataFrame, rendimento: float = 0.52) -> dict:
    """Agrupa os animais vivos por faixas de arrobas (@ de carcaça)."""
    hist = todas(df_man)
    vivos = A.vivos(df_animais)["ID"].tolist() if not df_animais.empty else []
    faixas_def = [
        ("< 7 @", "Bezerros / Desmama", 0.0, 7.0),
        ("7 a 10 @", "Recria", 7.0, 10.0),
        ("10 a 13 @", "Engorda", 10.0, 13.0),
        ("> 13 @", "Terminação / Venda", 13.0, 9999.0),
    ]
    contagens = {rotulo: {"nome": rotulo, "sub": sub, "n": 0, "kg_soma": 0.0, "arr_soma": 0.0}
                 for rotulo, sub, _, _ in faixas_def}
    sem_peso, pesados = 0, 0
    for i in vivos:
        if i in hist and hist[i]:
            kg = hist[i][-1][1]
            arr = kg * rendimento / 15.0
            pesados += 1
            for rotulo, _, f_min, f_max in faixas_def:
                if f_min <= arr < f_max or (f_max > 100 and arr >= f_min):
                    c = contagens[rotulo]
                    c["n"] += 1
                    c["kg_soma"] += kg
                    c["arr_soma"] += arr
                    break
        else:
            sem_peso += 1

    total = pesados + sem_peso
    lista = []
    for rotulo, _, _, _ in faixas_def:
        c = contagens[rotulo]
        n = c["n"]
        lista.append({
            "rotulo": c["nome"],
            "sub": c["sub"],
            "n": n,
            "pct": round(n * 100 / total, 1) if total > 0 else 0,
            "kg_medio": round(c["kg_soma"] / n, 1) if n > 0 else 0,
            "arr_media": round(c["arr_soma"] / n, 1) if n > 0 else 0,
        })

    return {
        "faixas": lista,
        "total_pesados": pesados,
        "sem_peso": sem_peso,
        "total_vivos": total,
    }


def curva_evolucao_peso(df_man: pd.DataFrame, rendimento: float = 0.52) -> list[dict]:
    """Pontos no tempo com o peso médio do lote em cada pesagem realizada."""
    if df_man is None or df_man.empty or "Data" not in df_man.columns:
        return []
    pesagens = df_man[df_man["Tipo"] == "Pesagem"]
    if pesagens.empty:
        return []

    por_data: dict[pd.Timestamp, list[float]] = {}
    for _, r in pesagens.iterrows():
        d = pd.to_datetime(r.get("Data"), dayfirst=True, errors="coerce")
        if pd.isna(d):
            continue
        d = d.normalize()
        pesos_dict = pesos_da_linha(r)
        if pesos_dict:
            por_data.setdefault(d, []).extend(pesos_dict.values())

    if not por_data:
        return []

    datas_ord = sorted(por_data.keys())
    pontos = []
    ult_kg, ult_data = None, None
    for d in datas_ord:
        kgs = por_data[d]
        kg_med = round(sum(kgs) / len(kgs), 1)
        arr_med = round(kg_med * rendimento / 15.0, 1)
        gmd = None
        if ult_data is not None and ult_kg is not None:
            dias = (d - ult_data).days
            if dias > 0:
                gmd = round((kg_med - ult_kg) / dias, 3)
        ult_kg, ult_data = kg_med, d
        pontos.append({
            "data": d.strftime("%Y-%m-%d"),
            "data_br": d.strftime("%d/%m/%Y"),
            "kg": kg_med,
            "arrobas": arr_med,
            "n": len(kgs),
            "gmd": gmd,
        })
    return pontos


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
