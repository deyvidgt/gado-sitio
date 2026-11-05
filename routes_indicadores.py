#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_indicadores.py — Rotas dos indicadores v5.8

- /indicadores/engorda-pastagem
- /indicadores/gmd-lotacao
- /indicadores/racao-consumo
- /indicadores/mortalidade-bezerros
"""

from flask import render_template
from extensions import app, login_required, _agora, _get_dados_cache, _get_evolucao_cache
from calculos import calcular_fluxo_caixa
from indicadores_v58 import (
    engorda_pastagem_resumo, gmd_lotacao_analise,
    racao_consumo_analise, mortalidade_bezerros_analise, mortalidade_por_faixa_etaria
)
import pandas as pd
import animais as A
import db
import pesagem as P
import leite
import reproducao as R
import cochos as CO
import pastos_ms as PMS


def _numero_br(valor, casas=1):
    if valor is None or pd.isna(valor):
        return "—"
    return f"{float(valor):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


@app.route("/indicadores")
@login_required
def painel_indicadores():
    """Consolida indicadores zootécnicos existentes sem criar métricas novas."""
    dados = _get_dados_cache()
    df_animais = A.carregar()
    df_manejo = dados["Manejo"]
    hoje = _agora().date()

    vivos = A.vivos(df_animais)
    historicos = P.todas(df_manejo)
    resumos_peso = [P.resumo(hist) for hist in historicos.values()]
    gmds = [r["gmd"] for r in resumos_peso if r and r["gmd"] is not None]
    peso_medio, pesados = P.peso_medio_vivos(df_animais, df_manejo)

    repro_situacoes = R.situacao(df_manejo, df_animais, hoje)
    repro = R.indicadores(repro_situacoes, df_animais)
    engorda = engorda_pastagem_resumo(dados)
    lotacao = gmd_lotacao_analise(dados)
    racao = racao_consumo_analise(dados)
    mortalidade = mortalidade_bezerros_analise(dados)
    faixas_mortalidade = mortalidade_por_faixa_etaria(dados)

    periodos = lotacao.get("periodos", [])
    ultimo_periodo = periodos[-1] if periodos else {}
    lotacao_ua = pd.to_numeric(pd.Series([ultimo_periodo.get("Lotação (UA/ha)")]), errors="coerce").iloc[0]
    gmd_lotacao = pd.to_numeric(pd.Series([ultimo_periodo.get("GMD (kg/dia)")]), errors="coerce").iloc[0]

    df_mortalidade = db.carregar_aba("Mortalidade Bezerros")
    df_taxa = pd.to_numeric(df_mortalidade.get(
        "Taxa Mortalidade (%)", pd.Series(dtype=float)), errors="coerce").dropna()
    taxa_mortalidade = float(df_taxa.mean()) if not df_taxa.empty else None

    df_leite = db.carregar_aba("Leite Produção")
    resumo_leite = leite.acumulados(df_leite, hoje)
    rebanho_leite = leite.contagens_rebanho(df_animais)
    df_mortes = df_manejo[df_manejo.get("Tipo", pd.Series(dtype=str)).eq("Morte/Perda")].copy()
    if not df_mortes.empty:
        cab_mortas = pd.to_numeric(df_mortes.get("Qtd Cabeças"), errors="coerce").fillna(0)
        df_mortes["_cab"] = cab_mortas
        df_mortes["_causa"] = df_mortes.get("Causa Mortis", pd.Series(index=df_mortes.index, dtype=object))
        df_mortes["_causa"] = df_mortes["_causa"].fillna("").astype(str).str.strip().replace("", "Sem causa registrada")
        contagem_causas = df_mortes.groupby("_causa")["_cab"].sum().sort_values(ascending=False)
        detalhe_causas = ", ".join(f"{causa}: {int(qtd)}" for causa, qtd in contagem_causas.items())
        total_mortes_causa = int(cab_mortas.sum())
    else:
        detalhe_causas, total_mortes_causa = "Nenhuma morte/perda registrada.", 0

    gastos_categoria = {}
    df_gastos = dados["Gastos"]
    if not df_gastos.empty and "Categoria" in df_gastos.columns:
        valores = pd.to_numeric(df_gastos.get("Valor Total (R$)"), errors="coerce").fillna(0)
        categorias = df_gastos["Categoria"].fillna("Outros").astype(str).str.strip().replace("", "Outros")
        gastos_categoria = valores.groupby(categorias).sum().to_dict()
    gasto_total_categoria = sum(gastos_categoria.values())
    detalhe_gastos = ", ".join(
        f"{categoria}: {_numero_br(valor, 0)}" for categoria, valor in sorted(gastos_categoria.items())
    ) or "Sem gastos categorizados."

    sit_cochos = CO.calcular_situacao_cochos(
        CO.carregar(), dados.get("Visitas"), CO.carregar_movimentos()
    )
    consumos_mineral = [
        item["consumo_g_cab_dia"] for item in sit_cochos.values()
        if item.get("consumo_g_cab_dia") is not None
        and any(chave in item.get("tipo", "") for chave in ("sal", "mineral"))
    ]
    consumo_mineral_medio = (
        sum(consumos_mineral) / len(consumos_mineral) if consumos_mineral else None
    )

    df_ms = PMS.carregar()
    ms_mediana = None
    if not df_ms.empty:
        df_ms["_ms"] = pd.to_numeric(df_ms["MS Estimada (kg/ha)"], errors="coerce")
        df_ms = df_ms.dropna(subset=["_ms"]).sort_values("Data")
        ultimas = df_ms.drop_duplicates("Pasto ID", keep="last")
        if not ultimas.empty:
            ms_mediana = float(ultimas["_ms"].median())

    return render_template(
        "indicadores/painel.html",
        grupos=[
            {
                "nome": "Rebanho e corte",
                "itens": [
                    {"nome": "Rebanho vivo", "valor": _numero_br(len(vivos), 0), "unidade": "cabeças",
                     "detalhe": "Animais cadastrados com status vivo/ativo.", "link": "animais"},
                    {"nome": "Peso médio dos pesados", "valor": _numero_br(peso_medio, 1) if pesados else "—",
                     "unidade": "kg", "detalhe": f"{pesados} de {len(vivos)} animais vivos com pesagem de balança.",
                     "link": "pesagem"},
                    {"nome": "GMD individual recente", "valor": _numero_br(sum(gmds) / len(gmds), 3) if gmds else "—",
                     "unidade": "kg/dia", "detalhe": f"Média do último intervalo de {len(gmds)} animais com duas ou mais pesagens.",
                     "link": "pesagem"},
                    {"nome": "GMD — engorda a pasto", "valor": _numero_br(engorda["ganho_medio"], 2)
                     if engorda.get("lotes_ativos") else "—", "unidade": "kg/dia",
                     "detalhe": f"{engorda.get('lotes_ativos', 0)} registros na aba Engorda Pastagem.",
                     "link": "indicadores_gmd"},
                    {"nome": "GMD — último registro com lotação", "valor": _numero_br(gmd_lotacao, 2),
                     "unidade": "kg/dia", "detalhe": "Valor do registro mais recente lançado na aba GMD Lotação.",
                     "link": "indicadores_gmd"},
                    {"nome": "Lotação — último registro", "valor": _numero_br(lotacao_ua, 2),
                     "unidade": "UA/ha", "detalhe": "Valor do registro mais recente lançado na aba GMD Lotação.",
                     "link": "indicadores_gmd"},
                    {"nome": "Consumo de ração registrado", "valor": _numero_br(racao["consumo_medio"], 1)
                     if racao.get("tabela") else "—", "unidade": "%",
                     "detalhe": "Média da taxa de consumo informada na aba Ração Consumo.",
                     "link": "indicadores_racao_consumo"},
                    {"nome": "Mortalidade de bezerros", "valor": _numero_br(taxa_mortalidade, 1),
                     "unidade": "%", "detalhe": f"Média dos registros lançados; {mortalidade.get('total_nascidos', 0)} nascidos e {mortalidade.get('total_mortos', 0)} mortos.",
                     "link": "indicadores_mortalidade_bezerros"},
                    {"nome": "Animais mortos por faixa etária", "valor": _numero_br(faixas_mortalidade.get("total", 0), 0),
                     "unidade": "animais", "detalhe": f"{faixas_mortalidade.get('sem_data', 0)} sem data suficiente para classificar.",
                     "link": "indicadores_mortalidade_bezerros"},
                    {"nome": "Mortes/perdas por causa", "valor": _numero_br(total_mortes_causa, 0),
                     "unidade": "cabeças", "detalhe": detalhe_causas, "link": "manejo"},
                    {"nome": "Consumo de mineral medido", "valor": _numero_br(consumo_mineral_medio, 1),
                     "unidade": "g/cab/dia", "detalhe": "Média das leituras calculadas nos cochos de sal/mineral; requer duas leituras.",
                     "link": "cochos"},
                    {"nome": "MS estimada dos pastos", "valor": _numero_br(ms_mediana, 0),
                     "unidade": "kg/ha", "detalhe": "Mediana da última medição de cada pasto, por altura × coeficiente configurado.",
                     "link": "medicoes_pastos"},
                    {"nome": "Gastos por categoria", "valor": _numero_br(gasto_total_categoria, 2),
                     "unidade": "R$", "detalhe": detalhe_gastos, "link": "gastos"},
                ],
            },
            {
                "nome": "Reprodução",
                "itens": [
                    {"nome": "Taxa de prenhez diagnosticada",
                     "valor": _numero_br(repro.get("taxa_prenhez"), 1),
                     "unidade": "%", "detalhe": f"Prenhas entre {sum(1 for v in repro_situacoes if v['resultado'])} diagnósticos lançados.",
                     "link": "reproducao"},
                    {"nome": "Intervalo entre partos (IEP)",
                     "valor": _numero_br(repro.get("iep_dias"), 0), "unidade": "dias",
                     "detalhe": "Média dos intervalos entre nascimentos registrados por mãe.",
                     "link": "reproducao"},
                    {"nome": "Vacas aguardando diagnóstico",
                     "valor": _numero_br(repro.get("aguardando_toque", 0), 0), "unidade": "animais",
                     "detalhe": "Coberturas sem resultado de diagnóstico registrado.",
                     "link": "reproducao"},
                ],
            },
            {
                "nome": "Leite",
                "itens": [
                    {"nome": "Produção no mês", "valor": _numero_br(resumo_leite.get("mes"), 1),
                     "unidade": "litros", "detalhe": "Soma dos registros de produção do mês atual.",
                     "link": "painel_leite"},
                    {"nome": "Vacas em lactação", "valor": _numero_br(rebanho_leite["vacas_lactacao"], 0),
                     "unidade": "animais", "detalhe": f"{rebanho_leite['vacas_leiteiras_ativas']} vacas leiteiras ativas cadastradas.",
                     "link": "animais_leite"},
                ],
            },
        ],
    )


@app.route("/evolucao")
@login_required
def evolucao_rebanho():
    """Gráficos alinhados de peso, rebanho e fluxo de caixa mensal."""
    dados = _get_dados_cache()
    curva_peso = P.curva_evolucao_peso(dados["Manejo"])[-60:]
    evolucao = _get_evolucao_cache()[-24:]
    financeiro = calcular_fluxo_caixa(dados["Compras"], dados["Gastos"], dados["Vendas"])
    financeiro = financeiro.tail(24) if not financeiro.empty else financeiro
    return render_template(
        "evolucao.html",
        curva_peso=curva_peso,
        evolucao=evolucao,
        financeiro={
            "labels": [p.strftime("%m/%Y") for p in financeiro["AnoMes"]] if not financeiro.empty else [],
            "entradas": [round(float(v), 2) for v in financeiro["Entradas"]] if not financeiro.empty else [],
            "saidas": [round(float(v), 2) for v in financeiro["Saidas"]] if not financeiro.empty else [],
            "saldo": [round(float(v), 2) for v in financeiro["Saldo"]] if not financeiro.empty else [],
        },
    )


@app.route("/indicadores/gmd")
@login_required
def indicadores_gmd():
    """Indicadores unificados de GMD: vs pastagem e vs lotação. Onda 8.5 com gráficos."""
    dados = _get_dados_cache()
    resumo_pastagem = engorda_pastagem_resumo(dados)
    analise_lotacao = gmd_lotacao_analise(dados)

    # Gráficos Onda 8.5 — dados simplificados
    grafico_gmd_linhas = None
    grafico_lotacao_barras = None

    try:
        # Extrai últimos 12 pontos do histórico
        if analise_lotacao.get("periodos"):
            periodos = analise_lotacao["periodos"][-12:]
            labels = [p.get("Data", "")[:7] for p in periodos]  # AAAA-MM
            data_gmd = [float(p.get("GMD (kg/dia)", 0) or 0) for p in periodos]
            data_lotacao = [float(p.get("Lotação (UA/ha)", 0) or 0) for p in periodos]

            if labels:
                grafico_gmd_linhas = {"labels": labels, "data": data_gmd}
                grafico_lotacao_barras = {"labels": labels, "data": data_lotacao}
    except Exception as e:
        app.logger.debug(f"Gráficos indicadores falharam: {e}")

    return render_template(
        "indicadores/gmd_unificado.html",
        resumo_pastagem=resumo_pastagem,
        analise_lotacao=analise_lotacao,
        grafico_gmd_linhas=grafico_gmd_linhas,
        grafico_lotacao_barras=grafico_lotacao_barras
    )


# Manter rotas antigas para compatibilidade (redirecionam)
@app.route("/indicadores/engorda-pastagem")
@login_required
def indicadores_engorda_pastagem():
    """Redireciona para a rota unificada."""
    from flask import redirect, url_for
    return redirect(url_for('indicadores_gmd'), code=301)


@app.route("/indicadores/gmd-lotacao")
@login_required
def indicadores_gmd_lotacao():
    """Redireciona para a rota unificada."""
    from flask import redirect, url_for
    return redirect(url_for('indicadores_gmd'), code=301)


@app.route("/indicadores/racao-consumo")
@login_required
def indicadores_racao_consumo():
    """Análise de ração oferecida vs consumida."""
    dados = _get_dados_cache()
    analise = racao_consumo_analise(dados)
    return render_template(
        "indicadores/racao_consumo.html",
        analise=analise
    )


@app.route("/indicadores/mortalidade-bezerros")
@login_required
def indicadores_mortalidade_bezerros():
    """Taxa de mortalidade de bezerros."""
    dados = _get_dados_cache()
    analise = mortalidade_bezerros_analise(dados)
    return render_template(
        "indicadores/mortalidade_bezerros.html",
        analise=analise,
        mortalidade_faixa=mortalidade_por_faixa_etaria(dados),
    )
