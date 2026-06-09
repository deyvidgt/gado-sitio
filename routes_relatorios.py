#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_relatorios.py — Sítio Santo Antonio
Rotas de relatórios, PDF e exportação Excel.
"""
import os
import io
from flask import render_template, redirect, url_for, send_file, flash
from calculos import (
    calcular_resumo_financeiro, calcular_todos_membros,
    calcular_gasto_por_tipo,
)
from config import MEMBROS, NOMES_MEMBROS, EMOJIS_MEMBROS
from extensions import (
    app, login_required,
    _get_dados_cache, _get_resumo_cache,
    _gerar_alertas, _calc_anual,
)


@app.route("/relatorios")
@login_required
def relatorios():
    dados   = _get_dados_cache()
    r       = _get_resumo_cache()
    mbr     = calcular_todos_membros(dados["Vendas"], dados["Compras"],
                                     dados["Gastos"], dados["Manejo"])
    gastos_tipo = calcular_gasto_por_tipo(dados["Gastos"])
    anual       = _calc_anual(dados)
    alertas     = _gerar_alertas(dados)

    return render_template(
        "relatorios.html",
        r=r, mbr=mbr,
        gastos_tipo=gastos_tipo,
        anual=anual,
        alertas=alertas,
        MEMBROS=MEMBROS,
        NOMES=NOMES_MEMBROS,
        EMOJIS=EMOJIS_MEMBROS,
    )


@app.route("/relatorio-pdf")
@login_required
def relatorio_pdf():
    """Gera PDF do resumo financeiro e faz download."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                         Table, TableStyle)
        from reportlab.lib.units import cm
    except ImportError:
        flash("reportlab não instalado. Execute: pip install reportlab", "error")
        return redirect(url_for("relatorios"))

    dados = _get_dados_cache()
    r     = _get_resumo_cache()
    mbr   = calcular_todos_membros(dados["Vendas"], dados["Compras"],
                                    dados["Gastos"], dados["Manejo"])

    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    verde  = colors.HexColor("#1B5E20")
    creme  = colors.HexColor("#f8f4ee")
    story  = []

    # Título
    titulo_style = ParagraphStyle("titulo", parent=styles["Title"],
                                   textColor=verde, fontSize=18, spaceAfter=6)
    sub_style    = ParagraphStyle("sub", parent=styles["Normal"],
                                   textColor=colors.gray, fontSize=10, spaceAfter=16)
    story.append(Paragraph("🐄 Sítio Santo Antonio — Relatório Financeiro", titulo_style))
    story.append(Paragraph("Família: Geane, Deyvid e Nilson", sub_style))
    story.append(Spacer(1, 0.3*cm))

    def brl(v):
        try:
            return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "—"

    def pct(v):
        try:
            f = float(v)
            return f"{'+'if f>0 else ''}{f:.1f}%"
        except Exception:
            return "—"

    # Tabela resumo financeiro
    hdr_style = [
        ("BACKGROUND",    (0, 0), (-1, 0), verde),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 10),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
        ("ALIGN",         (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [creme, colors.white]),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]

    resumo_data = [
        ["Indicador", "Valor"],
        ["Cabeças compradas",             str(r["cab_comp"])],
        ["Cabeças vendidas",              str(r["cab_vend"])],
        ["Estoque atual",                 str(r["estoque"])],
        ["CMP (Custo Médio Ponderado)",   brl(r["cmp"]) + "/cab."],
        ["GPCab (Gastos acum./cabeça)",   brl(r["gpcab"]) + "/cab."],
        ["CTCab (Custo Total/cabeça)",    brl(r["ctcab"]) + "/cab."],
        ["Total Compras",                 brl(r["total_comp"])],
        ["Total Gastos",                  brl(r["total_gast"])],
        ["Custo Total",                   brl(r["total_custo"])],
        ["Receita (Vendas)",              brl(r["total_vend"])],
        ["Capital Imobilizado",           brl(r["capital_imobilizado"])],
        ["Resultado Realizado",           brl(r["resultado_realizado"])],
        ["ROI Realizado",                 pct(r["roi_realizado"])],
        ["Resultado Total (+Estoque)",    brl(r["resultado_total"])],
        ["ROI Total",                     pct(r["roi_total"])],
        ["Break-even do Estoque",         brl(r["break_even"]) + "/cab."],
        ["Ticket Médio de Venda",         brl(r["ticket_medio"]) + "/cab."],
        ["Margem Bruta",                  pct(r["margem_bruta"])],
    ]

    story.append(Paragraph("Resumo Financeiro", styles["Heading2"]))
    t = Table(resumo_data, colWidths=[10*cm, 6*cm])
    t.setStyle(TableStyle(hdr_style))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # Resultado por membro
    story.append(Paragraph("Resultado por Membro", styles["Heading2"]))
    mbr_data = [["Membro", "Cabeças", "Receita", "Custo Total", "Resultado", "Margem"]]
    for m in MEMBROS:
        mr = mbr[m]
        mbr_data.append([
            NOMES_MEMBROS[m],
            str(mr["cabecas"]),
            brl(mr["receita"]),
            brl(mr["custo_total"]),
            brl(mr["resultado"]),
            pct(mr["margem_pct"]),
        ])
    t2 = Table(mbr_data, colWidths=[3.5*cm, 2*cm, 3.5*cm, 3.5*cm, 3.5*cm, 2.5*cm])
    t2.setStyle(TableStyle(hdr_style))
    story.append(t2)

    doc.build(story)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="relatorio_gado.pdf",
    )
