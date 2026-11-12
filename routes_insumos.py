#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comparador de proteinado/ração e painel de estoque — Sítio Santo Antonio v5.10
"""
from flask import render_template, request, redirect, url_for, flash

import insumos as I
import db
from calculos import calcular_estoque
from config import INSUMOS
from extensions import app, login_required, _get_dados_cache, _validar_csrf, parse_valor

LINHAS = 3
CONSUMO_PADRAO = 300


@app.route("/insumos/comparar")
@login_required
def comparar_insumos():
    f = request.args
    dados = _get_dados_cache()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    try:
        cabecas = max(0, int(f.get("cabecas") or estoque))
    except ValueError:
        cabecas = estoque
    opcoes = [{"nome": f.get(f"nome_{i}", ""), "preco_saco": f.get(f"preco_saco_{i}"),
               "kg_saco": f.get(f"kg_saco_{i}"), "consumo_g": f.get(f"consumo_g_{i}")}
              for i in range(LINHAS)]
    pagos = [(p, I.ultimo_preco_saco(dados["Gastos"], p)) for p in INSUMOS]
    return render_template("comparar_insumos.html", opcoes=opcoes, cabecas=cabecas,
                           resultado=I.comparar(opcoes, cabecas), linhas=range(LINHAS),
                           pagos=[(p, u) for p, u in pagos if u],
                           consumo_padrao=CONSUMO_PADRAO)


@app.route("/insumos/estoque", methods=["GET", "POST"])
@login_required
def estoque_insumos():
    """Painel de estoque atual de insumos com suporte a dar entrada e ver valor investido."""
    from models import Insumo
    from extensions import db as db_sqla

    if request.method == "POST":
        _validar_csrf()
        f = request.form
        insumo_id = f.get("insumo_id")
        novo_sacos = parse_valor(f.get("sacos", 0))
        if insumo_id and novo_sacos > 0:
            ins = Insumo.query.get(insumo_id)
            if ins:
                adicionar_kg = novo_sacos * (ins.peso_saco or 25.0)
                ins.quantidade = (ins.quantidade or 0.0) + adicionar_kg
                db_sqla.session.commit()
                flash(f"Adicionados {novo_sacos:g} saco(s) ({adicionar_kg:g} kg) ao estoque de {ins.nome}!", "success")
        return redirect(url_for("estoque_insumos"))

    insumos_db = Insumo.query.all()
    if not insumos_db:
        padroes = [
            ("Sal Proteinado", "Nutrição", 125.0, 25.0),
            ("Ração de Produção", "Nutrição", 150.0, 30.0),
            ("Sal Mineral", "Nutrição", 100.0, 25.0),
        ]
        for nome, cat, qtd, ps in padroes:
            ins = Insumo(nome=nome, categoria=cat, quantidade=qtd, peso_saco=ps, unidade_medida="kg")
            db_sqla.session.add(ins)
        db_sqla.session.commit()
        insumos_db = Insumo.query.all()

    dados = _get_dados_cache()
    lista_insumos = []
    for ins in insumos_db:
        peso = ins.peso_saco or 25.0
        kg = ins.quantidade or 0.0
        sacos = round(kg / peso, 1) if peso > 0 else 0.0

        preco_saco = I.ultimo_preco_saco(dados.get("Gastos"), ins.nome)
        p_saco = preco_saco[0] if (preco_saco and preco_saco[0] > 0) else 100.0
        valor_total = round(sacos * p_saco, 2)
        baixo = sacos <= 5 or kg <= 50.0

        lista_insumos.append({
            "id": ins.id,
            "produto": ins.nome,
            "categoria": ins.categoria or "Nutrição",
            "peso_saco": peso,
            "kg_estoque": round(kg, 1),
            "sacos_estoque": sacos,
            "preco_saco": p_saco,
            "valor_total": valor_total,
            "baixo": baixo,
        })

    return render_template("estoque.html", insumos=lista_insumos)
