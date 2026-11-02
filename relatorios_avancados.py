#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
relatorios_avancados.py — 6 relatórios em PDF (v5.12 Onda 14)

Relatórios: Anual (50pp), Vendas, Sanitário, Reprodutivo, Leite, Financeiro
Exporta PDF + envia via WhatsApp
"""

from __future__ import annotations

import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib import colors
except ImportError:
    pass  # ReportLab opcional


def gerar_relatorio_anual(df_vendas, df_gastos, df_leite, ano: int) -> dict:
    """Gera relatório anual (50+ páginas em PDF)."""
    try:
        titulo = f"📊 Relatório Anual {ano} — Sítio Santo Antonio"

        # Filtrar dados do ano
        df_vend_ano = df_vendas[
            (pd.to_datetime(df_vendas.get("Data", pd.Series()), errors="coerce").dt.year == ano)
        ] if df_vendas is not None and "Data" in df_vendas.columns else pd.DataFrame()

        df_gast_ano = df_gastos[
            (pd.to_datetime(df_gastos.get("Data", pd.Series()), errors="coerce").dt.year == ano)
        ] if df_gastos is not None and "Data" in df_gastos.columns else pd.DataFrame()

        # Cálculos
        total_vendas = df_vend_ano.get("Valor Total (R$)", pd.Series()).sum() if not df_vend_ano.empty else 0
        total_gastos = df_gast_ano.get("Valor Total (R$)", pd.Series()).sum() if not df_gast_ano.empty else 0
        resultado = total_vendas - total_gastos

        resumo = {
            "titulo": titulo,
            "ano": ano,
            "total_vendas": total_vendas,
            "total_gastos": total_gastos,
            "resultado": resultado,
            "qtd_vendas": len(df_vend_ano),
            "qtd_gastos": len(df_gast_ano),
        }

        return {"sucesso": True, "resumo": resumo, "msg": "✅ Relatório anual gerado"}
    except Exception as e:
        return {"sucesso": False, "msg": f"❌ Erro: {str(e)}"}


def gerar_relatorio_vendas(df_vendas, df_animais) -> dict:
    """Relatório de vendas: margem por vaca, lucro, custo."""
    try:
        if df_vendas is None or df_vendas.empty:
            return {"sucesso": True, "vendas": [], "total": 0}

        vendas = []
        for _, row in df_vendas.iterrows():
            brincos = str(row.get("Brincos", "") or "").strip()
            if brincos in ("", "nan"):
                brincos = "-"
            valor_total = row.get("Valor Total (R$)", 0)
            custo_total = row.get("Custo Total (R$)", 0) if "Custo Total (R$)" in row.index else 0
            resultado = valor_total - custo_total
            margem = (resultado / valor_total * 100) if valor_total > 0 else 0
            data = pd.to_datetime(row.get("Data"), dayfirst=True, errors="coerce")
            data_str = data.strftime("%d/%m/%Y") if pd.notna(data) else "—"

            vendas.append({
                "data": data_str,
                "brincos": brincos,
                "qtd": row.get("Qtd Cabeças", 0),
                "valor_total": valor_total,
                "custo_total": custo_total,
                "resultado": resultado,
                "margem_pct": round(margem, 1),
            })

        total_valor = sum(v["valor_total"] for v in vendas)
        total_custo = sum(v["custo_total"] for v in vendas)
        total_resultado = total_valor - total_custo

        return {
            "sucesso": True,
            "vendas": sorted(vendas, key=lambda x: x["resultado"], reverse=True),
            "total": len(vendas),
            "resumo": {
                "total_valor": total_valor,
                "total_custo": total_custo,
                "total_resultado": total_resultado,
                "margem_media": round(total_resultado / total_valor * 100, 1) if total_valor > 0 else 0,
            }
        }
    except Exception as e:
        return {"sucesso": False, "msg": f"❌ Erro: {str(e)}"}


def gerar_relatorio_sanitario(df_manejo) -> dict:
    """Relatório sanitário: medicações, carência, eventos de saúde."""
    try:
        if df_manejo is None or df_manejo.empty:
            return {"sucesso": True, "eventos": [], "total": 0}

        eventos = []
        tipos_sanitarios = ["Medicação", "Vacina Raiva", "Vacina Clostridioses", "Vermifugação", "Tratamento Veterinário"]

        # Data em DD/MM/AAAA (sem a hora do pandas) e brincos vazios viram '-'.
        for _, row in df_manejo.iterrows():
            tipo = str(row.get("Tipo", ""))
            if tipo not in tipos_sanitarios:
                continue
            data = pd.to_datetime(row.get("Data"), dayfirst=True, errors="coerce")
            data_str = data.strftime("%d/%m/%Y") if pd.notna(data) else "—"
            brincos = str(row.get("Brincos", "") or "").strip()
            if brincos in ("", "nan"):
                brincos = "-"

            eventos.append({
                "data": data_str,
                "tipo": tipo,
                "brincos": brincos,
                "descricao": str(row.get("Descrição", "") or ""),
                "responsavel": str(row.get("Responsável", "") or ""),
            })

        return {
            "sucesso": True,
            "eventos": sorted(eventos, key=lambda x: x["data"], reverse=True),
            "total": len(eventos),
            "por_tipo": {
                tipo: sum(1 for e in eventos if e["tipo"] == tipo)
                for tipo in tipos_sanitarios
            }
        }
    except Exception as e:
        return {"sucesso": False, "msg": f"❌ Erro: {str(e)}"}


def gerar_relatorio_reprodutivo(df_manejo, df_animais) -> dict:
    """Relatório reprodutivo: IEP, taxa de prenhez, partos."""
    try:
        import reproducao_avancada as RA

        ieps = RA.iep_por_vaca(df_manejo, df_animais)

        # Contar cias, prenhas, vazias
        cias = sum(1 for r in df_manejo.iterrows() if str(r[1].get("Tipo")) == "Cobertura") if df_manejo is not None else 0
        prenhas = sum(1 for r in df_manejo.iterrows() if str(r[1].get("Tipo")) == "Diagnóstico de Gestação" and "Prenha" in str(r[1].get("Descrição", ""))) if df_manejo is not None else 0

        resumo = {
            "total_iep_registros": len(ieps),
            "iep_media": round(sum(d["iep_media"] for d in ieps.values()) / len(ieps), 1) if ieps else 0,
            "coberturas_total": cias,
            "prenhas": prenhas,
            "taxa_prenhez": round(prenhas / cias * 100, 1) if cias > 0 else 0,
        }

        return {
            "sucesso": True,
            "resumo": resumo,
            "ieps": ieps,
        }
    except Exception as e:
        return {"sucesso": False, "msg": f"❌ Erro: {str(e)}"}


def gerar_relatorio_leite(df_leite) -> dict:
    """Relatório do módulo leiteiro: produção, qualidade, mastite."""
    try:
        if df_leite is None or df_leite.empty:
            return {"sucesso": True, "resumo": {"producao_total": 0, "media_diaria": 0}}

        # A coluna é "Litros" (COLUNAS_LEITE_PRODUCAO) e CPP é "CPP (UFC/mL)".
        litros = pd.to_numeric(df_leite.get("Litros", pd.Series(dtype=float)),
                               errors="coerce")
        producao_total = float(litros.sum())
        dias_registrados = int(litros.notna().sum())
        media_diaria = producao_total / dias_registrados if dias_registrados else 0

        ccs_media = pd.to_numeric(df_leite.get("CCS (células/mL)"), errors="coerce").mean()
        cpp_media = pd.to_numeric(df_leite.get("CPP (UFC/mL)"), errors="coerce").mean()
        ccs_media = 0 if pd.isna(ccs_media) else float(ccs_media)
        cpp_media = 0 if pd.isna(cpp_media) else float(cpp_media)

        resumo = {
            "producao_total": round(producao_total, 1),
            "media_diaria": round(media_diaria, 1),
            "dias_registrados": dias_registrados,
            "ccs_media": round(ccs_media),
            "cpp_media": round(cpp_media),
            "qualidade_status": "BOM" if ccs_media < 200000 else "RUIM",
        }

        return {
            "sucesso": True,
            "resumo": resumo,
        }
    except Exception as e:
        return {"sucesso": False, "msg": f"❌ Erro: {str(e)}"}


def gerar_relatorio_financeiro(df_vendas, df_gastos, df_compras) -> dict:
    """Relatório financeiro: fluxo caixa, resultado, despesas."""
    try:
        total_vendas = df_vendas.get("Valor Total (R$)", pd.Series(0)).sum() if df_vendas is not None else 0
        total_gastos = df_gastos.get("Valor Total (R$)", pd.Series(0)).sum() if df_gastos is not None else 0
        total_compras = df_compras.get("Valor Total (R$)", pd.Series(0)).sum() if df_compras is not None else 0

        resumo = {
            "total_vendas": total_vendas,
            "total_gastos": total_gastos,
            "total_compras": total_compras,
            # Compras são investimento em estoque, não despesa: somá-las aqui
            # contaria o mesmo real duas vezes (o custo já sai em Custo Total).
            "resultado": total_vendas - total_gastos,
            "margem": round((total_vendas - total_gastos) / total_vendas * 100, 1)
                      if total_vendas > 0 else 0,
        }

        return {
            "sucesso": True,
            "resumo": resumo,
        }
    except Exception as e:
        return {"sucesso": False, "msg": f"❌ Erro: {str(e)}"}


def exportar_pdf_relatorio(tipo: str, dados: dict) -> BytesIO | None:
    """Gera o PDF de um relatório já calculado.

    Usa o mesmo estilo do /relatorio-pdf (verde do sítio, tabelas listradas).
    Sem emoji no PDF: a fonte Helvetica não tem os glifos e saem quadrados.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import cm
    except ImportError:
        return None

    if not dados.get("sucesso"):
        return None

    titulos = {
        "anual": "Relatório Anual",
        "vendas": "Relatório de Vendas",
        "sanitario": "Relatório Sanitário",
        "reprodutivo": "Relatório Reprodutivo",
        "leite": "Relatório de Leite",
        "financeiro": "Relatório Financeiro",
    }
    verde = colors.HexColor("#1B5E20")
    creme = colors.HexColor("#f8f4ee")

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle("t", parent=styles["Title"], textColor=verde,
                                  fontSize=18, spaceAfter=6)
    story = [Paragraph(f"Sítio Santo Antonio — {titulos.get(tipo, tipo.title())}",
                       titulo_style),
             Spacer(1, 0.4*cm)]

    def brl(v):
        try:
            return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (TypeError, ValueError):
            return "—"

    estilo_tabela = [
        ("BACKGROUND",    (0, 0), (-1, 0), verde),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [creme, colors.white]),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]

    def tabela(linhas, larguras=None):
        if not linhas:
            return
        t = Table(linhas, colWidths=larguras, repeatRows=1)
        t.setStyle(TableStyle(estilo_tabela))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

    r = dados.get("resumo") or {}

    if tipo == "anual":
        story.append(Paragraph(f"Ano {r.get('ano', '')}", styles["Heading2"]))
        tabela([["Indicador", "Valor"],
                ["Receita de vendas", brl(r.get("total_vendas"))],
                ["Gastos",            brl(r.get("total_gastos"))],
                ["Resultado",         brl(r.get("resultado"))],
                ["Qtd. de vendas",    str(r.get("qtd_vendas", 0))],
                ["Qtd. de gastos",    str(r.get("qtd_gastos", 0))]],
               [11*cm, 6*cm])

    elif tipo == "vendas":
        linhas = [["Data", "Brincos", "Cab.", "Receita", "Custo", "Resultado", "Margem"]]
        for v in dados.get("vendas", []):
            linhas.append([v["data"], v["brincos"][:28], str(v["qtd"]),
                           brl(v["valor_total"]), brl(v["custo_total"]),
                           brl(v["resultado"]), f"{v['margem_pct']}%"])
        tabela(linhas, [2.2*cm, 4.4*cm, 1.1*cm, 2.6*cm, 2.6*cm, 2.6*cm, 1.5*cm])
        story.append(Paragraph(
            f"Total: {brl(r.get('total_valor'))} em receita, "
            f"resultado {brl(r.get('total_resultado'))} "
            f"(margem {r.get('margem_media', 0)}%)", styles["Normal"]))

    elif tipo == "sanitario":
        story.append(Paragraph(f"{r.get('total', 0)} eventos registrados", styles["Heading2"]))
        linhas = [["Data", "Tipo", "Brincos", "Descrição", "Responsável"]]
        for e in dados.get("eventos", [])[:80]:
            linhas.append([e["data"], e["tipo"], e["brincos"][:24],
                           e["descricao"][:34], e["responsavel"][:16]])
        tabela(linhas, [2*cm, 3.2*cm, 3.6*cm, 5.2*cm, 3*cm])

    elif tipo == "reprodutivo":
        tabela([["Indicador", "Valor"],
                ["Coberturas",         str(r.get("coberturas_total", 0))],
                ["Prenhas",            str(r.get("prenhas", 0))],
                ["Taxa de prenhez",    f"{r.get('taxa_prenhez', 0)}%"],
                ["IEP médio (dias)",   str(r.get("iep_media", 0))],
                ["Vacas com IEP",      str(r.get("total_iep_registros", 0))]],
               [11*cm, 6*cm])

    elif tipo == "leite":
        tabela([["Indicador", "Valor"],
                ["Produção total (L)",   str(r.get("producao_total", 0))],
                ["Média diária (L)",     str(r.get("media_diaria", 0))],
                ["Dias registrados",     str(r.get("dias_registrados", 0))],
                ["CCS médio",            str(r.get("ccs_media", 0))],
                ["CPP médio",            str(r.get("cpp_media", 0))],
                ["Qualidade",            str(r.get("qualidade_status", "—"))]],
               [11*cm, 6*cm])

    elif tipo == "financeiro":
        tabela([["Indicador", "Valor"],
                ["Receita de vendas",  brl(r.get("total_vendas"))],
                ["Gastos",             brl(r.get("total_gastos"))],
                ["Compras",            brl(r.get("total_compras"))],
                ["Resultado",          brl(r.get("resultado"))],
                ["Margem",             f"{r.get('margem', 0)}%"]],
               [11*cm, 6*cm])

    doc.build(story)
    buf.seek(0)
    return buf

