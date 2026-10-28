#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_reconhecimento.py — RA e Genealogia Visual (v5.10)

Rotas para:
- /animais/reconhecer — Reconhecimento de animal por foto (RA)
- /animais/<animal_id>/genealogia — Árvore genealógica visual
"""

from flask import render_template, jsonify, session
import animais as A
import genetica as G
from extensions import app, login_required, _get_dados_cache
from db import carregar_aba


@app.route("/animais/reconhecer")
@login_required
def reconhecer_animal():
    """Página de reconhecimento de animal por foto (RA)."""
    dados = _get_dados_cache()
    return render_template("reconhecer_animal.html",
                          total_animais=len(dados.get("Animais", [])))


@app.route("/api/reconhecer-animal", methods=["POST"])
@login_required
def api_reconhecer_animal():
    """API: processa foto e retorna animal mais provável com genealogia."""
    from flask import request
    import json
    import base64

    try:
        data = request.get_json()
        foto_base64 = data.get("foto")

        if not foto_base64:
            return jsonify({"erro": "Foto não fornecida"}), 400

        # TODO: Implementar IA de reconhecimento visual
        # Por enquanto: retorna dados dummy
        return jsonify({
            "sucesso": False,
            "msg": "Reconhecimento em desenvolvimento (v5.10)",
            "animal_id": None
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route("/animais/<animal_id>/genealogia")
@login_required
def genealogia_animal(animal_id: str):
    """Página de árvore genealógica visual para um animal."""
    dados = _get_dados_cache()
    animais_aba = dados.get("Animais", [])
    genetica_aba = dados.get("Genética", [])

    # Busca o animal
    animal = None
    for row in animais_aba:
        if row.get("ID") == animal_id:
            animal = row
            break

    if not animal:
        from flask import abort
        abort(404)

    # Constrói árvore genealógica
    arvore = _construir_arvore_genealogica(animal_id, genetica_aba, animais_aba, nivel=0, max_nivel=3)

    return render_template("genealogia_visual.html",
                          animal=animal,
                          animal_id=animal_id,
                          arvore=arvore)


@app.route("/api/genealogia/<animal_id>")
@login_required
def api_genealogia(animal_id: str):
    """API: retorna árvore genealógica em JSON para visualização interativa."""
    dados = _get_dados_cache()
    genetica_aba = dados.get("Genética", [])
    animais_aba = dados.get("Animais", [])

    arvore = _construir_arvore_genealogica(animal_id, genetica_aba, animais_aba,
                                           nivel=0, max_nivel=4, formato="json")
    return jsonify(arvore)


def _construir_arvore_genealogica(animal_id: str, genetica_aba, animais_aba,
                                  nivel: int = 0, max_nivel: int = 3,
                                  formato: str = "dict") -> dict:
    """Constrói estrutura de árvore genealógica recursivamente."""

    if nivel > max_nivel:
        return None

    # Busca dados do animal
    animal_data = None
    for row in animais_aba:
        if row.get("ID") == animal_id:
            animal_data = row
            break

    if not animal_data:
        return None

    # Busca registro genético
    gen_data = None
    for row in genetica_aba:
        if row.get("Animal ID") == animal_id:
            gen_data = row
            break

    pai_id = gen_data.get("Pai ID") if gen_data else None
    mae_id = gen_data.get("Mãe ID") if gen_data else None

    nodo = {
        "id": animal_id,
        "nome": animal_data.get("Brinco") or animal_id,
        "categoria": animal_data.get("Categoria", "—"),
        "sexo": animal_data.get("Sexo", "—"),
        "data_nasc": animal_data.get("Data Nasc", "—"),
        "genótipo": gen_data.get("Genótipo", "—") if gen_data else "—",
        "endogamia_pct": gen_data.get("Coeficiente Endogamia %", 0) if gen_data else 0,
        "pai": None,
        "mae": None,
    }

    # Recursão para pais
    if pai_id and nivel < max_nivel:
        nodo["pai"] = _construir_arvore_genealogica(pai_id, genetica_aba, animais_aba,
                                                    nivel + 1, max_nivel, formato)

    if mae_id and nivel < max_nivel:
        nodo["mae"] = _construir_arvore_genealogica(mae_id, genetica_aba, animais_aba,
                                                    nivel + 1, max_nivel, formato)

    return nodo


@app.route("/api/compatibilidade-visual/<animal_id>")
@login_required
def api_compatibilidade_visual(animal_id: str):
    """API: retorna compatibilidade de acasalamento com visualização."""
    dados = _get_dados_cache()
    animais_aba = dados.get("Animais", [])
    genetica_aba = dados.get("Genética", [])

    # Busca o animal
    animal = None
    for row in animais_aba:
        if row.get("ID") == animal_id:
            animal = row
            break

    if not animal:
        return jsonify({"erro": "Animal não encontrado"}), 404

    # Se for fêmea, busca touros compatíveis; se for touro, busca fêmeas
    sexo = animal.get("Sexo", "").lower()
    candidatos = []

    for outro in animais_aba:
        outro_id = outro.get("ID")
        outro_sexo = outro.get("Sexo", "").lower()

        # Compatibilidade: fêmea + touro ou vice-versa
        if outro_id != animal_id and outro_sexo and sexo and outro_sexo != sexo:
            compat = G.compatibilidade_acasalamento(
                animal_id if sexo == "macho" else outro_id,
                outro_id if sexo == "fêmea" else animal_id
            )

            candidatos.append({
                "id": outro_id,
                "nome": outro.get("Brinco") or outro_id,
                "sexo": outro.get("Sexo", "—"),
                "categoria": outro.get("Categoria", "—"),
                "compativel": compat.get("compativel", False),
                "risco_endogamia": compat.get("risco_endogamia", "baixo"),
                "msg": compat.get("msg", "—")
            })

    # Ordena por compatibilidade
    candidatos.sort(key=lambda x: (not x["compativel"], x["risco_endogamia"]))

    return jsonify({
        "animal_id": animal_id,
        "nome": animal.get("Brinco") or animal_id,
        "sexo": sexo,
        "total_candidatos": len(candidatos),
        "compativel": sum(1 for c in candidatos if c["compativel"]),
        "candidatos": candidatos[:20]  # Limita a 20
    })
