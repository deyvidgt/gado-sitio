from agora import agora
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_enfermaria.py — Rotas do Módulo de Enfermaria e Saúde Animal (v5.23)
"""
from flask import render_template, request, redirect, url_for, flash
import pandas as pd
from datetime import datetime

import db
import animais as A
import enfermaria as ENF
from extensions import app, login_required, _agora, _validar_csrf
from routes_animais import _membro_logado, fazer_backup_seguro

@app.route("/animais/enfermaria")
@login_required
def enfermaria_painel():
    """Painel da Enfermaria: animais em observação ou tratamento crítico."""
    df_animais = A.carregar()
    df_enfermaria = ENF.carregar_enfermaria()
    
    tratamento = ENF.animais_em_tratamento()
    
    # Adicionar dados legíveis do animal
    lista_tratamento = []
    for item in tratamento:
        aid = item.get("Animal ID")
        animal_obj = A.por_id(df_animais, aid) if aid else None
        brinco_fmt = A.fmt_brinco(animal_obj["Brinco Cor"], animal_obj["Brinco Nº"]) if animal_obj else aid
        lista_tratamento.append({
            **item,
            "animal_ref": brinco_fmt,
        })

    vivos = df_animais[df_animais["Status"].astype(str) == "Vivo"] if not df_animais.empty else pd.DataFrame()

    return render_template(
        "enfermaria.html",
        tratamentos=lista_tratamento,
        vacas=vivos,
    )


@app.route("/animais/enfermaria/adicionar", methods=["POST"])
@login_required
def enfermaria_adicionar():
    """Adiciona um animal à enfermaria."""
    _validar_csrf()
    f = request.form
    brinco = f.get("brinco", "").strip()
    gravidade = f.get("gravidade", "Observação").strip()
    sintomas = f.get("sintomas", "").strip()
    diagnostico = f.get("diagnostico", "").strip()
    tratamento = f.get("tratamento", "").strip()
    data = f.get("data", _agora().strftime("%d/%m/%Y"))

    try:
        if not brinco:
            raise ValueError("Informe o animal (brinco ou ID).")
        
        refs, erros = A.resolver_texto(brinco)
        if erros or not refs:
            raise ValueError(f"Animal '{brinco}' não encontrado.")
        
        id_animal = A.ids_de(refs[0])[0]
        fazer_backup_seguro()

        novo_id = f"ENF-{agora().strftime('%m%d%H%M')}"
        linha = [
            novo_id,
            data,
            id_animal,
            gravidade,
            sintomas,
            diagnostico,
            tratamento,
            "Em Tratamento",
            "",
            f"Registrado por {_membro_logado()}"
        ]
        db.salvar_linha("Enfermaria", linha)
        flash(f"🏥 Animal #{id_animal} admitido na enfermaria ({gravidade})!", "success")
        return redirect(url_for("enfermaria_painel"))
    except ValueError as e:
        flash(f"❌ {e}", "error")
        return redirect(url_for("enfermaria_painel"))


@app.route("/animais/enfermaria/alta/<id_enf>", methods=["POST"])
@login_required
def enfermaria_alta(id_enf):
    """Dá alta (cura) a um animal na enfermaria."""
    _validar_csrf()
    df = ENF.carregar_enfermaria()
    data_hoje = _agora().strftime("%d/%m/%Y")
    
    atualizado = False
    for idx, r in df.iterrows():
        if str(r.get("ID")) == str(id_enf):
            df.at[idx, "Status"] = "Curado / Alta"
            df.at[idx, "Data Cura"] = data_hoje
            atualizado = True
            break
            
    if atualizado:
        fazer_backup_seguro()
        db.reescrever_aba("Enfermaria", df)
        flash("✅ Animal dado de alta com sucesso!", "success")
    else:
        flash("❌ Registro não encontrado na enfermaria.", "error")
        
    return redirect(url_for("enfermaria_painel"))
