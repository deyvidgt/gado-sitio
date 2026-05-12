#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor de cálculos financeiros do rebanho
Versão 3.1 — correções de bugs e melhorias de desempenho

Conceitos implementados:
─────────────────────────────────────────────────────────────────────
CMP  — Custo Médio Ponderado por cabeça
       = Σ(valor_compra_i) / Σ(qtd_compra_i)
       Reflete o custo real de cada cabeça considerando todas as
       compras em momentos e preços diferentes.

GPCab — Gasto acumulado por cabeça
       = Σ(valor_gasto_i / estoque_no_momento_do_gasto_i)
       Cada despesa é dividida pelo número de cabeças do rebanho
       no momento em que ocorreu, dando o custo real por cabeça.

       NOTA: quando o gasto foi importado com Qtd Cabeças = 0
       e Valor/Cabeça = 0, o estoque é recalculado automaticamente
       a partir das compras/vendas até aquela data.

CTCab — Custo Total por cabeça
       = CMP + GPCab

Resultado por membro (na hora da venda):
       receita        = valor recebido pelo membro
       custo_compra   = qtd_membro × CMP_no_momento_da_venda
       custo_gastos   = qtd_membro × GPCab_acumulado_até_a_venda
       resultado      = receita − custo_compra − custo_gastos
       margem         = resultado / receita × 100

Custo histórico das vendas:
       Para cada venda, usa o CMP e GPCab válidos naquela data,
       não o valor atual — garantindo precisão temporal.

Estoque em valor (a preço de custo):
       = estoque_atual × CTCab_atual

Break-even de mercado:
       = capital_imobilizado / estoque_atual
       Preço mínimo por cabeça para recuperar todo o capital ainda
       imobilizado no rebanho.

MELHORIAS v3.1:
  • Timelines pré-computadas de CMP e GPCab → consultas O(log n)
    em vez de O(n²) nas funções de custo histórico/por membro
  • Bug corrigido: calcular_estoque_por_membro — vendas importadas
    com Qtd Mae/Deyvid/Nilson = 0 agora caem no fallback de terços,
    evitando sobresaldo fantasma de estoque por membro
  • Funções novas: calcular_indicadores_extras (TMP, custo/dia,
    arrobas mínimas), calcular_evolucao_cmp, calcular_gasto_por_tipo
─────────────────────────────────────────────────────────────────────
"""

import bisect
import numpy as np
import pandas as pd
from datetime import datetime
from config import MEMBROS


# ── Estoque global ────────────────────────────────────────────────────────────

def calcular_estoque(df_comp: pd.DataFrame, df_vend: pd.DataFrame,
                     df_man: pd.DataFrame) -> int:
    comp        = int(df_comp["Qtd Cabeças"].sum()) if not df_comp.empty else 0
    vend        = int(df_vend["Qtd Cabeças"].sum()) if not df_vend.empty else 0
    mortes      = 0
    nascimentos = 0
    if not df_man.empty and "Tipo" in df_man.columns:
        mortes      = int(df_man[df_man["Tipo"] == "Morte/Perda"]["Qtd Cabeças"].sum())
        nascimentos = int(df_man[df_man["Tipo"] == "Nascimento"]["Qtd Cabeças"].sum())
    return max(0, comp - vend - mortes + nascimentos)


def calcular_estoque_ate_data(df_comp: pd.DataFrame, df_vend: pd.DataFrame,
                               df_man: pd.DataFrame,
                               data_corte: pd.Timestamp) -> int:
    """
    Estoque de cabeças existente até (e incluindo) uma determinada data.
    Considera compras, vendas, mortes e nascimentos ocorridos até essa data.
    """
    comp = 0
    if not df_comp.empty and "Data" in df_comp.columns:
        mask = df_comp["Data"].notna() & (df_comp["Data"] <= data_corte)
        comp = int(df_comp.loc[mask, "Qtd Cabeças"].sum())

    vend = 0
    if not df_vend.empty and "Data" in df_vend.columns:
        mask = df_vend["Data"].notna() & (df_vend["Data"] <= data_corte)
        vend = int(df_vend.loc[mask, "Qtd Cabeças"].sum())

    mortes = nascimentos = 0
    if not df_man.empty and "Tipo" in df_man.columns and "Data" in df_man.columns:
        mask  = df_man["Data"].notna() & (df_man["Data"] <= data_corte)
        df_m  = df_man.loc[mask]
        mortes      = int(df_m[df_m["Tipo"] == "Morte/Perda"]["Qtd Cabeças"].sum())
        nascimentos = int(df_m[df_m["Tipo"] == "Nascimento"]["Qtd Cabeças"].sum())

    return max(0, comp - vend - mortes + nascimentos)


# ── CMP — Custo Médio Ponderado ───────────────────────────────────────────────

def calcular_cmp(df_comp: pd.DataFrame) -> float:
    """
    Custo Médio Ponderado por cabeça considerando todas as compras.
    Exemplo: compra 10 cab a R$1.000 e depois 5 cab a R$1.500
             CMP = (10.000 + 7.500) / 15 = R$1.166,67 por cabeça
    """
    if df_comp.empty:
        return 0.0
    total_val = df_comp["Valor Total (R$)"].sum()
    total_cab = df_comp["Qtd Cabeças"].sum()
    return float(total_val / total_cab) if total_cab > 0 else 0.0


def calcular_cmp_ate_data(df_comp: pd.DataFrame, data_corte: pd.Timestamp) -> float:
    """CMP considerando apenas compras até determinada data."""
    if df_comp.empty:
        return 0.0
    mask = df_comp["Data"].notna() & (df_comp["Data"] <= data_corte)
    df = df_comp[mask]
    if df.empty:
        return 0.0
    total_cab = df["Qtd Cabeças"].sum()
    return float(df["Valor Total (R$)"].sum() / total_cab) if total_cab > 0 else 0.0


# ── Timelines pré-computadas para consultas O(log n) ─────────────────────────

def _build_cmp_timeline(df_comp: pd.DataFrame):
    """
    Pré-computa o CMP cumulativo em cada data de compra.

    Retorna: (datas_sorted, cmp_values) — arrays numpy ordenados por data.
    A consulta `CMP até data D` é feita com bisect em O(log n).
    """
    if df_comp.empty:
        return np.array([], dtype="datetime64[ns]"), np.array([], dtype=float)

    df = df_comp[df_comp["Data"].notna()].sort_values("Data").copy()
    if df.empty:
        return np.array([], dtype="datetime64[ns]"), np.array([], dtype=float)

    cum_val = df["Valor Total (R$)"].cumsum().values.astype(float)
    cum_cab = df["Qtd Cabeças"].cumsum().values.astype(float)
    cmp_vals = np.where(cum_cab > 0, cum_val / cum_cab, 0.0)
    datas    = df["Data"].values  # numpy datetime64

    return datas, cmp_vals


def _query_cmp_timeline(datas: np.ndarray, cmp_vals: np.ndarray,
                        data_corte: pd.Timestamp) -> float:
    """CMP até data_corte usando busca binária na timeline pré-computada."""
    if len(datas) == 0:
        return 0.0
    ts = np.datetime64(data_corte, "ns")
    idx = bisect.bisect_right(datas, ts) - 1
    return float(cmp_vals[idx]) if idx >= 0 else 0.0


def _build_gpcab_timeline(df_gast: pd.DataFrame,
                           df_comp: pd.DataFrame | None = None,
                           df_vend: pd.DataFrame | None = None,
                           df_man:  pd.DataFrame | None = None):
    """
    Pré-computa o incremento de GPCab de cada gasto, ordenado por data.
    O incremento de cada gasto é: val / estoque_na_data_do_gasto.
    Como é um valor fixo por gasto, a soma acumulada permite queries
    O(log n) via busca binária, em vez de O(n) por consulta.

    Retorna: (datas_sorted, gpcab_cumsum) — arrays numpy ordenados por data.

    NOTA: gastos sem data ficam no final do array (posição NaT → max date).
    """
    if df_gast.empty:
        return np.array([], dtype="datetime64[ns]"), np.array([], dtype=float)

    _df_vend = df_vend if (df_vend is not None and not df_vend.empty) else pd.DataFrame()
    _df_man  = df_man  if (df_man  is not None and not df_man.empty)  else pd.DataFrame()
    total_cab_comp = (
        max(1, int(df_comp["Qtd Cabeças"].sum()))
        if df_comp is not None and not df_comp.empty
        else 1
    )

    incrementos = []
    datas_list  = []

    df_sorted = df_gast.sort_values("Data", na_position="last")
    for _, row in df_sorted.iterrows():
        val  = float(row.get("Valor Total (R$)", 0) or 0)
        vcab = float(row.get("Valor/Cabeça (R$)", 0) or 0)
        qtd  = float(row.get("Qtd Cabeças",      0) or 0)
        data = row.get("Data")

        if vcab > 0:
            inc = vcab
        elif qtd > 0:
            inc = val / qtd
        elif val > 0 and df_comp is not None and not df_comp.empty:
            est = (calcular_estoque_ate_data(df_comp, _df_vend, _df_man, data)
                   if pd.notna(data)
                   else calcular_estoque(df_comp, _df_vend, _df_man))
            if est <= 0:
                est = total_cab_comp
            inc = val / est
        else:
            inc = 0.0

        # Gastos sem data são colocados no fim com timestamp sentinela
        ts = data if pd.notna(data) else pd.Timestamp.max
        datas_list.append(np.datetime64(ts, "ns"))
        incrementos.append(inc)

    datas_np = np.array(datas_list, dtype="datetime64[ns]")
    incs_np  = np.array(incrementos, dtype=float)

    # Garantir ordenação (df_sorted já ordena, mas reforçamos)
    ordem = np.argsort(datas_np, kind="stable")
    datas_np = datas_np[ordem]
    incs_np  = incs_np[ordem]

    gpcab_cumsum = np.cumsum(incs_np)
    return datas_np, gpcab_cumsum


def _query_gpcab_timeline(datas: np.ndarray, gpcab_cumsum: np.ndarray,
                           data_corte: pd.Timestamp) -> float:
    """GPCab até data_corte usando busca binária na timeline pré-computada."""
    if len(datas) == 0:
        return 0.0
    ts = np.datetime64(data_corte, "ns")
    idx = bisect.bisect_right(datas, ts) - 1
    return float(gpcab_cumsum[idx]) if idx >= 0 else 0.0


# ── GPCab — Gasto acumulado por cabeça ───────────────────────────────────────

def calcular_gpcab(df_gast: pd.DataFrame,
                   df_comp: pd.DataFrame | None = None,
                   df_vend: pd.DataFrame | None = None,
                   df_man:  pd.DataFrame | None = None) -> float:
    """
    Gasto acumulado por cabeça (total de todo o período).

    Para cada linha de gasto:
    - Se Valor/Cabeça (R$) > 0: usa diretamente (já calculado na inserção).
    - Se Qtd Cabeças > 0 e Valor/Cabeça = 0: recalcula = Valor Total / Qtd.
    - Se ambos = 0 (dados importados sem referência): usa o estoque do rebanho
      na data do gasto, obtido a partir de df_comp/df_vend/df_man.

    BUG CORRIGIDO: dados importados chegavam com Qtd Cabeças = 0 e
    Valor/Cabeça = 0, fazendo GPCab = 0 e distorcendo todos os cálculos.
    """
    # Reutiliza a timeline: soma total = último valor do cumsum
    _, gpcab_cs = _build_gpcab_timeline(df_gast, df_comp, df_vend, df_man)
    return float(gpcab_cs[-1]) if len(gpcab_cs) > 0 else 0.0


def calcular_gpcab_ate_data(df_gast: pd.DataFrame, data_corte: pd.Timestamp,
                             df_comp: pd.DataFrame | None = None,
                             df_vend: pd.DataFrame | None = None,
                             df_man:  pd.DataFrame | None = None) -> float:
    """GPCab acumulado até uma data específica (consulta O(log n))."""
    if df_gast.empty:
        return 0.0
    datas, cs = _build_gpcab_timeline(df_gast, df_comp, df_vend, df_man)
    return _query_gpcab_timeline(datas, cs, data_corte)


# ── Enriquecimento de gastos ──────────────────────────────────────────────────

def enriquecer_gastos(df_gast: pd.DataFrame,
                      df_comp: pd.DataFrame,
                      df_vend: pd.DataFrame | None = None,
                      df_man:  pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Preenche Qtd Cabeças e Valor/Cabeça (R$) para registros importados com zeros.
    Retorna uma CÓPIA do DataFrame — não modifica o original.

    Útil tanto para exibição (mostrando o custo por cabeça real) quanto para
    salvar a correção definitiva no arquivo Excel.
    """
    if df_gast.empty or df_comp is None or df_comp.empty:
        return df_gast.copy()

    _df_vend = df_vend if (df_vend is not None and not df_vend.empty) else pd.DataFrame()
    _df_man  = df_man  if (df_man  is not None and not df_man.empty)  else pd.DataFrame()
    total_cab_comp = max(1, int(df_comp["Qtd Cabeças"].sum()))

    df = df_gast.copy()
    # Garantir que colunas numéricas aceitem float (importação pode deixá-las como int64)
    for col in ["Qtd Cabeças", "Valor/Cabeça (R$)"]:
        if col in df.columns:
            df[col] = df[col].astype(float)

    for idx, row in df.iterrows():
        vcab = float(row.get("Valor/Cabeça (R$)", 0) or 0)
        qtd  = float(row.get("Qtd Cabeças",      0) or 0)
        if vcab == 0 and qtd == 0:
            val = float(row.get("Valor Total (R$)", 0) or 0)
            if val > 0:
                data = row.get("Data")
                est  = (calcular_estoque_ate_data(df_comp, _df_vend, _df_man, data)
                        if pd.notna(data)
                        else calcular_estoque(df_comp, _df_vend, _df_man))
                if est <= 0:
                    est = total_cab_comp
                df.at[idx, "Qtd Cabeças"]        = float(est)
                df.at[idx, "Valor/Cabeça (R$)"]  = round(val / est, 4)
    return df


# ── CTCab — Custo Total por cabeça ───────────────────────────────────────────

def calcular_ctcab(df_comp: pd.DataFrame, df_gast: pd.DataFrame,
                   df_vend: pd.DataFrame | None = None,
                   df_man:  pd.DataFrame | None = None) -> float:
    """Custo Total por cabeça = CMP + GPCab."""
    return calcular_cmp(df_comp) + calcular_gpcab(df_gast, df_comp, df_vend, df_man)


# ── Custo histórico das vendas ────────────────────────────────────────────────

def _calcular_custo_historico_vendas(df_vend: pd.DataFrame, df_comp: pd.DataFrame,
                                      df_gast: pd.DataFrame,
                                      df_man:  pd.DataFrame | None = None) -> float:
    """
    Custo total das cabeças vendidas, usando o CMP e GPCab válidos
    no MOMENTO de cada venda (não o valor atual global).

    MELHORIA v3.1: timelines pré-computadas → O(n log n) em vez de O(n²).
    Antes, para cada venda recomputava toda a série de GPCab desde o início.
    Agora, cada consulta é uma busca binária O(log n).
    """
    if df_vend.empty or df_comp.empty:
        return 0.0

    _df_man = df_man if (df_man is not None and not df_man.empty) else pd.DataFrame()

    # Pré-computar timelines uma única vez
    cmp_datas, cmp_vals   = _build_cmp_timeline(df_comp)
    gpcab_datas, gpcab_cs = _build_gpcab_timeline(df_gast, df_comp, df_vend, _df_man)

    total = 0.0
    for _, venda in df_vend.iterrows():
        qtd = int(venda.get("Qtd Cabeças", 0) or 0)
        if qtd <= 0:
            continue
        data_v = venda.get("Data")
        if pd.isna(data_v):
            cmp_v   = calcular_cmp(df_comp)
            gpcab_v = float(gpcab_cs[-1]) if len(gpcab_cs) > 0 else 0.0
        else:
            cmp_v   = _query_cmp_timeline(cmp_datas, cmp_vals, data_v)
            gpcab_v = _query_gpcab_timeline(gpcab_datas, gpcab_cs, data_v)
        total += qtd * (cmp_v + gpcab_v)
    return total


# ── Resultado por membro ──────────────────────────────────────────────────────

def calcular_resultado_membro(membro: str, df_vend: pd.DataFrame,
                               df_comp: pd.DataFrame, df_gast: pd.DataFrame,
                               df_man: pd.DataFrame | None = None) -> dict:
    """
    Resultado líquido de um membro usando CMP e GPCab históricos.

    O custo de cada cabeça vendida pelo membro é calculado usando o
    CMP e GPCab vigentes NA DATA da venda, não o valor atual.
    Isso garante precisão mesmo quando os preços variaram ao longo do tempo.

    MELHORIA v3.1: timelines pré-computadas → O(n log n) em vez de O(n²).
    """
    col_qtd = f"Qtd {membro}"
    col_val = f"Valor {membro} (R$)"

    resultado = {
        "membro":            membro,
        "cabecas":           0,
        "receita":           0.0,
        "custo_compra":      0.0,
        "custo_gastos":      0.0,
        "custo_total":       0.0,
        "resultado":         0.0,
        "margem_pct":        0.0,
        "ticket_medio":      0.0,
        "custo_medio_cab":   0.0,
        "vendas_detalhadas": [],
    }

    if df_vend.empty or col_qtd not in df_vend.columns:
        return resultado

    _df_man = df_man if (df_man is not None and not df_man.empty) else pd.DataFrame()

    # Pré-computar timelines uma única vez
    cmp_datas, cmp_vals   = _build_cmp_timeline(df_comp)
    gpcab_datas, gpcab_cs = _build_gpcab_timeline(df_gast, df_comp, df_vend, _df_man)

    cmp_global   = calcular_cmp(df_comp)
    gpcab_global = float(gpcab_cs[-1]) if len(gpcab_cs) > 0 else 0.0

    for _, venda in df_vend.iterrows():
        qtd_m = int(venda.get(col_qtd, 0) or 0)
        val_m = float(venda.get(col_val, 0) or 0)
        if qtd_m <= 0:
            continue

        data_v = venda.get("Data")
        if pd.isna(data_v):
            cmp_v   = cmp_global
            gpcab_v = gpcab_global
        else:
            cmp_v   = _query_cmp_timeline(cmp_datas, cmp_vals, data_v)
            gpcab_v = _query_gpcab_timeline(gpcab_datas, gpcab_cs, data_v)

        custo_comp_m  = qtd_m * cmp_v
        custo_gast_m  = qtd_m * gpcab_v
        custo_total_m = custo_comp_m + custo_gast_m
        resultado_m   = val_m - custo_total_m
        margem_m      = (resultado_m / val_m * 100) if val_m > 0 else 0.0

        resultado["cabecas"]      += qtd_m
        resultado["receita"]      += val_m
        resultado["custo_compra"] += custo_comp_m
        resultado["custo_gastos"] += custo_gast_m

        data_str = data_v.strftime("%d/%m/%Y") if pd.notna(data_v) else "?"
        resultado["vendas_detalhadas"].append({
            "data":       data_str,
            "cabecas":    qtd_m,
            "receita":    val_m,
            "cmp":        cmp_v,
            "gpcab":      gpcab_v,
            "custo_comp": custo_comp_m,
            "custo_gast": custo_gast_m,
            "resultado":  resultado_m,
            "margem_pct": margem_m,
        })

    resultado["custo_total"]     = resultado["custo_compra"] + resultado["custo_gastos"]
    resultado["resultado"]       = resultado["receita"] - resultado["custo_total"]
    resultado["margem_pct"]      = (resultado["resultado"] / resultado["receita"] * 100
                                    if resultado["receita"] > 0 else 0.0)
    resultado["ticket_medio"]    = (resultado["receita"] / resultado["cabecas"]
                                    if resultado["cabecas"] > 0 else 0.0)
    resultado["custo_medio_cab"] = (resultado["custo_total"] / resultado["cabecas"]
                                    if resultado["cabecas"] > 0 else 0.0)
    return resultado


def calcular_todos_membros(df_vend, df_comp, df_gast,
                            df_man: pd.DataFrame | None = None) -> dict:
    return {m: calcular_resultado_membro(m, df_vend, df_comp, df_gast, df_man)
            for m in MEMBROS}


# ── Resumo financeiro global ──────────────────────────────────────────────────

def calcular_resumo_financeiro(df_comp, df_gast, df_vend, df_man) -> dict:
    estoque = calcular_estoque(df_comp, df_vend, df_man)

    # Indicadores com GPCab corrigido (passa contexto completo)
    cmp   = calcular_cmp(df_comp)
    gpcab = calcular_gpcab(df_gast, df_comp, df_vend, df_man)
    ctcab = cmp + gpcab

    total_comp  = float(df_comp["Valor Total (R$)"].sum()) if not df_comp.empty else 0.0
    total_gast  = float(df_gast["Valor Total (R$)"].sum()) if not df_gast.empty else 0.0
    total_vend  = float(df_vend["Valor Total (R$)"].sum()) if not df_vend.empty else 0.0
    total_custo = total_comp + total_gast

    cab_comp = int(df_comp["Qtd Cabeças"].sum()) if not df_comp.empty else 0
    cab_vend = int(df_vend["Qtd Cabeças"].sum()) if not df_vend.empty else 0

    # Custo das cabeças vendidas usando CMP+GPCab no MOMENTO de cada venda
    # (mais preciso que cab_vend × ctcab_atual)
    custo_vendidos = _calcular_custo_historico_vendas(df_vend, df_comp, df_gast, df_man)

    # Capital ainda imobilizado no rebanho (a preço de custo atual)
    capital_imobilizado = estoque * ctcab

    # Resultado realizado = receita − custo das cabeças vendidas
    resultado_realizado = total_vend - custo_vendidos

    # Resultado total = realizado + valor de mercado do estoque − investimento não vendido
    # = total_vend + capital_imobilizado − total_custo
    resultado_total = total_vend + capital_imobilizado - total_custo

    roi_realizado = (resultado_realizado / custo_vendidos * 100
                     if custo_vendidos > 0 else 0.0)
    roi_total     = (resultado_total / total_custo * 100
                     if total_custo > 0 else 0.0)

    # Break-even: preço mínimo por cabeça para recuperar capital restante
    break_even = capital_imobilizado / estoque if estoque > 0 else 0.0

    # Ticket médio de venda
    ticket_medio = total_vend / cab_vend if cab_vend > 0 else 0.0

    # Margem bruta das vendas realizadas
    margem_bruta = (resultado_realizado / total_vend * 100
                    if total_vend > 0 else 0.0)

    return {
        # Estoque
        "estoque":              estoque,
        "cab_comp":             cab_comp,
        "cab_vend":             cab_vend,
        # Indicadores de custo
        "cmp":                  cmp,
        "gpcab":                gpcab,
        "ctcab":                ctcab,
        # Financeiro
        "total_comp":           total_comp,
        "total_gast":           total_gast,
        "total_custo":          total_custo,
        "total_vend":           total_vend,
        "capital_imobilizado":  capital_imobilizado,
        "custo_vendidos":       custo_vendidos,
        # Resultados
        "resultado_realizado":  resultado_realizado,
        "resultado_total":      resultado_total,
        "roi_realizado":        roi_realizado,
        "roi_total":            roi_total,
        "break_even":           break_even,
        "ticket_medio":         ticket_medio,
        "margem_bruta":         margem_bruta,
    }


# ── Estimativa de valor do rebanho ───────────────────────────────────────────

def estimar_rebanho_arroba(estoque: int, peso_kg: float,
                            preco_arroba: float,
                            ctcab: float) -> dict:
    """Estima o valor do rebanho pelo preço da arroba."""
    if peso_kg <= 0 or preco_arroba <= 0:
        return {"arrobas_cab": 0, "valor_cab": 0, "valor_total": 0,
                "capital_imob": ctcab * estoque, "lucro_pot": 0, "margem_pot": 0}
    arrobas_cab  = peso_kg / 15.0
    valor_cab    = arrobas_cab * preco_arroba
    valor_total  = valor_cab * estoque
    capital_imob = ctcab * estoque
    lucro_pot    = valor_total - capital_imob
    return {
        "arrobas_cab":  arrobas_cab,
        "valor_cab":    valor_cab,
        "valor_total":  valor_total,
        "capital_imob": capital_imob,
        "lucro_pot":    lucro_pot,
        "margem_pot":   (lucro_pot / valor_total * 100) if valor_total > 0 else 0.0,
    }


def estimar_rebanho_preco_cab(estoque: int, preco_cab: float,
                               ctcab: float) -> dict:
    """Estima o valor do rebanho por preço à vista por cabeça."""
    valor_total  = preco_cab * estoque
    capital_imob = ctcab * estoque
    lucro_pot    = valor_total - capital_imob
    return {
        "valor_total":  valor_total,
        "capital_imob": capital_imob,
        "lucro_pot":    lucro_pot,
        "margem_pot":   (lucro_pot / valor_total * 100) if valor_total > 0 else 0.0,
    }


# ── Estoque por membro ────────────────────────────────────────────────────────

def calcular_estoque_por_membro(df_comp: pd.DataFrame, df_vend: pd.DataFrame,
                                 df_man: pd.DataFrame) -> dict:
    """
    Estoque atual de cabeças por membro.

    Compras: se tiver colunas Qtd Mae/Deyvid/Nilson usa elas;
             senão divide igualmente (arredondando o resto para Nilson).
    Vendas:  subtrai o que cada um já vendeu.
             BUG CORRIGIDO v3.1: vendas importadas com Qtd Mae/Deyvid/Nilson = 0
             (soma zero) agora caem no fallback de terços, evitando sobresaldo
             fantasma de estoque para todos os membros.
    Manejo:  mortes e nascimentos tratados separadamente por terços.
    """
    resultado = {m: 0 for m in ["Mae", "Deyvid", "Nilson"]}

    # Compras
    if not df_comp.empty:
        for _, row in df_comp.iterrows():
            total = int(row.get("Qtd Cabeças", 0) or 0)
            mae    = int(row.get("Qtd Mae",    0) or 0)
            deyvid = int(row.get("Qtd Deyvid", 0) or 0)
            nilson = int(row.get("Qtd Nilson", 0) or 0)
            if "Qtd Mae" in row and pd.notna(row.get("Qtd Mae")) and (mae + deyvid + nilson) > 0:
                resultado["Mae"]    += mae
                resultado["Deyvid"] += deyvid
                resultado["Nilson"] += nilson
            else:
                # Fallback: divisão em terços (resto vai para Nilson)
                base  = total // 3
                resto = total - base * 3
                resultado["Mae"]    += base
                resultado["Deyvid"] += base
                resultado["Nilson"] += base + resto

    # Vendas (subtrair)
    # BUG CORRIGIDO: registros importados com soma zero agora usam fallback de terços
    if not df_vend.empty:
        for _, row in df_vend.iterrows():
            total  = int(row.get("Qtd Cabeças", 0) or 0)
            mae    = int(row.get("Qtd Mae",    0) or 0)
            deyvid = int(row.get("Qtd Deyvid", 0) or 0)
            nilson = int(row.get("Qtd Nilson", 0) or 0)
            soma   = mae + deyvid + nilson

            if soma > 0:
                # Dados individuais presentes
                resultado["Mae"]    -= mae
                resultado["Deyvid"] -= deyvid
                resultado["Nilson"] -= nilson
            elif total > 0:
                # Sem dados individuais: fallback proporcional por terços
                base  = total // 3
                resto = total - base * 3
                resultado["Mae"]    -= base
                resultado["Deyvid"] -= base
                resultado["Nilson"] -= base + resto
            # se total == 0, ignora

    # Manejo: mortes e nascimentos tratados SEPARADAMENTE
    if not df_man.empty and "Tipo" in df_man.columns:
        mortes      = int(df_man[df_man["Tipo"] == "Morte/Perda"]["Qtd Cabeças"].sum())
        nascimentos = int(df_man[df_man["Tipo"] == "Nascimento"]["Qtd Cabeças"].sum())

        # Distribuir mortes em terços
        base_m  = mortes // 3
        resto_m = mortes - base_m * 3
        resultado["Mae"]    -= base_m
        resultado["Deyvid"] -= base_m
        resultado["Nilson"] -= base_m + resto_m

        # Distribuir nascimentos em terços
        base_n  = nascimentos // 3
        resto_n = nascimentos - base_n * 3
        resultado["Mae"]    += base_n
        resultado["Deyvid"] += base_n
        resultado["Nilson"] += base_n + resto_n

    # Garantir que nenhum membro fique com estoque negativo
    for m in resultado:
        resultado[m] = max(0, resultado[m])

    return resultado


# ── Fluxo de caixa mensal ────────────────────────────────────────────────────

def calcular_fluxo_caixa(df_comp, df_gast, df_vend) -> pd.DataFrame:
    """
    Consolida todas as movimentações financeiras mês a mês.
    Saídas = compras + gastos (valores negativos)
    Entradas = vendas (valores positivos)
    """
    registros = []

    for _, r in df_comp.iterrows():
        if pd.notna(r.get("Data")):
            registros.append({
                "Data":      r["Data"],
                "Tipo":      "Compra",
                "Valor":     -float(r.get("Valor Total (R$)", 0) or 0),
                "Descrição": r.get("Descrição", ""),
            })

    for _, r in df_gast.iterrows():
        if pd.notna(r.get("Data")):
            registros.append({
                "Data":      r["Data"],
                "Tipo":      "Gasto",
                "Valor":     -float(r.get("Valor Total (R$)", 0) or 0),
                "Descrição": r.get("Descrição", ""),
            })

    for _, r in df_vend.iterrows():
        if pd.notna(r.get("Data")):
            registros.append({
                "Data":      r["Data"],
                "Tipo":      "Venda",
                "Valor":     float(r.get("Valor Total (R$)", 0) or 0),
                "Descrição": r.get("Descrição", ""),
            })

    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros).sort_values("Data")
    df["AnoMes"] = df["Data"].dt.to_period("M")

    mensal = (df.groupby("AnoMes")
                .agg(
                    Entradas=("Valor", lambda x: x[x > 0].sum()),
                    Saidas  =("Valor", lambda x: x[x < 0].sum()),
                    Saldo   =("Valor", "sum"),
                )
                .reset_index())
    mensal["Saldo Acumulado"] = mensal["Saldo"].cumsum()
    return mensal


# ── Indicadores extras ────────────────────────────────────────────────────────

def calcular_indicadores_extras(df_comp: pd.DataFrame, df_gast: pd.DataFrame,
                                 df_vend: pd.DataFrame, df_man: pd.DataFrame,
                                 ctcab: float) -> dict:
    """
    Indicadores complementares de gestão:

    • TMP (Tempo Médio de Permanência): dias entre primeira compra e última venda
    • custo_dia_cab: custo total dividido por (TMP × cabeças compradas)
    • arrobas_min_cab: arrobas mínimas por cabeça para cobrir CTCab (a 15 kg/@ = padrão boi gordo)
    • pct_gasto_sobre_compra: quanto os gastos representam sobre o investimento em compras
    • ticket_medio_venda: receita média por cabeça vendida
    """
    resultado = {
        "tmp_dias":              0,
        "custo_dia_cab":         0.0,
        "arrobas_min_cab":       0.0,
        "pct_gasto_sobre_compra": 0.0,
        "ticket_medio_venda":   0.0,
    }

    # TMP
    datas = []
    for df, col in [(df_comp, "Data"), (df_vend, "Data")]:
        if not df.empty and col in df.columns:
            d = df[col].dropna()
            if not d.empty:
                datas.extend([d.min(), d.max()])
    if len(datas) >= 2:
        resultado["tmp_dias"] = max(0, (max(datas) - min(datas)).days)

    # Custo por cabeça por dia
    total_custo = 0.0
    cab_comp    = 0
    if not df_comp.empty:
        total_custo += float(df_comp["Valor Total (R$)"].sum())
        cab_comp     = int(df_comp["Qtd Cabeças"].sum())
    if not df_gast.empty:
        total_custo += float(df_gast["Valor Total (R$)"].sum())

    if resultado["tmp_dias"] > 0 and cab_comp > 0:
        resultado["custo_dia_cab"] = total_custo / (resultado["tmp_dias"] * cab_comp)

    # Arrobas mínimas para cobrir CTCab (1 arroba = 15 kg peso vivo padrão)
    # Em Minas, @boi gordo = aprox. 15 kg de carcaça ≈ 30 kg vivo, mas usamos convenção local
    if ctcab > 0:
        # Referência: 1 arroba ≈ 15 kg peso vivo (convenção mais usada)
        # Para cobrir CTCab: arrobas = CTCab / preco_arroba — só calculável com preço
        # Sem preço de arroba, calculamos quantas arrobas equivalem ao CTCab em peso
        # Esta é a "quantidade mínima" que a cabeça precisa produzir (em arrobas) para
        # cobrir custos se vendida ao menor preço histórico de arroba, ou usamos
        # a referência de que 1 arroba de boi gordo = ~R$ 280 (valor indicativo)
        # Referência: R$320/@ — média boi gordo Sudeste/MG (atualizado 2025)
        # Ajuste conforme cotação atual do mercado local se necessário
        PRECO_ARROBA_REF = 320.0  # R$/@ — referência indicativa para cálculo
        resultado["arrobas_min_cab"] = ctcab / PRECO_ARROBA_REF

    # % Gastos sobre compras
    total_comp = float(df_comp["Valor Total (R$)"].sum()) if not df_comp.empty else 0.0
    total_gast = float(df_gast["Valor Total (R$)"].sum()) if not df_gast.empty else 0.0
    if total_comp > 0:
        resultado["pct_gasto_sobre_compra"] = total_gast / total_comp * 100

    # Ticket médio de venda
    if not df_vend.empty:
        tv = float(df_vend["Valor Total (R$)"].sum())
        cv = int(df_vend["Qtd Cabeças"].sum())
        resultado["ticket_medio_venda"] = tv / cv if cv > 0 else 0.0

    return resultado


def calcular_gasto_por_tipo(df_gast: pd.DataFrame) -> dict:
    """
    Retorna o total gasto por tipo de despesa, ordenado do maior para o menor.
    Inclui percentual de cada tipo sobre o total.
    """
    if df_gast.empty or "Tipo" not in df_gast.columns:
        return {}

    res = df_gast.groupby("Tipo")["Valor Total (R$)"].sum().sort_values(ascending=False)
    total = float(res.sum())
    return {
        k: {"valor": round(float(v), 2),
            "pct":   round(float(v) / total * 100, 1) if total > 0 else 0.0}
        for k, v in res.items()
    }


def calcular_evolucao_cmp(df_comp: pd.DataFrame) -> list[dict]:
    """
    Evolução do CMP a cada compra realizada.
    Útil para visualizar como o custo médio variou ao longo do tempo.
    Retorna lista de dicionários com data, qtd_acum, val_acum, cmp.
    """
    if df_comp.empty:
        return []

    df = df_comp[df_comp["Data"].notna()].sort_values("Data").copy()
    if df.empty:
        return []

    df["qtd_acum"] = df["Qtd Cabeças"].cumsum()
    df["val_acum"] = df["Valor Total (R$)"].cumsum()
    df["cmp"]      = df["val_acum"] / df["qtd_acum"].replace(0, float("nan"))

    return [
        {
            "data":      row["Data"].strftime("%d/%m/%Y"),
            "qtd_acum":  int(row["qtd_acum"]),
            "val_acum":  round(float(row["val_acum"]), 2),
            "cmp":       round(float(row["cmp"]), 2) if pd.notna(row["cmp"]) else 0.0,
            "descricao": str(row.get("Descrição", "")),
        }
        for _, row in df.iterrows()
    ]
