#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
busca.py — Busca rápida global por animais, tarefas, eventos, registros, abas (v5.10)
"""
import re
from functools import lru_cache
import db
import animais
import tarefas

# Atalhos de abas/páginas que podem ser pesquisados
ABAS_DISPONIVEIS = [
    {"termo": "dashboard", "titulo": "Dashboard", "link": "/", "icone": "🏠"},
    {"termo": "animais", "titulo": "Animais", "link": "/animais", "icone": "🐄"},
    {"termo": "pesagem", "titulo": "Pesagem", "link": "/animais/pesagem", "icone": "⚖️"},
    {"termo": "reproducao", "titulo": "Reprodução", "link": "/reproducao", "icone": "🐮"},
    {"termo": "pastos", "titulo": "Pastos", "link": "/pastos", "icone": "🗺️"},
    {"termo": "manejo", "titulo": "Manejo", "link": "/manejo", "icone": "🌿"},
    {"termo": "insumos", "titulo": "Insumos", "link": "/insumos/comparar", "icone": "🧂"},
    {"termo": "estoque", "titulo": "Estoque de Insumos", "link": "/insumos/estoque", "icone": "📦"},
    {"termo": "visita", "titulo": "Visitas", "link": "/visitas", "icone": "🗓️"},
    {"termo": "tarefa", "titulo": "Tarefas", "link": "/tarefas", "icone": "📋"},
    {"termo": "calendario", "titulo": "Calendário", "link": "/calendario", "icone": "📅"},
    {"termo": "agenda", "titulo": "Agenda Unificada", "link": "/agenda", "icone": "📅"},
    {"termo": "compra", "titulo": "Compras", "link": "/compras", "icone": "📦"},
    {"termo": "gasto", "titulo": "Gastos", "link": "/gastos", "icone": "💸"},
    {"termo": "venda", "titulo": "Vendas", "link": "/vendas", "icone": "🤝"},
    {"termo": "lote", "titulo": "Lotes", "link": "/lotes", "icone": "📦"},
    {"termo": "relatorio", "titulo": "Relatórios", "link": "/relatorios", "icone": "📈"},
    {"termo": "financeiro", "titulo": "Financeiro", "link": "/financeiro", "icone": "💰"},
    {"termo": "resultado", "titulo": "Resultado por Membro", "link": "/resultado", "icone": "📊"},
    {"termo": "fluxo", "titulo": "Fluxo de Caixa", "link": "/fluxo-caixa", "icone": "📈"},
    {"termo": "genetica", "titulo": "Genética", "link": "/genetica", "icone": "🧬"},
    {"termo": "confinamento", "titulo": "Confinamento", "link": "/confinamento", "icone": "🏚️"},
    {"termo": "conversao alimentar", "titulo": "Conversão Alimentar", "link": "/nutrição/conversão", "icone": "🥣"},
    {"termo": "ocupacao pastos", "titulo": "Ocupação de Pastos", "link": "/pastos/ocupação", "icone": "🌾"},
    {"termo": "medicacao", "titulo": "Medicações", "link": "/medicacoes", "icone": "💉"},
    {"termo": "cocho", "titulo": "Cochos", "link": "/cochos", "icone": "🥣"},
    {"termo": "iatf", "titulo": "IATF", "link": "/reproducao/iatf", "icone": "💉"},
    {"termo": "observacao de cio", "titulo": "Observação de Cio", "link": "/reproducao/observacao-cio", "icone": "🔥"},
    {"termo": "descarte culling", "titulo": "Sugestões de Descarte", "link": "/reproducao/culling", "icone": "✂️"},
    {"termo": "ia preditiva", "titulo": "IA Preditiva", "link": "/reproducao/ia-predicoes", "icone": "🤖"},
]


def buscar_global(termo: str, tipo_filtro: str | None = None) -> list[dict]:
    """Busca por termo em animais, tarefas e manejo. Retorna até 10 resultados."""
    if not termo or len(termo.strip()) < 2:
        return []

    termo = termo.strip().lower()
    resultados = []

    # Animais: brinco, ID, nome
    try:
        df_animais = animais.carregar()
        for _, row in df_animais.iterrows():
            if (termo in f"{row.get('Brinco Cor', '')} {row.get('Brinco Nº', '')}".lower() or
                termo in str(row.get('ID', '')).lower() or
                termo in str(row.get('Nome', '')).lower()):
                cat = str(row.get('Categoria', 'Animal')).strip() or 'Animal'
                peso = row.get('Peso Estimado', '') or row.get('Peso', '')
                subtitulo = f"{cat.title()}"
                if peso:
                    subtitulo += f", {peso} kg"
                resultados.append({
                    "tipo": "animal",
                    "id": str(row.get('ID', '')),
                    "titulo": f"{row.get('Brinco Cor', '')} {int(row.get('Brinco Nº', 0)) or '??'} ({cat})",
                    "subtitulo": subtitulo,
                    "link": f"/animais/{row.get('ID', '')}",
                    "icone": "🐄"
                })
    except Exception:
        pass

    # Tarefas: descrição, ID
    try:
        df_tarefas = tarefas.carregar()
        for _, row in df_tarefas.iterrows():
            if (termo in str(row.get('Título', '')).lower() or
                termo in str(row.get('ID', '')).lower() or
                termo in str(row.get('Responsável', '')).lower()):
                feito = "✓" if row.get('Feito Em') else ""
                resultados.append({
                    "tipo": "tarefa",
                    "id": str(row.get('ID', '')),
                    "titulo": f"{feito} {row.get('Título', '')}",
                    "subtitulo": f"Data: {row.get('Data', '')}",
                    "link": f"/tarefas?id={row.get('ID', '')}",
                    "icone": "📋"
                })
    except Exception:
        pass

    # Manejo: tipo de evento (Cobertura, Parto, Vacinação, etc)
    try:
        df_manejo = db.carregar_aba("Manejo")
        for _, row in df_manejo.iterrows():
            tipo = str(row.get('Tipo', '')).strip().lower()
            if termo in tipo or termo in str(row.get('Descrição', '')).lower():
                resultados.append({
                    "tipo": "evento",
                    "id": str(row.get('Data', '')),
                    "titulo": f"{row.get('Tipo', 'Evento')} — {row.get('Brincos', 'Rebanho')}",
                    "subtitulo": f"{row.get('Data', '')} — {row.get('Descrição', '')}",
                    "link": "/manejo",
                    "icone": "📅"
                })
    except Exception:
        pass

    # Abas/Páginas: pesquisa rápida por nome de aba
    for aba in ABAS_DISPONIVEIS:
        if termo in aba["termo"]:
            resultados.append({
                "tipo": "aba",
                "id": aba["link"],
                "titulo": aba["titulo"],
                "subtitulo": "Ir para esta página",
                "link": aba["link"],
                "icone": aba["icone"]
            })

    # Filtro por tipo se pedido
    if tipo_filtro:
        resultados = [r for r in resultados if r["tipo"] == tipo_filtro]

    # Ordena por tipo (animal > tarefa > evento > aba) e limita a 10
    ordem = {"animal": 0, "tarefa": 1, "evento": 2, "aba": 3}
    resultados.sort(key=lambda r: (ordem.get(r["tipo"], 99), r["titulo"]))
    return resultados[:10]
