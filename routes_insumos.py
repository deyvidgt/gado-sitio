#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comparador de proteinado/ração e painel de estoque — Sítio Santo Antonio v5.10

Comparador: só calcula, nada é gravado (valores na URL).
Estoque: mostra estado atual com marca, nutrição e valor.
"""
from flask import render_template, request

import insumos as I
import db
from calculos import calcular_estoque
from config import INSUMOS
from extensions import app, login_required, _get_dados_cache

LINHAS = 3          # quantas marcas cabem na comparação
CONSUMO_PADRAO = 300  # g/cabeça/dia — proteinado de seca, só como sugestão


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


@app.route("/insumos/estoque")
@login_required
def estoque_insumos():
    """Painel de estoque atual: sacos, kg, valor, marca, nutrição."""
    dados = _get_dados_cache()
    insumos_info = I.estoque_completo(dados.get("Insumos"), dados["Visitas"],
                                      dados["Gastos"])
    return render_template("estoque_insumos.html", insumos=insumos_info)
