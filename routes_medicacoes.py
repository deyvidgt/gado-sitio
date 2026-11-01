#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_medicacoes.py — Rotas de medicações + quarentena leite (v5.12 Onda 12.X)
"""
import pandas as pd
from flask import render_template, request, redirect, url_for, flash, jsonify

import animais as A
import db
import medicacoes as M
from extensions import app, _agora, _validar_csrf, login_required
from routes_animais import _membro_logado, fazer_backup_seguro


@app.route("/medicacoes")
@login_required
def medicacoes():
    """Dashboard de medicações: histórico, quarentena, resumo."""
    df_med = db.carregar_aba("Medicações")
    df_an = A.carregar()

    resumo = M.dashboard_medicacoes(df_med, df_an)
    quarentena = M.animais_em_quarentena(df_med, df_an)

    return render_template("medicacoes_dashboard.html",
                         resumo=resumo,
                         quarentena=quarentena,
                         tipos_medicacao=M.TIPOS_MEDICACAO,
                         vias=M.VIAS_APLICACAO,
                         motivos=M.MOTIVOS_MEDICACAO)


@app.route("/medicacoes/registrar", methods=["POST"])
@login_required
def registrar_medicacao():
    """Registra nova medicação via formulário."""
    _validar_csrf()
    f = request.form

    # Validar e preparar dados
    resultado = M.registrar_medicacao(
        data=f.get("data", ""),
        brincos_str=f.get("brincos", ""),
        tipo=f.get("tipo_medicacao", ""),
        principio=f.get("principio_ativo", ""),
        dosagem=f.get("dosagem", ""),
        via=f.get("via", ""),
        motivo=f.get("motivo", ""),
        quarentena_leite=int(f.get("quarentena_leite", 0) or 0),
        responsavel=_membro_logado(),
    )

    if not resultado["sucesso"]:
        flash(resultado["msg"], "error")
        return redirect(url_for("medicacoes"))

    # Gravar em Manejo (tipo "Medicação") + aba "Medicações"
    try:
        # 1. Registra em Manejo para histórico integrado
        nova_linha_manejo = [
            f.get("data", ""),
            "Medicação",
            len(resultado["ids_animais"]),
            f"{f.get('tipo_medicacao', '')} — {f.get('motivo', '')}",
            _membro_logado(),
            "",  # Perda De
            f.get("principio_ativo", ""),
            "",  # Nascimento De
            f.get("brincos", ""),  # Brincos
            "",  # Pesos
        ]
        db.salvar_linha("Manejo", nova_linha_manejo)

        # 2. Registra em aba "Medicações" (detalhado)
        nova_linha_medicacoes = [
            f.get("data", ""),
            f.get("brincos", ""),
            f.get("tipo_medicacao", ""),
            f.get("principio_ativo", ""),
            f.get("dosagem", ""),
            f.get("via", ""),
            f.get("motivo", ""),
            int(f.get("quarentena_leite", 0) or 0),
            resultado["data_liberacao"],
            _membro_logado(),
            "",  # ID Envio (preenchido automaticamente)
            pd.Timestamp.now().isoformat(),  # Criado Em
        ]
        db.salvar_linha("Medicações", nova_linha_medicacoes)

        fazer_backup_seguro()
        flash(f"💊 {resultado['msg']}", "success")
    except Exception as e:
        flash(f"❌ Erro ao gravar: {str(e)}", "error")

    return redirect(url_for("medicacoes"))


@app.route("/medicacoes/animal/<animal_id>")
@login_required
def medicacoes_animal(animal_id):
    """Histórico de medicações de um animal específico."""
    df_an = A.carregar()
    df_med = db.carregar_aba("Medicações")

    # Buscar animal
    animal = None
    if df_an is not None and not df_an.empty:
        animal = df_an[df_an["ID"] == animal_id].iloc[0] if animal_id in df_an["ID"].values else None

    if animal is None:
        flash("🐄 Animal não encontrado.", "error")
        return redirect(url_for("medicacoes"))

    # Histórico
    historico = M.historico_animal(df_med, animal_id)

    return render_template("medicacoes_animal.html",
                         animal=animal,
                         animal_ref=A.ref(animal),
                         historico=historico)


@app.route("/medicacoes/editar/<int:row_index>", methods=["GET", "POST"])
@login_required
def editar_medicacao(row_index):
    """Editar medicação existente."""
    df_med = db.carregar_aba("Medicações")

    if df_med is None or row_index >= len(df_med):
        flash("Medicação não encontrada.", "error")
        return redirect(url_for("medicacoes"))

    if request.method == "POST":
        _validar_csrf()
        f = request.form

        # Atualizar linha
        df_med.loc[row_index, "Data"] = f.get("data")
        df_med.loc[row_index, "Tipo Medicação"] = f.get("tipo_medicacao")
        df_med.loc[row_index, "Princípio Ativo"] = f.get("principio_ativo")
        df_med.loc[row_index, "Dosagem"] = f.get("dosagem")
        df_med.loc[row_index, "Via"] = f.get("via")
        df_med.loc[row_index, "Motivo"] = f.get("motivo")

        quarentena = int(f.get("quarentena_leite", 0) or 0)
        df_med.loc[row_index, "Quarentena Leite (dias)"] = quarentena

        data_obj = pd.Timestamp(f.get("data")).normalize()
        data_liberacao = data_obj + pd.Timedelta(days=quarentena)
        df_med.loc[row_index, "Data Liberação"] = str(data_liberacao.date())

        try:
            db.reescrever_aba("Medicações", df_med)
            fazer_backup_seguro()
            flash("✅ Medicação atualizada.", "success")
        except Exception as e:
            flash(f"❌ Erro: {str(e)}", "error")

        return redirect(url_for("medicacoes"))

    med = df_med.iloc[row_index]
    return render_template("medicacoes_editar.html",
                         medicacao=med,
                         row_index=row_index,
                         tipos_medicacao=M.TIPOS_MEDICACAO,
                         vias=M.VIAS_APLICACAO,
                         motivos=M.MOTIVOS_MEDICACAO)


@app.route("/medicacoes/deletar/<int:row_index>", methods=["POST"])
@login_required
def deletar_medicacao(row_index):
    """Deletar medicação (soft delete ou reescrever aba)."""
    _validar_csrf()
    df_med = db.carregar_aba("Medicações")

    if df_med is None or row_index >= len(df_med):
        return jsonify({"sucesso": False, "msg": "Não encontrado"}), 404

    try:
        df_med = df_med.drop(row_index).reset_index(drop=True)
        db.reescrever_aba("Medicações", df_med)
        fazer_backup_seguro()
        flash("✅ Medicação removida.", "success")
    except Exception as e:
        flash(f"❌ Erro: {str(e)}", "error")

    return redirect(url_for("medicacoes"))


@app.route("/api/medicacoes/quarentena")
@login_required
def api_quarentena():
    """API para alertas de quarentena (WhatsApp, dashboard)."""
    df_med = db.carregar_aba("Medicações")
    df_an = A.carregar()

    alertas = M.alertas_quarentena(df_med, df_an)

    return jsonify({
        "sucesso": True,
        "total": len(alertas),
        "alertas": alertas,
    })
