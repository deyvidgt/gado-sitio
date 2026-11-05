# -*- coding: utf-8 -*-
"""Medições de altura e estimativa simplificada de matéria seca por pasto."""
from datetime import date, datetime
import math
import uuid

import pandas as pd

import db
import pastos
from config import COLUNAS_PASTOS_MEDICOES

ABA = "Pastos Medições"
COEFICIENTE_PADRAO = 250.0


def _data(valor) -> date | None:
    if isinstance(valor, (datetime, date)):
        return valor.date() if isinstance(valor, datetime) else valor
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        if len(texto) >= 10 and texto[4:5] == "-":
            return datetime.strptime(texto[:10], "%Y-%m-%d").date()
        return datetime.strptime(texto[:10], "%d/%m/%Y").date()
    except ValueError:
        return None


def carregar() -> pd.DataFrame:
    df = db.carregar_aba(ABA)
    for coluna in COLUNAS_PASTOS_MEDICOES:
        if coluna not in df.columns:
            df[coluna] = None
    return df[COLUNAS_PASTOS_MEDICOES].copy().reset_index(drop=True)


def coeficientes_atuais() -> dict[str, float]:
    df = carregar()
    saida = {}
    if df.empty:
        return saida
    for _, row in df.iterrows():
        pasto_id = str(row.get("Pasto ID") or "").strip()
        coef = pd.to_numeric(row.get("Coeficiente MS (kg/ha/cm)"), errors="coerce")
        if pasto_id and pd.notna(coef) and coef > 0:
            saida[pasto_id] = float(coef)
    return saida


def registrar(pasto_id, data, altura, coeficiente, observacoes="", responsavel="") -> dict:
    data_medicao = _data(data)
    try:
        altura_cm = float(str(altura).replace(",", "."))
        coef = float(str(coeficiente).replace(",", "."))
    except (TypeError, ValueError):
        raise ValueError("Informe altura e coeficiente numéricos.")
    if data_medicao is None:
        raise ValueError("Informe uma data válida.")
    if not math.isfinite(altura_cm) or not 1 <= altura_cm <= 300:
        raise ValueError("A altura deve estar entre 1 e 300 cm.")
    if not math.isfinite(coef) or not 1 <= coef <= 10000:
        raise ValueError("O coeficiente deve estar entre 1 e 10.000 kg MS/ha por cm.")
    pastos_ativos = pastos.ativos(pastos.carregar())
    if str(pasto_id or "").strip() not in set(pastos_ativos["ID"].astype(str)):
        raise ValueError("Selecione um pasto ativo.")
    ms_estimado = round(altura_cm * coef, 1)
    db.salvar_linha(ABA, [
        uuid.uuid4().hex[:12].upper(), data_medicao.strftime("%d/%m/%Y"),
        str(pasto_id).strip(), altura_cm, coef, ms_estimado,
        str(observacoes or "").strip()[:300], str(responsavel or "").strip(),
    ])
    return {"altura_cm": altura_cm, "coeficiente": coef, "ms_kg_ha": ms_estimado}
