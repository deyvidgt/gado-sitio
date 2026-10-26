#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lotes.py — painel econômico por lote (v5.3)

Um lote é uma **entrada de gado**: cada linha de Compras e cada Nascimento.
Nada de aba nem coluna nova — o lote é a compra que já está lançada.

A pergunta que isto responde é a que a média móvel do painel não responde:
"aquele caminhão de 20 bois que a gente comprou em março deu lucro?".

Regra única: **FIFO** (o gado mais velho sai primeiro). Cada venda e cada morte
consomem cabeças do lote mais antigo ainda aberto; cada gasto é dividido entre
os lotes que tinham gado vivo naquele dia, por cabeça.

⚠️ É uma visão APROXIMADA e paralela: o resultado oficial do sítio continua
sendo o da média móvel (`calculos.py`), que divide o custo entre todas as
cabeças em vez de supor FIFO. Este módulo só lê — não grava nada e não entra
em nenhuma conta do painel.
"""
from __future__ import annotations

import pandas as pd

SENTINELA = pd.Timestamp.max


def _num(v) -> float:
    try:
        return float(v) if pd.notna(v) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _data(v):
    return v if pd.notna(v) else SENTINELA


def _eventos(df_comp, df_gast, df_vend, df_man) -> list[tuple]:
    """Mesma ordem de eventos da média móvel: entradas antes das saídas no dia."""
    ev = []
    if df_comp is not None and not df_comp.empty:
        for i, r in df_comp.iterrows():
            ev.append((_data(r.get("Data")), 0, "compra", _num(r.get("Qtd Cabeças")),
                       _num(r.get("Valor Total (R$)")), i, r.get("Descrição")))
    if df_gast is not None and not df_gast.empty:
        for _, r in df_gast.iterrows():
            ev.append((_data(r.get("Data")), 1, "gasto", 0.0,
                       _num(r.get("Valor Total (R$)")), None, None))
    if df_man is not None and not df_man.empty and "Tipo" in df_man.columns:
        for _, r in df_man.iterrows():
            qtd = _num(r.get("Qtd Cabeças"))
            if qtd <= 0:
                continue
            if r.get("Tipo") == "Nascimento":
                ev.append((_data(r.get("Data")), 2, "nasc", qtd, 0.0, None, r.get("Descrição")))
            elif r.get("Tipo") == "Morte/Perda":
                ev.append((_data(r.get("Data")), 4, "morte", qtd, 0.0, None, None))
    if df_vend is not None and not df_vend.empty:
        for _, r in df_vend.iterrows():
            ev.append((_data(r.get("Data")), 3, "venda", _num(r.get("Qtd Cabeças")),
                       _num(r.get("Valor Total (R$)")), None, None))
    ev.sort(key=lambda e: (e[0], e[1]))
    return ev


def _novo_lote(data, origem, cab, custo, desc) -> dict:
    return {"data": data, "origem": origem, "rotulo": "", "descricao": str(desc or "").strip(),
            "cab": cab, "vivas": cab, "vendidas": 0.0, "mortas": 0.0,
            "custo_compra": custo, "gastos": 0.0, "receita": 0.0, "saida": None}


def _consumir(abertos: list[dict], qtd: float, campo: str, valor_cab: float, data):
    """Tira `qtd` cabeças dos lotes mais antigos (FIFO). Devolve o que não couber."""
    for lote in abertos:
        if qtd <= 0:
            break
        leva = min(lote["vivas"], qtd)
        if leva <= 0:
            continue
        lote["vivas"] -= leva
        lote[campo] += leva
        lote["receita"] += leva * valor_cab
        qtd -= leva
        if lote["vivas"] <= 0:
            lote["saida"] = data
    return qtd


def calcular(df_comp, df_gast, df_vend, df_man=None, hoje=None) -> dict:
    """{lotes: [...], sem_lote: {...}, totais: {...}} — lotes do mais novo ao mais velho."""
    hoje = pd.Timestamp(hoje or pd.Timestamp.now()).normalize()
    lotes: list[dict] = []
    # Venda/morte sem lote aberto (lançamento fora de ordem): o dinheiro não some,
    # fica aqui em vez de ser jogado num lote que não existia.
    sem_lote = {"cabecas": 0.0, "receita": 0.0}

    for data, _, tipo, qtd, valor, idx, desc in _eventos(df_comp, df_gast, df_vend, df_man):
        if tipo in ("compra", "nasc"):
            lotes.append(_novo_lote(data, "Compra" if tipo == "compra" else "Nascimento",
                                    qtd, valor, desc))
            continue

        abertos = [l for l in lotes if l["vivas"] > 0]
        if tipo == "gasto":
            vivas = sum(l["vivas"] for l in abertos)
            for l in abertos:           # gado comprado depois não paga gasto anterior
                l["gastos"] += valor * l["vivas"] / vivas if vivas else 0.0
        elif tipo in ("venda", "morte"):
            campo = "vendidas" if tipo == "venda" else "mortas"
            val_cab = valor / qtd if (tipo == "venda" and qtd) else 0.0
            sobra = _consumir(abertos, qtd, campo, val_cab, data)
            if sobra > 0:
                sem_lote["cabecas"] += sobra
                sem_lote["receita"] += sobra * val_cab

    for n, l in enumerate(lotes, 1):
        l["rotulo"] = (f"Lote {n} · {l['data']:%d/%m/%Y}" if l["data"] != SENTINELA
                       else f"Lote {n} · sem data")
        l["investido"] = l["custo_compra"] + l["gastos"]
        l["custo_cab"] = l["investido"] / l["cab"] if l["cab"] else 0.0
        saiu = l["vendidas"] + l["mortas"]
        # Resultado REALIZADO: o que saiu já pagou a sua parte do investido.
        l["resultado"] = l["receita"] - l["custo_cab"] * saiu
        l["valor_cab_vendida"] = l["receita"] / l["vendidas"] if l["vendidas"] else 0.0
        l["ganho_cab"] = (l["valor_cab_vendida"] - l["custo_cab"]) if l["vendidas"] else 0.0
        l["fechado"] = l["vivas"] <= 0
        l["parado"] = l["vivas"] * l["custo_cab"]      # capital ainda no pasto
        fim = l["saida"] if l["fechado"] and l["saida"] is not None else hoje
        l["dias"] = max(0, (fim - l["data"]).days) if l["data"] != SENTINELA else 0
        l["meses"] = l["dias"] / 30.0
        l["custo_cab_mes"] = (l["gastos"] / l["cab"] / l["meses"]
                              if l["cab"] and l["meses"] >= 1 else None)

    tot = {k: sum(l[k] for l in lotes) for k in
           ("cab", "vivas", "vendidas", "mortas", "custo_compra", "gastos",
            "receita", "investido", "resultado", "parado")}
    tot["lotes"] = len(lotes)
    tot["abertos"] = sum(1 for l in lotes if not l["fechado"])
    return {"lotes": lotes[::-1], "sem_lote": sem_lote, "totais": tot}
