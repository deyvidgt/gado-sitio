#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tarefas.py — agenda do sítio (v5.3)

Aba "Tarefas": o que precisa ser feito e quando ("consertar a cerca do fundo",
"trocar o sal do cocho"). Diferente do calendário sanitário (saude.py), que é
calculado das regras; aqui quem escreve é a família.

Datas ficam como texto dd/mm/aaaa, igual ao resto da planilha. "Feito Em" vazio
= pendente. Ao concluir uma tarefa que se repete, a próxima já nasce sozinha —
senão a família esquecia de recriar.
Não mexe nas finanças.
"""
from __future__ import annotations
from agora import agora

import re

import pandas as pd

import animais as A
import db
from config import COLUNAS_TAREFAS, REPETICOES_TAREFA

ABA = "Tarefas"
PROXIMAS_DIAS = 30        # janela da lista "o que vem aí"


def carregar() -> pd.DataFrame:
    df = db.carregar_aba(ABA)
    for c in COLUNAS_TAREFAS:
        if c not in df.columns:
            df[c] = None
    # O db converte a coluna "Data" em Timestamp; aqui tudo é texto dd/mm/aaaa.
    df["Data"] = df["Data"].apply(lambda d: f"{d:%d/%m/%Y}" if isinstance(d, pd.Timestamp) else d)
    # fillna antes do _txt: célula vazia vira NaN e str(NaN) daria o texto "nan".
    return df[COLUNAS_TAREFAS].fillna("").map(A._txt).astype(object).reset_index(drop=True)


def _gravar(df: pd.DataFrame):
    out = df[COLUNAS_TAREFAS].astype(object)
    db.reescrever_aba(ABA, out.where(pd.notna(out), None))


def _data_br(valor) -> str:
    d = A._data(valor) if valor else pd.NaT
    if pd.isna(d):
        raise ValueError("Escolha a data da tarefa.")
    return f"{d:%d/%m/%Y}"


def criar(titulo, data, responsavel="", repetir="Não", obs="", criado_por="") -> str:
    titulo = re.sub(r"\s+", " ", str(titulo or "")).strip()
    if not 1 <= len(titulo) <= 80:
        raise ValueError("Escreva o que precisa ser feito (até 80 letras).")
    repetir = str(repetir or "Não").strip() or "Não"
    if repetir not in REPETICOES_TAREFA:
        raise ValueError(f"Repetição '{repetir}' não existe.")
    df = carregar()
    nums = [int(i[1:]) for i in df["ID"] if re.fullmatch(r"T\d+", i)]
    id_ = f"T{max(nums, default=0) + 1:04d}"
    db.salvar_linha(ABA, [id_, _data_br(data), titulo, str(responsavel or "").strip(),
                          repetir, "", str(obs or "").strip()[:200], criado_por])
    return id_


def _linha(df, id_):
    m = df.index[df["ID"] == id_]
    if m.empty:
        raise ValueError("Tarefa não encontrada.")
    return m[0]


def concluir(id_, hoje=None, por: str = ""):
    """Marca como feita e, se ela se repete, já cria a próxima.
    Concluir de novo não faz nada (evita duplicar a repetição num toque duplo)."""
    df = carregar()
    i = _linha(df, id_)
    if df.at[i, "Feito Em"]:
        return
    hoje = pd.Timestamp(hoje or pd.Timestamp(agora())).normalize()
    df.at[i, "Feito Em"] = f"{hoje:%d/%m/%Y}"
    _gravar(df)
    dias = REPETICOES_TAREFA.get(df.at[i, "Repetir"] or "Não", 0)
    if dias:
        base = A._data(df.at[i, "Data"])
        proxima = (hoje if pd.isna(base) else base) + pd.Timedelta(days=dias)
        criar(df.at[i, "Título"], proxima, df.at[i, "Responsável"],
              df.at[i, "Repetir"], df.at[i, "Observações"], por or df.at[i, "Criado Por"])


def excluir(id_):
    df = carregar()
    _gravar(df.drop(index=_linha(df, id_)))


def pendentes(df: pd.DataFrame, hoje=None, limite_dias: int = PROXIMAS_DIAS) -> list[dict]:
    """Tarefas não feitas até daqui a `limite_dias`, das mais atrasadas para a frente.
    Atrasada não some nunca — some só quando alguém marca como feita."""
    hoje = pd.Timestamp(hoje or pd.Timestamp(agora())).normalize()
    out = []
    for _, r in df.iterrows():
        if r["Feito Em"] or not r["ID"]:
            continue
        d = A._data(r["Data"])
        if pd.isna(d):
            continue
        dias = (d.normalize() - hoje).days
        if dias > limite_dias:
            continue
        out.append({"id": r["ID"], "titulo": r["Título"], "data": d.normalize(),
                    "responsavel": r["Responsável"], "repetir": r["Repetir"],
                    "obs": r["Observações"], "dias": dias,
                    "situacao": "atrasada" if dias < 0 else ("hoje" if dias == 0 else "proxima")})
    out.sort(key=lambda t: t["dias"])
    return out
