#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_curral.py — Manejos de Curral e Apontamentos Rápidos (v5.22)
Módulo unificado e tátil para pecuária de precisão:
  - Pesagens (individual ou lote, cálculo automático de GMD e @)
  - Sanitário / Vacinas (lote, carência, histórico)
  - Mortes / Perdas (baixa no rebanho ativo, causa e data)
  - Nascimentos (registro de bezerro, vínculo com matriz, atualização de inventário)
  - Troca de Lote / Pasto
  - Leitura RFID / Tag (campo otimizado para brincos eletrônicos/visuais)
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
import pandas as pd
from datetime import datetime

import db
import animais as A
import pesagem as P
import pastos as PA
import reproducao as R
from extensions import app, login_required, _agora, _validar_csrf
from routes_animais import _membro_logado, fazer_backup_seguro


@app.route("/curral")
@login_required
def curral_painel():
    """Painel central de Manejos de Curral (Grid tátil para celular e desktop)."""
    df_animais = A.carregar()
    df_pastos = PA.carregar()
    
    vivos = df_animais[df_animais["Status"].astype(str) == "Vivo"] if not df_animais.empty else pd.DataFrame()
    pastos_ativos = PA.ativos(df_pastos) if not df_pastos.empty else pd.DataFrame()

    return render_template(
        "curral_painel.html",
        total_vivos=len(vivos),
        pastos=pastos_ativos.to_dict("records"),
        hoje=_agora().strftime("%Y-%m-%d"),
    )


@app.route("/curral/pesagem", methods=["GET", "POST"])
@login_required
def curral_pesagem():
    """Registro rápido de pesagem individual ou lote."""
    df_animais = A.carregar()
    vivos = df_animais[df_animais["Status"].astype(str) == "Vivo"] if not df_animais.empty else pd.DataFrame()

    if request.method == "POST":
        _validar_csrf()
        brinco = request.form.get("brinco", "").strip()
        peso = request.form.get("peso", "").strip()
        data = request.form.get("data", _agora().strftime("%d/%m/%Y"))
        obs = request.form.get("observacao", "").strip()

        try:
            if not brinco or not peso:
                raise ValueError("Informe o brinco e o peso do animal.")
            
            peso_kg = float(str(peso).replace(",", "."))
            refs, erros = A.resolver_texto(brinco)
            if erros or not refs:
                raise ValueError(f"Animal '{brinco}' não encontrado.")
            
            id_animal = A.ids_de(refs[0])[0]
            animal_obj = A.por_id(df_animais, id_animal)
            brinco_fmt = A.fmt_brinco(animal_obj["Brinco Cor"], animal_obj["Brinco Nº"]) if animal_obj else id_animal
            ref_texto = f"{brinco_fmt} #{id_animal}"

            fazer_backup_seguro()
            linha = [
                data,
                "Pesagem",
                ref_texto,
                f"Pesagem de curral: {peso_kg} kg. {obs}",
                "",
                "",
                _membro_logado(),
                f"{ref_texto}: {peso_kg} kg",
                _agora().isoformat(),
            ]
            db.salvar_linha("Manejo", linha)
            flash(f"⚖️ Pesagem de {peso_kg} kg registrada para {brinco_fmt}!", "success")
            return redirect(url_for("curral_pesagem"))
        except ValueError as e:
            flash(f"❌ {e}", "error")

    return render_template("curral_pesagem.html", vacas=vivos)


@app.route("/curral/sanitario", methods=["GET", "POST"])
@login_required
def curral_sanitario():
    """Registro de vacinas e medicamentos com carência."""
    df_animais = A.carregar()
    vivos = df_animais[df_animais["Status"].astype(str) == "Vivo"] if not df_animais.empty else pd.DataFrame()

    if request.method == "POST":
        _validar_csrf()
        brinco = request.form.get("brinco", "").strip()
        produto = request.form.get("produto", "").strip()
        lote_med = request.form.get("lote_medicamento", "").strip()
        carencia_dias = request.form.get("carencia", "0")
        data = request.form.get("data", _agora().strftime("%d/%m/%Y"))

        try:
            if not produto:
                raise ValueError("Informe o nome da vacina ou medicamento.")
            
            ref_texto = "Rebanho todo"
            if brinco:
                refs, erros = A.resolver_texto(brinco)
                if erros or not refs:
                    raise ValueError(f"Animal '{brinco}' não encontrado.")
                id_animal = A.ids_de(refs[0])[0]
                animal_obj = A.por_id(df_animais, id_animal)
                brinco_fmt = A.fmt_brinco(animal_obj["Brinco Cor"], animal_obj["Brinco Nº"]) if animal_obj else id_animal
                ref_texto = f"{brinco_fmt} #{id_animal}"

            fazer_backup_seguro()
            linha = [
                data,
                "Sanitário / Vacina",
                ref_texto,
                f"Aplicação de {produto} (Lote: {lote_med}). Carência: {carencia_dias} dias.",
                produto,
                "",
                _membro_logado(),
                "",
                _agora().isoformat(),
            ]
            db.salvar_linha("Manejo", linha)
            flash(f"💉 Aplicação de {produto} registrada com sucesso!", "success")
            return redirect(url_for("curral_sanitario"))
        except ValueError as e:
            flash(f"❌ {e}", "error")

    return render_template("curral_sanitario.html", vacas=vivos)


@app.route("/curral/mortalidade", methods=["GET", "POST"])
@login_required
def curral_mortalidade():
    """Registro de óbito ou perda (baixa no rebanho ativo)."""
    df_animais = A.carregar()
    vivos = df_animais[df_animais["Status"].astype(str) == "Vivo"] if not df_animais.empty else pd.DataFrame()

    if request.method == "POST":
        _validar_csrf()
        brinco = request.form.get("brinco", "").strip()
        causa = request.form.get("causa", "Desconhecida").strip()
        data = request.form.get("data", _agora().strftime("%d/%m/%Y"))

        try:
            if not brinco:
                raise ValueError("Informe o animal (brinco).")
            
            refs, erros = A.resolver_texto(brinco)
            if erros or not refs:
                raise ValueError(f"Animal '{brinco}' não encontrado.")
            
            id_animal = A.ids_de(refs[0])[0]
            fazer_backup_seguro()
            
            # Atualizar status do animal para 'Morto' ou 'Perdido' na aba Animais
            for idx, r in df_animais.iterrows():
                if r.get("ID") == id_animal:
                    df_animais.at[idx, "Status"] = "Morto"
                    df_animais.at[idx, "Data Saída"] = data
                    break
            db.reescrever_aba("Animais", df_animais)

            # Registrar no Manejo
            linha = [
                data,
                "Mortalidade",
                id_animal,
                f"Baixa por óbito/perda. Causa: {causa}",
                "",
                "",
                _membro_logado(),
                "",
                _agora().isoformat(),
            ]
            db.salvar_linha("Manejo", linha)
            flash(f"⚠️ Animal {id_animal} baixado por mortalidade ({causa}).", "success")
            return redirect(url_for("curral_mortalidade"))
        except ValueError as e:
            flash(f"❌ {e}", "error")

    return render_template("curral_mortalidade.html", vacas=vivos)


@app.route("/curral/nascimento", methods=["GET", "POST"])
@login_required
def curral_nascimento():
    """Registro de novos bezerros (nascimentos) e vínculo com a matriz."""
    df_animais = A.carregar()
    femeas = df_animais[df_animais["Sexo"].astype(str).str.upper().str.startswith("F") & (df_animais["Status"].astype(str) == "Vivo")] if not df_animais.empty else pd.DataFrame()

    if request.method == "POST":
        _validar_csrf()
        mae = request.form.get("mae", "").strip()
        sexo = request.form.get("sexo", "M").strip()
        raca = request.form.get("raca", "Zebuíno").strip()
        cor = request.form.get("cor", "Amarelo").strip()
        num = request.form.get("numero", "").strip()
        data = request.form.get("data", _agora().strftime("%d/%m/%Y"))

        try:
            if not num.isdigit():
                raise ValueError("Informe um número de brinco válido para o bezerro.")
            
            fazer_backup_seguro()
            
            # Criar novo ID de animal
            novo_id = A.proximo_id(df_animais)
            
            nova_linha_animal = [
                novo_id, cor, int(num), _membro_logado(), "Bezerro(a)", sexo, raca,
                "", "", data, data, "Nascimento", "", mae, "Nascido no sítio", "Reprodução", "Em Lactação", data
            ]
            
            # Inserir na aba Animais
            nova_df = pd.DataFrame([nova_linha_animal], columns=db.carregar_aba("Animais").columns if not db.carregar_aba("Animais").empty else None)
            # Se a aba estiver vazia ou com colunas padrão
            db.salvar_linha("Animais", nova_linha_animal)

            # Registrar parto no Manejo
            linha_manejo = [
                data,
                "Parto",
                f"Mãe: {mae}",
                f"Nascimento de bezerro(a) #{novo_id} ({cor} {num}).",
                "",
                "",
                _membro_logado(),
                "",
                _agora().isoformat(),
            ]
            db.salvar_linha("Manejo", linha_manejo)
            flash(f"🐮 Bezerro(a) #{novo_id} ({cor} {num}) registrado com sucesso!", "success")
            return redirect(url_for("curral_nascimento"))
        except ValueError as e:
            flash(f"❌ {e}", "error")

    return render_template("curral_nascimento.html", femeas=femeas)


@app.route("/curral/troca-lote", methods=["GET", "POST"])
@login_required
def curral_troca_lote():
    """Movimentação rápida de animais entre pastos."""
    df_animais = A.carregar()
    df_pastos = PA.carregar()
    vivos = df_animais[df_animais["Status"].astype(str) == "Vivo"] if not df_animais.empty else pd.DataFrame()
    pastos_ativos = PA.ativos(df_pastos) if not df_pastos.empty else pd.DataFrame()

    if request.method == "POST":
        _validar_csrf()
        brinco = request.form.get("brinco", "").strip()
        pasto_destino = request.form.get("pasto_destino", "").strip()
        data = request.form.get("data", _agora().strftime("%d/%m/%Y"))

        try:
            if not pasto_destino:
                raise ValueError("Selecione o pasto de destino.")
            
            ref_texto = "Rebanho todo"
            if brinco:
                refs, erros = A.resolver_texto(brinco)
                if erros or not refs:
                    raise ValueError(f"Animal '{brinco}' não encontrado.")
                id_animal = A.ids_de(refs[0])[0]
                animal_obj = A.por_id(df_animais, id_animal)
                brinco_fmt = A.fmt_brinco(animal_obj["Brinco Cor"], animal_obj["Brinco Nº"]) if animal_obj else id_animal
                ref_texto = f"{brinco_fmt} #{id_animal}"

            fazer_backup_seguro()
            linha = [
                data,
                "Movimentação de Pasto",
                ref_texto,
                f"Movimentação para o pasto {pasto_destino}",
                "",
                pasto_destino,
                _membro_logado(),
                "",
                _agora().isoformat(),
            ]
            db.salvar_linha("Manejo", linha)
            flash(f"🌱 Movimentação registrada para o pasto {pasto_destino}!", "success")
            return redirect(url_for("curral_troca_lote"))
        except ValueError as e:
            flash(f"❌ {e}", "error")

    return render_template("curral_troca_lote.html", vacas=vivos, pastos=pastos_ativos.to_dict("records"))
