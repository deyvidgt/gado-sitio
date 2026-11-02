#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_doencas.py — Rotas de histórico de doenças, tratamentos e carência (v5.10 Onda 2)
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from extensions import app, _agora, _validar_csrf, login_required, salvar_linha
from doencas_carencia import (
    PERIODOS_CARENCIA_PADRAO, historico_animal, obter_status_carencia,
    status_por_animal, validar_venda,
)
import animais


@app.route("/doencas", methods=["GET"])
@login_required
def listar_doencas():
    """Lista todos os registros de doença/tratamento e status de carência."""
    # Fonte única: as 3 abas de medicação, não só `Tratamentos`.
    status_todos = status_por_animal("leite")

    animais_com_alerta = []
    for vaca_id, status in status_todos.items():
        try:
            df_animais = animais.carregar()
            animal = df_animais[df_animais['ID'].astype(str) == str(vaca_id)].iloc[0] if not df_animais.empty else {}
            brinco_desc = f"{animal.get('Brinco Cor', '')} {int(animal.get('Brinco Nº', 0)) or '??'}"
        except Exception:
            brinco_desc = f"ID {vaca_id}"

        animais_com_alerta.append({
            "vaca_id": vaca_id,
            "brinco": brinco_desc,
            "em_carencia": status['em_carencia'],
            "dias_restantes": status['dias_restantes'],
            "medicamento": status['medicamento'],
            "data_liberacao": status['data_liberacao'],
        })

    # Ordena: em carência primeiro
    animais_com_alerta.sort(key=lambda x: (not x['em_carencia'], x['dias_restantes']))

    return render_template("doencas_lista.html", animais_com_alerta=animais_com_alerta)


@app.route("/doencas/registrar", methods=["GET", "POST"])
@login_required
def registrar_doenca():
    """Registra uma doença/tratamento com período de carência."""
    if request.method == "POST":
        _validar_csrf()
        f = request.form

        vaca_id = str(f.get("vaca_id", "")).strip()
        data = f.get("data", "").strip()
        doenca = f.get("tipo_doenca", "").strip()
        tratamento = f.get("tratamento", "").strip()
        medicamento = f.get("medicamento", "").strip()
        observacoes = f.get("observacoes", "").strip()

        if not all([vaca_id, data, doenca, medicamento]):
            flash("⚠️ Preencha todos os campos obrigatórios.", "warning")
            return render_template("doencas_registrar.html", hoje=_agora().strftime("%Y-%m-%d"),
                                   periodos=PERIODOS_CARENCIA_PADRAO)

        try:
            salvar_linha("Tratamentos", [
                vaca_id,
                data,
                "",  # Brinco (preenchido depois se necessário)
                doenca,
                tratamento,
                medicamento,
                observacoes,
                "Não",  # Resolvido
                None,   # Data Resolução
                request.environ.get('REMOTE_USER', 'desconhecido'),
                None,   # ID Envio
                _agora().isoformat(timespec="seconds"),
            ])

            # Calcula carência e avisa
            status = obter_status_carencia(vaca_id, "leite")
            if status['em_carencia']:
                dias = status['dias_restantes']
                flash(f"✅ Doença registrada — {medicamento} libera em {dias} dias ({status['data_liberacao'].strftime('%d/%m/%Y')}).", "success")
            else:
                flash("✅ Doença registrada.", "success")

            return redirect(url_for("listar_doencas"))
        except Exception as e:
            app.logger.error(f"Erro ao registrar doença: {e}")
            flash(f"❌ Erro ao registrar: {e}", "error")

    # GET: formulário
    df_animais = animais.carregar()
    vacas_opcoes = []
    for _, animal in df_animais.iterrows():
        id_animal = str(animal.get("ID", "")).strip()
        brinco = f"{animal.get('Brinco Cor', '')} {animal.get('Brinco Nº', '')}".strip()
        if id_animal:
            vacas_opcoes.append({"id": id_animal, "brinco": brinco})

    return render_template("doencas_registrar.html",
                          vacas_opcoes=vacas_opcoes,
                          periodos=PERIODOS_CARENCIA_PADRAO,
                          hoje=_agora().strftime("%Y-%m-%d"))


@app.route("/doencas/<animal_id>", methods=["GET"])
@login_required
def historico_doencas(animal_id):
    """Histórico de doenças de um animal específico."""
    historico = historico_animal(animal_id, dias=365)
    status = obter_status_carencia(animal_id, "leite")

    try:
        df_animais = animais.carregar()
        animal = df_animais[df_animais['ID'].astype(str) == str(animal_id)].iloc[0]
        animal_desc = f"{animal.get('Brinco Cor', '')} {animal.get('Brinco Nº', '')} #{animal.get('ID', '')}"
    except Exception:
        animal_desc = f"ID {animal_id}"

    return render_template("doencas_historico.html",
                          animal_id=animal_id,
                          animal_desc=animal_desc,
                          historico=historico,
                          status_carencia=status)


@app.route("/api/doencas/validar-venda", methods=["POST"])
@login_required
def api_validar_venda():
    """API: valida se animal pode ser vendido (leite ou carne)."""
    f = request.get_json() or {}
    animal_id = f.get("animal_id", "").strip()
    tipo_produto = f.get("tipo", "leite").strip().lower()

    if tipo_produto not in ["leite", "carne"]:
        tipo_produto = "leite"

    pode_vender, motivo = validar_venda(animal_id, tipo_produto)

    return jsonify({
        "pode_vender": pode_vender,
        "motivo": motivo,
        "animal_id": animal_id,
        "tipo_produto": tipo_produto
    })


@app.route("/api/doencas/resumo", methods=["GET"])
@login_required
def api_resumo_carencias():
    """API: resumo de animais em carência (mesma fonte da venda e do painel)."""
    animais_em_carencia = [
        {
            "vaca_id": s["animal_id"],
            "medicamento": s["medicamento"],
            "dias_restantes": s["dias_restantes"],
            "data_liberacao": s["data_liberacao"].isoformat() if s["data_liberacao"] else None,
        }
        for s in status_por_animal("leite").values() if s["em_carencia"]
    ]

    return jsonify({
        "total_em_carencia": len(animais_em_carencia),
        "animais": animais_em_carencia
    })
