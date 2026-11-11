# -*- coding: utf-8 -*-
"""Rotas do estoque de medicamentos por lote."""
import os
from flask import flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename
import pandas as pd

import db
import estoque_medicamentos as estoque
from extensions import _agora, _validar_csrf, app, login_required, db as db_sqla
from models import Medicamento, Bula


@app.route("/medicamentos/estoque", methods=["GET", "POST"])
@login_required
def estoque_medicamentos():
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        movimento = f.get("movimento", "")
        produto_nome = f.get("produto", "").strip()
        principio_nome = f.get("principio", "").strip()
        lote_fab = f.get("lote", "").strip()
        try:
            estoque.registrar_movimento(
                movimento=movimento,
                data=f.get("data"),
                produto=produto_nome,
                principio=principio_nome,
                lote=lote_fab,
                validade=f.get("validade"),
                quantidade=f.get("quantidade"),
                unidade=f.get("unidade", ""),
                lote_id=f.get("lote_id", ""),
                fornecedor=f.get("fornecedor", ""),
                observacoes=f.get("observacoes", ""),
                responsavel=request.environ.get("REMOTE_USER", "Sistema"),
            )
            if movimento == "Entrada" and produto_nome:
                med = Medicamento.query.filter_by(nome=produto_nome).first()
                if not med:
                    med = Medicamento(nome=produto_nome, principio_ativo=principio_nome, lote=lote_fab)
                    db_sqla.session.add(med)
                    db_sqla.session.commit()
        except ValueError as erro:
            flash(str(erro), "error")
        else:
            flash("Movimentação de estoque registrada.", "success")
        return redirect(url_for("estoque_medicamentos"))

    lotes = estoque.lotes_ativos(_agora().date())
    for l in lotes:
        p_nome = l.get("produto")
        if p_nome:
            med = Medicamento.query.filter_by(nome=p_nome).first()
            if not med:
                med = Medicamento(nome=p_nome, principio_ativo=l.get("principio"), lote=l.get("lote"))
                db_sqla.session.add(med)
                db_sqla.session.commit()

    # Query com outerjoin entre Medicamento e Bula conforme solicitado
    medicamentos_bulas = db_sqla.session.query(Medicamento, Bula).outerjoin(Bula, Medicamento.id == Bula.medicamento_id).all()

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
        medicamentos_bulas=medicamentos_bulas,
        lotes_para_uso=[l for l in lotes if not l["vencido"]],
        movimentos_recentes=recentes,
        hoje=_agora().strftime("%Y-%m-%d"),
    )


@app.route("/medicamentos/adicionar-bula/<int:medicamento_id>", methods=["GET", "POST"])
@login_required
def adicionar_bula_medicamento(medicamento_id):
    medicamento = Medicamento.query.get_or_404(medicamento_id)
    if request.method == "POST":
        _validar_csrf()
        arquivo = request.files.get("bula_arquivo")
        if not arquivo or not arquivo.filename:
            flash("Nenhum ficheiro selecionado.", "error")
            return redirect(request.url)
        
        filename = secure_filename(arquivo.filename)
        if not filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg', '.webp')):
            flash("Formato de ficheiro inválido. Use PDF ou imagem.", "error")
            return redirect(request.url)
        
        upload_dir = os.path.join(app.static_folder, "uploads", "bulas")
        os.makedirs(upload_dir, exist_ok=True)
        
        caminho_salvar = os.path.join(upload_dir, filename)
        arquivo.save(caminho_salvar)
        
        bula_reg = Bula.query.filter_by(medicamento_id=medicamento.id).first()
        caminho_rel = f"uploads/bulas/{filename}"
        if bula_reg:
            bula_reg.arquivo = caminho_rel
        else:
            bula_reg = Bula(medicamento_id=medicamento.id, arquivo=caminho_rel)
            db_sqla.session.add(bula_reg)
        db_sqla.session.commit()
        
        flash(f"Bula de {medicamento.nome} adicionada com sucesso!", "success")
        return redirect(url_for("estoque_medicamentos"))
        
    return render_template("form_adicionar_bula.html", medicamento=medicamento)
