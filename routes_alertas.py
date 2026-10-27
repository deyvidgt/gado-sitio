# -*- coding: utf-8 -*-
from flask import jsonify, render_template

import alertas
import tempo
from db import carregar_aba
from extensions import _agora, app, login_required
import animais


def _dados_alertas():
    return alertas.todos(
        producao=carregar_aba("Leite Produção"),
        animais=animais.carregar(),
        tratamentos=carregar_aba("Leite Tratamentos"),
        colchao=carregar_aba("Leite Colchão"),
        alimentacao=carregar_aba("Leite Alimentação"),
        referencia=_agora().date(),
    )


@app.route("/alertas")
@login_required
def central_alertas():
    return render_template("alertas.html", alertas=_dados_alertas(), tempo=tempo.previsao())


@app.route("/api/alertas")
@login_required
def api_alertas():
    return jsonify({"alertas": _dados_alertas(), "tempo": tempo.previsao()})


@app.route("/api/tempo/geo", methods=["POST"])
@login_required
def api_tempo_geo():
    """Previsão com coordenadas do navegador (geolocalização mobile)."""
    dados = request.get_json() or {}
    latitude = dados.get("latitude")
    longitude = dados.get("longitude")
    return jsonify(tempo.previsao(latitude=latitude, longitude=longitude))
