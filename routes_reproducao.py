#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas da Reprodução — Sítio Santo Antonio v5.3 + Onda 8.4 gráficos + Onda 12 IATF/culling
"""
import pandas as pd
from flask import render_template, request, redirect, url_for, flash

import animais as A
import db
import reproducao as R
import reproducao_avancada as RA
from extensions import app, _agora, _validar_csrf, login_required
from routes_animais import _membro_logado, fazer_backup_seguro


def _grafico_composicao_reprodutivo(sit, df_animais):
    """Pizza: Composição (Coberta/Prenha/Vazia/Pariu). Onda 8.4.3"""
    try:
        if not sit:
            return None

        labels = ["Coberta", "Prenha", "Vazia", "Pariu"]
        data = [
            sum(1 for s in sit if s.get("status") == "coberta"),
            sum(1 for s in sit if s.get("status") == "prenha"),
            sum(1 for s in sit if s.get("status") == "vazia"),
            sum(1 for s in sit if s.get("status") == "pariu"),
        ]

        if sum(data) == 0:
            return None

        return {"labels": labels, "data": data}
    except Exception as e:
        app.logger.debug(f"Gráfico composição reprodutivo falhou: {e}")
        return None


def _grafico_timeline_partos(sit):
    """Timeline: Próximos partos nos 285 dias (com foco próximos 90). Onda 8.4.4"""
    try:
        if not sit:
            return None

        hoje = _agora().date()

        # Agrupa prenhas por data prevista
        partos_por_data = {}
        for s in sit:
            if s.get("status") == "prenha" and s.get("parto_previsto"):
                data = pd.to_datetime(s["parto_previsto"]).date()
                dias_restantes = (data - hoje).days
                if 0 <= dias_restantes <= 285:
                    data_str = data.isoformat()
                    partos_por_data[data_str] = partos_por_data.get(data_str, 0) + 1

        if not partos_por_data:
            return None

        datas = sorted(partos_por_data.keys())
        labels = [pd.to_datetime(d).strftime("%d/%m") for d in datas]
        data = [partos_por_data[d] for d in datas]

        return {"labels": labels, "data": data}
    except Exception as e:
        app.logger.debug(f"Gráfico timeline partos falhou: {e}")
        return None


@app.route("/reproducao")
@login_required
def reproducao():
    hoje = pd.Timestamp(_agora()).normalize()
    df_an = A.carregar()
    df_man = db.carregar_aba("Manejo")
    sit = R.situacao(df_man, df_an, hoje)
    vacas = [A.ref(r) for _, r in A.vivos(df_an).iterrows()
             if A._txt(r.get("Sexo")).upper().startswith("F")]

    # Gráficos Onda 8.4
    grafico_composicao = _grafico_composicao_reprodutivo(sit, df_an)
    grafico_partos = _grafico_timeline_partos(sit)

    return render_template("reproducao.html", situacoes=sit,
                           ind=R.indicadores(sit, df_an),
                           alertas=R.alertas(sit, hoje), vacas=vacas,
                           grafico_composicao=grafico_composicao,
                           grafico_partos=grafico_partos,
                           hoje=f"{hoje:%Y-%m-%d}", resultados=R.RESULTADOS)


@app.route("/reproducao/registrar", methods=["POST"])
@login_required
def registrar_reproducao():
    _validar_csrf()
    f = request.form
    tipo = R.TIPO_DIAGNOSTICO if f.get("tipo") == "diagnostico" else R.TIPO_COBERTURA
    try:
        R.registrar(tipo, f.get("vaca", ""), f.get("data"), f.get("touro", ""),
                    f.get("resultado", ""), _membro_logado())
        fazer_backup_seguro()
        flash("🐮 Anotado!" if tipo == R.TIPO_COBERTURA else "🩺 Resultado anotado!",
              "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("reproducao"))


# ── Onda 12: IATF + Cio + IEP + Culling ─────────────────────────────────────────

@app.route("/reproducao/iatf")
@login_required
def reproducao_iatf():
    """Dashboard IATF: alertas de protocolo, detecção de cio, sincronização."""
    hoje = pd.Timestamp(_agora()).normalize()
    df_man = db.carregar_aba("Manejo")
    df_an = A.carregar()

    alertas_iatf = RA.alertas_iatf(df_man, df_an, hoje)
    cios_proximos = RA.detectar_cios_proximos(df_man, df_an, hoje, dias_proximos=7)

    return render_template("reproducao_iatf.html",
                         alertas_iatf=alertas_iatf,
                         cios_proximos=cios_proximos,
                         hoje=f"{hoje:%Y-%m-%d}")


@app.route("/reproducao/culling")
@login_required
def reproducao_culling():
    """Dashboard de culling: sugestões de descarte por IEP + taxa prenhez."""
    df_man = db.carregar_aba("Manejo")
    df_an = A.carregar()

    # IEP por vaca
    ieps = RA.iep_por_vaca(df_man, df_an)

    # Sugestões de culling (já ordenadas por urgência)
    culling = RA.sugestoes_culling(df_man, df_an)

    # Resumo para cards
    resumo = {
        "vacas_analisadas": len(ieps),
        "candidatas_culling": len(culling),
        "iep_medio": round(sum(d["iep_media"] for d in ieps.values()) / len(ieps), 1) if ieps else 0,
    }

    return render_template("reproducao_culling.html",
                         culling=culling,
                         ieps=ieps,
                         resumo=resumo)


@app.route("/reproducao/vaca/<animal_id>")
@login_required
def reproducao_vaca(animal_id):
    """Ficha reprodutiva de uma vaca: histórico completo, IEP, taxa prenhez."""
    df_man = db.carregar_aba("Manejo")
    df_an = A.carregar()

    # Buscar animal
    animal = None
    if df_an is not None and not df_an.empty:
        animal = df_an[df_an["ID"] == animal_id].iloc[0] if animal_id in df_an["ID"].values else None

    if animal is None:
        flash("🐄 Animal não encontrado.", "error")
        return redirect(url_for("reproducao"))

    # Dados reprodutivos
    iep_data = RA.iep_por_vaca(df_man, df_an).get(animal_id, {})
    taxa = RA.taxa_prenhez(df_man, animal_id)

    return render_template("reproducao_vaca_ficha.html",
                         animal=animal,
                         animal_ref=A.ref(animal),
                         iep_data=iep_data,
                         taxa_prenhez=taxa)


@app.route("/reproducao/observacao-cio")
@login_required
def reproducao_observacao_cio():
    """Formulário de observação manual de cio + sugestão de inseminação."""
    df_man = db.carregar_aba("Manejo")
    df_an = A.carregar()

    # Histórico de cios nos últimos 21 dias
    historico = _historico_cios_recentes(df_man, df_an, dias=21)

    return render_template("reproducao_observacao_cio.html",
                         historico_cios=historico,
                         usuario_atual=_membro_logado())


@app.route("/reproducao/registrar-cio", methods=["POST"])
@login_required
def registrar_observacao_cio():
    """Registra observação de cio + calcula sugestão de inseminação."""
    _validar_csrf()
    f = request.form

    try:
        data = f.get("data", "")
        hora = f.get("hora", "12:00")
        brincos = f.get("brincos", "")
        intensidade = int(f.get("intensidade", 3))
        observacao = f.get("observacao", "")
        sinais = f.getlist("sinais")

        # Validações
        if not data or not brincos:
            flash("❌ Data e animal são obrigatórios.", "error")
            return redirect(url_for("reproducao_observacao_cio"))

        if not 1 <= intensidade <= 5:
            intensidade = 3

        # Buscar animal
        animal_ids = A.ids_de(brincos)
        if not animal_ids:
            flash("❌ Animal não encontrado.", "error")
            return redirect(url_for("reproducao_observacao_cio"))

        # Registrar em Manejo (tipo "Observação de Cio")
        descricao = f"Intensidade {intensidade}/5 — {', '.join(sinais) if sinais else 'Sem sinais'}"
        if observacao:
            descricao += f" — {observacao}"

        nova_linha = [
            data,
            "Observação de Cio",
            1,
            descricao,
            _membro_logado(),
            "",  # Perda De
            f"Cio {intensidade}/5",  # Produto
            "",  # Nascimento De
            brincos,  # Brincos
            "",  # Pesos
        ]
        db.salvar_linha("Manejo", nova_linha)

        fazer_backup_seguro()

        flash(f"🔥 Cio registrado para {brincos}! Sugestão: inseminar em 12h", "success")

        return redirect(url_for("reproducao_iatf"))

    except Exception as e:
        flash(f"❌ Erro ao registrar: {str(e)}", "error")
        return redirect(url_for("reproducao_observacao_cio"))


def _historico_cios_recentes(df_man, df_an, dias=21) -> list[dict]:
    """Retorna cios registrados nos últimos N dias."""
    if df_man is None or df_man.empty:
        return []

    hoje = pd.Timestamp(_agora()).normalize()
    data_limite = hoje - pd.Timedelta(days=dias)

    cios = []
    for _, row in df_man.iterrows():
        if A._txt(row.get("Tipo")) != "Observação de Cio":
            continue

        try:
            data_registro = pd.Timestamp(row.get("Data")).normalize()
            if data_registro < data_limite or data_registro > hoje:
                continue

            brincos_str = A._txt(row.get("Brincos", ""))
            animal_id = (A.ids_de(brincos_str) or ["?"])[0]

            # Extrair intensidade da descrição
            desc = A._txt(row.get("Descrição", ""))
            intensidade = 3
            if "Intensidade" in desc:
                try:
                    intensidade = int(desc.split("Intensidade ")[1].split("/")[0])
                except:
                    pass

            # Calcular sugestão de inseminação (12h depois)
            data_inseminacao = data_registro + pd.Timedelta(hours=12)

            cios.append({
                "data": str(data_registro.date()),
                "hora": "—",
                "animal_id": animal_id,
                "animal_ref": brincos_str,
                "intensidade": intensidade,
                "sinais": [s for s in desc.split(" — ")[1:] if s],
                "data_inseminacao_sugerida": str(data_inseminacao.date()),
                "hora_inseminacao": "14:00",
            })
        except Exception:
            continue

    return sorted(cios, key=lambda x: x["data"], reverse=True)
