#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Relatórios, análises e visualizações
"""

import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from config import MEMBROS, NOMES_MEMBROS, EMOJIS_MEMBROS, ALERTAS_SAUDE
from db import carregar_todas
from calculos import (
    calcular_estoque, calcular_cmp, calcular_gpcab, calcular_ctcab,
    calcular_resumo_financeiro, calcular_todos_membros,
    calcular_fluxo_caixa, estimar_rebanho_arroba, estimar_rebanho_preco_cab,
)

try:
    import requests
    WEB_OK = True
except ImportError:
    WEB_OK = False


# ── Resumo Geral ──────────────────────────────────────────────────────────────

def ver_resumo_geral():
    ui_titulo("RESUMO GERAL DO REBANHO 🐄")
    dados = carregar_todas()
    r = calcular_resumo_financeiro(
        dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"]
    )

    # Bloco de estoque
    linhas = [
        ("📦 Cabeças compradas",            fmt_cabecas(r["cab_comp"])),
        ("🤝 Cabeças vendidas",             fmt_cabecas(r["cab_vend"])),
        ("🐄 Estoque atual",                fmt_cabecas(r["estoque"])),
        ("─", "─"),
        ("💲 CMP  (compra/cab. atual)",     f"{fmt_r(r['cmp'])}/cabeça"),
        ("🔧 GPCab (gastos/cab. atual)",    f"{fmt_r(r['gpcab'])}/cabeça"),
        ("📌 CTCab (custo/cab. atual)",     f"{fmt_r(r['ctcab'])}/cabeça"),
        ("─", "─"),
        ("💸 Total compras",                fmt_r(r["total_comp"])),
        ("🔧 Total gastos",                 fmt_r(r["total_gast"])),
        ("📊 CUSTO TOTAL",                  fmt_r(r["total_custo"])),
        ("🤝 Total vendas (receita)",       fmt_r(r["total_vend"])),
        ("─", "─"),
        ("🏦 Capital imobilizado (estoque)",fmt_r(r["capital_imobilizado"])),
        ("🎯 Break-even do estoque",        f"{fmt_r(r['break_even'])}/cabeça"),
        ("─", "─"),
        ("✅ Resultado realizado" if r["resultado_realizado"] >= 0
         else "❌ Resultado realizado",     fmt_r(r["resultado_realizado"])),
        ("📈 ROI realizado",                fmt_pct(r["roi_realizado"])),
        ("📊 Resultado total (+ estoque)",  fmt_r(r["resultado_total"])),
        ("📈 ROI total (+ estoque)",        fmt_pct(r["roi_total"])),
        ("─", "─"),
        ("🎫 Ticket médio de venda",        f"{fmt_r(r['ticket_medio'])}/cabeça"),
        ("📉 Margem bruta",                 fmt_pct(r["margem_bruta"])),
    ]
    ui_tabela("Resumo Geral", ["Indicador", "Valor"], linhas)

    # Nota explicativa
    ui_info("")
    ui_info("💡 Glossário:")
    ui_info("  CMP   = média ponderada de todas as compras por cabeça")
    ui_info("  GPCab = soma dos gastos por cabeça no período")
    ui_info("  CTCab = custo total por cabeça (CMP + GPCab)")
    ui_info("  Break-even = preço mínimo p/ recuperar capital do estoque atual")
    ui_info("  ROI realizado = lucro sobre as vendas já feitas")
    ui_info("  ROI total = inclui o valor estimado do estoque a custo")


# ── Resumo por Membro ─────────────────────────────────────────────────────────

def ver_resumo_por_membro():
    ui_titulo("RESULTADO POR MEMBRO 👨‍👩‍👦")
    dados = carregar_todas()
    membros_res = calcular_todos_membros(
        dados["Vendas"], dados["Compras"], dados["Gastos"], dados["Manejo"]
    )

    ui_info("Método: CMP + GPCab no momento de cada venda\n")

    linhas_geral = []
    for m in MEMBROS:
        r = membros_res[m]
        emoji = EMOJIS_MEMBROS[m]
        nome  = NOMES_MEMBROS[m]
        sinal = "✅" if r["resultado"] >= 0 else "❌"
        linhas_geral.append((
            f"{emoji} {nome}",
            fmt_cabecas(r["cabecas"]),
            fmt_r(r["receita"]),
            fmt_r(r["custo_compra"]),
            fmt_r(r["custo_gastos"]),
            fmt_r(r["custo_total"]),
            f"{sinal} {fmt_r(r['resultado'])}",
            fmt_pct(r["margem_pct"]),
        ))

    ui_tabela("Resultado por Membro",
              ["Membro", "Cabeças", "Receita", "Custo Compra",
               "Custo Gastos", "Custo Total", "Resultado", "Margem"],
              linhas_geral)

    # Detalhe por membro
    for m in MEMBROS:
        r   = membros_res[m]
        nome = NOMES_MEMBROS[m]
        if not r["vendas_detalhadas"]:
            continue

        ui_separador()
        ui_info(f"{EMOJIS_MEMBROS[m]} {nome.upper()} — detalhamento por venda\n")

        linhas_d = []
        for v in r["vendas_detalhadas"]:
            sinal = "✅" if v["resultado"] >= 0 else "❌"
            linhas_d.append((
                v["data"],
                fmt_cabecas(v["cabecas"]),
                fmt_r(v["receita"]),
                fmt_r(v["cmp"]) + "/cab",
                fmt_r(v["gpcab"]) + "/cab",
                f"{sinal} {fmt_r(v['resultado'])}",
                fmt_pct(v["margem_pct"]),
            ))

        ui_tabela(f"Vendas de {nome}",
                  ["Data", "Cabeças", "Receita", "CMP", "GPCab", "Resultado", "Margem"],
                  linhas_d)


# ── Listar todos os registros ─────────────────────────────────────────────────

def listar_registros():
    ui_titulo("TODOS OS REGISTROS 📋")
    dados = carregar_todas()
    for aba, df in dados.items():
        if not df.empty:
            colunas = ["#"] + list(df.columns)
            linhas  = []
            for i, row in df.iterrows():
                linha = [str(i)]
                for v in row:
                    if isinstance(v, pd.Timestamp):
                        linha.append(v.strftime("%d/%m/%Y"))
                    else:
                        linha.append("" if (not isinstance(v, str) and pd.isna(v))
                                     else str(v))
                linhas.append(linha)
            ui_tabela(f"{aba} ({len(df)} registros)", colunas, linhas)
        else:
            ui_info(f"📁 {aba}: (sem registros)")


# ── Relatório por Período ─────────────────────────────────────────────────────

def relatorio_por_periodo():
    ui_titulo("RELATÓRIO POR PERÍODO 📅")
    data_ini = ui_data_simples("Data inicial (dd/mm/aaaa)")
    data_fim = ui_data_simples("Data final   (dd/mm/aaaa)")
    dt_ini = datetime.strptime(data_ini, "%d/%m/%Y")
    dt_fim = datetime.strptime(data_fim, "%d/%m/%Y")

    def filtrar(df):
        if df.empty or "Data" not in df.columns:
            return df
        df = df.copy()
        df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
        return df[(df["Data"] >= dt_ini) & (df["Data"] <= dt_fim)]

    dados = carregar_todas()
    df_c = filtrar(dados["Compras"])
    df_g = filtrar(dados["Gastos"])
    df_v = filtrar(dados["Vendas"])
    df_m = filtrar(dados["Manejo"])

    tc  = df_c["Valor Total (R$)"].sum() if not df_c.empty else 0
    tg  = df_g["Valor Total (R$)"].sum() if not df_g.empty else 0
    tv  = df_v["Valor Total (R$)"].sum() if not df_v.empty else 0
    custo = tc + tg
    lucro = tv - custo

    cab_c = int(df_c["Qtd Cabeças"].sum()) if not df_c.empty else 0
    cab_v = int(df_v["Qtd Cabeças"].sum()) if not df_v.empty else 0

    linhas = [
        ("📅 Período",           f"{data_ini} → {data_fim}"),
        ("─", "─"),
        ("🛒 Compras",           f"{len(df_c)} registros | {cab_c} cabeças | {fmt_r(tc)}"),
        ("💸 Gastos",            f"{len(df_g)} registros | {fmt_r(tg)}"),
        ("🤝 Vendas",            f"{len(df_v)} registros | {cab_v} cabeças | {fmt_r(tv)}"),
        ("🩺 Manejo",            f"{len(df_m)} registros"),
        ("─", "─"),
        ("📊 Custo total",       fmt_r(custo)),
        ("📥 Receita total",     fmt_r(tv)),
        ("✅ Resultado" if lucro >= 0 else "❌ Resultado", fmt_r(lucro)),
        ("📈 ROI no período",    fmt_pct(lucro / custo * 100) if custo > 0 else "—"),
    ]
    ui_tabela(f"Relatório {data_ini} — {data_fim}", ["Item", "Valor"], linhas)

    # Gastos por categoria
    if not df_g.empty and "Tipo" in df_g.columns:
        ui_separador()
        ui_info("Gastos por categoria:")
        resumo = df_g.groupby("Tipo")["Valor Total (R$)"].sum().sort_values(ascending=False)
        for tipo, val in resumo.items():
            pct = val / tg * 100 if tg > 0 else 0
            ui_info(f"  {tipo:<30}  {fmt_r(val):>14}  ({pct:.1f}%)")


# ── Comparativo anual ─────────────────────────────────────────────────────────

def comparativo_anual():
    ui_titulo("COMPARATIVO ANUAL 📊")
    dados = carregar_todas()

    def add_ano(df):
        if df.empty or "Data" not in df.columns:
            return df
        df = df.copy()
        df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
        df["Ano"] = df["Data"].dt.year
        return df

    dc = add_ano(dados["Compras"])
    dg = add_ano(dados["Gastos"])
    dv = add_ano(dados["Vendas"])

    anos = set()
    for df in [dc, dg, dv]:
        if not df.empty and "Ano" in df.columns:
            anos |= set(df["Ano"].dropna().astype(int))
    if not anos:
        ui_aviso("Sem dados para exibir.")
        return

    linhas = []
    for ano in sorted(anos):
        ca = dc[dc["Ano"] == ano]["Valor Total (R$)"].sum() if not dc.empty and "Ano" in dc else 0
        ga = dg[dg["Ano"] == ano]["Valor Total (R$)"].sum() if not dg.empty and "Ano" in dg else 0
        va = dv[dv["Ano"] == ano]["Valor Total (R$)"].sum() if not dv.empty and "Ano" in dv else 0
        custo = ca + ga
        lucro = va - custo
        roi   = lucro / custo * 100 if custo > 0 else 0
        cab_c = int(dc[dc["Ano"] == ano]["Qtd Cabeças"].sum()) if not dc.empty and "Ano" in dc else 0
        cab_v = int(dv[dv["Ano"] == ano]["Qtd Cabeças"].sum()) if not dv.empty and "Ano" in dv else 0
        linhas.append((
            str(int(ano)),
            fmt_cabecas(cab_c), fmt_cabecas(cab_v),
            fmt_r(ca), fmt_r(ga), fmt_r(custo), fmt_r(va),
            f"{'✅' if lucro >= 0 else '❌'} {fmt_r(lucro)}",
            fmt_pct(roi),
        ))

    ui_tabela("Comparativo Anual",
              ["Ano", "Compradas", "Vendidas",
               "Compras", "Gastos", "Custo", "Receita", "Resultado", "ROI"],
              linhas)


# ── Estimativa do rebanho ─────────────────────────────────────────────────────

def estimativa_rebanho():
    ui_titulo("ESTIMATIVA DO REBANHO 🐄")
    dados   = carregar_todas()
    r_fin   = calcular_resumo_financeiro(
        dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"]
    )
    estoque = r_fin["estoque"]
    ctcab   = r_fin["ctcab"]

    if estoque <= 0:
        ui_aviso("Sem cabeças em estoque.")
        return

    ui_info(f"Estoque atual:  {fmt_cabecas(estoque)}")
    ui_info(f"CTCab:          {fmt_r(ctcab)}/cabeça  (custo médio total por cabeça)")
    ui_info(f"Capital em risco: {fmt_r(ctcab * estoque)}")
    ui_info(f"Break-even de mercado: {fmt_r(r_fin['break_even'])}/cabeça")
    ui_separador()

    ui_info("Método de estimativa:")
    ui_info("  1. Pelo preço da arroba")
    ui_info("  2. Pelo preço à vista por cabeça")
    ui_info("  3. Só ver o custo imobilizado")
    opcao = ui_int("Escolha", 1, 3)

    if opcao == 1:
        peso  = ui_float("Peso médio estimado dos animais (kg)", 200)
        arr   = ui_float("Valor da arroba (R$/@)")
        e     = estimar_rebanho_arroba(estoque, peso, arr, ctcab)
        linhas = [
            ("🐄 Estoque",              fmt_cabecas(estoque)),
            ("⚖️  Peso médio",           f"{peso:.0f} kg ({e['arrobas_cab']:.1f} @/cabeça)"),
            ("💲 Cotação arroba",        f"{fmt_r(arr)}/@"),
            ("💰 Valor/cabeça",          fmt_r(e["valor_cab"])),
            ("📦 VALOR DE MERCADO",      fmt_r(e["valor_total"])),
            ("🏦 Capital imobilizado",   fmt_r(e["capital_imob"])),
            ("✅ Lucro potencial" if e["lucro_pot"] >= 0
             else "❌ Lucro potencial",  fmt_r(e["lucro_pot"])),
            ("📉 Margem potencial",      fmt_pct(e["margem_pot"])),
        ]
    elif opcao == 2:
        preco = ui_float("Preço à vista por cabeça (R$)")
        e     = estimar_rebanho_preco_cab(estoque, preco, ctcab)
        linhas = [
            ("🐄 Estoque",              fmt_cabecas(estoque)),
            ("💲 Preço/cabeça",         fmt_r(preco)),
            ("📦 VALOR DE MERCADO",     fmt_r(e["valor_total"])),
            ("🏦 Capital imobilizado",  fmt_r(e["capital_imob"])),
            ("✅ Lucro potencial" if e["lucro_pot"] >= 0
             else "❌ Lucro potencial", fmt_r(e["lucro_pot"])),
            ("📉 Margem potencial",     fmt_pct(e["margem_pot"])),
        ]
    else:
        linhas = [
            ("🐄 Estoque",             fmt_cabecas(estoque)),
            ("💲 CMP",                 fmt_r(r_fin["cmp"]) + "/cabeça"),
            ("🔧 GPCab",               fmt_r(r_fin["gpcab"]) + "/cabeça"),
            ("📌 CTCab",               fmt_r(ctcab) + "/cabeça"),
            ("🏦 Capital imobilizado", fmt_r(ctcab * estoque)),
            ("🎯 Break-even",          fmt_r(r_fin["break_even"]) + "/cabeça"),
        ]

    ui_tabela("Estimativa do Rebanho", ["Indicador", "Valor"], linhas)


# ── Fluxo de Caixa ────────────────────────────────────────────────────────────

def ver_fluxo_caixa():
    ui_titulo("FLUXO DE CAIXA MENSAL 💰")
    dados = carregar_todas()
    df_fc = calcular_fluxo_caixa(
        dados["Compras"], dados["Gastos"], dados["Vendas"]
    )
    if df_fc.empty:
        ui_aviso("Sem dados para fluxo de caixa.")
        return

    linhas = []
    for _, row in df_fc.iterrows():
        saldo = row["Saldo"]
        saldo_acum = row["Saldo Acumulado"]
        linhas.append((
            str(row["AnoMes"]),
            fmt_r(row["Entradas"]),
            fmt_r(abs(row["Saidas"])),
            f"{'✅' if saldo >= 0 else '❌'} {fmt_r(saldo)}",
            f"{'🟢' if saldo_acum >= 0 else '🔴'} {fmt_r(saldo_acum)}",
        ))

    ui_tabela("Fluxo de Caixa Mensal",
              ["Mês", "Entradas", "Saídas", "Saldo do Mês", "Saldo Acumulado"],
              linhas)


# ── Alertas ───────────────────────────────────────────────────────────────────

def verificar_alertas():
    ui_titulo("ALERTAS DO REBANHO ⚠️")
    dados = carregar_todas()
    df_man = dados["Manejo"]
    alertas = []
    from extensions import _agora
    hoje = _agora()

    # Alertas de saúde
    from db import get_alertas_saude
    for tipo, dias in get_alertas_saude().items():
        from saude import ultima_data
        ultima = ultima_data(df_man, tipo)
        if ultima is None:
            alertas.append(f"⚠️  Nenhum registro de {tipo} encontrado!")
            continue
        dias_passados = (hoje - ultima.to_pydatetime()).days
        if dias_passados > dias:
            alertas.append(
                f"⏰ {tipo} atrasada! Último: {ultima.strftime('%d/%m/%Y')} "
                f"({dias_passados} dias atrás — limite: {dias} dias)"
            )

    # Alertas de mortes recentes
    if not df_man.empty:
        df_mortes = df_man[df_man["Tipo"] == "Morte/Perda"].copy()
        if not df_mortes.empty:
            df_mortes["Data"] = pd.to_datetime(df_mortes["Data"], dayfirst=True, errors="coerce")
            recentes = df_mortes[df_mortes["Data"] >= pd.Timestamp(hoje - timedelta(days=30))]
            if not recentes.empty:
                total = int(recentes["Qtd Cabeças"].sum())
                alertas.append(f"💀 {total} morte(s) nos últimos 30 dias")

    # Alertas financeiros
    r = calcular_resumo_financeiro(
        dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"]
    )
    if r["resultado_realizado"] < 0:
        alertas.append(f"💸 Resultado realizado negativo: {fmt_r(r['resultado_realizado'])}")
    if r["estoque"] > 0:
        alertas.append(
            f"💡 Break-even do estoque: {fmt_r(r['break_even'])}/cabeça "
            f"(precisam render mais que isso para dar lucro)"
        )

    if alertas:
        for a in alertas:
            ui_aviso(a)
    else:
        ui_ok("Nenhum alerta no momento. Tudo em dia!")


# ── Cotação online ────────────────────────────────────────────────────────────

def ver_cotacao():
    ui_titulo("COTAÇÃO DE MERCADO 🌐")
    if not WEB_OK:
        ui_aviso("Instale 'requests' para cotações online:  pip install requests")
        return
    ui_info("Buscando cotações...")
    cotacoes = _buscar_cotacao_imea()
    if cotacoes:
        linhas = [(k, fmt_r(v) + "/@") for k, v in cotacoes.items()]
        ui_tabela("Cotações IMEA", ["Indicador", "Valor"], linhas)
    else:
        ui_aviso("Não foi possível obter cotações no momento.")


def _buscar_cotacao_imea() -> dict | None:
    try:
        import requests
        r = requests.get(
            "https://www.imea.com.br/imea-site/view/arquivos/indicadores-boi/indicadores_boi.json",
            timeout=8,
        )
        dados = r.json()
        cotacoes = {}
        for item in dados:
            nome = item.get("indicador", "").upper()
            val  = float(str(item.get("valor", "0")).replace(",", "."))
            if "NOVILHA NELORE 18M" in nome:
                cotacoes["Novilha Nelore 18m"] = val
            elif "BEZERRA NELORE 12M" in nome:
                cotacoes["Bezerra Nelore 12m"] = val
            elif "BEZERRA NELORE 8M" in nome:
                cotacoes["Bezerra Nelore 8m"]  = val
        return cotacoes or None
    except Exception:
        return None


# ── Gráficos ──────────────────────────────────────────────────────────────────

def gerar_graficos():
    ui_titulo("GRÁFICOS 📊")
    ui_info("  1. Evolução das vendas")
    ui_info("  2. Gastos por categoria")
    ui_info("  3. Receita × Custo total")
    ui_info("  4. Fluxo de caixa acumulado")
    ui_info("  5. Resultado por membro")
    opcao = ui_int("Escolha", 1, 5)

    dados = carregar_todas()

    if opcao == 1:
        df = dados["Vendas"]
        if df.empty:
            ui_aviso("Sem dados de vendas.")
            return
        df = df.dropna(subset=["Data"]).sort_values("Data")
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.plot(df["Data"], df["Valor Total (R$)"], marker="o", color="#2e7d32", lw=2)
        ax.fill_between(df["Data"], df["Valor Total (R$)"], alpha=0.15, color="#2e7d32")
        ax.set_title("Evolução das Vendas — Sítio Santo Antonio", fontsize=13, fontweight="bold")
        ax.set_ylabel("R$")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))
        fig.autofmt_xdate()
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"R$ {x:,.0f}"))
        ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.show()

    elif opcao == 2:
        df = dados["Gastos"]
        if df.empty:
            ui_aviso("Sem dados de gastos.")
            return
        resumo = df.groupby("Tipo")["Valor Total (R$)"].sum().sort_values()
        cores  = ["#ef5350","#ab47bc","#42a5f5","#26a69a","#ffca28","#8d6e63"]
        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.barh(resumo.index, resumo.values, color=cores[:len(resumo)])
        for bar, val in zip(bars, resumo.values):
            ax.text(bar.get_width() + resumo.values.max() * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    f"R$ {val:,.0f}", va="center", fontsize=9)
        ax.set_title("Gastos por Categoria", fontsize=13, fontweight="bold")
        ax.set_xlabel("R$")
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"R$ {x:,.0f}"))
        plt.tight_layout()
        plt.show()

    elif opcao == 3:
        r = calcular_resumo_financeiro(
            dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"]
        )
        labels = ["Compras", "Gastos", "Custo Total", "Receita Vendas"]
        vals   = [r["total_comp"], r["total_gast"], r["total_custo"], r["total_vend"]]
        cores  = ["#1565c0", "#e65100", "#bf360c", "#2e7d32"]
        fig, ax = plt.subplots(figsize=(9, 5))
        bars = ax.bar(labels, vals, color=cores)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.01,
                    f"R$ {val:,.0f}", ha="center", fontsize=9)
        ax.set_title("Receita × Custo Total", fontsize=13, fontweight="bold")
        ax.set_ylabel("R$")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"R$ {x:,.0f}"))
        ax.grid(axis="y", alpha=0.3)
        plt.tight_layout()
        plt.show()

    elif opcao == 4:
        df_fc = calcular_fluxo_caixa(dados["Compras"], dados["Gastos"], dados["Vendas"])
        if df_fc.empty:
            ui_aviso("Sem dados de fluxo de caixa.")
            return
        periodos = [str(p) for p in df_fc["AnoMes"]]
        saldos   = df_fc["Saldo Acumulado"].tolist()
        cores    = ["#2e7d32" if s >= 0 else "#c62828" for s in saldos]
        fig, ax  = plt.subplots(figsize=(11, 5))
        ax.bar(periodos, saldos, color=cores)
        ax.axhline(0, color="black", lw=0.8, linestyle="--")
        ax.set_title("Saldo de Caixa Acumulado por Mês", fontsize=13, fontweight="bold")
        ax.set_ylabel("R$")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"R$ {x:,.0f}"))
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.show()

    elif opcao == 5:
        membros_res = calcular_todos_membros(
            dados["Vendas"], dados["Compras"], dados["Gastos"], dados["Manejo"]
        )
        nomes    = [NOMES_MEMBROS[m] for m in MEMBROS]
        receitas = [membros_res[m]["receita"]   for m in MEMBROS]
        custos   = [membros_res[m]["custo_total"] for m in MEMBROS]
        resultados = [membros_res[m]["resultado"] for m in MEMBROS]

        x = range(len(MEMBROS))
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.bar([i - 0.27 for i in x], receitas,   0.25, label="Receita",  color="#2e7d32")
        ax.bar([i        for i in x], custos,     0.25, label="Custo",    color="#e65100")
        ax.bar([i + 0.27 for i in x], resultados, 0.25, label="Resultado",
               color=["#1565c0" if r >= 0 else "#c62828" for r in resultados])
        ax.set_xticks(list(x))
        ax.set_xticklabels(nomes)
        ax.legend()
        ax.set_title("Resultado por Membro", fontsize=13, fontweight="bold")
        ax.set_ylabel("R$")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x_, _: f"R$ {x_:,.0f}"))
        ax.grid(axis="y", alpha=0.3)
        plt.tight_layout()
        plt.show()
