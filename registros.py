#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Operações de CRUD — Compras, Gastos, Vendas, Manejo, Editar, Excluir
"""

import pandas as pd
from datetime import datetime

from config import TIPOS_GASTO, TIPOS_MANEJO
from db import carregar_aba, salvar_linha, reescrever_aba, fazer_backup, carregar_todas
from ui_helper import (
    ui_titulo, ui_ok, ui_aviso, ui_info, ui_separador,
    ui_input, ui_int, ui_float, ui_data, ui_escolher_membro,
    ui_tabela, fmt_r,
)
from calculos import (
    calcular_estoque, calcular_cmp, calcular_gpcab,
    calcular_cmp_ate_data, calcular_gpcab_ate_data, dividir_cotas,
)


# ── Compras ───────────────────────────────────────────────────────────────────

def adicionar_compra():
    ui_titulo("NOVA COMPRA 🛒")
    data      = ui_data()
    cabecas   = ui_int("Quantidade de cabeças compradas", 1)
    valor     = ui_float("Valor total da compra (R$)")
    descricao = ui_input("Descrição (ex: Nelore Garrotes...)").strip()
    registrado = ui_escolher_membro("Quem está registrando?")

    valor_cab = round(valor / cabecas, 2) if cabecas > 0 else 0

    # Distribuição entre membros
    ui_info(f"Distribuição entre membros (total: {cabecas} cabeças):")
    qtd_mae    = ui_int("  Mãe    — quantidade de cabeças", 0, cabecas)
    qtd_deyvid = ui_int("  Deyvid — quantidade de cabeças", 0, cabecas)
    qtd_nilson = ui_int("  Nilson — quantidade de cabeças", 0, cabecas)

    soma = qtd_mae + qtd_deyvid + qtd_nilson
    if soma not in (0, cabecas):
        ui_aviso(f"Soma ({soma}) ≠ cabeças compradas ({cabecas}). Ajustando proporcionalmente.")
    qtd_mae, qtd_deyvid, qtd_nilson = dividir_cotas(cabecas, qtd_mae, qtd_deyvid, qtd_nilson)

    # Mostrar como isso afeta o CMP
    df_comp = carregar_aba("Compras")
    cmp_antes = calcular_cmp(df_comp)
    if cmp_antes > 0:
        ui_info(f"CMP atual:  {fmt_r(cmp_antes)}/cabeça")

    # BUG CORRIGIDO: salvar todas as 9 colunas (antes faltavam qtd_mae, qtd_deyvid, qtd_nilson)
    salvar_linha("Compras", [
        data, cabecas, valor, valor_cab,
        qtd_mae, qtd_deyvid, qtd_nilson,
        descricao, registrado
    ])

    df_comp  = carregar_aba("Compras")
    cmp_novo = calcular_cmp(df_comp)
    ui_ok(f"Compra registrada! {cabecas} cabeças por {fmt_r(valor)} ({fmt_r(valor_cab)}/cabeça)")
    ui_info(f"  Mãe: {qtd_mae} | Deyvid: {qtd_deyvid} | Nilson: {qtd_nilson}")
    if cmp_antes > 0:
        ui_info(f"Novo CMP:   {fmt_r(cmp_novo)}/cabeça  (era {fmt_r(cmp_antes)})")
    else:
        ui_info(f"CMP:        {fmt_r(cmp_novo)}/cabeça")


# ── Gastos ────────────────────────────────────────────────────────────────────

def adicionar_gasto():
    ui_titulo("NOVO GASTO 💸")
    data = ui_data()

    ui_info("Tipos de gasto:")
    for i, t in enumerate(TIPOS_GASTO, 1):
        ui_info(f"  {i}. {t}")
    tipo_idx = ui_int("Escolha o tipo (número)", 1, len(TIPOS_GASTO))
    tipo = TIPOS_GASTO[tipo_idx - 1]

    descricao = ui_input("Detalhe do gasto").strip()
    valor     = ui_float("Valor total (R$)")

    dados   = carregar_todas()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    cab_str = ui_input(
        f"Qtd cabeças de referência (Enter = estoque atual [{estoque}])", estoque
    ).strip()
    # BUG CORRIGIDO: cab_str.isdigit() retornava False para entradas com espaços,
    # valores negativos ou decimais (ex: "10 " ou "10.0"), caindo silenciosamente
    # no fallback sem aviso. Substituído por try/except mais robusto.
    try:
        ref_cab = max(1, int(float(cab_str.replace(",", ".")))) if cab_str else estoque
    except (ValueError, TypeError):
        ref_cab = estoque

    registrado = ui_escolher_membro("Quem está registrando?")
    valor_cab  = round(valor / ref_cab, 4) if ref_cab > 0 else 0

    gpcab_antes = calcular_gpcab(dados["Gastos"], dados["Compras"], dados["Vendas"], dados["Manejo"])
    salvar_linha("Gastos", [data, tipo, descricao, valor, ref_cab, valor_cab, registrado])

    ui_ok(f"Gasto registrado! {fmt_r(valor)}  ({tipo})")
    ui_info(f"→ {fmt_r(valor_cab)}/cabeça  |  GPCab era {fmt_r(gpcab_antes)}, agora {fmt_r(gpcab_antes + valor_cab)}")


# ── Vendas ────────────────────────────────────────────────────────────────────

def adicionar_venda():
    ui_titulo("NOVA VENDA 🤝")
    data    = ui_data()
    cabecas = ui_int("Quantidade de cabeças vendidas", 1)
    valor   = ui_float("Valor total recebido (R$)")

    arr_str = ui_input("Valor da arroba (R$) [Enter para pular]", "0").strip()
    try:
        arroba = float(arr_str.replace(",", ".")) if arr_str else 0.0
    except ValueError:
        arroba = 0.0

    descricao = ui_input("Descrição da venda").strip()

    ui_info(f"Distribuição entre membros (total: {cabecas} cabeças):")
    qtd_mae    = ui_int("  Mãe    — quantidade de cabeças", 0, cabecas)
    qtd_deyvid = ui_int("  Deyvid — quantidade de cabeças", 0, cabecas)
    qtd_nilson = ui_int("  Nilson — quantidade de cabeças", 0, cabecas)

    total_cotas = qtd_mae + qtd_deyvid + qtd_nilson
    if total_cotas != cabecas:
        ui_aviso(f"Soma ({total_cotas}) ≠ cabeças vendidas ({cabecas}). Ajustando proporcionalmente.")
    qtd_mae, qtd_deyvid, qtd_nilson = dividir_cotas(cabecas, qtd_mae, qtd_deyvid, qtd_nilson)

    valor_cab    = round(valor / cabecas, 2) if cabecas > 0 else 0
    valor_mae    = round(valor * (qtd_mae    / cabecas), 2) if cabecas > 0 else 0
    valor_deyvid = round(valor * (qtd_deyvid / cabecas), 2) if cabecas > 0 else 0
    valor_nilson = round(valor - valor_mae - valor_deyvid, 2)

    # Calcular custo e resultado no MOMENTO da venda (com contexto completo)
    dados   = carregar_todas()
    data_ts = pd.Timestamp(datetime.strptime(data, "%d/%m/%Y"))
    cmp_v   = calcular_cmp_ate_data(dados["Compras"], data_ts)
    gpcab_v = calcular_gpcab_ate_data(
        dados["Gastos"], data_ts,
        dados["Compras"], dados["Vendas"], dados["Manejo"]
    )
    ctcab_v = cmp_v + gpcab_v

    def custo_m(qtd):          return round(qtd * ctcab_v, 2)
    def result_m(val, qtd):    return round(val - custo_m(qtd), 2)

    c_mae    = custo_m(qtd_mae)
    c_deyvid = custo_m(qtd_deyvid)
    c_nilson = custo_m(qtd_nilson)
    r_mae    = result_m(valor_mae,    qtd_mae)
    r_deyvid = result_m(valor_deyvid, qtd_deyvid)
    r_nilson = result_m(valor_nilson, qtd_nilson)

    salvar_linha("Vendas", [
        data, cabecas, valor, valor_cab, arroba,
        qtd_mae, qtd_deyvid, qtd_nilson,
        valor_mae, valor_deyvid, valor_nilson,
        c_mae, c_deyvid, c_nilson,
        r_mae, r_deyvid, r_nilson,
        round(ctcab_v, 2),
        descricao,
    ])

    ui_ok("Venda registrada!")
    ui_info(f"🐄 {cabecas} cabeças → {fmt_r(valor)} ({fmt_r(valor_cab)}/cabeça)")
    ui_info(f"CMP + GPCab no momento: {fmt_r(ctcab_v)}/cabeça")
    ui_info(f"  CMP: {fmt_r(cmp_v)}/cab  |  GPCab: {fmt_r(gpcab_v)}/cab")
    ui_separador()

    linhas_r = []
    for nome, emoji, qtd, val, custo, res in [
        ("Mãe",    "👩", qtd_mae,    valor_mae,    c_mae,    r_mae),
        ("Deyvid", "👦", qtd_deyvid, valor_deyvid, c_deyvid, r_deyvid),
        ("Nilson", "👦", qtd_nilson, valor_nilson, c_nilson, r_nilson),
    ]:
        sinal = "✅" if res >= 0 else "❌"
        linhas_r.append((
            f"{emoji} {nome}", str(qtd),
            fmt_r(val), fmt_r(custo),
            f"{sinal} {fmt_r(res)}",
        ))

    ui_tabela("Resultado por membro (esta venda)",
              ["Membro", "Cabeças", "Receita", "Custo", "Resultado"],
              linhas_r)

    if ui_input("Imprimir recibo? (s/n)", "n").strip().lower() == "s":
        _imprimir_recibo(
            data, cabecas, valor, valor_cab, arroba,
            qtd_mae, qtd_deyvid, qtd_nilson,
            valor_mae, valor_deyvid, valor_nilson,
            r_mae, r_deyvid, r_nilson,
            descricao,
        )


# ── Manejo ────────────────────────────────────────────────────────────────────

def adicionar_manejo():
    ui_titulo("REGISTRO DE MANEJO 🩺")
    for i, t in enumerate(TIPOS_MANEJO, 1):
        ui_info(f"  {i}. {t}")
    tipo_idx  = ui_int("Tipo de manejo", 1, len(TIPOS_MANEJO))
    tipo      = TIPOS_MANEJO[tipo_idx - 1]
    data      = ui_data()
    cabecas   = ui_int("Quantidade de cabeças envolvidas", 0)
    descricao = ui_input("Descrição").strip()
    resp      = ui_escolher_membro("Responsável pelo manejo?")

    salvar_linha("Manejo", [data, tipo, cabecas, descricao, resp])
    ui_ok(f"Manejo registrado! ({tipo} — {cabecas} cabeças)")


# ── Editar registro ───────────────────────────────────────────────────────────

def editar_registro():
    ui_titulo("EDITAR REGISTRO ✏️")
    abas = ["Compras", "Gastos", "Vendas", "Manejo"]
    for i, a in enumerate(abas, 1):
        ui_info(f"  {i}. {a}")
    aba = abas[ui_int("Aba", 1, len(abas)) - 1]

    df = carregar_aba(aba)
    if df.empty:
        ui_aviso("Nenhum registro encontrado.")
        return

    _exibir_df(aba, df)
    idx = ui_int(f"Índice do registro para editar (0 a {len(df)-1})", 0, len(df) - 1)

    ui_info("Deixe em branco para manter o valor atual.")
    novos = {}
    for col in df.columns:
        val     = df.iloc[idx][col]
        val_str = val.strftime("%d/%m/%Y") if isinstance(val, pd.Timestamp) else (
            "" if (not isinstance(val, str) and pd.isna(val)) else str(val)
        )
        entrada = ui_input(f"  {col}", val_str or None).strip()
        if not entrada or entrada == val_str:
            novos[col] = df.iloc[idx][col]
        else:
            try:
                if isinstance(val, pd.Timestamp):
                    novos[col] = pd.to_datetime(entrada, dayfirst=True)
                elif isinstance(val, int):
                    novos[col] = int(entrada)
                elif isinstance(val, float):
                    novos[col] = float(entrada.replace(",", "."))
                else:
                    novos[col] = entrada
            except Exception:
                novos[col] = entrada

    if ui_input("Confirmar edição? (s/n)", "n").strip().lower() != "s":
        ui_aviso("Edição cancelada.")
        return

    fazer_backup()
    for col, val in novos.items():
        df.at[idx, col] = val
    reescrever_aba(aba, df)
    ui_ok("Registro editado com sucesso!")


# ── Excluir registro ──────────────────────────────────────────────────────────

def excluir_registro():
    ui_titulo("EXCLUIR REGISTRO 🗑️")
    abas = ["Compras", "Gastos", "Vendas", "Manejo"]
    for i, a in enumerate(abas, 1):
        ui_info(f"  {i}. {a}")
    aba = abas[ui_int("Aba", 1, len(abas)) - 1]

    df = carregar_aba(aba)
    if df.empty:
        ui_aviso("Nenhum registro encontrado.")
        return

    _exibir_df(aba, df)
    idx = ui_int(f"Índice para excluir (0 a {len(df)-1})", 0, len(df) - 1)

    ui_info("Registro selecionado:")
    for col in df.columns:
        ui_info(f"  {col}: {df.iloc[idx][col]}")

    if ui_input("Tem certeza? (s/n)", "n").strip().lower() != "s":
        ui_aviso("Cancelado.")
        return

    fazer_backup()
    df = df.drop(idx).reset_index(drop=True)
    reescrever_aba(aba, df)
    ui_ok("Registro excluído!")


# ── Helpers internos ──────────────────────────────────────────────────────────

def _exibir_df(aba: str, df: pd.DataFrame):
    colunas = ["#"] + list(df.columns)
    linhas  = []
    for i, row in df.iterrows():
        linha = [str(i)]
        for v in row:
            if isinstance(v, pd.Timestamp):
                linha.append(v.strftime("%d/%m/%Y"))
            else:
                linha.append("" if (not isinstance(v, str) and pd.isna(v)) else str(v))
        linhas.append(linha)
    ui_tabela(f"Registros — {aba}", colunas, linhas)


def _imprimir_recibo(data, cabecas, valor, valor_cab, arroba,
                     qtd_mae, qtd_deyvid, qtd_nilson,
                     val_mae, val_deyvid, val_nilson,
                     res_mae, res_deyvid, res_nilson, descricao):
    linha = "═" * 52
    print(f"\n{linha}")
    print("  🧾 RECIBO DE VENDA — SÍTIO SANTO ANTONIO")
    print(f"  Família: Mãe, Deyvid e Nilson")
    print(linha)
    print(f"  Data:           {data}")
    print(f"  Descrição:      {descricao}")
    print(f"  Cabeças:        {cabecas}")
    print(f"  Valor total:    {fmt_r(valor)}")
    print(f"  Valor/cabeça:   {fmt_r(valor_cab)}")
    if arroba:
        print(f"  Valor arroba:   {fmt_r(arroba)}/@")
    print(f"{'─'*52}")
    print("  DISTRIBUIÇÃO:")
    for nome, emoji, qtd, val, res in [
        ("Mãe",    "👩", qtd_mae,    val_mae,    res_mae),
        ("Deyvid", "👦", qtd_deyvid, val_deyvid, res_deyvid),
        ("Nilson", "👦", qtd_nilson, val_nilson, res_nilson),
    ]:
        sinal = "✅" if res >= 0 else "❌"
        print(f"  {emoji} {nome:<8}  {qtd:>3} cab.  {fmt_r(val):>14}  {sinal} {fmt_r(res)}")
    print(f"{linha}")
    print(f"  Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}")
    print(f"{linha}\n")


def recibo_ultima_venda():
    df = carregar_aba("Vendas")
    if df.empty:
        ui_aviso("Sem vendas registradas.")
        return
    r = df.iloc[-1]
    d = r["Data"].strftime("%d/%m/%Y") if pd.notna(r.get("Data")) else "?"
    _imprimir_recibo(
        d,
        int(r.get("Qtd Cabeças", 0) or 0),
        float(r.get("Valor Total (R$)", 0) or 0),
        float(r.get("Valor/Cabeça (R$)", 0) or 0),
        float(r.get("Valor Arroba (R$)", 0) or 0),
        int(r.get("Qtd Mae", 0) or 0),
        int(r.get("Qtd Deyvid", 0) or 0),
        int(r.get("Qtd Nilson", 0) or 0),
        float(r.get("Valor Mae (R$)", 0) or 0),
        float(r.get("Valor Deyvid (R$)", 0) or 0),
        float(r.get("Valor Nilson (R$)", 0) or 0),
        float(r.get("Resultado Mae (R$)", 0) or 0),
        float(r.get("Resultado Deyvid (R$)", 0) or 0),
        float(r.get("Resultado Nilson (R$)", 0) or 0),
        str(r.get("Descrição", "") or ""),
    )
