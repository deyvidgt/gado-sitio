from agora import agora
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Onda 10: Exportação de gráficos em PDF/PNG
Renderiza gráficos como imagens usando Playwright + Pillow
"""
from flask import render_template, send_file, flash, redirect, url_for
from datetime import datetime
import io
from extensions import app, login_required, _agora
from db import carregar_aba
import pandas as pd


@app.route("/graficos/exportar/<modulo>/<formato>")
@login_required
def exportar_grafico(modulo, formato):
    """Exporta gráfico em PNG ou PDF.

    Onda 10.1 — Exportação de gráficos

    Uso: /graficos/exportar/dashboard/png
         /graficos/exportar/financeiro/pdf
         /graficos/exportar/leite/png
    """
    if formato not in ["png", "pdf"]:
        flash("Formato inválido. Use 'png' ou 'pdf'.", "error")
        return redirect(url_for("dashboard"))

    try:
        from playwright.sync_api import sync_playwright
        from PIL import Image
        import base64

        # Mapeia módulos para rotas
        rota_map = {
            "dashboard": "/",
            "financeiro": "/financeiro",
            "leite": "/leite",
            "pastos": "/pastos",
            "reproducao": "/reproducao",
            "indicadores": "/indicadores/gmd",
        }

        if modulo not in rota_map:
            flash("Módulo não encontrado.", "error")
            return redirect(url_for("dashboard"))

        rota = rota_map[modulo]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})

            # Acessa a página (assumindo que está rodando localmente)
            page.goto(f"http://localhost:5000{rota}", wait_until="networkidle")

            # Aguarda gráficos renderizarem
            page.wait_for_timeout(2000)

            # Screenshot da página
            screenshot = page.screenshot(full_page=True)

            browser.close()

        # Retorna como arquivo
        if formato == "png":
            return send_file(
                io.BytesIO(screenshot),
                mimetype="image/png",
                as_attachment=True,
                download_name=f"grafico_{modulo}_{agora().strftime('%Y%m%d_%H%M%S')}.png"
            )
        else:  # PDF via Pillow + ReportLab
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader

            img = Image.open(io.BytesIO(screenshot))
            img_resized = img.resize((595, int(595 * img.height / img.width)))  # A4 width

            pdf_buffer = io.BytesIO()
            c = canvas.Canvas(pdf_buffer, pagesize=A4)

            # Adiciona título
            c.setFont("Helvetica-Bold", 16)
            c.drawString(40, 780, f"Gráfico: {modulo.capitalize()}")
            c.setFont("Helvetica", 10)
            c.drawString(40, 760, f"Exportado em {agora().strftime('%d/%m/%Y %H:%M:%S')}")

            # Adiciona imagem
            img_reader = ImageReader(io.BytesIO(screenshot))
            c.drawImage(img_reader, 40, 100, width=515, height=int(515 * img.height / img.width))

            c.save()
            pdf_buffer.seek(0)

            return send_file(
                pdf_buffer,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"grafico_{modulo}_{agora().strftime('%Y%m%d_%H%M%S')}.pdf"
            )

    except ImportError as e:
        flash(f"Playwright ou Pillow não instalados: {e}", "error")
        return redirect(url_for("dashboard"))
    except Exception as e:
        app.logger.error(f"Erro ao exportar gráfico: {e}")
        flash(f"Erro ao exportar: {e}", "error")
        return redirect(url_for("dashboard"))


@app.route("/graficos/download/<modulo>/<tipo>")
@login_required
def download_dados_grafico(modulo, tipo):
    """Exporta dados do gráfico em CSV.

    Onda 10.2 — Exportação de dados em CSV

    Uso: /graficos/download/dashboard/csv
         /graficos/download/leite/csv
    """
    try:
        dados = None

        if modulo == "dashboard":
            from routes_dashboard import _grafico_resultado_mensal, _grafico_cmp_gpcab_evolucao, _grafico_gastos_por_tipo
            from extensions import _get_resumo_cache
            from db import _get_dados_cache

            r = _get_resumo_cache()
            dados_cache = _get_dados_cache()

            # Combina todos os dados de gráficos
            dfs = []

            resultado = _grafico_resultado_mensal(r)
            if resultado:
                df = pd.DataFrame({
                    "Mês": resultado["labels"],
                    "Resultado (R$)": resultado["data"]
                })
                dfs.append(("Resultado Mensal", df))

            cmp_gpcab = _grafico_cmp_gpcab_evolucao(r)
            if cmp_gpcab:
                df = pd.DataFrame({
                    "Mês": cmp_gpcab["labels"],
                    "CMP (R$/cab)": cmp_gpcab["cmp"],
                    "GPCab (R$/cab)": cmp_gpcab["gpcab"]
                })
                dfs.append(("CMP e GPCab", df))

            gastos = _grafico_gastos_por_tipo(dados_cache)
            if gastos:
                df = pd.DataFrame({
                    "Tipo": gastos["labels"],
                    "Valor (R$)": gastos["data"]
                })
                dfs.append(("Gastos por Tipo", df))

        elif modulo == "leite":
            from routes_leite import _grafico_producao_leite, _grafico_ccs_cpp, _grafico_top_vacas
            from db import carregar_aba
            from extensions import _agora

            df_producao = carregar_aba("Leite Produção")
            hoje = _agora().date()

            dfs = []

            producao = _grafico_producao_leite(df_producao, hoje)
            if producao:
                df = pd.DataFrame({
                    "Data": producao["labels"],
                    "Litros": producao["data"]
                })
                dfs.append(("Produção Diária", df))

            qualidade = _grafico_ccs_cpp(df_producao)
            if qualidade:
                df = pd.DataFrame({
                    "Data": qualidade["labels"],
                    "CCS": qualidade["ccs"],
                    "CPP": qualidade["cpp"]
                })
                dfs.append(("Qualidade CCS/CPP", df))

            top = _grafico_top_vacas(df_producao, None)
            if top:
                df = pd.DataFrame({
                    "Vaca": top["labels"],
                    "Litros": top["data"]
                })
                dfs.append(("Top 10 Vacas", df))

        if not dfs:
            flash("Nenhum dado disponível para exportar.", "warning")
            return redirect(url_for("dashboard"))

        # Escreve em Excel com múltiplas abas
        from openpyxl import Workbook

        wb = Workbook()
        wb.remove(wb.active)

        for nome_aba, df in dfs:
            ws = wb.create_sheet(nome_aba[:31])  # Excel limita a 31 caracteres
            for r_idx, row in enumerate(df.values, 1):
                for c_idx, value in enumerate(row, 1):
                    ws.cell(row=r_idx, column=c_idx, value=value)
            # Headers
            for c_idx, col in enumerate(df.columns, 1):
                ws.cell(row=1, column=c_idx, value=col)

        xlsx_buffer = io.BytesIO()
        wb.save(xlsx_buffer)
        xlsx_buffer.seek(0)

        return send_file(
            xlsx_buffer,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"dados_{modulo}_{agora().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )

    except Exception as e:
        app.logger.error(f"Erro ao exportar dados: {e}")
        flash(f"Erro ao exportar: {e}", "error")
        return redirect(url_for("dashboard"))
