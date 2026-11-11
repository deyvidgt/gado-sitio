#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""routes_ia.py — Painel da IA preditiva (Onda 19).

Somente leitura: lê os modelos de data/ia_models/ e mostra as previsões.
Se os modelos não foram treinados, explica como treinar.
"""
import logging
from flask import render_template, jsonify, flash, redirect, url_for, abort
import sitios
from pathlib import Path

import animais as A
import db
import ia_modelos
from extensions import app, login_required
from reproducao_avancada_ia import alertas_ia_preditiva

logger = logging.getLogger(__name__)


@app.route("/reproducao/ia-predicoes")
@login_required
def ia_predicoes():
    """Previsões de morte, cio e consanguinidade por animal."""
    df_an = A.carregar()
    df_man = db.carregar_aba("Manejo")
    df_compras = db.carregar_aba("Compras")
    df_vendas = db.carregar_aba("Vendas")

    resultado = alertas_ia_preditiva(df_an, df_man, df_compras, df_vendas)

    return render_template("ia_predicoes.html",
                           urgentes=resultado.get("urgentes", []),
                           avisos=resultado.get("avisos", []),
                           total=resultado.get("total", 0),
                           timestamp=resultado.get("timestamp", ""))


@app.route("/api/ia/alertas")
@login_required
def api_ia_alertas():
    """Retorna alertas de IA preditiva em JSON."""
    df_an = A.carregar()
    df_man = db.carregar_aba("Manejo")
    df_compras = db.carregar_aba("Compras")
    df_vendas = db.carregar_aba("Vendas")

    resultado = alertas_ia_preditiva(df_an, df_man, df_compras, df_vendas)
    return jsonify(resultado), 200


@app.route("/admin/treinar-ia", methods=["POST"])
@login_required
def treinar_ia():
    """Rota administrativa para treinar os modelos de IA preditiva."""
    if not sitios.e_admin(session.get("usuario")):
        abort(403)
    try:
        import subprocess
        import sys
        script_path = Path(__file__).parent / "scripts" / "train_ia_modelos.py"
        resultado = subprocess.run(
            [sys.executable, str(script_path), "--n-animais", "1000"],
            capture_output=True,
            text=True,
            timeout=180
        )
        if resultado.returncode == 0:
            flash("Modelos de IA preditiva treinados com sucesso!", "success")
        else:
            flash(f"Erro no treino da IA: {resultado.stderr[-300:]}", "error")
    except Exception as e:
        logger.error(f"Erro ao executar treino de IA: {e}")
        flash(f"Erro ao executar treino de IA: {e}", "error")
    return redirect(url_for("ia_predicoes"))
