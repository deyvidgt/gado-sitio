#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cálculos e validações do planejamento de pastagens e financeiro."""

from datetime import date, datetime, timedelta
from uuid import uuid4

import pandas as pd

from config import TIPOS_GASTO

CATEGORIAS_ORCAMENTO = [
    ("Despesa", "Compra de gado"),
    *(("Despesa", tipo) for tipo in TIPOS_GASTO),
    ("Receita", "Venda de gado"),
]
TIPOS_INSUMO_PASTO = ("Calcário", "Ureia", "Superfosfato", "Defensivo", "Outro")
UNIDADES_INSUMO = ("kg", "t", "L", "mL", "saco", "dose")


def novo_id(prefixo):
    return f"{prefixo}-{uuid4().hex[:12].upper()}"


def normalizar_data(valor):
    if isinstance(valor, (datetime, date, pd.Timestamp)):
        return pd.Timestamp(valor).normalize()
    texto = str(valor or "").strip()
    if not texto:
        return pd.NaT
    return pd.to_datetime(texto, dayfirst=not (len(texto) >= 10 and texto[4:5] == "-"),
                          errors="coerce")


def _numero(valor):
    try:
        if pd.isna(valor):
            return 0.0
        if isinstance(valor, str):
            texto = valor.strip().replace("R$", "").replace(" ", "")
            if "," in texto and "." in texto:
                texto = texto.replace(".", "").replace(",", ".")
            elif "," in texto:
                texto = texto.replace(",", ".")
            valor = texto
        numero = float(valor)
        return numero if numero == numero else 0.0
    except (TypeError, ValueError):
        return 0.0


def listar_aplicacoes(df_aplicacoes, df_pastos):
    """Enriquece aplicações com nome, área atual e custo por hectare."""
    if df_aplicacoes.empty:
        return []
    pastos = {}
    if not df_pastos.empty:
        pastos = {
            str(r.get("ID")): {
                "nome": str(r.get("Nome") or r.get("ID")),
                "area": _numero(r.get("Área (ha)")),
            }
            for _, r in df_pastos.iterrows()
        }
    linhas = []
    for _, row in df_aplicacoes.iterrows():
        item = row.to_dict()
        pasto_id = str(item.get("Pasto ID") or "")
        pasto = pastos.get(pasto_id, {})
        area = pasto.get("area", 0.0)
        custo = _numero(item.get("Custo Total (R$)"))
        dt = normalizar_data(item.get("Data"))
        item["Data exibida"] = dt.strftime("%d/%m/%Y") if not pd.isna(dt) else ""
        item["Pasto Nome"] = pasto.get("nome", pasto_id or "Pasto removido")
        item["Área (ha)"] = area
        item["Custo/ha (R$)"] = round(custo / area, 2) if area > 0 else None
        linhas.append(item)
    linhas.sort(key=lambda i: normalizar_data(i.get("Data")) if not pd.isna(normalizar_data(i.get("Data"))) else pd.Timestamp.min,
                reverse=True)
    return linhas


def comparar_orcamento(df_orcamento, df_compras, df_gastos, df_vendas, ano):
    """Compara orçamento e registros reais por mês, tipo e categoria."""
    previstos = {}
    if not df_orcamento.empty:
        for _, row in df_orcamento.iterrows():
            mes = str(row.get("Mês") or "").strip()[:7]
            if len(mes) != 7 or not mes[:4].isdigit() or not mes[5:7].isdigit():
                continue
            if int(mes[:4]) != ano:
                continue
            chave = (mes, str(row.get("Tipo") or ""), str(row.get("Categoria") or ""))
            previstos[chave] = previstos.get(chave, 0.0) + _numero(row.get("Valor Previsto (R$)"))

    realizados = {}

    def acumular(df, tipo, categoria_col, categoria_fixa=None):
        if df.empty or "Data" not in df.columns or "Valor Total (R$)" not in df.columns:
            return
        for _, row in df.iterrows():
            dt = normalizar_data(row.get("Data"))
            if pd.isna(dt) or dt.year != ano:
                continue
            categoria = categoria_fixa or str(row.get(categoria_col) or "").strip()
            if not categoria:
                continue
            chave = (dt.strftime("%Y-%m"), tipo, categoria)
            realizados[chave] = realizados.get(chave, 0.0) + _numero(row.get("Valor Total (R$)"))

    acumular(df_compras, "Despesa", None, "Compra de gado")
    acumular(df_gastos, "Despesa", "Tipo")
    acumular(df_vendas, "Receita", None, "Venda de gado")

    linhas = []
    for mes, tipo, categoria in sorted(set(previstos) | set(realizados)):
        previsto = round(previstos.get((mes, tipo, categoria), 0.0), 2)
        realizado = round(realizados.get((mes, tipo, categoria), 0.0), 2)
        linhas.append({
            "mes": mes,
            "tipo": tipo,
            "categoria": categoria,
            "previsto": previsto,
            "realizado": realizado,
            "diferenca": round(realizado - previsto, 2),
        })
    linhas.sort(key=lambda item: (item["mes"], item["tipo"], item["categoria"]))
    return linhas


def contas_proximas(df_contas, hoje, dias=7):
    """Contas vencidas e as que vencem até N dias, ainda não liquidadas."""
    if df_contas.empty:
        return []
    inicio = pd.Timestamp(hoje).normalize()
    fim = inicio + timedelta(days=dias)
    contas = []
    for _, row in df_contas.iterrows():
        status = str(row.get("Status") or "Pendente").strip().casefold()
        if status != "pendente":
            continue
        vencimento = normalizar_data(row.get("Data Vencimento"))
        if pd.isna(vencimento) or vencimento > fim:
            continue
        item = row.to_dict()
        item["vencimento_dt"] = vencimento
        item["vencimento_exibido"] = vencimento.strftime("%d/%m/%Y")
        item["atrasada"] = vencimento < inicio
        contas.append(item)
    return sorted(contas, key=lambda item: item["vencimento_dt"])
