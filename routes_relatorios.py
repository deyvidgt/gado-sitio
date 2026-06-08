#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas de Relatórios e PDF — Sítio Santo Antonio
Gerado automaticamente — não editar diretamente.
"""
from flask import render_template, request, redirect, url_for, flash, session, send_file, jsonify
import os, tempfile
import pandas as pd
from datetime import datetime, timedelta
from db import carregar_aba, carregar_todas, inicializar, fazer_backup
from calculos import (
    calcular_estoque, calcular_resumo_financeiro, calcular_todos_membros,
    calcular_fluxo_caixa, calcular_cmp_ate_data, calcular_gpcab_ate_data,
    calcular_cmp, calcular_gpcab, calcular_estoque_por_membro,
    calcular_indicadores_extras, calcular_gasto_por_tipo, calcular_evolucao_cmp,
)
from config import (TIPOS_GASTO, TIPOS_MANEJO, MEMBROS, NOMES_MEMBROS,
                    EMOJIS_MEMBROS, OPCOES_VISITA)
from extensions import (
    app, _agora, _validar_csrf, login_required,
    _get_dados_cache, _get_resumo_cache,
    salvar_linha, reescrever_aba,
    _fazer_backup_inteligente, _limpar_backups_antigos,
    _carregar_usuarios, _salvar_usuarios,
    _sha256, _hash_bcrypt, _bcrypt_disponivel, _verificar_hash,
    fmt_brl, fmt_data, parse_valor,
    _gerar_alertas, _calc_anual, BASE_DIR,
)

#  RELATÓRIOS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/relatorios")
@login_required
def relatorios():
    dados = _get_dados_cache()
    r_fin = _get_resumo_cache()
    mbr   = calcular_todos_membros(dados["Vendas"], dados["Compras"], dados["Gastos"], dados["Manejo"])
    gastos_tipo = calcular_gasto_por_tipo(dados["Gastos"])
    extras      = calcular_indicadores_extras(
        dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"], r_fin["ctcab"]
    )
    return render_template("relatorios.html", r=r_fin, mbr=mbr,
                           alertas=_gerar_alertas(dados), anual=_calc_anual(dados),
                           gastos_tipo=gastos_tipo, extras=extras,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS, EMOJIS=EMOJIS_MEMBROS)


# ══════════════════════════════════════════════════════════════════════════════
#  RELATÓRIO PDF
# ══════════════════════════════════════════════════════════════════════════════

def _gerar_pdf_relatorio():
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable, PageBreak)
    dados  = _get_dados_cache()
    r      = _get_resumo_cache()
    mbr    = calcular_todos_membros(dados["Vendas"], dados["Compras"], dados["Gastos"], dados["Manejo"])
    extras = calcular_indicadores_extras(
        dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"], r["ctcab"])
    gastos_tipo = calcular_gasto_por_tipo(dados["Gastos"])
    estoque_m   = calcular_estoque_por_membro(dados["Compras"], dados["Vendas"], dados["Manejo"])
    buf    = BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    VERDE   = colors.HexColor("#2e7d32")
    VERDE_L = colors.HexColor("#e8f5e9")
    CINZA   = colors.HexColor("#616161")
    BRANCO  = colors.white
    titulo_style = ParagraphStyle("titulo", parent=styles["Title"],
                                  textColor=VERDE, fontSize=20, spaceAfter=4)
    sub_style    = ParagraphStyle("sub", parent=styles["Normal"],
                                  textColor=CINZA, fontSize=10, spaceAfter=16)
    h2_style     = ParagraphStyle("h2", parent=styles["Heading2"],
                                  textColor=VERDE, fontSize=13, spaceBefore=14, spaceAfter=6)
    body_style   = styles["Normal"]

    def _brl(v):
        try: return f"R$ {float(v):,.2f}".replace(",","X").replace(".","¸").replace("X",".")
        except: return "—"
    def _pct(v):
        try:
            f = float(v)
            return f"{'+'if f>0 else ''}{f:.1f}%"
        except: return "—"
    def _tabela(dados_tab, col_widths=None):
        t = Table(dados_tab, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("FONTNAME",  (0,0), (-1,-1), "Helvetica"),
            ("FONTSIZE",  (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [BRANCO, VERDE_L]),
            ("GRID",      (0,0), (-1,-1), 0.4, colors.HexColor("#c8e6c9")),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("RIGHTPADDING",(0,0), (-1,-1), 6),
            ("TOPPADDING",  (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
            ("BACKGROUND",  (0,0), (-1,0), VERDE),
            ("TEXTCOLOR",   (0,0), (-1,0), BRANCO),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ]))
        return t

    story = []
    gerado_em = _agora().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph("🐄 Sítio Santo Antonio", titulo_style))
    story.append(Paragraph(f"Relatório Financeiro — {gerado_em}", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=VERDE, spaceAfter=12))

    story.append(Paragraph("Resumo do Estoque e Custos", h2_style))
    story.append(_tabela([
        ["Indicador", "Valor"],
        ["Cabeças compradas",           str(int(r["cab_comp"]))],
        ["Cabeças vendidas",            str(int(r["cab_vend"]))],
        ["Estoque atual",               f"{int(r['estoque'])} cabeças"],
        ["CMP",                         _brl(r["cmp"]) + "/cab."],
        ["GPCab",                       _brl(r["gpcab"]) + "/cab."],
        ["CTCab",                       _brl(r["ctcab"]) + "/cab."],
        ["Break-even",                  _brl(r["break_even"]) + "/cab."],
        ["Capital imobilizado",         _brl(r["capital_imobilizado"])],
    ], col_widths=[10*cm, 7*cm]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Resultado Financeiro", h2_style))
    story.append(_tabela([
        ["Indicador", "Valor"],
        ["Total compras",               _brl(r["total_comp"])],
        ["Total gastos",                _brl(r["total_gast"])],
        ["Custo total",                 _brl(r["total_custo"])],
        ["Receita (vendas)",            _brl(r["total_vend"])],
        ["Resultado realizado",         _brl(r["resultado_realizado"])],
        ["ROI realizado",               _pct(r["roi_realizado"])],
        ["Resultado total (+ estoque)", _brl(r["resultado_total"])],
        ["ROI total",                   _pct(r["roi_total"])],
        ["Margem bruta",                _pct(r["margem_bruta"])],
    ], col_widths=[10*cm, 7*cm]))
    story.append(Spacer(1, 12))

    story.append(PageBreak())
    story.append(Paragraph("Resultado por Membro", h2_style))
    tab_mbr = [["Membro","Cabeças","Receita","Custo Total","Resultado","Margem"]]
    for m in MEMBROS:
        mr = mbr[m]
        tab_mbr.append([NOMES_MEMBROS[m], str(mr["cabecas"]), _brl(mr["receita"]),
                        _brl(mr["custo_total"]), _brl(mr["resultado"]), _pct(mr["margem_pct"])])
    story.append(_tabela(tab_mbr, col_widths=[3.5*cm,2.5*cm,3.5*cm,3.5*cm,3*cm,2*cm]))
    story.append(Spacer(1,16))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=CINZA))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"<font size='8' color='grey'>Gerado pelo Sistema de Gado — Sítio Santo Antonio | {gerado_em}</font>",
        body_style))
    doc.build(story)
    return buf.getvalue()


@app.route("/relatorio-pdf")
@login_required
def relatorio_pdf():
    from flask import Response
    try:
        pdf_bytes = _gerar_pdf_relatorio()
        nome_arquivo = f"relatorio_gado_{_agora().strftime('%Y%m%d_%H%M')}.pdf"
        return Response(pdf_bytes, mimetype="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"})
    except Exception as e:
        flash(f"Erro ao gerar PDF: {e}", "error")
        return redirect(url_for("relatorios"))


# ══════════════════════════════════════════════════════════════════════════════
