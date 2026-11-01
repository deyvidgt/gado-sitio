#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_cochos.py — Rotas de gestão de cochos/bebedouros (v5.12 Onda 11)
"""
import pandas as pd
from flask import render_template, request, redirect, url_for, flash, jsonify

import animais as A
import db
import cochos as C
from extensions import app, _agora, _validar_csrf, login_required
from routes_animais import _membro_logado, fazer_backup_seguro


@app.route("/cochos")
@login_required
def cochos():
    """Dashboard de cochos: resumo, alertas, mapa."""
    df_cochos = db.carregar_aba("Cochos")

    resumo = C.dashboard_cochos(df_cochos)
    alertas_manut = C.alertas_manutencao(df_cochos)
    alertas_racao = C.alertas_reposicao(df_cochos, "ração")
    alertas_agua = C.alertas_reposicao(df_cochos, "água")
    alertas_sal = C.alertas_reposicao(df_cochos, "sal")

    return render_template("cochos_dashboard.html",
                         resumo=resumo,
                         alertas_manutencao=alertas_manut,
                         alertas_racao=alertas_racao,
                         alertas_agua=alertas_agua,
                         alertas_sal=alertas_sal,
                         tipos_cocho=C.TIPOS_COCHO)


@app.route("/cochos/novo", methods=["GET", "POST"])
@login_required
def novo_cocho():
    """Registrar novo cocho."""
    if request.method == "POST":
        _validar_csrf()
        f = request.form

        try:
            lat = float(f.get("lat", 0))
            lng = float(f.get("lng", 0))
            freq = int(f.get("frequencia", 7))

            resultado = C.registrar_cocho(
                pasto_id=f.get("pasto", ""),
                tipo=f.get("tipo", ""),
                lat=lat,
                lng=lng,
                freq_limpeza=freq,
                observacoes=f.get("observacoes", ""),
            )

            if resultado["sucesso"]:
                # Gravar em Excel
                nova_linha = [
                    resultado["cocho_id"],
                    f.get("pasto", ""),
                    f.get("tipo", ""),
                    f"{lat},{lng}",
                    pd.Timestamp.now().strftime("%d/%m/%Y"),
                    pd.Timestamp.now().strftime("%d/%m/%Y"),
                    freq,
                    "Ativo",
                    f.get("observacoes", ""),
                    pd.Timestamp.now().isoformat(),
                ]
                db.salvar_linha("Cochos", nova_linha)
                fazer_backup_seguro()
                flash(resultado["msg"], "success")
                return redirect(url_for("cochos"))
            else:
                flash(resultado["msg"], "error")
        except Exception as e:
            flash(f"❌ Erro: {str(e)}", "error")

    return render_template("cochos_novo.html",
                         tipos_cocho=C.TIPOS_COCHO)


@app.route("/cochos/pasto/<pasto_id>")
@login_required
def cochos_pasto(pasto_id):
    """Mapa de cochos de um pasto."""
    df_cochos = db.carregar_aba("Cochos")
    cochos_lista = C.cochos_por_pasto(df_cochos, pasto_id)

    return render_template("cochos_mapa.html",
                         pasto_id=pasto_id,
                         cochos=cochos_lista)


@app.route("/cochos/manutencao/<cocho_id>", methods=["POST"])
@login_required
def registrar_manutencao_cocho(cocho_id):
    """Registrar manutenção de cocho."""
    _validar_csrf()

    try:
        df_cochos = db.carregar_aba("Cochos")
        df_cochos.loc[df_cochos["ID"] == cocho_id, "Última Manutenção"] = pd.Timestamp.now().strftime("%d/%m/%Y")
        db.reescrever_aba("Cochos", df_cochos)
        fazer_backup_seguro()
        flash("✅ Manutenção registrada.", "success")
    except Exception as e:
        flash(f"❌ Erro: {str(e)}", "error")

    return redirect(url_for("cochos"))


@app.route("/api/cochos/alertas")
@login_required
def api_alertas_cochos():
    """API de alertas para WhatsApp/dashboard."""
    df_cochos = db.carregar_aba("Cochos")

    alertas = C.alertas_manutencao(df_cochos)

    return jsonify({
        "sucesso": True,
        "total": len(alertas),
        "alertas": alertas,
    })
