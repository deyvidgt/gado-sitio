#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas da Agenda de Tarefas — Sítio Santo Antonio v5.3
"""
import pandas as pd
from flask import render_template, request, redirect, url_for, flash

import tarefas as T
from config import MEMBROS, NOMES_MEMBROS, REPETICOES_TAREFA
from extensions import app, _agora, _validar_csrf, login_required
from routes_animais import _membro_logado, fazer_backup_seguro


@app.route("/tarefas")
@login_required
def tarefas():
    df = T.carregar()
    hoje = pd.Timestamp(_agora()).normalize()
    feitas = [{"titulo": r["Título"], "feito": r["Feito Em"], "quem": r["Responsável"]}
              for _, r in df[df["Feito Em"] != ""].iloc[::-1].head(10).iterrows()]
    return render_template("tarefas.html",
                           pendentes=T.pendentes(df, hoje, limite_dias=365),
                           feitas=feitas, hoje=f"{hoje:%Y-%m-%d}",
                           repeticoes=list(REPETICOES_TAREFA),
                           pessoas=[NOMES_MEMBROS[m] for m in MEMBROS])


@app.route("/tarefas/nova", methods=["POST"])
@login_required
def nova_tarefa():
    _validar_csrf()
    f = request.form
    try:
        T.criar(f.get("titulo"), f.get("data"), f.get("responsavel", ""),
                f.get("repetir", "Não"), f.get("obs", ""), _membro_logado())
        flash("📋 Tarefa anotada!", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("tarefas"))


@app.route("/tarefas/<id_>/concluir", methods=["POST"])
@login_required
def concluir_tarefa(id_):
    _validar_csrf()
    try:
        T.concluir(id_, _agora(), _membro_logado())
        flash("✅ Feito!", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("tarefas"))


@app.route("/tarefas/<id_>/excluir", methods=["POST"])
@login_required
def excluir_tarefa(id_):
    _validar_csrf()
    try:
        fazer_backup_seguro()
        T.excluir(id_)
        flash("Tarefa apagada.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("tarefas"))
