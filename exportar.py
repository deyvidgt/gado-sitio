#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Importação de planilhas antigas e exportação de relatório Excel
"""

import os, sys
import pandas as pd
from datetime import datetime
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from config import CORES, MEMBROS, NOMES_MEMBROS
from db import carregar_todas, salvar_linha, safe_val, DATA_DIR
from ui_helper import ui_ok, ui_aviso, ui_info, ui_titulo, ui_input, fmt_r
from calculos import (
    calcular_resumo_financeiro, calcular_todos_membros, calcular_fluxo_caixa,
)


# ── Exportar relatório Excel ──────────────────────────────────────────────────

def exportar_relatorio_excel() -> str:
    dados = carregar_todas()
    df_c  = dados["Compras"]
    df_g  = dados["Gastos"]
    df_v  = dados["Vendas"]
    df_m  = dados["Manejo"]

    nome_arquivo = f"relatorio_gado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    nome = os.path.join(DATA_DIR, nome_arquivo)
    wb   = Workbook()

    _border   = Border(left=Side(style="thin"), right=Side(style="thin"),
                       top=Side(style="thin"),  bottom=Side(style="thin"))
    _hdr_font = Font(bold=True, color="FFFFFF", size=11, name="Arial")
    _ttl_font = Font(bold=True, color="FFFFFF", size=13, name="Arial")
    _bold     = Font(bold=True, size=10, name="Arial")
    _base     = Font(size=10, name="Arial")
    _money    = 'R$ #,##0.00'
    _pct      = '0.0%'

    def fill(cor):
        return PatternFill("solid", start_color=cor)

    def header_row(ws, row, n_cols, cor):
        for c in range(1, n_cols + 1):
            cell = ws.cell(row=row, column=c)
            cell.fill = fill(cor)
            cell.font = _hdr_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = _border

    def auto_col(ws):
        for col in ws.columns:
            mx = max((len(str(c.value)) for c in col if c.value), default=8)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(mx + 4, 36)

    def data_str(v):
        if isinstance(v, pd.Timestamp) and pd.notna(v):
            return v.strftime("%d/%m/%Y")
        try:
            if pd.isna(v):
                return None
        except (TypeError, ValueError):
            pass
        return v

    # ── Aba: Resumo Geral ────────────────────────────────────────────────────
    ws = wb.active
    ws.title = "📊 Resumo Geral"
    ws.freeze_panes = "B2"

    ws.merge_cells("A1:G1")
    ws["A1"] = f"🐄 SISTEMA DE GESTÃO DE GADO — {_now()}"
    ws["A1"].font = _ttl_font
    ws["A1"].fill = fill(CORES["verde_escuro"])
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    r_fin = calcular_resumo_financeiro(df_c, df_g, df_v, df_m)
    mbr   = calcular_todos_membros(df_v, df_c, df_g, df_m)

    blocos_resumo = [
        ("📦 REBANHO", None, CORES["verde_medio"]),
        ("Cabeças compradas",           r_fin["cab_comp"],            None),
        ("Cabeças vendidas",            r_fin["cab_vend"],            None),
        ("Estoque atual",               r_fin["estoque"],             None),
        ("", "", None),
        ("💲 INDICADORES DE CUSTO", None, CORES["verde_medio"]),
        ("CMP  (Custo Médio Ponderado)", r_fin["cmp"],                "money"),
        ("GPCab (Gastos acum./cabeça)", r_fin["gpcab"],               "money"),
        ("CTCab (Custo Total/cabeça)",  r_fin["ctcab"],               "money"),
        ("", "", None),
        ("💰 FINANCEIRO", None, CORES["verde_medio"]),
        ("Total compras",               r_fin["total_comp"],          "money"),
        ("Total gastos",                r_fin["total_gast"],          "money"),
        ("CUSTO TOTAL",                 r_fin["total_custo"],         "money_bold"),
        ("Total vendas (receita)",      r_fin["total_vend"],          "money"),
        ("Capital imobilizado (estoque)", r_fin["capital_imobilizado"], "money"),
        ("", "", None),
        ("📈 RESULTADOS", None, CORES["verde_medio"]),
        ("Resultado realizado",         r_fin["resultado_realizado"], "result"),
        ("ROI realizado",               r_fin["roi_realizado"] / 100, "pct"),
        ("Resultado total (+ estoque)", r_fin["resultado_total"],     "result"),
        ("ROI total",                   r_fin["roi_total"] / 100,     "pct"),
        ("Break-even do estoque",       r_fin["break_even"],          "money"),
        ("Ticket médio de venda",       r_fin["ticket_medio"],        "money"),
        ("Margem bruta",                r_fin["margem_bruta"] / 100,  "pct"),
    ]

    row_i = 3
    for label, val, estilo in blocos_resumo:
        ws.cell(row_i, 1, label).font = _base
        ws.cell(row_i, 1).border = _border
        ws.cell(row_i, 2).border = _border
        if estilo is None and label.startswith("📦") or \
           estilo is None and label.startswith("💲") or \
           estilo is None and label.startswith("💰") or \
           estilo is None and label.startswith("📈"):
            for c in [1, 2]:
                ws.cell(row_i, c).fill = fill(CORES["verde_medio"])
                ws.cell(row_i, c).font = Font(bold=True, color="FFFFFF", name="Arial")
        elif estilo == "money":
            ws.cell(row_i, 2, val).number_format = _money
        elif estilo == "money_bold":
            ws.cell(row_i, 2, val).number_format = _money
            ws.cell(row_i, 1).font = _bold
            ws.cell(row_i, 2).font = _bold
            for c in [1, 2]:
                ws.cell(row_i, c).fill = fill(CORES["laranja"])
        elif estilo == "pct":
            ws.cell(row_i, 2, val).number_format = _pct
        elif estilo == "result":
            ws.cell(row_i, 2, val).number_format = _money
            ws.cell(row_i, 1).font = _bold
            ws.cell(row_i, 2).font = _bold
            cor = CORES["verde_claro"] if (val or 0) >= 0 else CORES["vermelho"]
            for c in [1, 2]:
                ws.cell(row_i, c).fill = fill(cor)
        elif val is not None:
            ws.cell(row_i, 2, val)
        row_i += 1

    # Tabela por membro
    row_i += 1
    ws.cell(row_i, 1, "👨‍👩‍👦 RESULTADO POR MEMBRO").font = _bold
    ws.cell(row_i, 1).fill = fill(CORES["verde_medio"])
    ws.cell(row_i, 1).font = Font(bold=True, color="FFFFFF", name="Arial")
    row_i += 1

    cols_m = ["Membro", "Cabeças", "Receita", "Custo Compra",
              "Custo Gastos", "Custo Total", "Resultado", "Margem"]
    for ci, col in enumerate(cols_m, 1):
        c = ws.cell(row_i, ci, col)
        c.fill = fill(CORES["verde_escuro"])
        c.font = _hdr_font
        c.border = _border
    row_i += 1

    for m in MEMBROS:
        mr = mbr[m]
        vals_m = [
            NOMES_MEMBROS[m],
            mr["cabecas"],
            mr["receita"],
            mr["custo_compra"],
            mr["custo_gastos"],
            mr["custo_total"],
            mr["resultado"],
            mr["margem_pct"] / 100,
        ]
        for ci, v in enumerate(vals_m, 1):
            cell = ws.cell(row_i, ci, v)
            cell.border = _border
            if ci in [3, 4, 5, 6, 7]:
                cell.number_format = _money
            elif ci == 8:
                cell.number_format = _pct
        # Colorir resultado
        res_cell = ws.cell(row_i, 7)
        res_cell.fill = fill(CORES["verde_claro"] if mr["resultado"] >= 0 else CORES["vermelho"])
        res_cell.font = _bold
        row_i += 1

    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 16
    for c in "CDEFGH":
        ws.column_dimensions[c].width = 18

    # ── Abas de dados ────────────────────────────────────────────────────────

    def aba_dados(titulo, df, headers, cols_money, cor_hdr):
        ws2 = wb.create_sheet(titulo)
        ws2.freeze_panes = "A2"
        ws2.append(headers)
        header_row(ws2, 1, len(headers), cor_hdr)
        if not df.empty:
            for _, row in df.iterrows():
                linha = [data_str(v) if isinstance(v, pd.Timestamp)
                         else (None if (not isinstance(v, str) and pd.isna(v)) else v)
                         for v in row]
                ws2.append(linha)
            for row_idx in range(2, len(df) + 2):
                for c in cols_money:
                    ws2.cell(row_idx, c).number_format = _money
                for c in range(1, len(headers) + 1):
                    ws2.cell(row_idx, c).border = _border
                    ws2.cell(row_idx, c).font = _base
        auto_col(ws2)
        return ws2

    aba_dados("🛒 Compras", df_c,
              ["Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)",
               "Qtd Mae", "Qtd Deyvid", "Qtd Nilson",
               "Descrição", "Registrado Por"],
              [3, 4], CORES["verde_escuro"])

    aba_dados("💸 Gastos", df_g,
              ["Data", "Tipo", "Descrição", "Valor Total (R$)", "Qtd Cabeças", "Valor/Cabeça (R$)", "Registrado Por"],
              [4, 6], CORES["vermelho_esc"])

    aba_dados("🤝 Vendas", df_v,
              ["Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)", "Valor Arroba (R$)",
               "Qtd Geane", "Qtd Deyvid", "Qtd Nilson",
               "Valor Geane (R$)", "Valor Deyvid (R$)", "Valor Nilson (R$)",
               "Custo Geane (R$)", "Custo Deyvid (R$)", "Custo Nilson (R$)",
               "Result. Geane (R$)", "Result. Deyvid (R$)", "Result. Nilson (R$)",
               "CMP no momento (R$)", "Descrição"],
              [3, 4, 5, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18], CORES["azul_escuro"])

    aba_dados("🩺 Manejo", df_m,
              ["Data", "Tipo", "Qtd Cabeças", "Descrição", "Responsável"],
              [], CORES["roxo"])

    # ── Aba Fluxo de Caixa ───────────────────────────────────────────────────
    df_fc = calcular_fluxo_caixa(df_c, df_g, df_v)
    if not df_fc.empty:
        ws_fc = wb.create_sheet("💰 Fluxo de Caixa")
        ws_fc.freeze_panes = "A2"
        headers_fc = ["Mês", "Entradas", "Saídas", "Saldo do Mês", "Saldo Acumulado"]
        ws_fc.append(headers_fc)
        header_row(ws_fc, 1, len(headers_fc), CORES["verde_escuro"])
        for _, row in df_fc.iterrows():
            ws_fc.append([
                str(row["AnoMes"]),
                row["Entradas"],
                abs(row["Saidas"]),
                row["Saldo"],
                row["Saldo Acumulado"],
            ])
        for r in range(2, len(df_fc) + 2):
            for c in [2, 3, 4, 5]:
                ws_fc.cell(r, c).number_format = _money
                ws_fc.cell(r, c).border = _border
            ws_fc.cell(r, 1).border = _border
            saldo = ws_fc.cell(r, 4).value
            ws_fc.cell(r, 4).fill = fill(
                CORES["verde_claro"] if (saldo or 0) >= 0 else CORES["vermelho"]
            )
        auto_col(ws_fc)

    wb.save(nome)
    return nome


# ── Importar Excel antigo ─────────────────────────────────────────────────────

def importar_excel_antigo():
    ui_titulo("IMPORTAR EXCEL ANTIGO 📥")
    arquivo = ui_input("Caminho do arquivo Excel (ex: gado.xlsx)").strip()
    if not os.path.exists(arquivo):
        ui_aviso(f"Arquivo não encontrado: {arquivo}")
        return

    ui_info(f"Importando: {arquivo}")
    try:
        wb_ant = load_workbook(arquivo, data_only=True)
        anos = sorted([s for s in wb_ant.sheetnames if s.isdigit()])

        nc, ng, nv = 0, 0, 0
        for ano in anos:
            df = pd.read_excel(arquivo, sheet_name=ano, header=None)

            cab_c   = safe_val(df, 0, 1)
            preco_c = safe_val(df, 0, 10)
            if cab_c and preco_c:
                cab_i = int(cab_c)
                base  = cab_i // 3
                salvar_linha("Compras", [
                    f"01/01/{ano}", cab_i, float(preco_c),
                    round(float(preco_c) / cab_i, 2),
                    base, base, cab_i - base * 2,          # Qtd Mae, Deyvid, Nilson
                    f"Nelore/Garrotes - Importado {ano}", "Importação",
                ])
                nc += 1

            for ri in range(1, len(df)):
                vg = safe_val(df, ri, 6)
                dg = safe_val(df, ri, 7)
                if vg and isinstance(vg, (int, float)) and float(vg) > 0:
                    salvar_linha("Gastos", [
                        f"01/01/{ano}", "Manutenção/Outros", str(dg) if dg else "",
                        float(vg), 0, 0, "Importação",
                    ])
                    ng += 1

            # Vendas por membro
            mae_v = safe_val(df, 1, 15) or 0
            dev_v = safe_val(df, 2, 15) or 0
            nil_v = safe_val(df, 3, 15) or 0
            mae_q = safe_val(df, 1, 19) or 0
            dev_q = safe_val(df, 2, 19) or 0
            nil_q = safe_val(df, 3, 19) or 0

            tv = sum(float(x) for x in [mae_v, dev_v, nil_v]
                     if isinstance(x, (int, float)) and float(x) > 0)
            tq = sum(int(x) for x in [mae_q, dev_q, nil_q]
                     if isinstance(x, (int, float)) and float(x) > 0)

            data_v = str(safe_val(df, 1, 17) or f"31/12/{ano}")[:10]

            if tv > 0:
                salvar_linha("Vendas", [
                    data_v, tq, tv,
                    round(tv / tq, 2) if tq else 0,
                    safe_val(df, 0, 12) or 0,
                    int(mae_q), int(dev_q), int(nil_q),
                    float(mae_v), float(dev_v), float(nil_v),
                    0, 0, 0,   # custo por membro (será recalculado)
                    0, 0, 0,   # resultado por membro
                    0,         # CMP no momento
                    f"Importado de {ano}",
                ])
                nv += 1

        ui_ok(f"Importação concluída! Compras: {nc} | Gastos: {ng} | Vendas: {nv}")

    except Exception as e:
        ui_aviso(f"Erro na importação: {e}")
        import traceback
        traceback.print_exc()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")
