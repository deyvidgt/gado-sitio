#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🐄 SISTEMA DE GESTÃO DE GADO - FAMÍLIA - SÍTIO SANTO ANTONIO
Membros: Mãe, Deyvid, Nilson
Versão 2.1 — interface visual com Rich
"""

import pandas as pd
import os
import sys
import shutil
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

try:
    import requests
    from bs4 import BeautifulSoup
    WEB_DISPONIVEL = True
except ImportError:
    WEB_DISPONIVEL = False

# ── Rich ──────────────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich import box
    from rich.text import Text
    from rich.prompt import Prompt, IntPrompt, Confirm
    from rich.rule import Rule
    from rich.padding import Padding
    from rich.align import Align
    RICH = True
except ImportError:
    RICH = False

console = Console() if RICH else None

# ── Helpers de UI ─────────────────────────────────────────────────────────────

def ui_titulo(texto):
    if RICH:
        console.print()
        console.rule(f"[bold green]{texto}[/bold green]")
        console.print()
    else:
        print(f"\n=== {texto} ===\n")

def ui_ok(msg):
    if RICH:
        console.print(f"[bold green]✔[/bold green]  {msg}")
    else:
        print(f"✅ {msg}")

def ui_erro(msg):
    if RICH:
        console.print(f"[bold red]✘[/bold red]  {msg}")
    else:
        print(f"❌ {msg}")

def ui_aviso(msg):
    if RICH:
        console.print(f"[bold yellow]⚠[/bold yellow]  {msg}")
    else:
        print(f"⚠️  {msg}")

def ui_info(msg):
    if RICH:
        console.print(f"[dim]  {msg}[/dim]")
    else:
        print(f"   {msg}")

def ui_painel(titulo, conteudo, estilo="green"):
    if RICH:
        console.print(Panel(conteudo, title=f"[bold]{titulo}[/bold]",
                            border_style=estilo, padding=(0, 2)))
    else:
        print(f"\n--- {titulo} ---\n{conteudo}\n")

def ui_separador():
    if RICH:
        console.rule(style="dim green")
    else:
        print("─" * 58)

def ui_tabela(titulo, colunas, linhas, estilos_col=None, cor_header="green"):
    """Exibe uma tabela formatada com Rich."""
    if not RICH:
        print(f"\n{titulo}")
        print("  ".join(str(c) for c in colunas))
        for l in linhas:
            print("  ".join(str(v) for v in l))
        return

    t = Table(title=titulo, box=box.ROUNDED,
              header_style=f"bold white on {cor_header}",
              border_style="green", show_lines=True)

    estilos_col = estilos_col or {}
    for i, col in enumerate(colunas):
        estilo = estilos_col.get(i, "")
        t.add_column(col, style=estilo, no_wrap=False)

    for linha in linhas:
        t.add_row(*[str(v) if v is not None else "" for v in linha])

    console.print(t)

def ui_input(prompt, default=None):
    if RICH:
        sufixo = f" [dim][{default}][/dim]" if default is not None else ""
        return Prompt.ask(f"[cyan]  {prompt}[/cyan]{sufixo}", default=str(default) if default is not None else "")
    else:
        suf = f" [{default}]" if default is not None else ""
        return input(f"  {prompt}{suf}: ").strip()

def ui_int(prompt, minv=0, maxv=999999, default=None):
    while True:
        s = ui_input(prompt, default)
        try:
            v = int(s)
            if minv <= v <= maxv:
                return v
            ui_aviso(f"Digite entre {minv} e {maxv}.")
        except (ValueError, TypeError):
            ui_aviso("Digite um número inteiro.")

def ui_float(prompt, default=None):
    while True:
        s = ui_input(prompt, default)
        try:
            return float(s.replace(",", "."))
        except (ValueError, AttributeError):
            ui_aviso("Digite um número válido.")

# ==============================
# Configurações
# ==============================

ARQUIVO_DADOS = "gado_familia.xlsx"
MEMBROS = ["Mae", "Deyvid", "Nilson"]
NOMES_MEMBROS = {"Mae": "Mãe", "Deyvid": "Deyvid", "Nilson": "Nilson"}
TIPOS_GASTO = [
    "Remédio/Vacina", "Sal/Proteínado", "Gasolina/Transporte",
    "Veneno/Defensivo", "Calcário/Adubação", "Manutenção/Outros"
]
TIPOS_MANEJO = [
    "Vacinação", "Vermifugação", "Pesagem",
    "Morte/Perda", "Nascimento", "Tratamento Veterinário",
    "Movimentação de Pasto", "Outro"
]

# ==============================
# 🔒 BACKUP AUTOMÁTICO
# ==============================

def fazer_backup():
    if not os.path.exists(ARQUIVO_DADOS):
        return
    os.makedirs("backups", exist_ok=True)
    nome = f"backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    shutil.copy(ARQUIVO_DADOS, nome)
    return nome


# ==============================
# 📦 INICIALIZAÇÃO
# ==============================

def inicializar():
    if not os.path.exists(ARQUIVO_DADOS):
        wb = Workbook()

        ws_compras = wb.active
        ws_compras.title = "Compras"
        ws_compras.append([
            "Data", "Qtd Cabeças", "Valor Total (R$)",
            "Valor/Cabeça (R$)", "Descrição", "Registrado Por"
        ])

        ws_gastos = wb.create_sheet("Gastos")
        ws_gastos.append([
            "Data", "Tipo", "Descrição", "Valor Total (R$)",
            "Qtd Cabeças", "Valor/Cabeça (R$)", "Registrado Por"
        ])

        ws_vendas = wb.create_sheet("Vendas")
        ws_vendas.append([
            "Data", "Qtd Cabeças", "Valor Total (R$)",
            "Valor/Cabeça (R$)", "Valor Arroba (R$)",
            "Qtd Mae", "Qtd Deyvid", "Qtd Nilson",
            "Valor Mae (R$)", "Valor Deyvid (R$)", "Valor Nilson (R$)",
            "Descrição"
        ])

        ws_manejo = wb.create_sheet("Manejo")
        ws_manejo.append([
            "Data", "Tipo", "Qtd Cabeças", "Descrição", "Responsável"
        ])

        wb.create_sheet("Resumo")
        wb.save(ARQUIVO_DADOS)
        print("✅ Arquivo de dados criado:", ARQUIVO_DADOS)


# ==============================
# 📂 BASE
# ==============================

def carregar_aba(aba):
    try:
        df = pd.read_excel(ARQUIVO_DADOS, sheet_name=aba)
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


def salvar_linha(aba, linha):
    wb = load_workbook(ARQUIVO_DADOS)
    ws = wb[aba]
    # Converter datas para string legível antes de salvar
    linha_conv = []
    for v in linha:
        if isinstance(v, datetime):
            linha_conv.append(v.strftime("%d/%m/%Y"))
        else:
            linha_conv.append(v)
    ws.append(linha_conv)
    wb.save(ARQUIVO_DADOS)


def reescrever_aba(aba, df):
    """Reescreve uma aba inteira a partir de um DataFrame."""
    wb = load_workbook(ARQUIVO_DADOS)
    ws = wb[aba]
    # Apaga tudo exceto cabeçalho
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.value = None
    # Reescreve linha a linha
    for _, row in df.iterrows():
        linha = []
        for v in row:
            if pd.isna(v) if not isinstance(v, str) else False:
                linha.append(None)
            elif isinstance(v, pd.Timestamp):
                linha.append(v.strftime("%d/%m/%Y"))
            else:
                linha.append(v)
        ws.append(linha)
    wb.save(ARQUIVO_DADOS)


# ==============================
# MÓDULO: Compras
# ==============================

def adicionar_compra():
    ui_titulo("NOVA COMPRA 🛒")
    data = _input_data()
    cabecas = ui_int("Quantidade de cabeças compradas", 1)
    valor = ui_float("Valor total da compra (R$)")
    descricao = ui_input("Descrição (ex: Nelore, Garrotes...)").strip()
    registrado = _escolher_membro("Quem está registrando?")

    valor_cabeca = round(valor / cabecas, 2) if cabecas > 0 else 0

    salvar_linha("Compras", [data, cabecas, valor, valor_cabeca, descricao, registrado])
    ui_ok(f"Compra registrada! {cabecas} cabeças por R$ {valor:.2f} (R$ {valor_cabeca:.2f}/cabeça)")


# ==============================
# MÓDULO: Gastos
# ==============================

def adicionar_gasto():
    ui_titulo("NOVO GASTO 💸")
    data = _input_data()

    ui_info("Tipos de gasto:")
    for i, t in enumerate(TIPOS_GASTO, 1):
        ui_info(f"  {i}. {t}")
    tipo_idx = ui_int("Escolha o tipo (número)", 1, len(TIPOS_GASTO))
    tipo = TIPOS_GASTO[tipo_idx - 1]

    descricao = ui_input("Detalhe do gasto").strip()
    valor = ui_float("Valor total (R$)")

    estoque = calcular_estoque()
    cab_str = ui_input(f"Quantas cabeças (Enter = todas [{estoque}])", estoque).strip()
    ref_cabecas = int(cab_str) if cab_str.isdigit() and int(cab_str) > 0 else estoque

    registrado = _escolher_membro("Quem está registrando?")

    valor_cabeca = round(valor / ref_cabecas, 4) if ref_cabecas > 0 else 0

    salvar_linha("Gastos", [data, tipo, descricao, valor, ref_cabecas, valor_cabeca, registrado])
    ui_ok(f"Gasto registrado! R$ {valor:.2f} ({tipo})")
    if ref_cabecas > 0:
        ui_info(f"→ R$ {valor_cabeca:.2f}/cabeça sobre {ref_cabecas} cabeças")


# ==============================
# MÓDULO: Vendas
# ==============================

def adicionar_venda():
    ui_titulo("NOVA VENDA 🤝")
    data = _input_data()
    cabecas = ui_int("Quantidade de cabeças vendidas", 1)
    valor = ui_float("Valor total recebido (R$)")

    arroba_str = ui_input("Valor da arroba (R$) [Enter para pular]", "0").strip()
    try:
        arroba = float(arroba_str.replace(",", ".")) if arroba_str else 0.0
    except ValueError:
        arroba = 0.0

    descricao = ui_input("Descrição da venda").strip()

    ui_info(f"Distribuição entre membros (total: {cabecas} cabeças)")
    qtd_mae    = ui_int("  Mãe", 0, cabecas)
    qtd_deyvid = ui_int("  Deyvid", 0, cabecas)
    qtd_nilson = ui_int("  Nilson", 0, cabecas)

    total_cotas = qtd_mae + qtd_deyvid + qtd_nilson
    if total_cotas != cabecas:
        ui_aviso(f"Soma ({total_cotas}) ≠ cabeças vendidas ({cabecas}). Ajustando proporcionalmente.")
        fator = cabecas / total_cotas if total_cotas > 0 else 0
        qtd_mae    = round(qtd_mae * fator)
        qtd_deyvid = round(qtd_deyvid * fator)
        qtd_nilson = cabecas - qtd_mae - qtd_deyvid

    valor_mae    = round(valor * (qtd_mae    / cabecas), 2) if cabecas > 0 else 0
    valor_deyvid = round(valor * (qtd_deyvid / cabecas), 2) if cabecas > 0 else 0
    valor_nilson = round(valor - valor_mae - valor_deyvid, 2)
    valor_cabeca = round(valor / cabecas, 2) if cabecas > 0 else 0

    salvar_linha("Vendas", [
        data, cabecas, valor, valor_cabeca, arroba,
        qtd_mae, qtd_deyvid, qtd_nilson,
        valor_mae, valor_deyvid, valor_nilson,
        descricao
    ])

    ui_ok(f"Venda registrada!")
    ui_info(f"🐄 {cabecas} cabeças → R$ {valor:.2f} (R$ {valor_cabeca:.2f}/cabeça)")
    ui_info(f"👩 Mãe:    {qtd_mae} cabeças → R$ {valor_mae:.2f}")
    ui_info(f"👦 Deyvid: {qtd_deyvid} cabeças → R$ {valor_deyvid:.2f}")
    ui_info(f"👦 Nilson: {qtd_nilson} cabeças → R$ {valor_nilson:.2f}")

    imp = ui_input("Deseja imprimir o recibo desta venda? (s/n)", "n").strip().lower()
    if imp == "s":
        _imprimir_recibo(data, cabecas, valor, valor_cabeca, arroba,
                         qtd_mae, qtd_deyvid, qtd_nilson,
                         valor_mae, valor_deyvid, valor_nilson, descricao)


# ==============================
# MÓDULO: Manejo
# ==============================

def adicionar_manejo():
    ui_titulo("REGISTRO DE MANEJO 🩺")
    for i, t in enumerate(TIPOS_MANEJO, 1):
        ui_info(f"  {i}. {t}")
    tipo_idx = ui_int("Tipo de manejo", 1, len(TIPOS_MANEJO))
    tipo = TIPOS_MANEJO[tipo_idx - 1]

    data = _input_data()
    cabecas = ui_int("Quantidade de cabeças envolvidas", 0)
    descricao = ui_input("Descrição").strip()
    responsavel = _escolher_membro("Responsável pelo manejo?")

    salvar_linha("Manejo", [data, tipo, cabecas, descricao, responsavel])
    ui_ok(f"Manejo registrado! ({tipo} - {cabecas} cabeças)")


# ==============================
# ✏️ EDITAR REGISTRO
# ==============================

def editar_registro():
    ui_titulo("EDITAR REGISTRO ✏️")
    abas = ["Compras", "Gastos", "Vendas", "Manejo"]
    for i, a in enumerate(abas, 1):
        ui_info(f"  {i}. {a}")
    idx_aba = ui_int("Aba", 1, len(abas)) - 1
    aba = abas[idx_aba]

    df = carregar_aba(aba)
    if df.empty:
        ui_aviso("Nenhum registro encontrado.")
        return

    # Exibir registros
    colunas = list(df.columns)
    linhas = []
    for i, row in df.iterrows():
        linha = [str(i)]
        for v in row:
            if isinstance(v, pd.Timestamp):
                linha.append(v.strftime("%d/%m/%Y"))
            else:
                linha.append("" if (not isinstance(v, str) and pd.isna(v)) else str(v))
        linhas.append(linha)
    ui_tabela(f"Registros — {aba}", ["#"] + colunas, linhas)

    idx = ui_int(f"Índice do registro para editar (0 a {len(df)-1})", 0, len(df) - 1)
    registro = df.iloc[idx]

    ui_info(f"Editando registro {idx}. Deixe em branco para manter o valor atual.")
    ui_separador()

    novos_valores = {}
    for col in df.columns:
        val_atual = registro[col]
        if isinstance(val_atual, pd.Timestamp):
            val_atual_str = val_atual.strftime("%d/%m/%Y")
        elif not isinstance(val_atual, str) and pd.isna(val_atual):
            val_atual_str = ""
        else:
            val_atual_str = str(val_atual)

        entrada = ui_input(f"  {col}", val_atual_str if val_atual_str else None).strip()
        if entrada == "" or entrada == val_atual_str:
            novos_valores[col] = registro[col]
        else:
            try:
                if isinstance(val_atual, int) or (isinstance(val_atual, float) and val_atual == int(val_atual)):
                    novos_valores[col] = int(entrada)
                elif isinstance(val_atual, float):
                    novos_valores[col] = float(entrada.replace(",", "."))
                elif isinstance(val_atual, pd.Timestamp):
                    novos_valores[col] = pd.to_datetime(entrada, dayfirst=True)
                else:
                    novos_valores[col] = entrada
            except Exception:
                novos_valores[col] = entrada

    confirmar = ui_input("Confirmar edição? (s/n)", "n").strip().lower()
    if confirmar != "s":
        ui_aviso("Edição cancelada.")
        return

    fazer_backup()
    for col, val in novos_valores.items():
        df.at[idx, col] = val

    reescrever_aba(aba, df)
    ui_ok("Registro editado com sucesso!")


# ==============================
# 🗑️ EXCLUIR REGISTRO
# ==============================

def excluir_registro():
    ui_titulo("EXCLUIR REGISTRO 🗑️")
    abas = ["Compras", "Gastos", "Vendas", "Manejo"]
    for i, a in enumerate(abas, 1):
        ui_info(f"  {i}. {a}")
    idx_aba = ui_int("Aba", 1, len(abas)) - 1
    aba = abas[idx_aba]

    df = carregar_aba(aba)
    if df.empty:
        ui_aviso("Nenhum registro encontrado.")
        return

    colunas = list(df.columns)
    linhas = []
    for i, row in df.iterrows():
        linha = [str(i)]
        for v in row:
            if isinstance(v, pd.Timestamp):
                linha.append(v.strftime("%d/%m/%Y"))
            else:
                linha.append("" if (not isinstance(v, str) and pd.isna(v)) else str(v))
        linhas.append(linha)
    ui_tabela(f"Registros — {aba}", ["#"] + colunas, linhas)

    idx = ui_int(f"Índice para excluir (0 a {len(df)-1})", 0, len(df) - 1)

    ui_info("Registro selecionado:")
    for col in df.columns:
        ui_info(f"  {col}: {df.iloc[idx][col]}")

    confirmar = ui_input("Tem certeza? (s/n)", "n").strip().lower()
    if confirmar != "s":
        ui_aviso("Cancelado.")
        return

    fazer_backup()
    df = df.drop(idx).reset_index(drop=True)
    reescrever_aba(aba, df)
    ui_ok("Registro excluído!")


# ==============================
# ⚠️ ALERTAS INTELIGENTES
# ==============================

def verificar_alertas():
    ui_titulo("ALERTAS DE SAÚDE ⚠️")
    df = carregar_aba("Manejo")
    if df.empty:
        ui_aviso("Sem registros de manejo para verificar alertas.")
        return

    hoje = datetime.now()
    alertas = []

    for tipo, dias_limite, emoji in [
        ("Vacinação", 180, "💉"),
        ("Vermifugação", 120, "🐛"),
    ]:
        df_tipo = df[df["Tipo"] == tipo].copy()
        if df_tipo.empty:
            alertas.append(f"{emoji} Nenhum registro de {tipo} encontrado!")
            continue

        df_tipo["Data"] = pd.to_datetime(df_tipo["Data"], dayfirst=True, errors="coerce")
        ultima = df_tipo["Data"].max()
        if pd.isna(ultima):
            continue

        dias = (hoje - ultima).days
        if dias > dias_limite:
            alertas.append(
                f"{emoji} {tipo} atrasada! Último: {ultima.strftime('%d/%m/%Y')} "
                f"({dias} dias atrás — limite: {dias_limite} dias)"
            )

    df_mortes = df[df["Tipo"] == "Morte/Perda"].copy()
    if not df_mortes.empty:
        df_mortes["Data"] = pd.to_datetime(df_mortes["Data"], dayfirst=True, errors="coerce")
        recentes = df_mortes[df_mortes["Data"] >= pd.Timestamp(hoje - timedelta(days=30))]
        if not recentes.empty:
            total_mortes = int(recentes["Qtd Cabeças"].sum())
            alertas.append(f"💀 {total_mortes} morte(s)/perda(s) nos últimos 30 dias")

    if alertas:
        for a in alertas:
            ui_aviso(a)
    else:
        ui_ok("Nenhum alerta no momento.")


# ==============================
# 📊 RESUMO E RELATÓRIOS
# ==============================

def calcular_estoque():
    df_comp = carregar_aba("Compras")
    df_vend = carregar_aba("Vendas")
    df_man = carregar_aba("Manejo")

    compradas = int(df_comp["Qtd Cabeças"].sum()) if not df_comp.empty and "Qtd Cabeças" in df_comp.columns else 0
    vendidas = int(df_vend["Qtd Cabeças"].sum()) if not df_vend.empty and "Qtd Cabeças" in df_vend.columns else 0

    mortes = 0
    if not df_man.empty and "Tipo" in df_man.columns:
        mortes = int(df_man[df_man["Tipo"] == "Morte/Perda"]["Qtd Cabeças"].sum())

    nascimentos = 0
    if not df_man.empty and "Tipo" in df_man.columns:
        nascimentos = int(df_man[df_man["Tipo"] == "Nascimento"]["Qtd Cabeças"].sum())

    return compradas - vendidas - mortes + nascimentos


def ver_resumo_geral():
    ui_titulo("RESUMO GERAL DO REBANHO 🐄")
    df_comp = carregar_aba("Compras")
    df_gast = carregar_aba("Gastos")
    df_vend = carregar_aba("Vendas")

    total_comp  = df_comp["Valor Total (R$)"].sum() if not df_comp.empty else 0
    total_gast  = df_gast["Valor Total (R$)"].sum() if not df_gast.empty else 0
    total_vend  = df_vend["Valor Total (R$)"].sum() if not df_vend.empty else 0
    total_custo = total_comp + total_gast

    cab_comp = int(df_comp["Qtd Cabeças"].sum()) if not df_comp.empty else 0
    cab_vend = int(df_vend["Qtd Cabeças"].sum()) if not df_vend.empty else 0
    estoque  = calcular_estoque()

    lucro = total_vend - total_custo
    roi   = (lucro / total_custo * 100) if total_custo > 0 else 0

    linhas_resumo = [
        ("📦 Cabeças compradas",        str(cab_comp)),
        ("💰 Cabeças vendidas",         str(cab_vend)),
        ("🐄 Estoque atual",            str(estoque)),
        ("─", "─"),
        ("💸 Total investido (compras)", f"R$ {total_comp:,.2f}"),
        ("🔧 Total gastos (manejo)",     f"R$ {total_gast:,.2f}"),
        ("📊 CUSTO TOTAL",              f"R$ {total_custo:,.2f}"),
        ("🤝 Total recebido (vendas)",  f"R$ {total_vend:,.2f}"),
        ("─", "─"),
        ("✅ Lucro/Prejuízo" if lucro >= 0 else "❌ Lucro/Prejuízo", f"R$ {lucro:,.2f}"),
        ("📈 ROI",                      f"{roi:.1f}%"),
    ]
    ui_tabela("Resumo Geral", ["Indicador", "Valor"], linhas_resumo)

    if cab_comp > 0:
        custo_medio  = total_custo / cab_comp
        ui_info(f"Custo médio total/cabeça:  R$ {custo_medio:,.2f}")
        if estoque > 0:
            ui_info(f"Valor estimado do estoque: R$ {estoque * custo_medio:,.2f} ({estoque} × R$ {custo_medio:,.2f})")

    if not df_vend.empty:
        ui_separador()
        ui_info("RESUMO POR MEMBRO (vendas)")
        gasto_por_membro = total_gast / 3
        for membro, col_qtd, col_val in [
            ("Mãe",    "Qtd Mae",    "Valor Mae (R$)"),
            ("Deyvid", "Qtd Deyvid", "Valor Deyvid (R$)"),
            ("Nilson", "Qtd Nilson", "Valor Nilson (R$)"),
        ]:
            qtd = int(df_vend[col_qtd].sum()) if col_qtd in df_vend.columns else 0
            val = df_vend[col_val].sum()       if col_val in df_vend.columns else 0
            custo_compra = (total_comp * qtd / cab_vend) if cab_vend > 0 else 0
            custo_total  = custo_compra + gasto_por_membro
            resultado    = val - custo_total
            sinal        = "✅" if resultado >= 0 else "❌"
            ui_info(
                f"👤 {membro:<8} | {qtd:>3} cab. | "
                f"Vendas: R${val:>10,.2f} | "
                f"Custo: R${custo_total:>9,.2f} | "
                f"{sinal} R${resultado:>10,.2f}"
            )


def ver_resumo_por_membro():
    df_vend = carregar_aba("Vendas")
    df_gast = carregar_aba("Gastos")
    df_comp = carregar_aba("Compras")

    total_gast = df_gast["Valor Total (R$)"].sum() if not df_gast.empty else 0
    total_comp = df_comp["Valor Total (R$)"].sum() if not df_comp.empty else 0
    cab_vend = int(df_vend["Qtd Cabeças"].sum()) if not df_vend.empty else 0
    gasto_por_membro = total_gast / 3

    print("\n" + "═"*58)
    print("👨‍👩‍👦  RESUMO INDIVIDUAL POR MEMBRO")
    print("═"*58)

    for membro, col_qtd, col_val in [
        ("Mãe",    "Qtd Mae",    "Valor Mae (R$)"),
        ("Deyvid", "Qtd Deyvid", "Valor Deyvid (R$)"),
        ("Nilson", "Qtd Nilson", "Valor Nilson (R$)"),
    ]:
        print(f"\n👤 {membro.upper()}")
        print("─"*45)

        total_cabecas = 0
        total_recebido = 0

        if not df_vend.empty and col_qtd in df_vend.columns:
            for _, row in df_vend.iterrows():
                data_str = row["Data"].strftime("%d/%m/%Y") if pd.notna(row.get("Data")) else "?"
                qtd = int(row.get(col_qtd, 0) or 0)
                val = float(row.get(col_val, 0) or 0)
                if qtd > 0:
                    total_cabecas += qtd
                    total_recebido += val
                    print(f"  {data_str}: {qtd} cabeças → R$ {val:,.2f}")

        custo_compra = (total_comp * total_cabecas / cab_vend) if cab_vend > 0 else 0
        custo_total = custo_compra + gasto_por_membro

        print(f"  {'─'*41}")
        print(f"  Total vendido:       {total_cabecas} cabeças → R$ {total_recebido:,.2f}")
        print(f"  Custo compra (prop): R$ {custo_compra:,.2f}")
        print(f"  Gastos divididos:    R$ {gasto_por_membro:,.2f}")
        lucro = total_recebido - custo_total
        sinal = "✅" if lucro >= 0 else "❌"
        print(f"  {sinal} Resultado líquido:  R$ {lucro:,.2f}")


# ==============================
# 📅 RELATÓRIO POR PERÍODO
# ==============================

def relatorio_por_periodo():
    print("\n📅 === RELATÓRIO POR PERÍODO ===")
    print("Informe o período desejado:")
    data_ini = _input_data_simples("Data inicial (dd/mm/aaaa): ")
    data_fim = _input_data_simples("Data final   (dd/mm/aaaa): ")

    dt_ini = datetime.strptime(data_ini, "%d/%m/%Y")
    dt_fim = datetime.strptime(data_fim, "%d/%m/%Y")

    def filtrar(df):
        if df.empty or "Data" not in df.columns:
            return df
        df = df.copy()
        df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
        return df[(df["Data"] >= dt_ini) & (df["Data"] <= dt_fim)]

    df_comp = filtrar(carregar_aba("Compras"))
    df_gast = filtrar(carregar_aba("Gastos"))
    df_vend = filtrar(carregar_aba("Vendas"))
    df_man  = filtrar(carregar_aba("Manejo"))

    total_comp = df_comp["Valor Total (R$)"].sum() if not df_comp.empty else 0
    total_gast = df_gast["Valor Total (R$)"].sum() if not df_gast.empty else 0
    total_vend = df_vend["Valor Total (R$)"].sum() if not df_vend.empty else 0
    total_custo = total_comp + total_gast
    lucro = total_vend - total_custo

    cab_comp = int(df_comp["Qtd Cabeças"].sum()) if not df_comp.empty else 0
    cab_vend = int(df_vend["Qtd Cabeças"].sum()) if not df_vend.empty else 0

    print(f"\n{'═'*58}")
    print(f"📅 PERÍODO: {data_ini} até {data_fim}")
    print(f"{'═'*58}")
    print(f"  🛒 Compras realizadas:     {len(df_comp):>3} registros | {cab_comp} cabeças | R$ {total_comp:,.2f}")
    print(f"  💸 Gastos registrados:     {len(df_gast):>3} registros | R$ {total_gast:,.2f}")
    print(f"  🤝 Vendas realizadas:      {len(df_vend):>3} registros | {cab_vend} cabeças | R$ {total_vend:,.2f}")
    print(f"  🩺 Eventos de manejo:      {len(df_man):>3} registros")
    print(f"{'─'*58}")
    print(f"  📊 Custo total:            R$ {total_custo:,.2f}")
    print(f"  💰 Receita total:          R$ {total_vend:,.2f}")
    sinal = "✅" if lucro >= 0 else "❌"
    print(f"  {sinal} Resultado:             R$ {lucro:,.2f}")
    print(f"{'═'*58}")

    # Detalhes por tipo de gasto
    if not df_gast.empty and "Tipo" in df_gast.columns:
        print("\n  💸 Gastos por categoria:")
        resumo_gastos = df_gast.groupby("Tipo")["Valor Total (R$)"].sum().sort_values(ascending=False)
        for tipo, val in resumo_gastos.items():
            pct = val / total_gast * 100 if total_gast > 0 else 0
            print(f"    {tipo:<30} R$ {val:>10,.2f}  ({pct:.1f}%)")


# ==============================
# 📊 COMPARATIVO ANUAL
# ==============================

def comparativo_anual():
    print("\n📊 === COMPARATIVO ANUAL ===")

    df_comp = carregar_aba("Compras")
    df_gast = carregar_aba("Gastos")
    df_vend = carregar_aba("Vendas")

    def add_ano(df):
        if df.empty or "Data" not in df.columns:
            return df
        df = df.copy()
        df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
        df["Ano"] = df["Data"].dt.year
        return df

    df_comp = add_ano(df_comp)
    df_gast = add_ano(df_gast)
    df_vend = add_ano(df_vend)

    anos = set()
    for df in [df_comp, df_gast, df_vend]:
        if not df.empty and "Ano" in df.columns:
            anos |= set(df["Ano"].dropna().astype(int).tolist())

    if not anos:
        print("Sem dados para exibir.")
        return

    anos = sorted(anos)
    print(f"\n{'Ano':<6} {'Compras':>12} {'Gastos':>12} {'Vendas':>12} {'Lucro':>12} {'ROI':>7}")
    print("─"*62)

    for ano in anos:
        comp_ano = df_comp[df_comp["Ano"] == ano]["Valor Total (R$)"].sum() if not df_comp.empty and "Ano" in df_comp.columns else 0
        gast_ano = df_gast[df_gast["Ano"] == ano]["Valor Total (R$)"].sum() if not df_gast.empty and "Ano" in df_gast.columns else 0
        vend_ano = df_vend[df_vend["Ano"] == ano]["Valor Total (R$)"].sum() if not df_vend.empty and "Ano" in df_vend.columns else 0
        custo = comp_ano + gast_ano
        lucro = vend_ano - custo
        roi = (lucro / custo * 100) if custo > 0 else 0
        sinal = "+" if lucro >= 0 else ""
        print(f"{ano:<6} {comp_ano:>12,.0f} {gast_ano:>12,.0f} {vend_ano:>12,.0f} "
              f"{sinal}{lucro:>11,.0f} {roi:>6.1f}%")

    print("─"*62)
    # Totais
    t_comp = df_comp["Valor Total (R$)"].sum() if not df_comp.empty else 0
    t_gast = df_gast["Valor Total (R$)"].sum() if not df_gast.empty else 0
    t_vend = df_vend["Valor Total (R$)"].sum() if not df_vend.empty else 0
    t_custo = t_comp + t_gast
    t_lucro = t_vend - t_custo
    t_roi = (t_lucro / t_custo * 100) if t_custo > 0 else 0
    sinal = "+" if t_lucro >= 0 else ""
    print(f"{'TOTAL':<6} {t_comp:>12,.0f} {t_gast:>12,.0f} {t_vend:>12,.0f} "
          f"{sinal}{t_lucro:>11,.0f} {t_roi:>6.1f}%")


# ==============================
# 🐄 ESTIMATIVA DO REBANHO
# ==============================

def estimativa_rebanho():
    print("\n🐄 === ESTIMATIVA DO VALOR DO REBANHO ===")

    estoque = calcular_estoque()
    if estoque <= 0:
        print("Sem cabeças em estoque.")
        return

    print(f"\nEstoque atual: {estoque} cabeças")
    print("\nForma de estimativa:")
    print("  1. Pelo preço da arroba")
    print("  2. Pelo preço à vista por cabeça")
    print("  3. Pelo custo médio de aquisição")

    opcao = _input_int("Escolha: ", 1, 3)

    df_comp = carregar_aba("Compras")
    df_gast = carregar_aba("Gastos")
    total_custo = (df_comp["Valor Total (R$)"].sum() if not df_comp.empty else 0) + \
                  (df_gast["Valor Total (R$)"].sum() if not df_gast.empty else 0)
    cab_comp = int(df_comp["Qtd Cabeças"].sum()) if not df_comp.empty else 0
    custo_medio = total_custo / cab_comp if cab_comp > 0 else 0

    if opcao == 1:
        peso_str = input("Peso médio estimado dos animais (kg) [Ex: 200]: ").strip()
        peso = float(peso_str.replace(",", ".")) if peso_str else 200.0
        arrobas = peso / 15  # 1 arroba = 15 kg

        # Tentar cotação online
        cotacao = None
        if WEB_DISPONIVEL:
            print("Buscando cotação online...")
            cotacao = obter_cotacao_imea()

        if cotacao:
            print(f"\nCotações IMEA disponíveis:")
            for k, v in cotacao.items():
                print(f"  {k}: R$ {v:.2f}/@")
            arroba_str = input("Valor da arroba a usar (R$) [ou Enter para digitar]: ").strip()
        else:
            arroba_str = ""

        if not arroba_str:
            arroba_str = input("Valor da arroba (R$): ").strip()

        arroba = float(arroba_str.replace(",", "."))
        valor_cabeca = arrobas * arroba
        valor_total = valor_cabeca * estoque

        print(f"\n{'═'*50}")
        print(f"  🐄 Estoque:            {estoque} cabeças")
        print(f"  ⚖️  Peso médio:          {peso:.0f} kg ({arrobas:.1f} @/cabeça)")
        print(f"  💲 Cotação arroba:      R$ {arroba:.2f}/@")
        print(f"  💰 Valor/cabeça:        R$ {valor_cabeca:,.2f}")
        print(f"  {'─'*46}")
        print(f"  📦 VALOR ESTIMADO:      R$ {valor_total:,.2f}")
        lucro_potencial = valor_total - total_custo
        sinal = "✅" if lucro_potencial >= 0 else "❌"
        print(f"  {sinal} Lucro potencial:     R$ {lucro_potencial:,.2f}")
        print(f"{'═'*50}")

    elif opcao == 2:
        preco_str = input("Preço à vista por cabeça (R$): ").strip()
        preco = float(preco_str.replace(",", "."))
        valor_total = preco * estoque

        print(f"\n{'═'*50}")
        print(f"  🐄 Estoque:            {estoque} cabeças")
        print(f"  💲 Preço/cabeça:       R$ {preco:,.2f}")
        print(f"  {'─'*46}")
        print(f"  📦 VALOR ESTIMADO:     R$ {valor_total:,.2f}")
        lucro_potencial = valor_total - total_custo
        sinal = "✅" if lucro_potencial >= 0 else "❌"
        print(f"  {sinal} Lucro potencial:    R$ {lucro_potencial:,.2f}")
        print(f"{'═'*50}")

    elif opcao == 3:
        valor_total = custo_medio * estoque
        print(f"\n{'═'*50}")
        print(f"  🐄 Estoque:            {estoque} cabeças")
        print(f"  💲 Custo médio/cabeça: R$ {custo_medio:,.2f}")
        print(f"  {'─'*46}")
        print(f"  📦 VALOR (custo):      R$ {valor_total:,.2f}")
        print(f"{'═'*50}")
        print("  ⚠️  Este é o custo de aquisição, não o valor de mercado.")


# ==============================
# 🧾 RECIBO DE VENDA
# ==============================

def _imprimir_recibo(data, cabecas, valor, valor_cabeca, arroba,
                      qtd_mae, qtd_deyvid, qtd_nilson,
                      valor_mae, valor_deyvid, valor_nilson, descricao):
    data_str = data if isinstance(data, str) else datetime.strptime(data, "%d/%m/%Y").strftime("%d/%m/%Y")
    linha = "═" * 50
    print(f"\n{linha}")
    print(f"  🧾 RECIBO DE VENDA — SÍTIO SANTO ANTONIO")
    print(f"  Família: Mãe, Deyvid e Nilson")
    print(linha)
    print(f"  Data:          {data_str}")
    print(f"  Descrição:     {descricao}")
    print(f"  Cabeças:       {cabecas}")
    print(f"  Valor total:   R$ {valor:,.2f}")
    print(f"  Valor/cabeça:  R$ {valor_cabeca:,.2f}")
    if arroba:
        print(f"  Valor arroba:  R$ {arroba:,.2f}/@")
    print(f"{'─'*50}")
    print(f"  DISTRIBUIÇÃO:")
    print(f"  👩 Mãe:        {qtd_mae:>3} cabeças → R$ {valor_mae:,.2f}")
    print(f"  👦 Deyvid:     {qtd_deyvid:>3} cabeças → R$ {valor_deyvid:,.2f}")
    print(f"  👦 Nilson:     {qtd_nilson:>3} cabeças → R$ {valor_nilson:,.2f}")
    print(f"{linha}")
    print(f"  Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}")
    print(f"{linha}\n")


def recibo_ultima_venda():
    df = carregar_aba("Vendas")
    if df.empty:
        print("Sem vendas registradas.")
        return
    row = df.iloc[-1]
    data_str = row["Data"].strftime("%d/%m/%Y") if pd.notna(row.get("Data")) else "?"
    _imprimir_recibo(
        data_str,
        int(row.get("Qtd Cabeças", 0) or 0),
        float(row.get("Valor Total (R$)", 0) or 0),
        float(row.get("Valor/Cabeça (R$)", 0) or 0),
        float(row.get("Valor Arroba (R$)", 0) or 0),
        int(row.get("Qtd Mae", 0) or 0),
        int(row.get("Qtd Deyvid", 0) or 0),
        int(row.get("Qtd Nilson", 0) or 0),
        float(row.get("Valor Mae (R$)", 0) or 0),
        float(row.get("Valor Deyvid (R$)", 0) or 0),
        float(row.get("Valor Nilson (R$)", 0) or 0),
        str(row.get("Descrição", "") or ""),
    )


# ==============================
# 📋 LISTAR REGISTROS
# ==============================

def listar_registros():
    print("\n📋 === TODOS OS REGISTROS ===")
    abas = ["Compras", "Gastos", "Vendas", "Manejo"]
    for aba in abas:
        df = carregar_aba(aba)
        if not df.empty:
            print(f"\n{'═'*60}")
            print(f"  📁 {aba.upper()} ({len(df)} registros)")
            print('═'*60)
            with pd.option_context('display.max_columns', None,
                                   'display.width', 130,
                                   'display.float_format', '{:.2f}'.format):
                print(df.to_string(index=True))
        else:
            print(f"\n📁 {aba}: (sem registros)")


# ==============================
# 📊 GRÁFICOS
# ==============================

def gerar_graficos():
    print("\n📊 === GRÁFICOS ===")
    print("  1. Evolução das vendas")
    print("  2. Gastos por categoria")
    print("  3. Comparativo receita × custo")
    opcao = _input_int("Escolha: ", 1, 3)

    if opcao == 1:
        df = carregar_aba("Vendas")
        if df.empty:
            print("Sem dados de vendas.")
            return
        df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
        df = df.sort_values("Data").dropna(subset=["Data"])
        plt.figure(figsize=(10, 5))
        plt.plot(df["Data"], df["Valor Total (R$)"], marker="o", color="#2e7d32", linewidth=2)
        plt.fill_between(df["Data"], df["Valor Total (R$)"], alpha=0.15, color="#2e7d32")
        plt.title("📈 Evolução das Vendas — Sítio Santo Antonio", fontsize=13)
        plt.xlabel("Data")
        plt.ylabel("R$")
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))
        plt.gcf().autofmt_xdate()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.show()

    elif opcao == 2:
        df = carregar_aba("Gastos")
        if df.empty:
            print("Sem dados de gastos.")
            return
        resumo = df.groupby("Tipo")["Valor Total (R$)"].sum().sort_values(ascending=True)
        cores = ["#ef5350", "#ab47bc", "#42a5f5", "#26a69a", "#ffca28", "#8d6e63"]
        plt.figure(figsize=(9, 5))
        bars = plt.barh(resumo.index, resumo.values, color=cores[:len(resumo)])
        for bar, val in zip(bars, resumo.values):
            plt.text(bar.get_width() + 50, bar.get_y() + bar.get_height()/2,
                     f"R$ {val:,.0f}", va="center", fontsize=9)
        plt.title("💸 Gastos por Categoria", fontsize=13)
        plt.xlabel("R$")
        plt.tight_layout()
        plt.show()

    elif opcao == 3:
        df_comp = carregar_aba("Compras")
        df_gast = carregar_aba("Gastos")
        df_vend = carregar_aba("Vendas")
        labels = ["Compras", "Gastos", "Total Custo", "Vendas"]
        t_comp = df_comp["Valor Total (R$)"].sum() if not df_comp.empty else 0
        t_gast = df_gast["Valor Total (R$)"].sum() if not df_gast.empty else 0
        t_vend = df_vend["Valor Total (R$)"].sum() if not df_vend.empty else 0
        values = [t_comp, t_gast, t_comp + t_gast, t_vend]
        cores = ["#1565c0", "#e65100", "#bf360c", "#2e7d32"]
        plt.figure(figsize=(8, 5))
        bars = plt.bar(labels, values, color=cores)
        for bar, val in zip(bars, values):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 300,
                     f"R$ {val:,.0f}", ha="center", fontsize=9)
        plt.title("📊 Receita × Custo Total", fontsize=13)
        plt.ylabel("R$")
        plt.grid(axis="y", alpha=0.3)
        plt.tight_layout()
        plt.show()


# ==============================
# 📥 IMPORTAR EXCEL ANTIGO
# ==============================

def importar_excel_antigo():
    arquivo = input("Caminho do arquivo Excel original (ex: gado.xlsx): ").strip()
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return

    try:
        print(f"\n📂 Importando dados de: {arquivo}")
        wb_ant = load_workbook(arquivo, data_only=True)
        anos = [s for s in wb_ant.sheetnames if s.isdigit()]

        registros_compras = 0
        registros_gastos = 0
        registros_vendas = 0

        for ano in sorted(anos):
            df_raw = pd.read_excel(arquivo, sheet_name=ano, header=None)

            cabecas_compradas = _safe_val(df_raw, 0, 1)
            preco_compra = _safe_val(df_raw, 0, 10)

            if cabecas_compradas and preco_compra:
                salvar_linha("Compras", [
                    f"01/01/{ano}", int(cabecas_compradas),
                    float(preco_compra),
                    round(float(preco_compra) / int(cabecas_compradas), 2),
                    f"Importado do ano {ano}", "Importação"
                ])
                registros_compras += 1

            for row_idx in range(1, len(df_raw)):
                val_gasto = _safe_val(df_raw, row_idx, 6)
                desc_gasto = _safe_val(df_raw, row_idx, 7)
                if val_gasto and isinstance(val_gasto, (int, float)) and float(val_gasto) > 0:
                    salvar_linha("Gastos", [
                        f"01/01/{ano}", "Manutenção/Outros", str(desc_gasto) if desc_gasto else "",
                        float(val_gasto), 0, 0, "Importação"
                    ])
                    registros_gastos += 1

            mae_val = _safe_val(df_raw, 1, 15)
            deyvid_val = _safe_val(df_raw, 2, 15)
            nilson_val = _safe_val(df_raw, 3, 15)
            mae_qtd = _safe_val(df_raw, 1, 19)
            deyvid_qtd = _safe_val(df_raw, 2, 19)
            nilson_qtd = _safe_val(df_raw, 3, 19)

            total_vend_val = sum([
                float(v) for v in [mae_val, deyvid_val, nilson_val]
                if v and isinstance(v, (int, float)) and float(v) > 0
            ])
            total_vend_qtd = sum([
                int(q) for q in [mae_qtd, deyvid_qtd, nilson_qtd]
                if q and isinstance(q, (int, float)) and float(q) > 0
            ])

            data_venda_str = str(_safe_val(df_raw, 1, 17) or f"31/12/{ano}")[:10]

            if total_vend_val > 0:
                salvar_linha("Vendas", [
                    data_venda_str, total_vend_qtd or 0, total_vend_val,
                    round(total_vend_val / total_vend_qtd, 2) if total_vend_qtd else 0,
                    _safe_val(df_raw, 0, 12) or 0,
                    int(mae_qtd) if mae_qtd else 0,
                    int(deyvid_qtd) if deyvid_qtd else 0,
                    int(nilson_qtd) if nilson_qtd else 0,
                    float(mae_val) if mae_val else 0,
                    float(deyvid_val) if deyvid_val else 0,
                    float(nilson_val) if nilson_val else 0,
                    f"Importado do ano {ano}"
                ])
                registros_vendas += 1

        print(f"\n✅ Importação concluída!")
        print(f"   Compras importadas: {registros_compras}")
        print(f"   Gastos importados:  {registros_gastos}")
        print(f"   Vendas importadas:  {registros_vendas}")

    except Exception as e:
        print(f"❌ Erro na importação: {e}")
        import traceback
        traceback.print_exc()


# ==============================
# 📤 EXPORTAR RELATÓRIO EXCEL
# ==============================

def exportar_relatorio_excel():
    df_comp = carregar_aba("Compras")
    df_gast = carregar_aba("Gastos")
    df_vend = carregar_aba("Vendas")
    df_man  = carregar_aba("Manejo")

    nome_arquivo = f"relatorio_gado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb = Workbook()

    verde_escuro = "1B5E20"
    verde_medio  = "388E3C"
    verde_claro  = "C8E6C9"
    amarelo      = "FFF9C4"
    laranja      = "FFE0B2"
    azul_claro   = "E3F2FD"
    vermelho     = "FFCDD2"

    header_font = Font(bold=True, color="FFFFFF", size=11)
    titulo_font = Font(bold=True, size=14, color="FFFFFF")
    bold_font   = Font(bold=True, size=10)
    money_fmt   = 'R$ #,##0.00'
    border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    def estilo_header(ws, row, cols, cor):
        for col in range(1, cols + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = PatternFill("solid", start_color=cor)
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border

    def auto_largura(ws):
        for col in ws.columns:
            max_len = max((len(str(cell.value)) for cell in col if cell.value), default=10)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 35)

    # ─── Resumo ───────────────────────────────────────────────────────────
    ws = wb.active
    ws.title = "📊 Resumo Geral"
    ws.freeze_panes = "B2"

    ws.merge_cells("A1:F1")
    ws["A1"] = "🐄 SISTEMA DE GESTÃO DE GADO — SÍTIO SANTO ANTONIO"
    ws["A1"].font = titulo_font
    ws["A1"].fill = PatternFill("solid", start_color=verde_escuro)
    ws["A1"].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 30
    ws["A2"] = f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ws["A2"].font = Font(italic=True, size=9)

    total_comp = df_comp["Valor Total (R$)"].sum() if not df_comp.empty else 0
    total_gast = df_gast["Valor Total (R$)"].sum() if not df_gast.empty else 0
    total_vend = df_vend["Valor Total (R$)"].sum() if not df_vend.empty else 0
    total_custo = total_comp + total_gast
    lucro_total = total_vend - total_custo
    estoque = calcular_estoque()
    cab_comp = int(df_comp["Qtd Cabeças"].sum()) if not df_comp.empty else 0
    cab_vend = int(df_vend["Qtd Cabeças"].sum()) if not df_vend.empty else 0

    dados_resumo = [
        ["", ""],
        ["📦 REBANHO", ""],
        ["Cabeças compradas", cab_comp],
        ["Cabeças vendidas", cab_vend],
        ["Estoque atual", estoque],
        ["", ""],
        ["💰 FINANCEIRO", ""],
        ["Total investido (compras)", total_comp],
        ["Total gastos (manejo)", total_gast],
        ["CUSTO TOTAL", total_custo],
        ["Total recebido (vendas)", total_vend],
        ["", ""],
        ["✅ LUCRO / PREJUÍZO", lucro_total],
        ["ROI (%)", f"{(lucro_total/total_custo*100):.1f}%" if total_custo > 0 else "0%"],
    ]

    for i, (label, valor) in enumerate(dados_resumo, 4):
        ws.cell(i, 1, label)
        ws.cell(i, 2, valor)
        ws.cell(i, 1).border = border
        ws.cell(i, 2).border = border
        if label in ["📦 REBANHO", "💰 FINANCEIRO"]:
            for c in [1, 2]:
                ws.cell(i, c).fill = PatternFill("solid", start_color=verde_medio)
                ws.cell(i, c).font = Font(bold=True, color="FFFFFF")
        elif label == "CUSTO TOTAL":
            for c in [1, 2]:
                ws.cell(i, c).fill = PatternFill("solid", start_color=laranja)
            ws.cell(i, 2).number_format = money_fmt
        elif "LUCRO" in str(label):
            cor_res = verde_claro if lucro_total >= 0 else vermelho
            for c in [1, 2]:
                ws.cell(i, c).fill = PatternFill("solid", start_color=cor_res)
                ws.cell(i, c).font = bold_font
            ws.cell(i, 2).number_format = money_fmt
        elif isinstance(valor, float):
            ws.cell(i, 2).number_format = money_fmt

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 20

    def _aba_dados(titulo, df, headers, cols_money, cor_header):
        ws2 = wb.create_sheet(titulo)
        ws2.freeze_panes = "A2"
        ws2.append(headers)
        estilo_header(ws2, 1, len(headers), cor_header)
        if not df.empty:
            for _, row in df.iterrows():
                linha = []
                for v in row:
                    if isinstance(v, pd.Timestamp):
                        linha.append(v.strftime("%d/%m/%Y"))
                    elif pd.isna(v) if not isinstance(v, str) else False:
                        linha.append(None)
                    else:
                        linha.append(v)
                ws2.append(linha)
            for r in range(2, len(df) + 2):
                for c in cols_money:
                    ws2.cell(r, c).number_format = money_fmt
                for c in range(1, len(headers) + 1):
                    ws2.cell(r, c).border = border
        auto_largura(ws2)
        return ws2

    _aba_dados("🛒 Compras", df_comp,
               ["Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)", "Descrição", "Registrado Por"],
               [3, 4], verde_escuro)
    _aba_dados("💸 Gastos", df_gast,
               ["Data", "Tipo", "Descrição", "Valor Total (R$)", "Qtd Cabeças", "Valor/Cabeça (R$)", "Registrado Por"],
               [4, 6], "BF360C")
    _aba_dados("🤝 Vendas", df_vend,
               ["Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)", "Valor Arroba (R$)",
                "Qtd Mãe", "Qtd Deyvid", "Qtd Nilson",
                "Valor Mãe (R$)", "Valor Deyvid (R$)", "Valor Nilson (R$)", "Descrição"],
               [3, 4, 5, 9, 10, 11], "1A237E")
    _aba_dados("🩺 Manejo", df_man,
               ["Data", "Tipo", "Qtd Cabeças", "Descrição", "Responsável"],
               [], "4A148C")

    wb.save(nome_arquivo)
    print(f"\n✅ Relatório Excel gerado: {nome_arquivo}")
    return nome_arquivo


# ==============================
# 🌐 COTAÇÃO ONLINE
# ==============================

def obter_cotacao_imea():
    """Busca cotações do IMEA."""
    if not WEB_DISPONIVEL:
        return None
    try:
        url = "https://www.imea.com.br/imea-site/view/arquivos/indicadores-boi/indicadores_boi.json"
        r = requests.get(url, timeout=8)
        dados = r.json()
        cotacoes = {}
        for item in dados:
            nome = item.get('indicador', '').upper()
            val_str = str(item.get('valor', '0')).replace(',', '.')
            try:
                val = float(val_str)
            except ValueError:
                continue
            if "NOVILHA NELORE 18M" in nome:
                cotacoes['Novilha Nelore 18m'] = val
            elif "BEZERRA NELORE 12M" in nome:
                cotacoes['Bezerra Nelore 12m'] = val
            elif "BEZERRA NELORE 8M" in nome:
                cotacoes['Bezerra Nelore 8m'] = val
        return cotacoes if cotacoes else None
    except Exception as e:
        print(f"  (Não foi possível buscar cotação IMEA: {e})")
        return None


def ver_cotacao():
    """Exibe cotações online."""
    print("\n🌐 === COTAÇÃO DE MERCADO (IMEA) ===")
    if not WEB_DISPONIVEL:
        print("⚠️  Pacotes 'requests' e 'beautifulsoup4' não instalados.")
        print("   Execute: pip install requests beautifulsoup4")
        return
    print("Buscando cotações...")
    cotacoes = obter_cotacao_imea()
    if cotacoes:
        print(f"\n{'─'*40}")
        for nome, val in cotacoes.items():
            print(f"  {nome:<28} R$ {val:.2f}/@")
        print(f"{'─'*40}")
    else:
        print("❌ Não foi possível obter cotações no momento.")


# ==============================
# Utilitários
# ==============================

def _safe_val(df, row, col):
    try:
        v = df.iloc[row, col]
        return v if pd.notna(v) else None
    except Exception:
        return None


def _input_data(prompt="Data (dd/mm/aaaa)"):
    """Solicita uma data com valor padrão = hoje. Compatível com Rich."""
    hoje = datetime.now().strftime("%d/%m/%Y")
    while True:
        s = ui_input(prompt, hoje).strip()
        if not s:
            return hoje
        try:
            datetime.strptime(s, "%d/%m/%Y")
            return s
        except ValueError:
            ui_aviso("Formato inválido. Use dd/mm/aaaa")


def _input_data_simples(prompt):
    """Solicita uma data sem valor padrão. Compatível com Rich."""
    while True:
        s = ui_input(prompt).strip()
        try:
            datetime.strptime(s, "%d/%m/%Y")
            return s
        except ValueError:
            ui_aviso("Formato inválido. Use dd/mm/aaaa")


def _input_float(prompt):
    """Alias para ui_float — mantido por compatibilidade."""
    return ui_float(prompt)


def _input_int(prompt, minv=0, maxv=999999):
    """Alias para ui_int — mantido por compatibilidade."""
    return ui_int(prompt, minv, maxv)


def _escolher_membro(prompt="Membro:"):
    ui_info(prompt)
    for i, m in enumerate(MEMBROS, 1):
        ui_info(f"  {i}. {NOMES_MEMBROS.get(m, m)}")
    idx = ui_int("Escolha", 1, len(MEMBROS))
    return MEMBROS[idx - 1]


# ==============================
# 📋 MENU Principal
# ==============================

def _menu_rich(estoque):
    console.clear()
    titulo = Text("SISTEMA DE GESTAO DE GADO  v2.1", style="bold white", justify="center")
    sub    = Text("Sitio Santo Antonio  |  Familia: Mae, Deyvid, Nilson", style="dim white", justify="center")
    header = Align.center(Text.assemble(titulo, "\n", sub))
    console.print(Panel(header, border_style="bold green", padding=(1, 4)))

    cor_est = "bold green" if estoque > 0 else "bold red"
    console.print(Align.center(
        Panel(f"[{cor_est}]  Estoque atual: {estoque} cabecas  [/{cor_est}]",
              border_style="green", width=40)
    ))
    console.print()

    def bloco(titulo_bloco, itens, cor):
        t = Table(box=box.SIMPLE, show_header=True,
                  header_style=f"bold {cor}", border_style=cor, min_width=32)
        t.add_column(titulo_bloco, style="white")
        for num, label in itens:
            t.add_row(f"[bold {cor}]{num:>2}.[/bold {cor}]  {label}")
        return t

    col1 = bloco("REGISTROS", [
        ("1",  "Adicionar Compra"),
        ("2",  "Adicionar Gasto"),
        ("3",  "Registrar Venda"),
        ("4",  "Registrar Manejo"),
    ], "cyan")
    col2 = bloco("CONSULTAS", [
        ("5",  "Resumo Geral"),
        ("6",  "Resumo por Membro"),
        ("7",  "Listar Registros"),
        ("8",  "Relatorio por Periodo"),
        ("9",  "Comparativo Anual"),
        ("10", "Estimativa Rebanho"),
        ("11", "Cotacao IMEA"),
    ], "yellow")
    col3 = bloco("GERENCIAR / FERRAMENTAS", [
        ("12", "Editar Registro"),
        ("13", "Excluir Registro"),
        ("14", "Recibo Ultima Venda"),
        ("15", "Alertas de Saude"),
        ("16", "Importar Excel Antigo"),
        ("17", "Exportar Excel"),
        ("18", "Graficos"),
        ("19", "Backup Manual"),
    ], "magenta")

    console.print(Columns([col1, col2, col3], equal=True, expand=True))
    console.print()
    console.rule("[dim]0 = Sair[/dim]")
    console.print()


def menu():
    while True:
        estoque = calcular_estoque()

        if RICH:
            _menu_rich(estoque)
            opcao = Prompt.ask("[bold cyan]  Escolha uma opcao[/bold cyan]").strip()
        else:
            print(f"\nGESTAO DE GADO v2.1 | Estoque: {estoque} cabecas")
            opcao = input("  Opcao: ").strip()

        acoes = {
            "1":  adicionar_compra,
            "2":  adicionar_gasto,
            "3":  adicionar_venda,
            "4":  adicionar_manejo,
            "5":  ver_resumo_geral,
            "6":  ver_resumo_por_membro,
            "7":  listar_registros,
            "8":  relatorio_por_periodo,
            "9":  comparativo_anual,
            "10": estimativa_rebanho,
            "11": ver_cotacao,
            "12": editar_registro,
            "13": excluir_registro,
            "14": recibo_ultima_venda,
            "15": verificar_alertas,
            "16": importar_excel_antigo,
            "17": exportar_relatorio_excel,
            "18": gerar_graficos,
            "19": lambda: ui_ok(f"Backup salvo: {fazer_backup()}"),
        }

        if opcao == "0":
            if RICH:
                console.print("\n[bold green]  Ate logo! Boas vendas![/bold green]\n")
            else:
                print("\nAte logo!\n")
            break
        elif opcao in acoes:
            try:
                acoes[opcao]()
            except KeyboardInterrupt:
                ui_aviso("Operacao cancelada.")
        else:
            ui_aviso("Opcao invalida!")

        if RICH:
            console.print()
            Prompt.ask("[dim]  Enter para continuar[/dim]", default="")
        else:
            input("\n  [Enter para continuar...]")

# ==============================
# Execução
# ==============================

if __name__ == "__main__":
    fazer_backup()
    inicializar()
    menu()
