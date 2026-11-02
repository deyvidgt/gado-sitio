#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_indicadores.py — Rotas dos indicadores v5.8

- /indicadores/engorda-pastagem
- /indicadores/gmd-lotacao
- /indicadores/racao-consumo
- /indicadores/mortalidade-bezerros
"""

from flask import render_template
from extensions import app, login_required, _get_dados_cache
from indicadores_v58 import (
    engorda_pastagem_resumo, gmd_lotacao_analise,
    racao_consumo_analise, mortalidade_bezerros_analise, mortalidade_por_faixa_etaria
)


@app.route("/indicadores/gmd")
@login_required
def indicadores_gmd():
    """Indicadores unificados de GMD: vs pastagem e vs lotação. Onda 8.5 com gráficos."""
    dados = _get_dados_cache()
    resumo_pastagem = engorda_pastagem_resumo(dados)
    analise_lotacao = gmd_lotacao_analise(dados)

    # Gráficos Onda 8.5 — dados simplificados
    grafico_gmd_linhas = None
    grafico_lotacao_barras = None

    try:
        # Extrai últimos 12 pontos do histórico
        if analise_lotacao.get("periodos"):
            periodos = analise_lotacao["periodos"][-12:]
            labels = [p.get("Data", "")[:7] for p in periodos]  # AAAA-MM
            data_gmd = [float(p.get("GMD (kg/dia)", 0) or 0) for p in periodos]
            data_lotacao = [float(p.get("Lotação (UA/ha)", 0) or 0) for p in periodos]

            if labels:
                grafico_gmd_linhas = {"labels": labels, "data": data_gmd}
                grafico_lotacao_barras = {"labels": labels, "data": data_lotacao}
    except Exception as e:
        app.logger.debug(f"Gráficos indicadores falharam: {e}")

    return render_template(
        "indicadores/gmd_unificado.html",
        resumo_pastagem=resumo_pastagem,
        analise_lotacao=analise_lotacao,
        grafico_gmd_linhas=grafico_gmd_linhas,
        grafico_lotacao_barras=grafico_lotacao_barras
    )


# Manter rotas antigas para compatibilidade (redirecionam)
@app.route("/indicadores/engorda-pastagem")
@login_required
def indicadores_engorda_pastagem():
    """Redireciona para a rota unificada."""
    from flask import redirect, url_for
    return redirect(url_for('indicadores_gmd'), code=301)


@app.route("/indicadores/gmd-lotacao")
@login_required
def indicadores_gmd_lotacao():
    """Redireciona para a rota unificada."""
    from flask import redirect, url_for
    return redirect(url_for('indicadores_gmd'), code=301)


@app.route("/indicadores/racao-consumo")
@login_required
def indicadores_racao_consumo():
    """Análise de ração oferecida vs consumida."""
    dados = _get_dados_cache()
    analise = racao_consumo_analise(dados)
    return render_template(
        "indicadores/racao_consumo.html",
        analise=analise
    )


@app.route("/indicadores/mortalidade-bezerros")
@login_required
def indicadores_mortalidade_bezerros():
    """Taxa de mortalidade de bezerros."""
    dados = _get_dados_cache()
    analise = mortalidade_bezerros_analise(dados)
    return render_template(
        "indicadores/mortalidade_bezerros.html",
        analise=analise,
        mortalidade_faixa=mortalidade_por_faixa_etaria(dados),
    )
