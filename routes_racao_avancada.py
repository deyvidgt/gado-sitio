#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_racao_avancada.py — Calculador de Ração Avançado (v5.10)

Rotas para:
- /racao/calculador — Interface avançada de cálculo de ração
- /api/racao/calcular — API para cálculos
- /api/racao/ingredientes — Lista de ingredientes cadastrados
"""

from flask import render_template, request, jsonify
from racao import (
    NecessidadesCategorias,
    calcular_necessidades,
    carregar_ingredientes_ativos,
    balancear_racao,
)
from db import carregar_aba
from extensions import app, login_required, _get_dados_cache
import pandas as pd


@app.route("/racao/calculador")
@login_required
def calculador_racao_avancado():
    """Página de calculador de ração avançado."""
    categorias = list(NecessidadesCategorias.BASE.keys())
    return render_template("racao_calculador_avancado.html",
                          categorias=categorias)


@app.route("/api/racao/calcular", methods=["POST"])
@login_required
def api_calcular_racao():
    """API: calcula necessidades e sugere ração."""
    try:
        data = request.get_json()
        categoria = data.get("categoria", "Lactação")
        peso_vivo = float(data.get("peso_vivo", 500))
        producao_litros = float(data.get("producao_litros", 0))

        if peso_vivo <= 0 or peso_vivo > 1000:
            return jsonify({"erro": "Peso vivo deve estar entre 1 e 1000 kg"}), 400

        # Calcula necessidades
        necessidades = calcular_necessidades(categoria, peso_vivo, producao_litros)

        # Carrega ingredientes e faz balanço
        ingredientes = carregar_ingredientes_ativos()
        sugestao = balancear_racao(necessidades, ingredientes, max_combinacoes=3)

        # Adiciona custos dos ingredientes
        if sugestao:
            sugestao = _adicionar_custos_racao(sugestao)

        return jsonify({
            "sucesso": True,
            "necessidades": necessidades,
            "sugestao": sugestao,
            "ingredientes_cadastrados": len(ingredientes),
        })
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception as e:
        return jsonify({"erro": f"Erro no cálculo: {str(e)}"}), 500


@app.route("/api/racao/ingredientes")
@login_required
def api_ingredientes_racao():
    """API: retorna lista de ingredientes cadastrados com preços."""
    try:
        ingredientes = carregar_ingredientes_ativos()

        # Adiciona preços se disponível
        ingredientes_com_preco = _enriquecer_ingredientes_com_preco(ingredientes)

        return jsonify({
            "sucesso": True,
            "total": len(ingredientes_com_preco),
            "ingredientes": ingredientes_com_preco,
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


def _enriquecer_ingredientes_com_preco(ingredientes: list) -> list:
    """Adiciona preço por kg aos ingredientes."""
    try:
        df_gastos = carregar_aba("Gastos")
        if df_gastos is None or df_gastos.empty:
            return ingredientes

        # Tenta encontrar preços em 'Gastos' com coluna 'Produto'
        for ing in ingredientes:
            nome_produto = ing.get("nome", "").lower()
            linha_produto = df_gastos[
                df_gastos.get("Produto", "").str.lower().str.contains(
                    nome_produto, na=False, regex=False
                )
            ]

            if not linha_produto.empty:
                try:
                    # Pega o preço mais recente
                    linha = linha_produto.iloc[-1]
                    preco_total = float(
                        str(linha.get("Valor Total (R$)", 0)).replace(",", ".")
                    )
                    qtd_sacos = float(str(linha.get("Qtd Sacos", 1)).replace(",", "."))
                    # Assume 25kg por saco (padrão Embrapa)
                    kg_total = qtd_sacos * 25
                    preco_kg = preco_total / kg_total if kg_total > 0 else 0

                    ing["preco_kg"] = round(preco_kg, 2)
                except Exception:
                    ing["preco_kg"] = None
            else:
                ing["preco_kg"] = None

        return ingredientes
    except Exception:
        return ingredientes


def _adicionar_custos_racao(sugestao: dict) -> dict:
    """Calcula custo total e por ingrediente na sugestão."""
    if not sugestao or "ingredientes" not in sugestao:
        return sugestao

    try:
        ingredientes_nomes = [ing.get("nome") for ing in sugestao.get("ingredientes", [])]
        df_gastos = carregar_aba("Gastos")

        preco_por_nome = {}
        for nome in ingredientes_nomes:
            if not nome:
                continue

            linha_produto = df_gastos[
                df_gastos.get("Produto", "").str.lower().str.contains(
                    nome.lower(), na=False, regex=False
                )
            ]

            if not linha_produto.empty:
                try:
                    linha = linha_produto.iloc[-1]
                    preco_total = float(
                        str(linha.get("Valor Total (R$)", 0)).replace(",", ".")
                    )
                    qtd_sacos = float(str(linha.get("Qtd Sacos", 1)).replace(",", "."))
                    kg_total = qtd_sacos * 25
                    preco_kg = preco_total / kg_total if kg_total > 0 else 0
                    preco_por_nome[nome] = preco_kg
                except Exception:
                    preco_por_nome[nome] = 0

        # Calcula custos
        custo_total = 0.0
        for ing in sugestao.get("ingredientes", []):
            kg = ing.get("kg", 0)
            preco_kg = preco_por_nome.get(ing.get("nome"), 0)
            custo = kg * preco_kg
            ing["custo_r"] = round(custo, 2)
            ing["preco_kg"] = round(preco_kg, 2)
            custo_total += custo

        sugestao["custo_total_r"] = round(custo_total, 2)
        if sugestao.get("ms_total_kg", 0) > 0:
            sugestao["custo_por_kg_ms"] = round(custo_total / sugestao["ms_total_kg"], 2)
    except Exception:
        pass  # Se não conseguir calcular custos, só não adiciona

    return sugestao
