#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_relatorios_avancados.py — Os 6 relatórios da Onda 14 (v5.14)

Tela de escolha + download em PDF. Só leitura, nada é gravado.
"""
from flask import render_template, request, send_file, redirect, url_for, flash

import animais as A
import db
import relatorios_avancados as R
from extensions import app, login_required, _get_dados_cache, _agora


@app.route("/relatorios/avancados")
@login_required
def relatorios_avancados():
    """Lista os relatórios disponíveis."""
    return render_template("relatorios_avancados.html")


@app.route("/relatorios/avancados/<tipo>")
@login_required
def relatorio_avancado(tipo):
    """Gera e baixa o PDF do relatório pedido."""
    if tipo not in ("anual", "vendas", "sanitario", "reprodutivo", "leite", "financeiro"):
        return redirect(url_for("relatorios_avancados"))

    # O cache só traz Compras/Gastos/Vendas/Manejo/Visitas; o resto vem direto.
    d = _get_dados_cache()
    df_animais = A.carregar()
    df_leite = db.carregar_aba("Leite Produção")

    if tipo == "anual":
        try:
            ano = int(request.args.get("ano") or 0)
        except ValueError:
            ano = 0
        if not ano:
            # Padrão: o ano da venda mais recente (ou o atual).
            datas = d["Vendas"]["Data"].dropna() if not d["Vendas"].empty else []
            ano = int(max(datas).year) if len(datas) else _agora().year
        dados = R.gerar_relatorio_anual(d["Vendas"], d["Gastos"], df_leite, ano)
    elif tipo == "vendas":
        dados = R.gerar_relatorio_vendas(d["Vendas"], df_animais)
    elif tipo == "sanitario":
        dados = R.gerar_relatorio_sanitario(d["Manejo"])
    elif tipo == "reprodutivo":
        dados = R.gerar_relatorio_reprodutivo(d["Manejo"], df_animais)
    elif tipo == "leite":
        dados = R.gerar_relatorio_leite(df_leite)
    else:
        dados = R.gerar_relatorio_financeiro(d["Vendas"], d["Gastos"], d["Compras"])

    buf = R.exportar_pdf_relatorio(tipo, dados)
    if buf is None:
        flash("Não foi possível gerar o PDF. Verifique se o reportlab está instalado.", "error")
        return redirect(url_for("relatorios_avancados"))

    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                     download_name=f"relatorio_{tipo}.pdf")
