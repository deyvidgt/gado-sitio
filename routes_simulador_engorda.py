#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_simulador_engorda.py — Módulo de Simulador de Custo de Produção e Viabilidade de Engorda (v5.35)
Compara lado a lado dois produtos (ex: Proteico vs. Ração) calculando GMD, custo por kg,
custo da @ produzida, lucro por animal e rentabilidade.
"""
from flask import render_template, request, jsonify
from extensions import app, login_required

@app.route("/pecuaria/simulador-engorda", methods=["GET"])
@login_required
def simulador_engorda():
    """Interface principal do simulador de viabilidade de engorda."""
    return render_template("simulador_engorda.html")


@app.route("/api/pecuaria/simular-engorda", methods=["POST"])
@login_required
def api_simular_engorda():
    """API que processa os cálculos lado a lado de dois produtos/tratamentos."""
    try:
        dados = request.get_json() or {}
        
        # Parâmetros gerais do lote
        peso_inicial = float(dados.get("peso_inicial", 350.0))
        peso_alvo = float(dados.get("peso_alvo", 520.0))
        preco_arroba = float(dados.get("preco_arroba", 300.0))
        custo_operacional_diario = float(dados.get("custo_operacional_diario", 3.50))
        rendimento_carcaca = float(dados.get("rendimento_carcaca", 54.0)) / 100.0

        # Tratamento A
        a = dados.get("produto_a", {})
        nome_a = a.get("nome", "Tratamento A")
        valor_saco_a = float(a.get("valor_saco", 95.0))
        peso_saco_a = float(a.get("peso_saco", 25.0))
        gmd_a = float(a.get("gmd", 1.1))
        consumo_dia_a = float(a.get("consumo_dia", 1.5)) # kg/dia

        # Tratamento B
        b = dados.get("produto_b", {})
        nome_b = b.get("nome", "Tratamento B")
        valor_saco_b = float(b.get("valor_saco", 110.0))
        peso_saco_b = float(b.get("peso_saco", 25.0))
        gmd_b = float(b.get("gmd", 1.3))
        consumo_dia_b = float(b.get("consumo_dia", 3.0)) # kg/dia

        def calcular_resultados(valor_saco, peso_saco, gmd, consumo_dia):
            if gmd <= 0 or peso_saco <= 0:
                return {}
            
            custo_kg_produto = valor_saco / peso_saco
            diaria_alimentar = consumo_dia * custo_kg_produto
            custo_total_diario = diaria_alimentar + custo_operacional_diario
            
            ganho_necessario = max(0.0, peso_alvo - peso_inicial)
            dias_confinamento = ganho_necessario / gmd
            meses_confinamento = dias_confinamento / 30.0
            
            custo_total_producao = dias_confinamento * custo_total_diario
            
            # Arrobas produzidas
            ganho_total_kg = ganho_necessario
            peso_carcaca_final = peso_alvo * rendimento_carcaca
            peso_carcaca_inicial = peso_inicial * rendimento_carcaca
            arrobas_produzidas = (peso_carcaca_final - peso_carcaca_inicial) / 15.0
            
            custo_arroba_produzida = custo_total_producao / arrobas_produzidas if arrobas_produzidas > 0 else 0
            
            receita_venda = arrobas_produzidas * preco_arroba
            lucro_animal = receita_venda - custo_total_producao
            lucro_mes = lucro_animal / meses_confinamento if meses_confinamento > 0 else 0
            
            rentabilidade_pct = (lucro_animal / custo_total_producao * 100.0) if custo_total_producao > 0 else 0

            return {
                "custo_kg_produto": round(custo_kg_produto, 2),
                "diaria_alimentar": round(diaria_alimentar, 2),
                "custo_total_diario": round(custo_total_diario, 2),
                "dias_confinamento": round(dias_confinamento, 1),
                "meses_confinamento": round(meses_confinamento, 1),
                "custo_total_producao": round(custo_total_producao, 2),
                "arrobas_produzidas": round(arrobas_produzidas, 2),
                "custo_arroba_produzida": round(custo_arroba_produzida, 2),
                "lucro_animal": round(lucro_animal, 2),
                "lucro_mes": round(lucro_mes, 2),
                "rentabilidade_pct": round(rentabilidade_pct, 1),
            }

        res_a = calcular_resultados(valor_saco_a, peso_saco_a, gmd_a, consumo_dia_a)
        res_b = calcular_resultados(valor_saco_b, peso_saco_b, gmd_b, consumo_dia_b)

        return jsonify({
            "sucesso": True,
            "produto_a": {"nome": nome_a, **res_a},
            "produto_b": {"nome": nome_b, **res_b},
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 400
