#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_reproducao.py — IA dashboard route (/reproducao/ia-predicoes)
Minimal: read models, predict, render template.
"""

from flask import render_template_string, Blueprint
from datetime import datetime
import pandas as pd
import pickle
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('reproducao', __name__, url_prefix='/reproducao')


@bp.route('/ia-predicoes', methods=['GET'])
def ia_predicoes():
    """Dashboard: IA predictions for morte, cio, inbreeding."""
    try:
        from db import ler_aba, DATA_DIR
        from reproducao_avancada_ia import alertas_ia_preditiva

        df_animais = ler_aba('Animais')
        df_manejo = ler_aba('Manejo')
        df_compras = ler_aba('Compras')
        df_vendas = ler_aba('Vendas')

        ia_result = alertas_ia_preditiva(df_animais, df_manejo, df_compras, df_vendas)

        return render_template_string('''
        <h1>🤖 IA Preditiva — Onda 19</h1>
        <div class="metrics">
            <div class="metric">
                <span class="value">{{ urgentes|length }}</span>
                <span class="label">🚨 Urgentes</span>
            </div>
            <div class="metric">
                <span class="value">{{ avisos|length }}</span>
                <span class="label">⚠️ Avisos</span>
            </div>
        </div>

        {% if urgentes %}
        <div class="card">
            <h2>🚨 Urgentes</h2>
            <ul>
            {% for u in urgentes %}
                <li><strong>{{ u.tipo }}</strong>: {{ u.animal }} — {{ u.motivos or u.acao }}</li>
            {% endfor %}
            </ul>
        </div>
        {% endif %}

        {% if avisos %}
        <div class="card">
            <h2>⚠️ Avisos</h2>
            <ul>
            {% for a in avisos %}
                <li><strong>{{ a.tipo }}</strong>: {{ a.animal }} — {{ a.acao }}</li>
            {% endfor %}
            </ul>
        </div>
        {% endif %}

        <p><small>Timestamp: {{ timestamp }}</small></p>
        ''',
        urgentes=ia_result.get('urgentes', []),
        avisos=ia_result.get('avisos', []),
        timestamp=ia_result.get('timestamp', '')
        )
    except Exception as e:
        logger.error(f"❌ IA dashboard erro: {e}")
        return f"<h1>Erro IA</h1><p>{str(e)}</p>", 500
