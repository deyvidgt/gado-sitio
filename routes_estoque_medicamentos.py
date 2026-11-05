# -*- coding: utf-8 -*-
"""Rotas do estoque de medicamentos por lote."""
from flask import flash, redirect, render_template, request, url_for
import pandas as pd

import db
import estoque_medicamentos as estoque
from extensions import _agora, _validar_csrf, app, login_required


@app.route("/medicamentos/estoque", methods=["GET", "POST"])
@login_required
def estoque_medicamentos():
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        movimento = f.get("movimento", "")
        try:
            estoque.registrar_movimento(
                movimento=movimento,
                data=f.get("data"),
                produto=f.get("produto", ""),
                principio=f.get("principio", ""),
                lote=f.get("lote", ""),
                validade=f.get("validade"),
                quantidade=f.get("quantidade"),
                unidade=f.get("unidade", ""),
                lote_id=f.get("lote_id", ""),
                fornecedor=f.get("fornecedor", ""),
                observacoes=f.get("observacoes", ""),
                responsavel=request.environ.get("REMOTE_USER", "Sistema"),
            )
        except ValueError as erro:
            flash(str(erro), "error")
        else:
            flash("Movimentação de estoque registrada.", "success")
        return redirect(url_for("estoque_medicamentos"))

    lotes = estoque.lotes_ativos(_agora().date())
    df = db.carregar_aba(estoque.ABA)
    recentes = []
    if not df.empty:
        for registro in df.tail(20).iloc[::-1].to_dict("records"):
            data = registro.get("Data")
            registro["Data"] = data.strftime("%d/%m/%Y") if pd.notna(data) else ""
            quantidade = registro.get("Quantidade")
            registro["Quantidade"] = quantidade if pd.notna(quantidade) else 0
            recentes.append(registro)
    return render_template(
        "estoque_medicamentos.html",
        lotes=lotes,
        lotes_para_uso=[l for l in lotes if not l["vencido"]],
        movimentos_recentes=recentes,
        hoje=_agora().strftime("%Y-%m-%d"),
    )
