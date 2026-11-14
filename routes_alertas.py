# -*- coding: utf-8 -*-
from flask import jsonify, render_template, request
import json

import alertas
import tempo
from db import carregar_aba
from extensions import _agora, app, login_required
import animais


def _dados_alertas():
    from doencas_carencia import carencias_ativas
    referencia = _agora().date()
    return alertas.todos(
        producao=carregar_aba("Leite Produção"),
        animais=animais.carregar(),
        carencias=carencias_ativas("leite", referencia),
        colchao=carregar_aba("Leite Colchão"),
        alimentacao=carregar_aba("Leite Alimentação"),
        referencia=referencia,
    )


def _preparar_notificacoes(alertas_lista):
    """Converte alertas para formato de Web Push com ações."""
    notificacoes = []
    categorias = {}

    for alerta in alertas_lista:
        categoria = alerta.get("categoria", "outros")
        if categoria not in categorias:
            categorias[categoria] = []
        categorias[categoria].append(alerta)

    # Agrupa por categoria com badge de contagem
    for categoria, items in categorias.items():
        urgentes = sum(1 for a in items if a.get("urgencia") == "urgente")
        if urgentes > 0 or len(items) <= 3:
            for alerta in items[:3]:  # Max 3 por categoria
                acao = alerta.get("rota", "/alertas")
                notificacoes.append({
                    "title": f"🔔 {categoria.title()}",
                    "body": alerta.get("titulo", alerta.get("msg", "Novo alerta")),
                    "tag": f"{categoria}-{len(notificacoes)}",
                    "urgencia": alerta.get("urgencia", "aviso"),
                    "categoria": categoria,
                    "url": acao,
                    "badge": f"{len(items)}" if len(items) > 1 else None,
                    "actions": [
                        {"action": "open", "title": "Abrir", "icon": "/static/icon-check.png"},
                        {"action": "dismiss", "title": "Descartar", "icon": "/static/icon-close.png"}
                    ] if acao != "/alertas" else []
                })

    return notificacoes


@app.route("/alertas", endpoint="central_alertas")
@login_required
def central_alertas():
    return render_template("alertas.html", alertas=_dados_alertas(), tempo=tempo.previsao())


@app.route("/api/alertas")
@login_required
def api_alertas():
    return jsonify({"alertas": _dados_alertas(), "tempo": tempo.previsao()})


@app.route("/api/alertas/push")
@login_required
def api_alertas_push():
    """Retorna alertas formatados para Web Push (com ações)."""
    alertas_lista = _dados_alertas()
    notificacoes = _preparar_notificacoes(alertas_lista)
    return jsonify({"notificacoes": notificacoes, "total": len(alertas_lista)})


@app.route("/api/notificacoes/acao", methods=["POST"])
@login_required
def api_notificacoes_acao():
    """Registra ação do usuário em notificação (botão clicado)."""
    try:
        dados = request.get_json() or {}
        # Log para análise de engajamento
        app.logger.info(f"Notificação {dados.get('notification_id')}: {dados.get('action')} às {dados.get('timestamp')}")
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


@app.route("/api/tempo/geo", methods=["POST"])
@login_required
def api_tempo_geo():
    """Previsão com coordenadas do navegador (geolocalização mobile)."""
    dados = request.get_json() or {}
    latitude = dados.get("latitude")
    longitude = dados.get("longitude")
    return jsonify(tempo.previsao(latitude=latitude, longitude=longitude))
