#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dashboard.py — Cards clicáveis do painel (v5.6)
Agregação mínima de dados dos módulos para exibir como cards interativos.
"""
from flask import current_app as app
from db import carregar_aba
from extensions import _agora


def cards_painel(dados, r, extras):
    """Retorna lista de cards para o painel com dados básicos.
    Cada card: {titulo, icone, numero, subtexto, link, alertas, status}
    status: 'ok' | 'aviso' | 'urgente'
    """
    cards = []

    # Leite (v5.4)
    try:
        import leite
        prod = carregar_aba("Leite Produção")
        resumo = leite.acumulados(prod, _agora().date())
        cards.append({
            "titulo": "Leite",
            "icone": "🥛",
            "numero": int(resumo.get("dia", 0)),
            "subtexto": "L/dia",
            "link": "painel_leite",
            "alertas": 0,
            "status": "ok",
        })
    except Exception as e:
        app.logger.debug(f"Card Leite falhou: {e}")

    # Corte (estoque)
    cards.append({
        "titulo": "Corte",
        "icone": "🐄",
        "numero": r.get("estoque", 0),
        "subtexto": "cabeças",
        "link": "compras",
        "alertas": 0,
        "status": "ok",
    })

    # Insumos (dias até faltar)
    try:
        from insumos import previsao_todos
        insumos = previsao_todos(dados.get("Visitas"), dados.get("Gastos"), _agora())
        urgentes = sum(1 for i in insumos if i.get("status") in ("urgente", "acabou"))
        dias_min = min((i.get("dias_restantes", 999) for i in insumos
                       if i.get("dias_restantes") and i.get("status") not in ("sem_dados", "sem_consumo")),
                      default=None)
        status = "urgente" if urgentes > 0 else ("aviso" if dias_min and dias_min < 15 else "ok")
        cards.append({
            "titulo": "Insumos",
            "icone": "🌾",
            "numero": int(dias_min) if dias_min else 0,
            "subtexto": "dias até faltar",
            "link": "comparar_insumos",
            "alertas": urgentes,
            "status": status,
        })
    except Exception as e:
        app.logger.debug(f"Card Insumos falhou: {e}")

    # Tarefas
    try:
        import tarefas as T
        ts = T.pendentes(T.carregar(), _agora(), limite_dias=7)
        atrasadas = sum(1 for t in ts if t.get("situacao") == "atrasada")
        status = "urgente" if atrasadas > 0 else ("aviso" if len(ts) > 0 else "ok")
        cards.append({
            "titulo": "Tarefas",
            "icone": "📋",
            "numero": len(ts),
            "subtexto": "próximas 7 dias",
            "link": "tarefas",
            "alertas": atrasadas,
            "status": status,
        })
    except Exception as e:
        app.logger.debug(f"Card Tarefas falhou: {e}")

    # Reprodução
    try:
        import animais as A
        import reproducao as R
        sit = R.situacao(dados.get("Manejo"), A.carregar(), _agora())
        alertas_repro = R.alertas(sit, _agora())
        urgentes_repro = sum(1 for a in alertas_repro if a.get("urgente"))
        status = "urgente" if urgentes_repro > 0 else ("aviso" if len(alertas_repro) > 0 else "ok")
        cards.append({
            "titulo": "Reprodução",
            "icone": "🐮",
            "numero": len(alertas_repro),
            "subtexto": "ações necessárias",
            "link": "reproducao",
            "alertas": urgentes_repro,
            "status": status,
        })
    except Exception as e:
        app.logger.debug(f"Card Reprodução falhou: {e}")

    return cards
