#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_estimar_peso.py — Rota e API para Estimação de Peso por Foto / Biometria Bovina (v5.20)
Inspirado em ferramentas de avaliação visual de gado (Jetbov, iRancho, FieldData).
"""
import os
import uuid
import pandas as pd
from flask import render_template, request, redirect, url_for, flash, jsonify, session
import animais as A
import db
import pesagem as P
import peso_foto as PF
from extensions import app, login_required, _agora, _validar_csrf
from routes_animais import _membro_logado, fazer_backup_seguro

@app.route("/animais/estimar_peso", methods=["GET", "POST"])
@login_required
def estimar_peso():
    """Interface de registro e upload de foto para estimativa de peso (biometria)."""
    id_animal = request.args.get("id", "").strip()
    df_animais = A.carregar()
    
    animal = None
    if id_animal:
        animal = A.por_id(df_animais, id_animal)

    vacas_ou_todos = df_animais[df_animais["Status"].astype(str) == "Vivo"] if not df_animais.empty else pd.DataFrame()

    if request.method == "POST":
        _validar_csrf()
        id_selecionado = request.form.get("animal_id", "").strip()
        comp_cm = request.form.get("comprimento_cm", "")
        prof_cm = request.form.get("profundidade_cm", "")
        ref_cm = request.form.get("referencia_cm", "100")  # padrão 100cm se não informado
        bcs = request.form.get("bcs", "5")
        raca = request.form.get("raca", "Zebuíno / Mestiço")
        fase = request.form.get("fase", "Adulto")
        salvar_historico = request.form.get("salvar_historico") == "on"

        try:
            # Validação das medidas
            c_val, p_val, r_val, bcs_val = PF.validar(comp_cm, prof_cm, ref_cm, bcs)
            
            # Cálculo do peso bruto (Schaeffer)
            peso_bruto = PF.estimar_bruto(c_val, p_val)
            f_bcs = PF.FATOR_BCS.get(bcs_val, 1.0)
            
            # Pega fator de calibração do sítio se houver
            dados_cache = db.carregar_aba("Manejo")
            fator_sitio, _ = PF.fator_calibracao(dados_cache)
            
            peso_estimado = round(peso_bruto * f_bcs * fator_sitio, 1)
            
            # Arrobas de carcaça (rendimento 50% ou configuração)
            rendimento = 0.50
            try:
                from routes_animais import _rendimento
                rendimento = _rendimento()
            except Exception:
                pass
                
            arrobas = round((peso_estimado * rendimento) / 15.0, 2)
            
            # Preço da arroba configurado
            from calculos import preco_arroba_config
            preco_arr = preco_arroba_config()
            
            # Se não houver preço configurado, usar valor padrão de mercado (ex: R$ 300/@)
            preco_arroba = preco_arr if preco_arr > 0 else 300.0
            valor_financeiro = round(arrobas * preco_arroba, 2)

            resultado = {
                "animal_id": id_selecionado,
                "peso_estimado": peso_estimado,
                "arrobas": arrobas,
                "valor_financeiro": valor_financeiro,
                "comprimento": c_val,
                "profundidade": p_val,
                "bcs": bcs_val,
                "raca": raca,
                "fase": fase,
            }

            if salvar_historico and id_selecionado:
                # Salvar no Manejo como "Peso Estimado"
                fazer_backup_seguro()
                animal_obj = A.por_id(df_animais, id_selecionado)
                brinco_str = A.fmt_brinco(animal_obj["Brinco Cor"], animal_obj["Brinco Nº"]) if animal_obj else id_selecionado
                ref_texto = f"{brinco_str} #{id_selecionado}"
                
                linha_manejo = [
                    _agora().strftime("%d/%m/%Y"),
                    PF.TIPO_ESTIMADO,
                    ref_texto,
                    f"Biometria por Foto: Comp={c_val}cm, Prof={p_val}cm, BCS={bcs_val} (fator {f_bcs}). Estimado={peso_estimado}kg.",
                    "",
                    "",
                    _membro_logado(),
                    f"{ref_texto}: {peso_estimado} kg",
                    _agora().isoformat(),
                ]
                db.salvar_linha("Manejo", linha_manejo)
                flash(f"✅ Peso estimado de {peso_estimado} kg salvo no histórico do animal {id_selecionado}!", "success")
                return redirect(url_for("ficha_animal", id_=id_selecionado))

            return render_template("estimar_peso.html", animal=animal, vacas=vacas_ou_todos, resultado=resultado, medidas={
                "comprimento": comp_cm, "profundidade": prof_cm, "referencia": ref_cm, "bcs": bcs, "raca": raca, "fase": fase
            })

        except ValueError as e:
            flash(f"❌ Erro nas medidas: {e}", "error")

    return render_template("estimar_peso.html", animal=animal, vacas=vacas_ou_todos, resultado=None)
