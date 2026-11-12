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


def _sincronizar_catalogo_e_estoque(dados):
    """Garante que todos os insumos de INSUMOS, Leite Alimentação e Gastos existem na tabela Insumo."""
    from models import Insumo
    from extensions import db as db_sqla
    from db import carregar_aba

    produtos_conhecidos = set(INSUMOS.keys())
    
    df_leite = carregar_aba("Leite Alimentação")
    if df_leite is not None and not df_leite.empty and "Produto" in df_leite.columns:
        for _, r in df_leite.iterrows():
            p = str(r.get("Produto", "")).strip()
            if p:
                produtos_conhecidos.add(p)

    df_gastos = dados.get("Gastos")
    if df_gastos is not None and not df_gastos.empty and "Produto" in df_gastos.columns:
        for _, r in df_gastos.iterrows():
            p = str(r.get("Produto", "")).strip()
            if p:
                produtos_conhecidos.add(p)

    existentes = {ins.nome.strip().lower(): ins for ins in Insumo.query.all()}
    
    for nome_prod in produtos_conhecidos:
        if not nome_prod:
            continue
        chave = nome_prod.strip().lower()
        if chave not in existentes:
            peso = 25.0
            cat = "Nutrição"
            if df_leite is not None and not df_leite.empty and "Produto" in df_leite.columns:
                match = df_leite[df_leite["Produto"].astype(str).str.strip().str.lower() == chave]
                if not match.empty:
                    row_l = match.iloc[0]
                    p_saco = parse_valor(row_l.get("Peso Saco (kg)", 25))
                    if p_saco > 0:
                        peso = p_saco
                    c_l = str(row_l.get("Categoria", "")).strip()
                    if c_l:
                        cat = c_l
            ins = Insumo(nome=nome_prod, categoria=cat, quantidade=0.0, peso_saco=peso, unidade_medida="kg")
            db_sqla.session.add(ins)
            existentes[chave] = ins
    db_sqla.session.commit()


@app.route("/insumos/estoque", methods=["GET", "POST"])
@login_required
def estoque_insumos():
    """Painel de estoque atual de insumos com suporte a dar entrada e ver valor investido."""
    from models import Insumo
    from extensions import db as db_sqla
    from db import carregar_aba

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

    dados = _get_dados_cache()
    _sincronizar_catalogo_e_estoque(dados)

    insumos_db = Insumo.query.all()
    df_gastos = dados.get("Gastos")
    df_leite = carregar_aba("Leite Alimentação")

    lista_insumos = []
    for ins in insumos_db:
        peso = ins.peso_saco or 25.0
        
        sacos_comprados_gastos = 0.0
        if df_gastos is not None and not df_gastos.empty and "Produto" in df_gastos.columns:
            mask = df_gastos["Produto"].astype(str).str.strip().str.lower() == ins.nome.strip().lower()
            for _, r in df_gastos[mask].iterrows():
                sq = parse_valor(r.get("Qtd Sacos", 0))
                if sq > 0:
                    sacos_comprados_gastos += sq

        kg_manual = ins.quantidade or 0.0
        kg_total = kg_manual + (sacos_comprados_gastos * peso)
        sacos = round(kg_total / peso, 1) if peso > 0 else 0.0

        preco_saco = I.ultimo_preco_saco(df_gastos, ins.nome)
        p_saco = 0.0
        if preco_saco and preco_saco[0] > 0:
            p_saco = preco_saco[0]
        elif df_leite is not None and not df_leite.empty and "Produto" in df_leite.columns:
            match = df_leite[df_leite["Produto"].astype(str).str.strip().str.lower() == ins.nome.strip().lower()]
            if not match.empty:
                p_saco = parse_valor(match.iloc[0].get("Preço por Saco (R$)", 0))
        
        if p_saco <= 0:
            p_saco = 100.0

        valor_total = round(sacos * p_saco, 2)
        baixo = sacos <= 5 or kg_total <= 50.0

        lista_insumos.append({
            "id": ins.id,
            "produto": ins.nome,
            "categoria": ins.categoria or "Nutrição",
            "peso_saco": peso,
            "kg_estoque": round(kg_total, 1),
            "sacos_estoque": sacos,
            "sacos_comprados": sacos_comprados_gastos,
            "preco_saco": p_saco,
            "valor_total": valor_total,
            "baixo": baixo,
        })

    return render_template("estoque.html", insumos=lista_insumos)
