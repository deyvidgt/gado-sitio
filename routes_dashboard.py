#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_dashboard.py — Sítio Santo Antonio
Rota principal do dashboard e lógica de alertas WhatsApp automáticos.
"""
import threading
from flask import render_template, session
import pandas as pd
from datetime import datetime, timedelta
from db import carregar_aba
from calculos import (
    calcular_todos_membros, calcular_estoque_por_membro,
    calcular_indicadores_extras, estimar_rebanho_arroba, preco_arroba_config,
)
from config import MEMBROS, NOMES_MEMBROS, EMOJIS_MEMBROS, ALERTAS_SAUDE
from extensions import (
    app, _agora, login_required,
    _get_dados_cache, _get_resumo_cache, _get_membros_cache,
    _carregar_usuarios, fmt_brl,
    _gerar_alertas, fmt_data, _ler_sitio_config_disco,
)


@app.route("/")
@login_required
def dashboard():
    dados = _get_dados_cache()
    r = _get_resumo_cache()
    membros_r      = _get_membros_cache()
    estoque_membro = calcular_estoque_por_membro(dados["Compras"], dados["Vendas"], dados["Manejo"])
    recentes = []
    for _, row in dados["Compras"].tail(3).iterrows():
        ts = row.get("Data")
        recentes.append({"tipo": "Compra", "cor": "compra", "data": fmt_data(ts),
                          "_ts": ts if pd.notna(ts) else pd.Timestamp.min,
                          "desc": row.get("Descrição", ""), "val": fmt_brl(row.get("Valor Total (R$)", 0))})
    for _, row in dados["Gastos"].tail(2).iterrows():
        ts = row.get("Data")
        recentes.append({"tipo": "Gasto", "cor": "gasto", "data": fmt_data(ts),
                          "_ts": ts if pd.notna(ts) else pd.Timestamp.min,
                          "desc": row.get("Descrição", ""), "val": fmt_brl(row.get("Valor Total (R$)", 0))})
    for _, row in dados["Vendas"].tail(3).iterrows():
        ts = row.get("Data")
        recentes.append({"tipo": "Venda", "cor": "venda", "data": fmt_data(ts),
                          "_ts": ts if pd.notna(ts) else pd.Timestamp.min,
                          "desc": row.get("Descrição", ""), "val": fmt_brl(row.get("Valor Total (R$)", 0))})
    recentes.sort(key=lambda x: x["_ts"], reverse=True)
    for rec in recentes:
        rec.pop("_ts", None)

    # Estimativa de valor do rebanho (peso médio, rendimento e @ das Configurações)
    cfg = _ler_sitio_config_disco()
    preco_arroba = preco_arroba_config(cfg)

    # Indicadores extras de gestão (custo/dia, arrobas mínimas, TMP, % gasto)
    indicadores = calcular_indicadores_extras(
        dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"],
        r.get("ctcab", 0.0), preco_arroba,
    )

    try:
        peso_medio = float(cfg.get("peso_medio", 0) or 0)
    except (TypeError, ValueError):
        peso_medio = 0.0
    try:
        rendimento = float(cfg.get("rendimento", 52) or 52)
    except (TypeError, ValueError):
        rendimento = 52.0
    peso_pesado = False
    if peso_medio <= 0:
        # Sem peso médio nas Configurações: usa o último peso dos animais pesados.
        import animais, pesagem
        peso_medio = round(pesagem.peso_medio_vivos(animais.carregar(), dados["Manejo"])[0], 1)
        peso_pesado = peso_medio > 0
    rebanho_est = None
    if peso_medio > 0 and r.get("estoque", 0) > 0:
        rebanho_est = estimar_rebanho_arroba(
            r["estoque"], peso_medio, preco_arroba, r.get("ctcab", 0.0),
            rendimento / 100.0,
        )
        rebanho_est["peso_medio"]   = peso_medio
        rebanho_est["peso_pesado"]  = peso_pesado
        rebanho_est["rendimento"]   = rendimento
        rebanho_est["preco_arroba"] = preco_arroba

    from insumos import previsao_todos
    insumos = previsao_todos(dados["Visitas"], dados["Gastos"], _agora())
    try:
        import leite
        producao_leite = carregar_aba("Leite Produção")
        resumo_leite = leite.acumulados(producao_leite, _agora().date())
    except Exception as erro:
        app.logger.warning(f"Painel: resumo leiteiro indisponível: {erro}")
        resumo_leite = {"dia": 0, "semana": 0, "mes": 0, "total": 0}
    extras = _cards_extras(dados, r)
    alertas = _gerar_alertas(dados)
    estado_sitio = {"cabecas": r.get("estoque", 0), "peso_medio": peso_medio,
                     "resultado": r.get("resultado_realizado", 0),
                     "lotacao": (extras.get("lotacao") or {}).get("ua_ha")}
    acoes_rapidas = [("⚖️ Nova pesagem", "pesagem"), ("🩺 Novo manejo", "novo_manejo"),
                     ("🗺️ Mover pasto", "pastos"), ("🛒 Nova compra", "nova_compra"),
                     ("🌾 Nova visita", "nova_visita")]
    atencao_agora = alertas + extras.get("repro", [])

    # Cards clicáveis do painel (v5.6)
    import dashboard
    cards = dashboard.cards_painel(dados, r, extras)

    return render_template("dashboard.html", r=r, membros=membros_r, insumos=insumos,
                           estoque_membro=estoque_membro, recentes=recentes[:6],
                           alertas=alertas, indicadores=indicadores, rebanho_est=rebanho_est,
                           estado_sitio=estado_sitio, acoes_rapidas=acoes_rapidas,
                           atencao_agora=atencao_agora, ocorrencias=recentes[:6],
                           resumo_leite=resumo_leite, tendencia_peso=[], cards=cards, **extras,
                           NOMES=NOMES_MEMBROS, EMOJIS=EMOJIS_MEMBROS, MEMBROS=MEMBROS)


def _cards_extras(dados, r) -> dict:
    """Cards de Lotação, Rebanho, Tarefas e Reprodução. Nenhum derruba o painel."""
    import tarefas as T
    out = {"tarefas": [], "repro": []}
    try:
        out["tarefas"] = T.pendentes(T.carregar(), _agora(), limite_dias=7)
    except Exception as e:
        app.logger.error(f"Painel: tarefas falharam: {e}")
    try:
        import animais as A
        import reproducao as R
        out["repro"] = R.alertas(R.situacao(dados["Manejo"], A.carregar(), _agora()),
                                 _agora())
    except Exception as e:
        app.logger.error(f"Painel: reprodução falhou: {e}")
    return {**out, **_lotacao_e_composicao(dados, r)}


def _lotacao_e_composicao(dados, r) -> dict:
    """Cards de Lotação e Rebanho do painel. Pasto quebrado não derruba o painel."""
    import animais as A
    import pastos as PA
    from routes_pastos import _capacidade_ua_ha, _peso_medio
    try:
        df_p, df_a = PA.carregar(), A.carregar()
        estoque = r.get("estoque", 0)
        sit = PA.situacao(df_p, df_a, dados["Manejo"], estoque,
                          _peso_medio(df_a, dados["Manejo"]), hoje=_agora())
        return {"lotacao": PA.total_lotacao(df_p, sit, _capacidade_ua_ha()),
                "composicao": A.composicao(df_a, estoque)}
    except Exception as e:
        app.logger.error(f"Painel: lotação/composição falhou: {e}")
        return {"lotacao": None, "composicao": None}


# ── Painel da Família (v5.0 fase 4): todos os sítios lado a lado e somados ────

CAMPOS_FAMILIA = ("estoque", "capital_imobilizado", "total_vend", "perdas", "resultado_total")


@app.route("/familia")
@login_required
def familia():
    """Só leitura. Entra em cada sítio dentro deste pedido (a trava já é nossa) e
    volta ao sítio do usuário no fim — o resto da página usa os donos dele."""
    import sitios
    volta = sitios.atual()
    linhas = []
    try:
        for slug in sitios.carregar()["sitios"]:
            linha = {"slug": slug, "nome": sitios.nome(slug)}
            try:
                sitios.ativar(slug)
                r = _get_resumo_cache()
                linha.update({k: r[k] for k in CAMPOS_FAMILIA},
                             donos=", ".join(NOMES_MEMBROS[m] for m in MEMBROS))
            except Exception as e:
                # Um sítio com planilha quebrada não derruba o painel dos outros.
                app.logger.error(f"Painel da família: erro no sítio {slug}: {e}")
                linha["erro"] = True
            linhas.append(linha)
    finally:
        sitios.ativar(volta)
    ok = [l for l in linhas if not l.get("erro")]
    total = {k: sum(l[k] for l in ok) for k in CAMPOS_FAMILIA}
    return render_template("familia.html", linhas=linhas, total=total,
                           faltou=len(ok) < len(linhas))


# ══════════════════════════════════════════════════════════════════════════════
