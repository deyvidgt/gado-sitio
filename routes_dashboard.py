#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_dashboard.py — Sítio Santo Antonio
Rota principal do dashboard e lógica de alertas WhatsApp automáticos.
"""
import threading
from flask import render_template, session, jsonify, abort, redirect, url_for
import pandas as pd
from datetime import datetime, timedelta
from db import carregar_aba
from calculos import (
    calcular_todos_membros, calcular_estoque_por_membro,
    calcular_indicadores_extras, estimar_rebanho_arroba, preco_arroba_config,
)
from config import MEMBROS, NOMES_MEMBROS, EMOJIS_MEMBROS, ALERTAS_SAUDE
import tempo as tempo_mod
from extensions import (
    app, _agora, login_required,
    _get_dados_cache, _get_resumo_cache, _get_membros_cache,
    _carregar_usuarios, fmt_brl,
    _gerar_alertas, fmt_data, _ler_sitio_config_disco,
)


def _cards_painel(dados, r, extras):
    """Retorna lista de cards para o painel com dados básicos."""
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
        "link": "transacoes",
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


def _entrada_saida_timeline(dados, dias=90):
    """Gráfico de entrada/saída de animais nos últimos N dias.

    Retorna dados para Chart.js com entrada (compra), saída (venda) e saldo diário.
    """
    from datetime import date, timedelta

    hoje = _agora().date()
    inicio = hoje - timedelta(days=dias)

    # Agrupa por data
    timeline = {}

    # Compras (entrada)
    df_comp = dados.get("Compras")
    if df_comp is None:
        df_comp = pd.DataFrame()
    for _, row in df_comp.iterrows():
        try:
            data = pd.to_datetime(row.get("Data")).date()
            if data < inicio:
                continue
            data_str = data.isoformat()
            timeline.setdefault(data_str, {"entrada": 0, "saida": 0})
            timeline[data_str]["entrada"] += int(row.get("Cabeças", 0) or 0)
        except Exception:
            pass

    # Vendas (saída)
    df_vend = dados.get("Vendas")
    if df_vend is None:
        df_vend = pd.DataFrame()
    for _, row in df_vend.iterrows():
        try:
            data = pd.to_datetime(row.get("Data")).date()
            if data < inicio:
                continue
            data_str = data.isoformat()
            timeline.setdefault(data_str, {"entrada": 0, "saida": 0})
            timeline[data_str]["saida"] += int(row.get("Cabeças", 0) or 0)
        except Exception:
            pass

    # Ordena por data
    datas = sorted(timeline.keys())

    return {
        "datas": datas,
        "entrada": [timeline[d]["entrada"] for d in datas],
        "saida": [timeline[d]["saida"] for d in datas],
    }


def _grafico_resultado_mensal(r_anual):
    """Gráfico de colunas: Resultado nos últimos 12 meses.

    r_anual vem de calculos.calcular_resultado_anual() e tem a chave 'resultado_por_mes'.
    """
    try:
        resultado_por_mes = r_anual.get("resultado_por_mes", {})
        if not resultado_por_mes:
            return None

        # Ordena por mês (jan-dez)
        meses_pt = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                    "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        labels = []
        data = []

        for mes_num in range(1, 13):
            mes_str = str(mes_num).zfill(2)
            if mes_str in resultado_por_mes:
                labels.append(meses_pt[mes_num - 1])
                data.append(resultado_por_mes[mes_str])

        if not labels:
            return None

        return {"labels": labels, "data": data}
    except Exception as e:
        app.logger.debug(f"Gráfico resultado mensal falhou: {e}")
        return None


def _grafico_cmp_gpcab_evolucao(r_timeline):
    """Gráfico de linhas: Evolução CMP e GPCab últimos 12 meses.

    r_timeline vem de calculos._build_cmp_timeline() e _build_gpcab_timeline().
    """
    try:
        from calculos import _build_cmp_timeline, _build_gpcab_timeline
        cmp_timeline = _build_cmp_timeline()
        gpcab_timeline = _build_gpcab_timeline()

        if not cmp_timeline or not gpcab_timeline:
            return None

        # Últimos 12 pontos
        meses_pt = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                    "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        labels = meses_pt[-12:] if len(meses_pt) >= 12 else meses_pt

        return {
            "labels": labels,
            "cmp": cmp_timeline[-12:] if len(cmp_timeline) >= 12 else cmp_timeline,
            "gpcab": gpcab_timeline[-12:] if len(gpcab_timeline) >= 12 else gpcab_timeline,
        }
    except Exception as e:
        app.logger.debug(f"Gráfico CMP/GPCab falhou: {e}")
        return None


def _grafico_gastos_por_tipo(dados):
    """Gráfico de pizza: Composição de gastos por tipo (SQLAlchemy query).

    Agrupa por tipo de gasto (Alimentação, Saúde, Manutenção, etc).
    """
    try:
        from datetime import timedelta
        from sqlalchemy import func
        from models import Despesa
        from extensions import db

        hoje = _agora().date()
        inicio = hoje - timedelta(days=30)
        inicio_dt = datetime.combine(inicio, datetime.min.time())

        resultados = db.session.query(Despesa.tipo, func.sum(Despesa.valor_total)).filter(Despesa.data >= inicio_dt).group_by(Despesa.tipo).all()
        if not resultados:
            resultados = db.session.query(Despesa.tipo, func.sum(Despesa.valor)).filter(Despesa.data >= inicio_dt).group_by(Despesa.tipo).all()

        if resultados:
            labels = [r[0] or "Outro" for r in resultados]
            data = [float(r[1] or 0) for r in resultados]
            if labels and sum(data) > 0:
                return {"labels": labels, "data": data}

        df_gastos = dados.get("Gastos")
        if df_gastos is None or df_gastos.empty:
            return None

        gastos_por_tipo = {}
        for _, row in df_gastos.iterrows():
            try:
                data = pd.to_datetime(row.get("Data")).date()
                if data < inicio:
                    continue
                tipo = row.get("Tipo", "Outro") or "Outro"
                valor = float(row.get("Valor Total (R$)", 0) or 0)
                gastos_por_tipo[tipo] = gastos_por_tipo.get(tipo, 0) + valor
            except Exception:
                pass

        if not gastos_por_tipo:
            return None

        labels = list(gastos_por_tipo.keys())
        data = list(gastos_por_tipo.values())

        return {"labels": labels, "data": data}
    except Exception as e:
        app.logger.debug(f"Gráfico gastos por tipo falhou: {e}")
        return None


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
                          "desc": (row.get("Descrição") or ""), "val": fmt_brl(row.get("Valor Total (R$)", 0))})
    for _, row in dados["Gastos"].tail(2).iterrows():
        ts = row.get("Data")
        recentes.append({"tipo": "Gasto", "cor": "gasto", "data": fmt_data(ts),
                          "_ts": ts if pd.notna(ts) else pd.Timestamp.min,
                          "desc": (row.get("Descrição") or ""), "val": fmt_brl(row.get("Valor Total (R$)", 0))})
    for _, row in dados["Vendas"].tail(3).iterrows():
        ts = row.get("Data")
        recentes.append({"tipo": "Venda", "cor": "venda", "data": fmt_data(ts),
                          "_ts": ts if pd.notna(ts) else pd.Timestamp.min,
                          "desc": (row.get("Descrição") or ""), "val": fmt_brl(row.get("Valor Total (R$)", 0))})
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

    # v5.10 Onda 1 — Mastite prediction & health monitoring
    try:
        from mastite_predicao import resumo_saude_leite
        saude_leite = resumo_saude_leite()
    except Exception as erro:
        app.logger.warning(f"Painel: saúde do leite indisponível: {erro}")
        saude_leite = {"total_vacas": 0, "alertas_urgentes": 0, "alertas_aviso": 0}

    # IA Preditiva (Onda 19)
    try:
        from reproducao_avancada_ia import alertas_ia_preditiva
        ia_alertas = alertas_ia_preditiva(carregar_aba("Animais"), dados["Manejo"], dados["Compras"], dados["Vendas"])
    except Exception as erro:
        app.logger.warning(f"Painel: IA preditiva indisponível: {erro}")
        ia_alertas = {"urgentes": [], "avisos": [], "total": 0}

    extras = _cards_extras(dados, r)
    alertas = _gerar_alertas(dados)
    estado_sitio = {"cabecas": r.get("estoque", 0), "peso_medio": peso_medio,
                     "resultado": r.get("resultado_realizado", 0),
                     "lotacao": (extras.get("lotacao") or {}).get("ua_ha")}
    pastos_disponivel = "pastos" in app.url_map._rules_by_endpoint
    acoes_rapidas = [("⚖️ Nova pesagem", "pesagem"), ("🩺 Novo manejo", "novo_manejo"),
                     ("🛒 Nova compra", "nova_compra"), ("🌾 Nova visita", "nova_visita")]
    # Adiciona pastos se a rota existir
    if pastos_disponivel:
        acoes_rapidas.insert(2, ("🗺️ Mover pasto", "pastos"))
    atencao_agora = alertas + extras.get("repro", [])

    # Cards clicáveis do painel (v5.6)
    cards = _cards_painel(dados, r, extras)

    # Gráfico temporal de entrada/saída (v5.8)
    entrada_saida = _entrada_saida_timeline(dados, dias=90)

    # Previsão do tempo (v5.9)
    tempo_previsao = tempo_mod.previsao()

    # Gráficos da Onda 8.2 (Dashboard)
    grafico_resultado = _grafico_resultado_mensal(r)
    grafico_cmp_gpcab = _grafico_cmp_gpcab_evolucao(r)
    grafico_gastos = _grafico_gastos_por_tipo(dados)

    import pesagem
    tendencia_peso = pesagem.curva_evolucao_peso(dados["Manejo"])[-24:]
    return render_template("dashboard.html", r=r, membros=membros_r, insumos=insumos,
                           estoque_membro=estoque_membro, recentes=recentes[:6],
                           alertas=alertas, indicadores=indicadores, rebanho_est=rebanho_est,
                           estado_sitio=estado_sitio, acoes_rapidas=acoes_rapidas,
                           atencao_agora=atencao_agora, ocorrencias=recentes[:6],
                           resumo_leite=resumo_leite, saude_leite=saude_leite, ia_alertas=ia_alertas, tendencia_peso=tendencia_peso, cards=cards,
                           entrada_saida=entrada_saida, tempo=tempo_previsao, pastos_disponivel=pastos_disponivel,
                           grafico_resultado=grafico_resultado, grafico_cmp_gpcab=grafico_cmp_gpcab,
                           grafico_gastos=grafico_gastos,
                           **extras, NOMES=NOMES_MEMBROS, EMOJIS=EMOJIS_MEMBROS, MEMBROS=MEMBROS)


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


def _vacas_prenhas(dados) -> dict:
    """Conta vacas prenhas, atrasadas e prestes a parir (próximos 14 dias).
    Integrado com reproducao.py indicadores()."""
    try:
        import reproducao as R
        indic = R.indicadores(dados["Manejo"])
        return {
            "prenhas": indic.get("prenhas_total", 0),
            "atrasadas": indic.get("atrasadas_total", 0),
            "proximo_parto": indic.get("parto_proximos_14d", 0),
            "taxa_prenhez_pct": round(indic.get("taxa_prenhez", 0) * 100, 1)
        }
    except Exception as e:
        app.logger.error(f"Painel: vacas prenhas falhou: {e}")
        return {"prenhas": 0, "atrasadas": 0, "proximo_parto": 0, "taxa_prenhez_pct": 0}


# ── Painel da Família (v5.0 fase 4): todos os sítios lado a lado e somados ────

CAMPOS_FAMILIA = ("estoque", "capital_imobilizado", "total_vend", "perdas", "resultado_total")


@app.route("/familia")
@login_required
def familia():
    """Redireciona imediatamente para o painel principal para garantir total privacidade dos sítios."""
    return redirect(url_for("dashboard"))


# ── Previsão do tempo (v5.6) ───────────────────────────────────────────────────

@app.route("/tempo")
@login_required
def tempo():
    """Página completa de previsão de tempo com gráficos, histórico de chuvas e alertas."""
    import tempo as T
    prev = T.previsao(agora=_agora())
    alertas = T.alertas_tempo(prev)
    dados = _get_dados_cache()
    analise_chuvas = T.analise_secas_e_chuvas(dados.get("Visitas"), _agora().date())

    # Recomendações por tipo (para filtragem no template)
    recomendacoes = {
        "leite": {
            "chuva_forte": "Risco de mastite — verificar ordenhadora e higiene da ordenha.",
            "calor_umidade": "Estresse térmico — aumentar sombra, água fresca e ventilação.",
            "vento_forte": "Risco de disseminação de doenças — aumentar vigilância sanitária.",
            "queda_temp": "Queda de temperatura — verificar abrigo e aquecimento.",
        },
        "corte": {
            "chuva_forte": "Armazenar camas/alimentos bem — evitar mofo e doenças.",
            "calor_umidade": "Calor extremo — aumentar sombra, água e ventilação.",
            "vento_forte": "Vento forte — proteger animais e reforçar abrigos.",
            "queda_temp": "Queda de temperatura — verificar abrigo dos animais.",
        },
        "volumosos": {
            "chuva_forte": "Chuva — armazenar volumosos e forragens bem para não estragar.",
            "calor_umidade": "Calor — vigilância em armazenamento de feno/silagem.",
            "vento_forte": "Vento forte — proteger pilhas de volumosos.",
            "queda_temp": "Queda de temperatura — nenhum impacto direto.",
        },
    }

    return render_template("tempo.html", prev=prev, alertas=alertas,
                          analise_chuvas=analise_chuvas,
                          recomendacoes=recomendacoes, fmt_data=fmt_data, fmt_brl=fmt_brl)


# ══════════════════════════════════════════════════════════════════════════════
# v5.7 Sprint 3: Bottom Navigation API Endpoints
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/tarefas/pendentes-count')
@login_required
def api_tarefas_pendentes_count():
    """Retorna número de tarefas pendentes para badge na nav"""
    try:
        import tarefas
        pend = tarefas.pendentes()
        count = len(pend.get('atrasadas', []))
        return jsonify({'count': count})
    except Exception as e:
        app.logger.debug(f'Error in api_tarefas_pendentes_count: {e}')
        return jsonify({'count': 0}), 200


@app.route('/api/alertas/count')
@login_required
def api_alertas_count():
    """Retorna número de alertas urgentes para badge na nav"""
    try:
        import alertas as A
        alts = A.todos()
        urgentes = [a for a in alts if a.get('urgencia') == 'urgente']
        return jsonify({'count': len(urgentes)})
    except Exception as e:
        app.logger.debug(f'Error in api_alertas_count: {e}')
        return jsonify({'count': 0}), 200


# ── Dashboard Novo (v5.8) — Mobile-First ──────────────────────────────────────
@app.route('/dashboard-novo')
@login_required
def dashboard_novo_view():
    """Dashboard mobile-first v5.8 com 7 cards prioritizados"""
    try:
        # Importar funções do novo módulo
        from dashboard_novo import chuvas_mes, cotacao_mercado, alertas_consolidados
        from insumos import previsao_todos

        # Cache de dados
        dados = _get_dados_cache()
        r = _get_resumo_cache()

        # 1. RESUMO LEITEIRO
        try:
            import leite
            prod = carregar_aba("Leite Produção")
            resumo_leite = leite.acumulados(prod, _agora().date())
        except Exception as e:
            app.logger.debug(f"Resumo leiteiro indisponível: {e}")
            resumo_leite = {"dia": 0, "semana": 0, "mes": 0}

        # 2. PREVISÃO DO TEMPO
        try:
            tempo_previsao = tempo_mod.previsao()
        except Exception as e:
            app.logger.debug(f"Previsão indisponível: {e}")
            tempo_previsao = {"status": "indisponível"}

        # 3. AVISOS & ALERTAS CONSOLIDADOS
        try:
            avisos = alertas_consolidados(dados)
        except Exception as e:
            app.logger.debug(f"Alertas consolidados falhou: {e}")
            avisos = []

        # 4. AGENDA DE MANEJO (TAREFAS)
        tarefas = []
        try:
            import tarefas as tf
            pendentes = tf.pendentes(_agora().date())
            for t in (pendentes or [])[:5]:
                dias_atraso = max(0, (_agora().date() - t.get("data_vencimento", _agora().date())).days)
                dias_ate = (t.get("data_vencimento", _agora().date()) - _agora().date()).days

                if dias_atraso > 0:
                    status_label = f"⏰ {dias_atraso}d atrasada"
                elif dias_ate == 0:
                    status_label = "🔴 Hoje"
                elif dias_ate < 0:
                    status_label = f"✅ +{abs(dias_ate)}d"
                else:
                    status_label = f"📅 +{dias_ate}d"

                tarefas.append({
                    "titulo": t.get("titulo", "Sem título"),
                    "status_label": status_label,
                    "dias_atraso": dias_atraso,
                    "dias_ate": dias_ate,
                })
        except Exception as e:
            app.logger.debug(f"Tarefas falhou: {e}")

        # 5. ESTOQUE DE ALIMENTAÇÃO
        estoque_info = []
        try:
            insumos_prev = previsao_todos(dados.get("Visitas"), dados.get("Gastos"), _agora())
            for nome, info in insumos_prev.items():
                estoque_info.append({
                    "nome": nome,
                    "quantidade": int(info.get("sacos", 0)),
                    "dias_faltam": int(info.get("dias_faltam", 999)),
                    "status": info.get("status", "ok"),
                    "percentual": min(100, max(0, info.get("percentual_sacos", 0))),
                })
        except Exception as e:
            app.logger.debug(f"Insumos falhou: {e}")

        # 6. CHUVAS DO MÊS
        try:
            chuvas = chuvas_mes()
        except Exception as e:
            app.logger.debug(f"Chuvas falhou: {e}")
            chuvas = {"total": 0, "media": 90, "semanas": []}

        # 7. COTAÇÃO DE MERCADO
        try:
            cotacao = cotacao_mercado()
        except Exception as e:
            app.logger.debug(f"Cotação falhou: {e}")
            cotacao = []

        # ESTADO DO SÍTIO (resumo)
        try:
            estoque_membro = calcular_estoque_por_membro(dados["Compras"], dados["Vendas"], dados["Manejo"])
        except Exception as e:
            app.logger.debug(f"Estoque por membro falhou: {e}")
            estoque_membro = []

        lot = (_lotacao_e_composicao(dados, r).get("lotacao") or {})
        estado_sitio = {
            "cabecas": r.get("estoque", 0),
            "lotacao": lot.get("ua_ha") or 0,
        }

        # Renderizar template
        return render_template("dashboard_novo.html",
                             resumo_leite=resumo_leite,
                             tempo=tempo_previsao,
                             avisos_consolidados=avisos,
                             tarefas_pendentes=tarefas,
                             estoque_info=estoque_info,
                             chuvas_mes=chuvas,
                             cotacao=cotacao,
                             cotacao_data=_agora().strftime("%d/%m %H:%M"),
                             estado_sitio=estado_sitio,
                             resultado=r,
                             estoque_por_membro=estoque_membro,
                             NOMES=NOMES_MEMBROS,
                             EMOJIS=EMOJIS_MEMBROS)

    except Exception as e:
        app.logger.error(f"Erro dashboard-novo: {e}", exc_info=True)
        return render_template("dashboard.html",  # Fallback ao dashboard antigo
                             r=_get_resumo_cache(),
                             erro=f"Dashboard novo temporariamente indisponível: {str(e)}")


@app.route('/dashboard-exemplo-graficos')
@login_required
def dashboard_exemplo_graficos():
    """Página de exemplos dos componentes gráficos v5.8 (Gauge, Cards, Barras, Linhas)."""
    return render_template("dashboard-exemplo-graficos.html")



# ══════════════════════════════════════════════════════════════════════════════

