#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pastos.py — pastos desenhados no mapa (v5.2)

Aba "Pastos": um polígono (GeoJSON) por pasto; a área é calculada AQUI pelo
contorno, não vem do navegador. Mover o gado grava "Movimentação de Pasto" no
Manejo com o ID do pasto na coluna "Pasto" (Brincos vazio = o rebanho todo).
Não mexe nas finanças. Design: docs/superpowers/specs/2026-10-25-pastos-mapa-design.md
"""
from __future__ import annotations

import json
import math
import re

import pandas as pd

import animais as A
import db
import pesagem as P
from config import COLUNAS_PASTOS

ABA = "Pastos"
TIPO_MOV = "Movimentação de Pasto"
UA_KG = 450                       # 1 unidade animal
RAIO_TERRA = 6378137.0
AREA_MIN, AREA_MAX = 0.01, 100000
PONTOS_MIN, PONTOS_MAX = 3, 500
CORES = ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231", "#911eb4",
         "#46f0f0", "#f032e6", "#bcf60c", "#fabebe"]


def area_ha(geo: dict) -> float:
    """Área esférica do anel externo (mesma fórmula do Leaflet.draw/Google), em ha."""
    anel = geo["coordinates"][0]
    soma = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(anel, anel[1:] + anel[:1]):
        soma += math.radians(lon2 - lon1) * (2 + math.sin(math.radians(lat1))
                                             + math.sin(math.radians(lat2)))
    return abs(soma * RAIO_TERRA ** 2 / 2) / 10000


def validar_contorno(texto: str) -> tuple[dict, float]:
    """Texto do formulário (Feature ou Polygon) → (Polygon limpo, área ha); ValueError."""
    try:
        geo = json.loads(texto)
        if geo.get("type") == "Feature":
            geo = geo["geometry"]
        if geo.get("type") != "Polygon":
            raise ValueError
        anel = [[float(lon), float(lat)] for lon, lat in geo["coordinates"][0]]
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        raise ValueError("Contorno do pasto inválido — desenhe de novo no mapa.")
    if anel and anel[0] == anel[-1]:
        anel = anel[:-1]
    if not PONTOS_MIN <= len(anel) <= PONTOS_MAX:
        raise ValueError(f"O contorno precisa ter de {PONTOS_MIN} a {PONTOS_MAX} cantos.")
    if not all(math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90
               for lon, lat in anel):
        raise ValueError("Contorno do pasto com ponto fora do mapa.")
    limpo = {"type": "Polygon", "coordinates": [anel + [anel[0]]]}
    area = area_ha(limpo)
    if not AREA_MIN <= area <= AREA_MAX:
        raise ValueError(f"Área de {area:g} ha não parece certa — desenhe de novo.")
    return limpo, round(area, 2)


def carregar() -> pd.DataFrame:
    df = db.carregar_aba(ABA)
    for c in COLUNAS_PASTOS:
        if c not in df.columns:
            df[c] = None
    df = df[COLUNAS_PASTOS].copy()
    for c in COLUNAS_PASTOS:
        if c != "Área (ha)":
            df[c] = df[c].apply(A._txt).astype(object)
    df["Área (ha)"] = pd.to_numeric(df["Área (ha)"], errors="coerce").fillna(0.0)
    return df.reset_index(drop=True)


def ativos(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["Ativo"] != "Não"]


def _gravar(df: pd.DataFrame):
    out = df[COLUNAS_PASTOS].astype(object)
    db.reescrever_aba(ABA, out.where(pd.notna(out), None))


def _nome(nome, df, exceto=None) -> str:
    nome = re.sub(r"\s+", " ", str(nome or "")).strip()
    if not 1 <= len(nome) <= 40:
        raise ValueError("Dê um nome ao pasto (até 40 letras).")
    outros = ativos(df)
    outros = outros[outros["ID"] != exceto]
    if nome.lower() in outros["Nome"].str.lower().tolist():
        raise ValueError(f"Já existe um pasto chamado {nome}.")
    return nome


def criar(nome, contorno_json, criado_por: str = "") -> str:
    df = carregar()
    nome = _nome(nome, df)
    geo, area = validar_contorno(contorno_json)
    nums = [int(i[1:]) for i in df["ID"] if re.fullmatch(r"P\d+", i)]
    id_ = f"P{max(nums, default=0) + 1:02d}"
    db.salvar_linha(ABA, [id_, nome, area, json.dumps(geo), CORES[len(df) % len(CORES)],
                          "Sim", "", criado_por])
    return id_


def _linha(df, id_):
    m = df.index[(df["ID"] == id_) & (df["Ativo"] != "Não")]
    if m.empty:
        raise ValueError("Pasto não encontrado.")
    return m[0]


def editar(id_, nome=None, contorno_json=None):
    df = carregar()
    i = _linha(df, id_)
    if nome is not None:
        df.at[i, "Nome"] = _nome(nome, df, exceto=id_)
    if contorno_json is not None:
        geo, area = validar_contorno(contorno_json)
        df.at[i, "Contorno"], df.at[i, "Área (ha)"] = json.dumps(geo), area
    _gravar(df)


def excluir(id_):
    """Só desativa: as movimentações antigas continuam apontando para um ID que existe."""
    df = carregar()
    df.at[_linha(df, id_), "Ativo"] = "Não"
    _gravar(df)


def mover(pasto_id, data, refs: list[str] | None, qtd: int, responsavel: str = ""):
    """refs None = o rebanho todo (Brincos vazio)."""
    df = carregar()
    nome = df.at[_linha(df, pasto_id), "Nome"]
    data_ts = A._data(data) if data else pd.NaT
    if pd.isna(data_ts):
        data_ts = pd.Timestamp.now().normalize()
    qtd = len(refs) if refs else int(qtd)
    if qtd <= 0:
        raise ValueError("Nenhuma cabeça para mover.")
    quem = "rebanho todo" if refs is None else f"{qtd} animal(is)"
    db.salvar_linha("Manejo", A._linha_manejo(
        data_ts, TIPO_MOV, qtd, f"Para o pasto {nome} ({quem})", responsavel,
        brincos="; ".join(refs or []), pasto=pasto_id))


def situacao(df_pastos, df_animais, df_man, estoque: int, peso_medio: float, hoje=None) -> dict:
    """{ID do pasto ativo: {cab, ua, ua_ha, dias, estimado}} + None = sem pasto.

    Percorre as movimentações em ordem: a do rebanho todo leva todo mundo (apaga
    as individuais anteriores); a com brincos leva só aqueles."""
    hoje = pd.Timestamp(hoje or pd.Timestamp.now()).normalize()
    peso_padrao = peso_medio if peso_medio and peso_medio > 0 else UA_KG
    rebanho, individual = (None, None), {}
    if df_man is not None and not df_man.empty and "Pasto" in df_man.columns:
        movs = df_man[(df_man["Tipo"] == TIPO_MOV) & df_man["Pasto"].apply(A._txt).ne("")]
        movs = movs.assign(_d=pd.to_datetime(movs["Data"], dayfirst=True, errors="coerce"))
        for _, r in movs.dropna(subset=["_d"]).sort_values("_d", kind="stable").iterrows():
            onde = (A._txt(r["Pasto"]), r["_d"].normalize())
            ids = A.ids_de(r.get("Brincos"))
            if ids:
                individual.update({i: onde for i in ids})
            else:
                rebanho, individual = onde, {}

    pesos = P.todas(df_man)
    vivos = A.vivos(df_animais)["ID"].tolist() if not df_animais.empty else []
    sem_brinco = max(0, int(estoque) - len(vivos))
    # (pasto, data de chegada, nº de cabeças, kg, quantas sem peso de balança)
    grupos = [(*rebanho, sem_brinco, sem_brinco * peso_padrao, sem_brinco)]
    for i in vivos:
        kg = pesos[i][-1][1] if i in pesos else None
        grupos.append((*individual.get(i, rebanho), 1, kg or peso_padrao, 0 if kg else 1))

    validos = set(ativos(df_pastos)["ID"]) if not df_pastos.empty else set()
    area = dict(zip(df_pastos["ID"], df_pastos["Área (ha)"])) if not df_pastos.empty else {}
    out = {p: {"cab": 0, "kg": 0.0, "estimado": False, "_chegadas": {}} for p in [*validos, None]}
    for pasto, data, n, kg, sem_peso in grupos:
        if n == 0:
            continue
        s = out[pasto if pasto in validos else None]
        s["cab"] += n
        s["kg"] += kg
        s["estimado"] |= sem_peso > 0
        if pasto in validos:
            s["_chegadas"][data] = s["_chegadas"].get(data, 0) + n
    for p, s in out.items():
        s["ua"] = s.pop("kg") / UA_KG
        chegadas = s.pop("_chegadas")
        s["dias"] = (hoje - max(chegadas, key=chegadas.get)).days if chegadas else None
        a = float(area.get(p) or 0)
        s["ua_ha"] = s["ua"] / a if a > 0 else None
    return out


def nivel(ua_ha: float | None, capacidade: float | None) -> str | None:
    """Semáforo da lotação: ok (<70%), atencao (70–100%), excesso (>100%).

    None quando não há como comparar — pasto sem contorno (ua_ha None) ou
    capacidade não configurada. Sem referência não se pinta nada."""
    if ua_ha is None or not capacidade or capacidade <= 0:
        return None
    pct = ua_ha / capacidade
    return "ok" if pct < 0.7 else ("atencao" if pct <= 1.0 else "excesso")


def total_lotacao(df_pastos, sit: dict, capacidade: float | None = None) -> dict:
    """Lotação somando os pastos desenhados: {ua, ha, ua_ha, nivel}.

    Só entra pasto ativo com área; o que está "sem pasto" fica de fora porque
    não tem área para dividir."""
    ids = set(ativos(df_pastos)["ID"]) if not df_pastos.empty else set()
    ha = sum(float(p["Área (ha)"] or 0) for _, p in ativos(df_pastos).iterrows()) if ids else 0.0
    ua = sum(s["ua"] for p, s in sit.items() if p in ids)
    ua_ha = ua / ha if ha > 0 else None
    return {"ua": ua, "ha": ha, "ua_ha": ua_ha, "nivel": nivel(ua_ha, capacidade),
            "capacidade": capacidade}
