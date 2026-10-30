#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_financeiro_novo.py — Rotas de reorganização do dashboard (v5.10)

Novas páginas para dashboard mobile-first:
- /financeiro — Indicadores financeiros completos
- /resultado — Resultado por membro + período
- /fluxo-caixa — Gráfico entrada/saída + saldo acumulado
- /fluxo-animais — Compras/vendas com gráfico
- /lembretes-whatsapp — Preferências + fila de avisos
"""

from flask import render_template, session, jsonify
import pandas as pd
from datetime import datetime, timedelta
from db import carregar_aba, RAIZ
from calculos import calcular_todos_membros, calcular_estoque_por_membro
from config import MEMBROS, NOMES_MEMBROS, EMOJIS_MEMBROS
from extensions import app, _agora, login_required, _get_dados_cache, _get_membros_cache, _get_resumo_cache, fmt_brl, fmt_data
import os
import json


def _grafico_receita_vs_custo(dados, r, meses=12):
    """Gráfico duplo-eixo: Receita (esquerda) vs Custo (direita) últimos N meses.

    Usa o resumo anual já calculado para extrair receita e custo por mês.
    """
    try:
        from calculos import calcular_resultado_anual
        r_anual = calcular_resultado_anual()
        resultado_por_mes = r_anual.get("resultado_por_mes", {})
        caixa_por_mes = r_anual.get("caixa_por_mes", {})

        if not resultado_por_mes or not caixa_por_mes:
            return None

        # Ordena por mês
        meses_pt = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                    "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        labels = []
        receita = []
        custo = []

        for mes_num in range(1, meses + 1):
            mes_str = str(mes_num).zfill(2)
            if mes_str in resultado_por_mes:
                labels.append(meses_pt[mes_num - 1])
                # Receita = resultado + custo (estimado)
                resultado = resultado_por_mes[mes_str]
                caixa = caixa_por_mes.get(mes_str, 0)
                receita.append(max(caixa, 0))  # Entrada de caixa
                custo.append(max(r.get("ctcab", 0) * (r.get("estoque", 0) / 12), 0))  # Custo médio

        if not labels:
            return None

        return {"labels": labels, "receita": receita, "custo": custo}
    except Exception as e:
        app.logger.debug(f"Gráfico receita vs custo falhou: {e}")
        return None


def _grafico_resultado_por_membro(membros_dict, r_membros):
    """Gráfico de pizza: Resultado por membro (composição do resultado total).

    r_membros vem de calculos.calcular_todos_membros().
    """
    try:
        if not r_membros:
            return None

        labels = []
        data = []

        for membro in MEMBROS:
            res = r_membros.get(membro, {}).get("resultado_realizado", 0)
            if res != 0:  # Só mostra membros com resultado
                nome = NOMES_MEMBROS.get(membro, membro)
                labels.append(nome)
                data.append(res)

        if not labels:
            return None

        return {"labels": labels, "data": data}
    except Exception as e:
        app.logger.debug(f"Gráfico resultado por membro falhou: {e}")
        return None


def _tabela_status_membros(r_membros):
    """Tabela com cores: Estoque, Resultado, Capital, Índices por membro.

    Retorna lista de dicts com status e cor para renderizar no template.
    """
    try:
        if not r_membros:
            return None

        rows = []
        for membro in MEMBROS:
            res = r_membros.get(membro, {})
            resultado = res.get("resultado_realizado", 0)

            # Status de cor: verde (positivo), amarelo (zero), vermelho (negativo)
            if resultado > 0:
                status = "ok"
            elif resultado == 0:
                status = "aviso"
            else:
                status = "critico"

            rows.append({
                "membro": NOMES_MEMBROS.get(membro, membro),
                "emoji": EMOJIS_MEMBROS.get(membro, ""),
                "estoque": res.get("estoque", 0),
                "resultado": resultado,
                "capital": res.get("capital_imobilizado", 0),
                "ctcab": res.get("ctcab", 0),
                "status": status,
            })

        return rows
    except Exception as e:
        app.logger.debug(f"Tabela status membros falhou: {e}")
        return None


@app.route("/financeiro")
@login_required
def financeiro():
    """Página de indicadores financeiros completos com gráficos Onda 8.2."""
    dados = _get_dados_cache()
    r = _get_resumo_cache()  # resumo geral
    membros_dict = _get_membros_cache()

    # Calcular resultado por membro
    from calculos import calcular_todos_membros
    r_membros = calcular_todos_membros(dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"])

    # Gráficos Onda 8.2 (Financeiro)
    grafico_receita_custo = _grafico_receita_vs_custo(dados, r)
    grafico_resultado_membro = _grafico_resultado_por_membro(membros_dict, r_membros)
    tabela_membros = _tabela_status_membros(r_membros)

    return render_template("financeiro.html", r=r,
                          grafico_receita_custo=grafico_receita_custo,
                          grafico_resultado_membro=grafico_resultado_membro,
                          tabela_membros=tabela_membros,
                          r_membros=r_membros,
                          MEMBROS=MEMBROS, NOMES_MEMBROS=NOMES_MEMBROS, EMOJIS_MEMBROS=EMOJIS_MEMBROS)


@app.route("/resultado")
@login_required
def resultado():
    """Página de resultado por membro e período."""
    from calculos import calcular_resumo_financeiro
    dados = _get_dados_cache()
    membros_dict = _get_membros_cache()
    resumo_geral = calcular_resumo_financeiro(dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"])
    # O resultado por membro não traz estoque (só o que já foi vendido); a página
    # mostra "Estoque" por dono, que vem da conta de entradas/saídas por membro.
    estoque = calcular_estoque_por_membro(dados["Compras"], dados["Vendas"], dados["Manejo"])

    return render_template(
        "resultado.html",
        resumo_geral=resumo_geral,
        membros=membros_dict,
        estoque_membros=estoque,
        MEMBROS=MEMBROS,
        NOMES_MEMBROS=NOMES_MEMBROS,
        EMOJIS_MEMBROS=EMOJIS_MEMBROS,
    )


@app.route("/fluxo-caixa")
@login_required
def fluxo_caixa():
    """Página de fluxo de caixa (entrada/saída/saldo acumulado)."""
    dados = _get_dados_cache()
    vendas = dados.get("Vendas", pd.DataFrame())
    compras = dados.get("Compras", pd.DataFrame())
    gastos = dados.get("Gastos", pd.DataFrame())

    # Agrupar por mês
    fluxo = _calcular_fluxo_mensal(vendas, compras, gastos)

    return render_template("fluxo_caixa.html", fluxo=fluxo)


@app.route("/fluxo-animais")
@login_required
def fluxo_animais():
    """Página de fluxo de animais (entrada de compras/nascimento, saída de vendas/morte)."""
    dados = _get_dados_cache()
    compras = dados.get("Compras", pd.DataFrame())
    vendas = dados.get("Vendas", pd.DataFrame())
    manejo = dados.get("Manejo", pd.DataFrame())

    fluxo = _calcular_fluxo_animais(compras, vendas, manejo)

    return render_template("fluxo_animais.html", fluxo=fluxo)


@app.route("/lembretes-whatsapp")
@login_required
def lembretes_whatsapp():
    """Página de preferências WhatsApp e fila de avisos pendentes."""
    usuarios = _carregar_usuarios_disco()
    user_id = session.get("user_id")
    user_prefs = usuarios.get(user_id, {}).get("whatsapp_prefs", {})

    # Ler fila de avisos pendentes
    avisos_pendentes = _ler_avisos_pendentes()

    return render_template(
        "lembretes_whatsapp.html",
        user_prefs=user_prefs,
        avisos_pendentes=avisos_pendentes,
    )


# ── Funções auxiliares ────────────────────────────────────────────────────────

def _calcular_fluxo_mensal(vendas, compras, gastos, meses=12):
    """Calcula fluxo de caixa mensal: receita (vendas), despesa (compras+gastos), saldo."""
    agora = _agora()
    fluxo_list = []
    saldo_acum = 0

    for i in range(meses, 0, -1):
        data_inicio = agora - timedelta(days=30*i)
        data_fim = agora - timedelta(days=30*(i-1))

        # Receita (vendas)
        receita = 0
        if not vendas.empty:
            v = vendas[(pd.to_datetime(vendas["Data"], format="%d/%m/%Y", errors="coerce") >= data_inicio) &
                      (pd.to_datetime(vendas["Data"], format="%d/%m/%Y", errors="coerce") < data_fim)]
            if not v.empty:
                receita = float(pd.to_numeric(v["Valor Total (R$)"], errors="coerce").sum())

        # Despesa (compras + gastos)
        despesa = 0
        if not compras.empty:
            c = compras[(pd.to_datetime(compras["Data"], format="%d/%m/%Y", errors="coerce") >= data_inicio) &
                       (pd.to_datetime(compras["Data"], format="%d/%m/%Y", errors="coerce") < data_fim)]
            if not c.empty:
                despesa += float(pd.to_numeric(c["Valor Total (R$)"], errors="coerce").sum())
        if not gastos.empty:
            g = gastos[(pd.to_datetime(gastos["Data"], format="%d/%m/%Y", errors="coerce") >= data_inicio) &
                      (pd.to_datetime(gastos["Data"], format="%d/%m/%Y", errors="coerce") < data_fim)]
            if not g.empty:
                despesa += float(pd.to_numeric(g["Valor Total (R$)"], errors="coerce").sum())

        saldo_mes = receita - despesa
        saldo_acum += saldo_mes

        fluxo_list.append({
            "mes": data_fim.strftime("%b/%y"),
            "receita": receita,
            "despesa": despesa,
            "saldo_mes": saldo_mes,
            "saldo_acumulado": saldo_acum,
        })

    return fluxo_list


def _calcular_fluxo_animais(compras, vendas, manejo, dias=90):
    """Calcula fluxo de animais (entrada/saída) nos últimos dias."""
    agora = _agora()
    data_inicio = agora - timedelta(days=dias)

    fluxo_list = []
    entrada_total = 0
    saida_total = 0

    for i in range(dias):
        data = data_inicio + timedelta(days=i)

        # Entrada: compras + nascimentos
        entrada = 0
        if not compras.empty:
            c = compras[pd.to_datetime(compras["Data"], format="%d/%m/%Y", errors="coerce").dt.date == data.date()]
            entrada += len(c)
        if not manejo.empty:
            n = manejo[(manejo["Tipo"] == "Nascimento") &
                      (pd.to_datetime(manejo["Data"], format="%d/%m/%Y", errors="coerce").dt.date == data.date())]
            entrada += len(n)

        # Saída: vendas + mortes + perdas
        saida = 0
        if not vendas.empty:
            v = vendas[pd.to_datetime(vendas["Data"], format="%d/%m/%Y", errors="coerce").dt.date == data.date()]
            if not v.empty:
                saida += int(pd.to_numeric(v["Qtd Cabeças"], errors="coerce").sum())
        if not manejo.empty:
            # O tipo na aba é "Morte/Perda" (config.TIPOS_MANEJO) — com ["Morte","Perda"]
            # nenhuma morte entrava na saída.
            m = manejo[(manejo["Tipo"].astype(str).str.strip().isin(["Morte/Perda", "Morte", "Perda"])) &
                      (pd.to_datetime(manejo["Data"], format="%d/%m/%Y", errors="coerce").dt.date == data.date())]
            if not m.empty:
                saida += int(pd.to_numeric(m["Qtd Cabeças"], errors="coerce").fillna(0).sum())

        entrada_total += entrada
        saida_total += saida

        if (i % 7 == 0) or (i == dias - 1):  # Mostrar a cada semana
            fluxo_list.append({
                "data": data.strftime("%d/%m"),
                "entrada": entrada_total,
                "saida": saida_total,
            })

    return {
        "datas": [f["data"] for f in fluxo_list],
        "entrada": [f["entrada"] for f in fluxo_list],
        "saida": [f["saida"] for f in fluxo_list],
        "entrada_total": entrada_total,
        "saida_total": saida_total,
        "saldo": entrada_total - saida_total,
    }


def _carregar_usuarios_disco():
    """Carrega usuários.json da raiz."""
    try:
        path = os.path.join(RAIZ, "usuarios.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def _ler_avisos_pendentes():
    """Lê fila de avisos pendentes de WhatsApp."""
    try:
        from db import DATA_DIR
        path = os.path.join(DATA_DIR, "avisos_pendentes.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f) or []
    except Exception:
        pass
    return []
