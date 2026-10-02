#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations  # compatibilidade Python 3.9+
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

# Preço de referência da arroba para cálculos de break-even e arrobas mínimas.
# Atualize conforme cotação do mercado local (Triângulo/MG, Scot/IMEA).
# Valor indicativo para boi gordo Nelore, Sudeste, 2026.
PRECO_ARROBA_REF: float = 340.0   # R$/@


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
                # BUG CORRIGIDO v3.2: sem rebanho na data, o gasto não tem
                # cabeças para absorver — inc=0.0 evita GPCab inflado.
                inc = 0.0
            else:
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


# ── Média Móvel Perpétua (custo real por cabeça) ─────────────────────────────

def _simular_media_movel(df_comp: pd.DataFrame,
                         df_gast: pd.DataFrame,
                         df_vend: pd.DataFrame,
                         df_man:  pd.DataFrame | None = None) -> dict:
    """
    Simula o rebanho ao longo do tempo pela MÉDIA MÓVEL PERPÉTUA e devolve o
    custo real por cabeça no momento de cada venda.

    Como funciona (exemplo):
      • Compro 10 bezerras a R$1.000  → média = R$1.000/cab
      • Gasto R$2.000 de vacina       → diluído nas 10 → média = R$1.200/cab
      • Vendo 7 a R$1.500 cada        → cada uma "custou" R$1.200
                                        (custo das vendidas = 7×1.200 = R$8.400;
                                         lucro = 10.500 − 8.400 = R$2.100).
                                        A venda NÃO altera a média; sobram 3 a R$1.200.
      • Compro mais 9 a R$1.300       → mistura as 3 antigas com as 9 novas
                                        (nova média de compra = R$1.225/cab).

    Regras:
      • Compra: entra no "pool de compra"; aumenta o nº de cabeças.
      • Gasto:  entra no "pool de gasto"; é diluído SÓ pelo rebanho vigente
                (nunca por gado comprado depois).
      • Venda:  sai pela média do momento (compra + gasto) e reduz os pools
                proporcionalmente — sem mudar a média.
      • Nascimento: + cabeças a custo zero (baixa a média).
      • Morte/Perda: − cabeças e remove o custo delas (pela média do momento) como
        PERDA separada — não infla os sobreviventes. Se houver "Perda De", a perda
        é atribuída ao dono; senão é dividida em terços.

    Dois pools separados (compra e gasto) preservam, para cada venda, a divisão
    entre custo de compra e custo de gastos — usada no resultado por membro.

    Retorna dict com:
      custo_vendidos          — COGS total (compra + gasto)
      custo_vendidos_compra   — parte de compra do COGS
      custo_vendidos_gasto    — parte de gasto do COGS
      perdas                  — custo das cabeças mortas/perdidas (perda separada)
      perdas_compra/_gasto    — divisão da perda entre compra e gasto
      cab_mortes              — nº de cabeças mortas/perdidas consideradas
      perdas_por_membro       — {membro: custo perdido} (usa "Perda De"; senão terços)
      capital                 — valor dos pools restantes (estoque a custo)
      avg_compra_final / avg_gasto_final / units_final
      avg_por_venda           — {índice df_vend: (avg_compra, avg_gasto)}

    Conservação: custo_vendidos + perdas + capital == total gasto (compras + gastos).
    """
    SENTINELA = pd.Timestamp.max

    def _data(x):
        return x if pd.notna(x) else SENTINELA

    eventos = []  # (data, prioridade, tipo, qtd, valor, vidx, perda_de)

    if not df_comp.empty:
        for _, r in df_comp.iterrows():
            eventos.append((_data(r.get("Data")), 0, "compra",
                            float(r.get("Qtd Cabeças", 0) or 0),
                            float(r.get("Valor Total (R$)", 0) or 0), None, None))

    if not df_gast.empty:
        for _, r in df_gast.iterrows():
            eventos.append((_data(r.get("Data")), 1, "gasto",
                            0.0, float(r.get("Valor Total (R$)", 0) or 0), None, None))

    if df_man is not None and not df_man.empty and "Tipo" in df_man.columns:
        for _, r in df_man.iterrows():
            tipo = r.get("Tipo")
            qtd  = float(r.get("Qtd Cabeças", 0) or 0)
            if qtd <= 0:
                continue
            if tipo == "Nascimento":
                eventos.append((_data(r.get("Data")), 2, "nasc",  qtd, 0.0, None, None))
            elif tipo == "Morte/Perda":
                perda_de = str(r.get("Perda De", "") or "").strip() or None
                eventos.append((_data(r.get("Data")), 4, "morte", qtd, 0.0, None, perda_de))

    if not df_vend.empty:
        for vidx, r in df_vend.iterrows():
            eventos.append((_data(r.get("Data")), 3, "venda",
                            float(r.get("Qtd Cabeças", 0) or 0), 0.0, vidx, None))

    # Ordena por data e, dentro da mesma data, pela prioridade (entradas antes de saídas)
    eventos.sort(key=lambda e: (e[0], e[1]))

    units = 0.0
    pool_c = 0.0   # pool de compra
    pool_g = 0.0   # pool de gasto
    cogs_c = 0.0
    cogs_g = 0.0
    perda_c = 0.0  # perdas por morte — parte de compra
    perda_g = 0.0  # perdas por morte — parte de gasto
    cab_mortes = 0.0
    perdas_por_membro = {m: 0.0 for m in MEMBROS}
    avg_por_venda: dict = {}

    def _ratear_perda_tercos(valor_perda: float):
        n = len(MEMBROS)
        if n == 0:
            return
        base = valor_perda / n
        for m in MEMBROS:
            perdas_por_membro[m] += base

    for data, _prio, tipo, qtd, valor, vidx, perda_de in eventos:
        if tipo == "compra":
            pool_c += valor
            units  += qtd
        elif tipo == "gasto":
            pool_g += valor
        elif tipo == "nasc":
            units  += qtd
        elif tipo == "morte":
            # v4.0: a morte é uma PERDA separada — remove as cabeças E o custo
            # delas (pela média do momento), sem inflar os sobreviventes.
            avg_c = pool_c / units if units > 0 else 0.0
            avg_g = pool_g / units if units > 0 else 0.0
            removido = min(qtd, units) if units > 0 else 0.0
            pc = avg_c * removido
            pg = avg_g * removido
            pool_c -= pc
            pool_g -= pg
            units  -= removido
            perda_c += pc
            perda_g += pg
            cab_mortes += removido
            if perda_de in perdas_por_membro:
                perdas_por_membro[perda_de] += pc + pg
            else:
                _ratear_perda_tercos(pc + pg)
        elif tipo == "venda":
            avg_c = pool_c / units if units > 0 else 0.0
            avg_g = pool_g / units if units > 0 else 0.0
            avg_por_venda[vidx] = (avg_c, avg_g)
            removido = min(qtd, units) if units > 0 else 0.0
            cc = avg_c * removido
            cg = avg_g * removido
            pool_c -= cc
            pool_g -= cg
            units  -= removido
            cogs_c += cc
            cogs_g += cg

    return {
        "custo_vendidos":        cogs_c + cogs_g,
        "custo_vendidos_compra": cogs_c,
        "custo_vendidos_gasto":  cogs_g,
        "perdas":                perda_c + perda_g,
        "perdas_compra":         perda_c,
        "perdas_gasto":          perda_g,
        "cab_mortes":            cab_mortes,
        "perdas_por_membro":     perdas_por_membro,
        "capital":               max(0.0, pool_c + pool_g),
        "avg_compra_final":      pool_c / units if units > 0 else 0.0,
        "avg_gasto_final":       pool_g / units if units > 0 else 0.0,
        "units_final":           units,
        "avg_por_venda":         avg_por_venda,
    }


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
                # BUG CORRIGIDO v3.2: se não há rebanho na data, não preencher
                if est > 0:
                    df.at[idx, "Qtd Cabeças"]       = float(est)
                    df.at[idx, "Valor/Cabeça (R$)"] = round(val / est, 4)
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
    Custo total das cabeças vendidas (COGS), pela MÉDIA MÓVEL PERPÉTUA.

    v4.0: cada venda sai pela média de custo (compra + gastos) vigente naquele
    momento — gastos só pesam no rebanho que estava vivo, e gado comprado depois
    nunca é cobrado por despesas anteriores. Isso garante a conservação contábil
    (custo_vendidos + capital == total gasto) sem "custo fantasma".
    """
    if df_vend.empty or df_comp.empty:
        return 0.0
    sim = _simular_media_movel(df_comp, df_gast, df_vend, df_man)
    return sim["custo_vendidos"]


def custo_medio_movel_venda(df_comp: pd.DataFrame, df_gast: pd.DataFrame,
                            df_vend: pd.DataFrame | None, df_man: pd.DataFrame | None,
                            data_venda, qtd_venda,
                            idx=None) -> tuple[float, float]:
    """
    Custo médio móvel por cabeça (compra, gasto) de UMA venda, posicionada pela sua
    data na linha do tempo — exatamente o que o motor usaria no dashboard.

    Usado ao registrar/editar uma venda para gravar o snapshot (Custo/Resultado por
    membro) coerente com a média móvel. Vendas não mudam a média no instante, mas
    alteram a base das compras seguintes — por isso a venda precisa entrar na simulação.

    idx: índice da venda em df_vend (modo edição). Se None/ausente, trata como venda nova.
    Retorna (avg_compra, avg_gasto).
    """
    if not isinstance(data_venda, pd.Timestamp):
        data_venda = pd.to_datetime(data_venda, dayfirst=True, errors="coerce")

    if df_vend is None or df_vend.empty:
        work = pd.DataFrame(columns=["Data", "Qtd Cabeças"])
    else:
        work = df_vend.copy()
        if "Data" not in work.columns:
            work["Data"] = pd.NaT
        if "Qtd Cabeças" not in work.columns:
            work["Qtd Cabeças"] = 0

    if idx is not None and idx in work.index:
        key = idx
        work.at[idx, "Data"]        = data_venda
        work.at[idx, "Qtd Cabeças"] = qtd_venda
    else:
        key = "__nova_venda__"
        linha = {c: None for c in work.columns}
        linha["Data"]        = data_venda
        linha["Qtd Cabeças"] = qtd_venda
        work.loc[key] = linha

    sim = _simular_media_movel(
        df_comp if df_comp is not None else pd.DataFrame(),
        df_gast if df_gast is not None else pd.DataFrame(),
        work, df_man,
    )
    return sim["avg_por_venda"].get(key, (0.0, 0.0))


# ── Resultado por membro ──────────────────────────────────────────────────────

def calcular_resultado_membro(membro: str, df_vend: pd.DataFrame,
                               df_comp: pd.DataFrame, df_gast: pd.DataFrame,
                               df_man: pd.DataFrame | None = None,
                               *, _avg_por_venda=None, _perda_membro=None) -> dict:
    """
    Resultado líquido de um membro pela MÉDIA MÓVEL PERPÉTUA (v4.0).

    Para cada venda, o custo por cabeça (compra e gastos) é a média de custo
    vigente naquele momento — a mesma usada no custo global das vendas, garantindo
    que a soma dos custos dos membros bata com o custo total das vendas.

    "perdas" é o custo das cabeças mortas/perdidas atribuídas a este membro (campo
    "Perda De"; sem dono, rateado em terços). "resultado_liquido" = resultado − perdas.

    Parâmetros opcionais (_avg_por_venda, _perda_membro):
        Pré-computados por calcular_todos_membros() (uma simulação para todos).
        Sem eles, a simulação é feita internamente (modo standalone).
    """
    col_qtd = f"Qtd {membro}"
    col_val = f"Valor {membro} (R$)"

    # Simulação (avg por venda + perdas por membro). Reusa a pré-computada se dada.
    if _avg_por_venda is not None and _perda_membro is not None:
        avg_por_venda = _avg_por_venda
        perda_membro  = _perda_membro
    else:
        _sim          = _simular_media_movel(df_comp, df_gast, df_vend, df_man)
        avg_por_venda = _sim["avg_por_venda"]
        perda_membro  = _sim["perdas_por_membro"].get(membro, 0.0)

    resultado = {
        "membro":            membro,
        "cabecas":           0,
        "receita":           0.0,
        "custo_compra":      0.0,
        "custo_gastos":      0.0,
        "custo_total":       0.0,
        "resultado":         0.0,
        "perdas":            round(perda_membro, 2),
        "resultado_liquido": round(-perda_membro, 2),
        "margem_pct":        0.0,
        "ticket_medio":      0.0,
        "custo_medio_cab":   0.0,
        "vendas_detalhadas": [],
    }

    if df_vend.empty or col_qtd not in df_vend.columns:
        return resultado

    for vidx, venda in df_vend.iterrows():
        qtd_m = int(venda.get(col_qtd, 0) or 0)
        val_m = float(venda.get(col_val, 0) or 0)
        if qtd_m <= 0:
            continue

        data_v = venda.get("Data")
        cmp_v, gpcab_v = avg_por_venda.get(vidx, (0.0, 0.0))

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
    # Resultado líquido = resultado das vendas − perdas por morte deste membro
    resultado["resultado_liquido"] = round(resultado["resultado"] - perda_membro, 2)
    resultado["margem_pct"]      = (resultado["resultado"] / resultado["receita"] * 100
                                    if resultado["receita"] > 0 else 0.0)
    resultado["ticket_medio"]    = (resultado["receita"] / resultado["cabecas"]
                                    if resultado["cabecas"] > 0 else 0.0)
    resultado["custo_medio_cab"] = (resultado["custo_total"] / resultado["cabecas"]
                                    if resultado["cabecas"] > 0 else 0.0)
    return resultado


def calcular_todos_membros(df_vend, df_comp, df_gast,
                            df_man: pd.DataFrame | None = None) -> dict:
    """
    Calcula resultado para todos os membros.

    A simulação de média móvel (custo por venda + perdas por membro) é feita
    UMA única vez e repassada a cada membro, garantindo que a soma dos custos
    dos membros feche com o custo global das vendas.
    """
    sim = _simular_media_movel(df_comp, df_gast, df_vend, df_man)
    avg_por_venda     = sim["avg_por_venda"]
    perdas_por_membro = sim["perdas_por_membro"]

    return {
        m: calcular_resultado_membro(
            m, df_vend, df_comp, df_gast, df_man,
            _avg_por_venda=avg_por_venda,
            _perda_membro=perdas_por_membro.get(m, 0.0),
        )
        for m in MEMBROS
    }


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

    # Motor de média móvel perpétua (v4.0): custo das vendas (COGS) e perdas por
    # morte no MOMENTO de cada evento. Uma única simulação alimenta tudo.
    sim            = _simular_media_movel(df_comp, df_gast, df_vend, df_man)
    custo_vendidos = sim["custo_vendidos"]
    perdas         = sim["perdas"]        # custo das cabeças mortas/perdidas
    cab_mortes     = int(round(sim["cab_mortes"]))

    # Capital ainda imobilizado no rebanho (a preço de custo).
    #
    # Identidade contábil (v4.0): todo real gasto ou (a) virou custo das cabeças
    # vendidas, ou (b) virou perda por morte, ou (c) ainda está parado no rebanho.
    # O capital é o RESÍDUO e a conservação é garantida:
    #     custo_vendidos + perdas + capital_imobilizado == total_custo
    # (Isso também eliminou o "custo fantasma" de +R$99 mil do modelo antigo.)
    capital_imobilizado = max(0.0, total_custo - custo_vendidos - perdas)

    # Resultado realizado = receita − custo das cabeças vendidas
    resultado_realizado = total_vend - custo_vendidos

    # Resultado total = realizado nas vendas − perdas por morte (estoque a custo,
    # sem preço de mercado; o ganho potencial é estimado em estimar_rebanho_*).
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
        # Perdas por morte (perda separada — v4.0)
        "perdas":               perdas,
        "cab_mortes":           cab_mortes,
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
                            ctcab: float,
                            rendimento: float = 0.52) -> dict:
    """
    Estima o valor do rebanho pelo preço da arroba.

    peso_kg   — peso VIVO por cabeça (kg).  Ex: 480 kg
    rendimento — percentual de rendimento de carcaça (padrão 52 % para boi gordo Nelore).
                 Esse valor converte peso vivo em peso de carcaça antes de dividir por 15.
                 Use rendimento=1.0 se peso_kg já for informado em peso de carcaça.

    Fórmula correta:
        arrobas/cab = (peso_kg × rendimento) / 15
    Exemplo:  480 kg vivo × 0,52 = 249,6 kg carcaça → 249,6 / 15 = 16,64 @

    BUG CORRIGIDO: versão anterior usava peso_kg / 15 sem aplicar o rendimento,
    o que dobrava o número de arrobas (ex: 480/15 = 32 @ em vez de ~16 @) quando
    o usuário digitava o peso vivo — erro de ~100% no valor estimado do rebanho.
    """
    if peso_kg <= 0 or preco_arroba <= 0:
        return {"arrobas_cab": 0, "valor_cab": 0, "valor_total": 0,
                "capital_imob": ctcab * estoque, "lucro_pot": 0, "margem_pot": 0}
    arrobas_cab  = (peso_kg * rendimento) / 15.0
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

    # Manejo: mortes e nascimentos tratados SEPARADAMENTE, linha a linha.
    if not df_man.empty and "Tipo" in df_man.columns:
        def _ratear_tercos(qtd: int, sinal: int):
            """Distribui qtd em terços (resto p/ Nilson), somando (sinal=+1)
            ou subtraindo (sinal=-1)."""
            base  = qtd // 3
            resto = qtd - base * 3
            resultado["Mae"]    += sinal * base
            resultado["Deyvid"] += sinal * base
            resultado["Nilson"] += sinal * (base + resto)

        for _, row in df_man.iterrows():
            tipo = row.get("Tipo")
            qtd  = int(row.get("Qtd Cabeças", 0) or 0)
            if qtd <= 0:
                continue

            if tipo == "Morte/Perda":
                # NOVO v3.6: se o registro diz de quem foi a perda, debita só
                # desse membro; senão divide a perda em terços (comportamento antigo).
                perda_de = str(row.get("Perda De", "") or "").strip()
                if perda_de in resultado:
                    resultado[perda_de] -= qtd
                else:
                    _ratear_tercos(qtd, -1)

            elif tipo == "Nascimento":
                _ratear_tercos(qtd, +1)

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
        # Usa PRECO_ARROBA_REF definido no topo do módulo (atualize conforme mercado).
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
