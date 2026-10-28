# -*- coding: utf-8 -*-
"""Gestão de volumosos (feno, silo, etc) — entrada e consumo."""

from datetime import date, datetime, timedelta
import pandas as pd


def _data(valor):
    """Parse dd/mm/aaaa ou yyyy-mm-dd → date."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if valor is None or str(valor).strip() == "":
        return None
    texto = str(valor).strip()[:10]
    formato = "%Y-%m-%d" if texto[4:5] == "-" else "%d/%m/%Y"
    try:
        return datetime.strptime(texto, formato).date()
    except ValueError:
        return None


def _numero(valor):
    """Parse número (inteiro ou decimal com vírgula)."""
    if isinstance(valor, (int, float)):
        return float(valor)
    if valor is None or str(valor).strip() == "":
        return None
    from extensions import parse_valor
    return parse_valor(valor)


def estoque_por_tipo(df_volumosos):
    """Retorna estoque total por tipo (kg). Agrupa entradas e subtrai consumo."""
    if df_volumosos is None or df_volumosos.empty:
        return {}

    # Colunas esperadas: Data, Tipo, Quantidade, Qualidade, Origem, Custo
    df = df_volumosos.copy()
    df["_data"] = df["Data"].map(_data) if "Data" in df.columns else pd.Series(dtype=object)
    df["_qty"] = df["Quantidade"].map(_numero) if "Quantidade" in df.columns else pd.Series(dtype=float)
    df["_tipo"] = df["Tipo"].astype(str).str.strip() if "Tipo" in df.columns else pd.Series(dtype=str)

    linhas = df[df["_data"].notna() & df["_qty"].notna() & (df["_tipo"] != "")].copy()
    if linhas.empty:
        return {}

    entrada_por_tipo = linhas.groupby("_tipo")["_qty"].sum().to_dict()
    return {k: float(v) for k, v in entrada_por_tipo.items()}


def consumo_periodo(df_consumo, df_volumosos, inicio, fim, tipo=None):
    """Consumo total (kg) num período, opcionalmente filtrado por tipo."""
    if df_consumo is None or df_consumo.empty:
        return 0.0

    df = df_consumo.copy()
    df["_data"] = df["Data"].map(_data) if "Data" in df.columns else pd.Series(dtype=object)
    df["_qty"] = df["Quantidade consumida"].map(_numero) if "Quantidade consumida" in df.columns else pd.Series(dtype=float)
    df["_tipo"] = df["Tipo"].astype(str).str.strip() if "Tipo" in df.columns else pd.Series(dtype=str)

    linhas = df[df["_data"].notna() & df["_qty"].notna() & (df["_tipo"] != "")].copy()

    inicio_d = _data(inicio)
    fim_d = _data(fim)

    if inicio_d:
        linhas = linhas[linhas["_data"] >= inicio_d]
    if fim_d:
        linhas = linhas[linhas["_data"] <= fim_d]

    if tipo:
        linhas = linhas[linhas["_tipo"] == tipo]

    total = float(linhas["_qty"].sum()) if not linhas.empty else 0.0
    return total


def dias_faltam(tipo, hoje=None):
    """Dias até acabar volumoso (baseado em última entrada e consumo médio últimos 7 dias)."""
    from db import carregar_aba

    hoje = _data(hoje) or date.today()
    df_vol = carregar_aba("Volumosos")
    df_cons = carregar_aba("Consumo Volumosos")

    estoque = estoque_por_tipo(df_vol).get(tipo, 0)
    if estoque <= 0:
        return None

    # Consumo médio últimos 7 dias
    inicio_7 = hoje - timedelta(days=7)
    consumo_7 = consumo_periodo(df_cons, df_vol, inicio_7, hoje, tipo=tipo)
    media_dia = consumo_7 / 7.0 if consumo_7 > 0 else 0

    if media_dia <= 0:
        return None  # sem consumo registrado

    dias = int(estoque / media_dia)
    return dias


def situacao_volumosos(hoje=None):
    """Status de todos os volumosos: estoque, dias faltam, alerta."""
    from db import carregar_aba

    hoje = _data(hoje) or date.today()
    df_vol = carregar_aba("Volumosos")

    if df_vol is None or df_vol.empty:
        return {}

    estoque = estoque_por_tipo(df_vol)
    resultado = {}

    for tipo in estoque.keys():
        dias = dias_faltam(tipo, hoje=hoje)
        alerta = "aviso" if dias and dias <= 7 else "ok"

        resultado[tipo] = {
            "kg": estoque[tipo],
            "dias_faltam": dias,
            "alerta": alerta,
        }

    return resultado


def alertas_volumosos(hoje=None):
    """Lista de volumosos com aviso (<=7 dias) para WhatsApp."""
    situacao = situacao_volumosos(hoje=hoje)
    return [
        {"tipo": tipo, "kg": info["kg"], "dias": info["dias_faltam"]}
        for tipo, info in situacao.items()
        if info["alerta"] == "aviso"
    ]
