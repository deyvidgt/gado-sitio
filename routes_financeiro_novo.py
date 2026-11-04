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

from flask import render_template, session, jsonify, request, redirect, url_for, flash
import pandas as pd
from datetime import datetime, timedelta
import math
import db
from db import carregar_aba, RAIZ
from calculos import calcular_todos_membros, calcular_estoque_por_membro
from config import MEMBROS, NOMES_MEMBROS, EMOJIS_MEMBROS
from extensions import (app, _agora, _validar_csrf, login_required, _get_dados_cache,
                        _get_membros_cache, _get_resumo_cache, fmt_brl, fmt_data, parse_valor,
                        _limpar_backups_antigos)
import planejamento as PL
import os
import json


_MESES_ABREV_PT = (
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
)


def _rotulo_mes_pt(data):
    return f"{_MESES_ABREV_PT[data.month - 1]}/{data.strftime('%y')}"


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


def _tabela_status_membros(r_membros, estoque_membros):
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
                "estoque": estoque_membros.get(membro, 0),
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
    estoque_membros = calcular_estoque_por_membro(
        dados["Compras"], dados["Vendas"], dados["Manejo"]
    )

    # Gráficos Onda 8.2 (Financeiro)
    grafico_receita_custo = _grafico_receita_vs_custo(dados, r)
    grafico_resultado_membro = _grafico_resultado_por_membro(membros_dict, r_membros)
    tabela_membros = _tabela_status_membros(r_membros, estoque_membros)

    return render_template("financeiro.html", r=r,
                          grafico_receita_custo=grafico_receita_custo,
                          grafico_resultado_membro=grafico_resultado_membro,
                          tabela_membros=tabela_membros,
                          r_membros=r_membros,
                          MEMBROS=MEMBROS, NOMES_MEMBROS=NOMES_MEMBROS, EMOJIS_MEMBROS=EMOJIS_MEMBROS)


def _backup_planejamento():
    db.fazer_backup()
    _limpar_backups_antigos()


def _alterar_registro_por_id(aba, registro_id, operacao):
    """Aplica alteração sob a trava de escrita do Excel e exige ID existente."""
    encontrado = False

    def alterar(df):
        nonlocal encontrado
        if df.empty or "ID" not in df.columns:
            return df
        mascara = df["ID"].astype(str) == str(registro_id)
        if not mascara.any():
            return df
        encontrado = True
        return operacao(df, mascara)

    db.alterar_aba(aba, alterar)
    if not encontrado:
        raise ValueError("Registro não encontrado.")


@app.route("/planejamento")
@login_required
def planejamento_financeiro():
    dados = _get_dados_cache()
    agora = _agora()
    try:
        ano = int(request.args.get("ano", agora.year))
        if ano < 2000 or ano > 2100:
            raise ValueError
    except (TypeError, ValueError):
        ano = agora.year

    df_orcamento = carregar_aba("Orçamento Previsto")
    df_contas = carregar_aba("Contas Futuras")
    comparativo = PL.comparar_orcamento(
        df_orcamento, dados["Compras"], dados["Gastos"], dados["Vendas"], ano
    )
    orcamentos = []
    if not df_orcamento.empty:
        for _, row in df_orcamento.iterrows():
            if str(row.get("Mês") or "")[:4] != str(ano):
                continue
            item = row.to_dict()
            item["valor_formatado"] = fmt_brl(parse_valor(item.get("Valor Previsto (R$)")))
            orcamentos.append(item)
    orcamentos.sort(key=lambda i: (str(i.get("Mês") or ""), str(i.get("Categoria") or "")))

    contas = []
    if not df_contas.empty:
        for _, row in df_contas.iterrows():
            item = row.to_dict()
            vencimento = PL.normalizar_data(item.get("Data Vencimento"))
            item["vencimento_exibido"] = vencimento.strftime("%d/%m/%Y") if not pd.isna(vencimento) else ""
            item["valor_formatado"] = fmt_brl(parse_valor(item.get("Valor (R$)")))
            contas.append(item)
    contas.sort(key=lambda i: PL.normalizar_data(i.get("Data Vencimento"))
                if not pd.isna(PL.normalizar_data(i.get("Data Vencimento"))) else pd.Timestamp.max)
    proximas = PL.contas_proximas(df_contas, agora.date())
    for conta in proximas:
        conta["valor_formatado"] = fmt_brl(parse_valor(conta.get("Valor (R$)")))

    anos = {agora.year - 1, agora.year, agora.year + 1}
    for _, row in df_orcamento.iterrows() if not df_orcamento.empty else []:
        mes = str(row.get("Mês") or "")
        if len(mes) >= 4 and mes[:4].isdigit():
            anos.add(int(mes[:4]))

    totais = {
        tipo: {
            "previsto": sum(r["previsto"] for r in comparativo if r["tipo"] == tipo),
            "realizado": sum(r["realizado"] for r in comparativo if r["tipo"] == tipo),
        }
        for tipo in ("Despesa", "Receita")
    }
    return render_template(
        "planejamento.html", ano=ano, anos=sorted(anos, reverse=True),
        categorias=PL.CATEGORIAS_ORCAMENTO, membros=MEMBROS,
        orcamentos=orcamentos, comparativo=comparativo, totais=totais,
        contas=contas, proximas=proximas, hoje=agora.strftime("%Y-%m-%d"),
        fmt_brl=fmt_brl,
    )


@app.route("/orcamento/novo", methods=["POST"])
@login_required
def novo_orcamento():
    _validar_csrf()
    f = request.form
    try:
        mes = (f.get("mes") or "").strip()
        try:
            datetime.strptime(mes, "%Y-%m")
        except ValueError:
            raise ValueError("Informe o mês do orçamento.")
        tipo = (f.get("tipo") or "").strip()
        categoria = (f.get("categoria") or "").strip()
        if (tipo, categoria) not in PL.CATEGORIAS_ORCAMENTO:
            raise ValueError("Selecione uma categoria compatível com o tipo.")
        descricao = (f.get("descricao") or "").strip()
        valor = parse_valor(f.get("valor"))
        if not descricao:
            raise ValueError("Informe a descrição do orçamento.")
        if not math.isfinite(valor) or valor <= 0:
            raise ValueError("O valor previsto deve ser maior que zero.")
        membro = (f.get("membro") or "").strip()
        if membro and membro not in MEMBROS:
            raise ValueError("Selecione um membro válido.")
        _backup_planejamento()
        db.salvar_linha("Orçamento Previsto", [
            PL.novo_id("ORC"), mes, tipo, categoria, descricao, valor, membro,
        ])
        flash("Previsão de orçamento registrada.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        app.logger.exception("Falha ao registrar previsão de orçamento")
        flash(f"Erro ao registrar orçamento: {e}", "error")
    return redirect(url_for("planejamento_financeiro"))


@app.route("/orcamento/<registro_id>/excluir", methods=["POST"])
@login_required
def excluir_orcamento(registro_id):
    _validar_csrf()
    try:
        _backup_planejamento()
        _alterar_registro_por_id(
            "Orçamento Previsto", registro_id,
            lambda df, mascara: df.loc[~mascara].reset_index(drop=True),
        )
        flash("Previsão removida.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        app.logger.exception("Falha ao excluir previsão de orçamento")
        flash(f"Erro ao remover previsão: {e}", "error")
    return redirect(url_for("planejamento_financeiro"))


@app.route("/contas-futuras/nova", methods=["POST"])
@login_required
def nova_conta_futura():
    _validar_csrf()
    f = request.form
    try:
        vencimento = PL.normalizar_data(f.get("vencimento"))
        tipo = (f.get("tipo") or "").strip()
        categoria = (f.get("categoria") or "").strip()
        descricao = (f.get("descricao") or "").strip()
        valor = parse_valor(f.get("valor"))
        membro = (f.get("membro") or "").strip()
        if pd.isna(vencimento):
            raise ValueError("Informe uma data de vencimento válida.")
        if tipo not in ("Pagar", "Receber"):
            raise ValueError("Selecione pagar ou receber.")
        tipo_orcamento = "Despesa" if tipo == "Pagar" else "Receita"
        if (tipo_orcamento, categoria) not in PL.CATEGORIAS_ORCAMENTO:
            raise ValueError("Selecione uma categoria compatível com o tipo.")
        if not descricao:
            raise ValueError("Informe a descrição da conta.")
        if not math.isfinite(valor) or valor <= 0:
            raise ValueError("O valor da conta deve ser maior que zero.")
        if membro and membro not in MEMBROS:
            raise ValueError("Selecione um membro válido.")
        _backup_planejamento()
        db.salvar_linha("Contas Futuras", [
            PL.novo_id("CF"), vencimento.strftime("%Y-%m-%d"), tipo, categoria,
            descricao, valor, "Pendente", membro,
        ])
        flash("Conta futura registrada.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        app.logger.exception("Falha ao registrar conta futura")
        flash(f"Erro ao registrar conta: {e}", "error")
    return redirect(url_for("planejamento_financeiro"))


@app.route("/contas-futuras/<registro_id>/status", methods=["POST"])
@login_required
def alterar_status_conta(registro_id):
    _validar_csrf()
    try:
        df = carregar_aba("Contas Futuras")
        if df.empty or "ID" not in df.columns:
            raise ValueError("Conta não encontrada.")
        achadas = df[df["ID"].astype(str) == str(registro_id)]
        if achadas.empty:
            raise ValueError("Conta não encontrada.")
        conta = achadas.iloc[0]
        tipo = str(conta.get("Tipo") or "")
        status = (request.form.get("status") or "").strip()
        status_permitidos = {"Pendente", "Pago" if tipo == "Pagar" else "Recebido"}
        if tipo not in ("Pagar", "Receber") or status not in status_permitidos:
            raise ValueError("Status inválido para esta conta.")
        _backup_planejamento()

        def definir_status(df_, mascara):
            if "Status" not in df_.columns:
                df_["Status"] = ""
            df_["Status"] = df_["Status"].astype(object)
            df_.loc[mascara, "Status"] = status
            return df_

        _alterar_registro_por_id(
            "Contas Futuras", registro_id, definir_status,
        )
        if status == "Pendente":
            flash("Conta reaberta. O realizado só muda quando for lançado nas telas financeiras.", "success")
        else:
            flash(f"Conta marcada como {status.lower()}. Registre o realizado nas telas financeiras.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        app.logger.exception("Falha ao atualizar status da conta futura")
        flash(f"Erro ao atualizar conta: {e}", "error")
    return redirect(url_for("planejamento_financeiro"))


@app.route("/contas-futuras/<registro_id>/excluir", methods=["POST"])
@login_required
def excluir_conta_futura(registro_id):
    _validar_csrf()
    try:
        _backup_planejamento()
        _alterar_registro_por_id(
            "Contas Futuras", registro_id,
            lambda df, mascara: df.loc[~mascara].reset_index(drop=True),
        )
        flash("Conta futura removida.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        app.logger.exception("Falha ao excluir conta futura")
        flash(f"Erro ao remover conta: {e}", "error")
    return redirect(url_for("planejamento_financeiro"))


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
            "mes": _rotulo_mes_pt(data_fim),
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
