# -*- coding: utf-8 -*-
"""Rotas iniciais do módulo leiteiro."""

from datetime import timedelta
from io import BytesIO

from flask import abort, flash, redirect, render_template, request, send_file, url_for
from openpyxl import Workbook

from datetime import timedelta, date
import pandas as pd

import animais as A
from config import COLUNAS_LEITE_COLCHAO, COLUNAS_LEITE_CONFORTO, COLUNAS_LEITE_TRATAMENTOS, MEMBROS, NOMES_MEMBROS
from db import alterar_aba, carregar_aba, fazer_backup
from extensions import _agora, _limpar_backups_antigos, _validar_csrf, app, login_required, salvar_linha, parse_valor
from leite import _data, _numero, acumulados, contagens_rebanho, dias_em_lactacao, medias_periodo, producao_por_animal, serie_diaria, validar_producao, historico_colchao


def _grafico_producao_leite(df_producao, hoje, dias=30):
    """Linhas: Produção dia/semana/mês. Onda 8.3.1"""
    try:
        if df_producao is None or df_producao.empty:
            return None

        from datetime import timedelta
        inicio = hoje - timedelta(days=dias)

        producao_dia = {}
        for _, row in df_producao.iterrows():
            data = _data(row.get("Data"))
            litros = _numero(row.get("Litros", 0)) or 0
            if data and data >= inicio and data <= hoje:
                data_str = data.isoformat()
                producao_dia[data_str] = producao_dia.get(data_str, 0) + litros

        if not producao_dia:
            return None

        datas = sorted(producao_dia.keys())
        labels = [pd.to_datetime(d).strftime("%d/%m") for d in datas]
        data = [producao_dia[d] for d in datas]

        return {"labels": labels, "data": data}
    except Exception as e:
        app.logger.debug(f"Gráfico produção leite falhou: {e}")
        return None


def _grafico_ccs_cpp(df_producao, dias=60):
    """Linhas: CCS/CPP trending (qualidade do leite). Onda 8.3.2"""
    try:
        if df_producao is None or df_producao.empty:
            return None

        from datetime import timedelta
        hoje = _agora().date()
        inicio = hoje - timedelta(days=dias)

        ccs_data = {}
        cpp_data = {}

        for _, row in df_producao.iterrows():
            data = _data(row.get("Data"))
            ccs = _numero(row.get("CCS (células/mL)"))
            cpp = _numero(row.get("CPP (UFC/mL)"))

            if data and data >= inicio and data <= hoje:
                data_str = data.isoformat()
                if ccs:
                    ccs_data[data_str] = ccs
                if cpp:
                    cpp_data[data_str] = cpp

        if not ccs_data and not cpp_data:
            return None

        # Últimos 15 pontos
        datas = sorted(set(list(ccs_data.keys()) + list(cpp_data.keys())))[-15:]
        labels = [pd.to_datetime(d).strftime("%d/%m") for d in datas]

        return {
            "labels": labels,
            "ccs": [ccs_data.get(d, None) for d in datas],
            "cpp": [cpp_data.get(d, None) for d in datas],
        }
    except Exception as e:
        app.logger.debug(f"Gráfico CCS/CPP falhou: {e}")
        return None


def _grafico_top_vacas(df_producao, df_animais, dias=30):
    """Barras: Produção por vaca (top 10). Onda 8.3.3"""
    try:
        if df_producao is None or df_producao.empty:
            return None

        from datetime import timedelta
        hoje = _agora().date()
        inicio = hoje - timedelta(days=dias)

        producao_vaca = {}

        for _, row in df_producao.iterrows():
            data = _data(row.get("Data"))
            vaca_id = str(row.get("Vaca ID", "")).strip()
            litros = _numero(row.get("Litros", 0)) or 0

            if data and data >= inicio and data <= hoje and vaca_id:
                producao_vaca[vaca_id] = producao_vaca.get(vaca_id, 0) + litros

        if not producao_vaca:
            return None

        # Top 10
        top = sorted(producao_vaca.items(), key=lambda x: x[1], reverse=True)[:10]
        labels = [item[0][:15] for item in top]
        data = [item[1] for item in top]

        return {"labels": labels, "data": data}
    except Exception as e:
        app.logger.debug(f"Gráfico top vacas falhou: {e}")
        return None


def _grafico_saude_leite(df_producao):
    """Gauge: Saúde geral (% vacas saudáveis). Onda 8.3.4"""
    try:
        if df_producao is None or df_producao.empty:
            return None

        hoje = _agora().date()

        # Últimas medições de cada vaca
        ultimas = {}
        for _, row in df_producao.iterrows():
            data = _data(row.get("Data"))
            vaca_id = str(row.get("Vaca ID", "")).strip()
            ccs = _numero(row.get("CCS (células/mL)"))
            cpp = _numero(row.get("CPP (UFC/mL)"))

            if data and data <= hoje and vaca_id and (ccs or cpp):
                if vaca_id not in ultimas or data > _data(ultimas[vaca_id].get("Data", "")):
                    ultimas[vaca_id] = {"data": data, "ccs": ccs, "cpp": cpp}

        if not ultimas:
            return None

        saudaveis = 0
        for vaca_data in ultimas.values():
            ccs = vaca_data.get("ccs")
            cpp = vaca_data.get("cpp")

            # Saudável: CCS < 200k E CPP < 100k
            ccs_ok = ccs is None or ccs < 200000
            cpp_ok = cpp is None or cpp < 100000

            if ccs_ok and cpp_ok:
                saudaveis += 1

        pct_saudaveis = (saudaveis / len(ultimas) * 100) if ultimas else 0

        return {"valor": pct_saudaveis, "total": len(ultimas), "saudaveis": saudaveis}
    except Exception as e:
        app.logger.debug(f"Gráfico saúde leite falhou: {e}")
        return None


def _comparar_vacas(ids_animais, periodo_dias=30):
    """Compara até 3 vacas leiteiras no período."""
    hoje = _agora().date()
    inicio = hoje - timedelta(days=periodo_dias)

    df_producao = carregar_aba("Leite Produção")
    df_config = carregar_aba("Leite Configuração")

    preco_litro = 0
    if df_config is not None and not df_config.empty:
        preco = _numero(df_config.iloc[0].get("Preço por Litro"))
        preco_litro = preco if preco else 0

    resultado = {}
    for vaca_id in ids_animais:
        vaca_id = str(vaca_id).strip()
        if df_producao is None or df_producao.empty:
            registros = pd.DataFrame()
        else:
            registros = df_producao[df_producao.get("Vaca ID", "").astype(str).str.strip() == vaca_id].copy()
            if not registros.empty:
                datas_lista = [_data(d) for d in registros.get("Data", [])]
                mask = [d is not None and d >= inicio and d <= hoje for d in datas_lista]
                registros = registros[mask]

        if registros.empty:
            resultado[vaca_id] = {
                "producao_litros_dia": 0.0,
                "custo_diario": 0.0,
                "receita_diario": 0.0,
                "margem_diario": 0.0,
                "ccs_ultimo": None,
                "cpp_ultimo": None,
                "ultimos_eventos": []
            }
        else:
            litros_total = sum(_numero(r.get("Litros", 0)) or 0 for _, r in registros.iterrows())
            # Nomes reais das colunas (config.COLUNAS_LEITE_PRODUCAO); "CCS"/"CPP"
            # puro não existe na aba e o filtro virava KeyError → 500.
            ccs_col = registros.get("CCS (células/mL)", pd.Series("", index=registros.index))
            cpp_col = registros.get("CPP (UFC/mL)", pd.Series("", index=registros.index))
            ccs_ultim = registros[ccs_col.astype(str).str.strip() != ""].tail(1).get("CCS (células/mL)").values
            cpp_ultim = registros[cpp_col.astype(str).str.strip() != ""].tail(1).get("CPP (UFC/mL)").values
            resultado[vaca_id] = {
                "producao_litros_dia": round(litros_total / max(len(registros), 1), 2),
                "custo_diario": 0.0,
                "receita_diario": round((litros_total / max(len(registros), 1)) * preco_litro, 2),
                "margem_diario": round((litros_total / max(len(registros), 1)) * preco_litro, 2),
                "ccs_ultimo": _numero(ccs_ultim[0]) if len(ccs_ultim) > 0 else None,
                "cpp_ultimo": _numero(cpp_ultim[0]) if len(cpp_ultim) > 0 else None,
                "ultimos_eventos": []
            }
    return resultado


def _dados_operacionais(df, animais, hoje):
    """Monta os poucos indicadores de ação exibidos no painel principal."""
    inicio = hoje - timedelta(days=13)
    serie = [{"data": dia.isoformat(), "litros": litros}
             for dia, litros in serie_diaria(df, inicio, hoje)]

    linhas = df.copy() if df is not None else pd.DataFrame()
    qualidade = {"data": None, "ccs": None, "cpp": None, "status": "sem dados"}
    if not linhas.empty:
        linhas["_data"] = linhas.get("Data", "").map(_data)
        linhas = linhas[linhas["_data"].notna() & (linhas["_data"] <= hoje)]
        if not linhas.empty:
            linha = linhas.sort_values("_data").iloc[-1]
            ccs = _numero(linha.get("CCS (células/mL)"))
            cpp = _numero(linha.get("CPP (UFC/mL)"))
            niveis = [
                "urgente" if ccs is not None and ccs >= 400000 or cpp is not None and cpp >= 500000 else
                "aviso" if ccs is not None and ccs >= 200000 or cpp is not None and cpp >= 100000 else
                "ok"
            ]
            qualidade = {"data": linha["_data"].isoformat(), "ccs": ccs, "cpp": cpp,
                         "status": niveis[0]}

    contagens = contagens_rebanho(animais)
    sem_registro = 0
    if animais is not None and not animais.empty and "ID" in animais.columns:
        vivos = animais[animais.get("Status", "").astype(str).str.lower().isin({"vivo", "ativo"})]
        leiteiras = vivos[vivos.get("Uso Produtivo", "").astype(str).str.lower().isin({"leite", "ambos"})]
        ids_hoje = set(linhas.loc[linhas["_data"] == hoje, "Vaca ID"].astype(str).str.strip()) if not linhas.empty else set()
        sem_registro = int(sum(str(animal).strip() not in ids_hoje for animal in leiteiras["ID"]))

    return {"serie": serie, "qualidade": qualidade, "sem_registro": sem_registro,
            "tem_registro_hoje": bool(not linhas.empty and (linhas["_data"] == hoje).any()),
            "contagens": contagens}


@app.route("/leite")
@login_required
def painel_leite():
    hoje = _agora().date()
    df = carregar_aba("Leite Produção")
    animais = A.carregar()
    contagens = contagens_rebanho(animais)
    acumulado = acumulados(df, hoje)
    medias = medias_periodo(df, hoje.replace(day=1), hoje,
                            animais_lactacao=contagens["vacas_lactacao"])

    from doencas_carencia import carencias_ativas
    carencias_leite = carencias_ativas("leite", hoje)

    # Alertas de colchão: conta urgentes e avisos
    df_colchao = carregar_aba("Leite Colchão")
    colchoes_alertas = {"urgente": 0, "aviso": 0, "ok": 0}
    if df_colchao is not None and not df_colchao.empty:
        historicos = historico_colchao(df_colchao, referencia=hoje)
        for hist in historicos.values():
            status = hist.get("status", "ok")
            colchoes_alertas[status] += 1

    operacional = _dados_operacionais(df, animais, hoje)

    # Gráficos Onda 8.3
    grafico_producao = _grafico_producao_leite(df, hoje)
    grafico_qualidade = _grafico_ccs_cpp(df)
    grafico_top_vacas = _grafico_top_vacas(df, animais)
    grafico_saude = _grafico_saude_leite(df)

    return render_template("leite.html", acumulado=acumulado, medias=medias,
                           contagens=contagens, registros=len(df), hoje=hoje,
                           colchoes_alertas=colchoes_alertas, operacional=operacional,
                           carencias_leite=carencias_leite,
                           grafico_producao=grafico_producao,
                           grafico_qualidade=grafico_qualidade,
                           grafico_top_vacas=grafico_top_vacas,
                           grafico_saude=grafico_saude)


@app.route("/leite/animais")
@login_required
def animais_leite():
    hoje = _agora().date()
    animais = A.carregar()
    colunas = {str(c) for c in animais.columns}
    vivos = animais[animais["Status"].astype(str).str.strip().str.lower().isin({"vivo", "ativo"})]
    if "Uso Produtivo" in colunas:
        vivos = vivos[vivos["Uso Produtivo"].astype(str).str.lower().isin({"leite", "ambos"})]
    else:
        vivos = vivos[(vivos["Sexo"].astype(str).str.upper() == "F") &
                      vivos["Categoria"].astype(str).str.lower().isin({"vaca", "novilha", "bezerra"})]
    lista = []
    for _, animal in vivos.iterrows():
        lista.append({
            "id": animal.get("ID", ""),
            "brinco": f"{animal.get('Brinco Cor', '')} {animal.get('Brinco Nº', '')}".strip(),
            "situacao": animal.get("Situação Leite", "não informado"),
            "parto": animal.get("Último Parto", ""),
            "dias": dias_em_lactacao(animal.get("Último Parto", ""), hoje),
        })
    return render_template("leite_animais.html", animais=lista)


@app.route("/leite/animal/<animal_id>")
@login_required
def ficha_animal_leite(animal_id):
    df_animais = A.carregar()
    encontrado = df_animais[df_animais["ID"].astype(str).str.strip() == str(animal_id).strip()]
    if encontrado.empty:
        abort(404)
    linha = encontrado.iloc[0]
    hoje = _agora().date()
    df_producao = carregar_aba("Leite Produção")
    historico = []
    lactacao_atual = None  # Dados da lactação atual

    if not df_producao.empty:
        registros = df_producao[df_producao.get("Vaca ID", "").astype(str).str.strip() == str(animal_id).strip()]
        for _, registro in registros.iterrows():
            data = _data(registro.get("Data"))
            litros = _numero(registro.get("Litros"))
            if data is not None and litros is not None:
                historico.append({"data": data, "litros": litros, "ordenha": registro.get("Ordenha", "")})
        historico.sort(key=lambda item: item["data"], reverse=True)

        # Calcula lactação atual (após último parto)
        parto = _data(linha.get("Último Parto", ""))
        if parto and historico:
            registros_lactacao = [h for h in historico if h["data"] >= parto]
            if registros_lactacao:
                dias_lactacao = dias_em_lactacao(parto, hoje) or 1
                total_litros = sum(h["litros"] for h in registros_lactacao)
                media_diaria = total_litros / dias_lactacao if dias_lactacao > 0 else 0

                # Persistência = (média últimos 100 dias) / (média primeiros 100 dias) * 100
                registros_ord = sorted(registros_lactacao, key=lambda x: x["data"])
                primeiros_100 = [h["litros"] for h in registros_ord[:100]]
                ultimos_100 = [h["litros"] for h in registros_ord[-100:]]
                persistencia = 0
                if primeiros_100 and ultimos_100:
                    media_primeiros = sum(primeiros_100) / len(primeiros_100)
                    media_ultimos = sum(ultimos_100) / len(ultimos_100)
                    persistencia = (media_ultimos / media_primeiros * 100) if media_primeiros > 0 else 0

                # Série diária para gráfico (últimos 90 dias)
                hoje_dt = pd.Timestamp(hoje)
                inicio_grafico = hoje_dt - pd.Timedelta(days=90)
                serie_grafico = {}
                for h in registros_lactacao:
                    if h["data"] >= inicio_grafico.date():
                        data_str = h["data"].isoformat()
                        if data_str not in serie_grafico:
                            serie_grafico[data_str] = 0
                        serie_grafico[data_str] += h["litros"]

                datas_grafico = sorted(serie_grafico.keys())
                valores_grafico = [serie_grafico[d] for d in datas_grafico]

                lactacao_atual = {
                    "dias": dias_lactacao,
                    "total_litros": total_litros,
                    "media_diaria": media_diaria,
                    "persistencia": persistencia,
                    "datas_grafico": datas_grafico,
                    "valores_grafico": valores_grafico,
                }

    from doencas_carencia import carencias_ativas
    carencias = [{"descricao": c["descricao"] or c["medicamento"] or "Tratamento",
                  "fim": c["data_liberacao"]}
                 for c in carencias_ativas("leite", hoje, vaca_id=animal_id)]

    parto = linha.get("Último Parto", "")
    return render_template("leite_animal.html", animal={
        "id": animal_id,
        "brinco": f"{linha.get('Brinco Cor', '')} {linha.get('Brinco Nº', '')}".strip(),
        "situacao": linha.get("Situação Leite", "não informado"),
        "parto": parto,
        "dias": dias_em_lactacao(parto, hoje),
    }, historico=historico, total=sum(item["litros"] for item in historico), carencias=carencias,
       lactacao_atual=lactacao_atual)


@app.route("/leite/alimentacao", methods=["GET", "POST"])
@login_required
def alimentacao_leite():
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        produto = str(f.get("produto") or "").strip()
        if not produto:
            flash("Informe o produto.", "error")
            return redirect(url_for("alimentacao_leite"))

        peso_saco = _numero(f.get("peso_saco", 25)) or 25.0
        from models import Insumo
        from extensions import db as db_sqla
        insumo = Insumo.query.filter_by(nome=produto).first()
        if not insumo:
            insumo = Insumo(nome=produto, categoria=f.get("categoria", "Nutrição"), peso_saco=peso_saco, unidade_medida="sacos")
            db_sqla.session.add(insumo)
        else:
            insumo.peso_saco = peso_saco
            if f.get("categoria"):
                insumo.categoria = f.get("categoria")
        db_sqla.session.commit()

        salvar_linha("Leite Alimentação", [
            produto, f.get("fabricante", ""), f.get("categoria", ""), peso_saco,
            f.get("proteina", ""), f.get("ndt", ""), f.get("fibra", ""), f.get("calcio", ""),
            f.get("fosforo", ""), f.get("consumo", ""), f.get("preco", ""), f.get("lote", ""),
            f.get("validade", ""), f.get("observacao", ""), "Sim",
        ])
        flash("Produto de nutrição cadastrado e sincronizado com o estoque!", "success")
        return redirect(url_for("alimentacao_leite"))
    df = carregar_aba("Leite Alimentação")
    produtos = []
    for real_idx, linha in df.iterrows():
        produtos.append({
            "_idx": int(real_idx),
            "produto": linha.get("Produto", ""),
            "fabricante": linha.get("Fabricante", ""),
            "categoria": linha.get("Categoria", ""),
            "peso_saco": linha.get("Peso Saco (kg)", 25),
            "proteina": linha.get("Proteína Bruta (%)", ""),
            "ndt": linha.get("NDT/Energia (%)", ""),
            "preco": linha.get("Preço por Saco (R$)", ""),
        })
    return render_template("leite_alimentacao.html", produtos=produtos)


@app.route("/produtos/editar/<int:idx>", methods=["GET", "POST"])
@login_required
def editar_produto_nutricao(idx):
    df = carregar_aba("Leite Alimentação")
    if df.empty or idx >= len(df):
        flash("Produto não encontrado.", "error")
        return redirect(url_for("alimentacao_leite"))

    if request.method == "POST":
        _validar_csrf()
        f = request.form
        produto = str(f.get("produto") or "").strip()
        if not produto:
            flash("Informe o produto.", "error")
            return redirect(url_for("editar_produto_nutricao", idx=idx))

        peso_saco = _numero(f.get("peso_saco", 25)) or 25.0
        linha = [
            produto, f.get("fabricante", ""), f.get("categoria", ""), peso_saco,
            f.get("proteina", ""), f.get("ndt", ""), f.get("fibra", ""), f.get("calcio", ""),
            f.get("fosforo", ""), f.get("consumo", ""), f.get("preco", ""), f.get("lote", ""),
            f.get("validade", ""), f.get("observacao", ""), "Sim",
        ]

        from routes_animais import fazer_backup_seguro
        from db import reescrever_aba
        fazer_backup_seguro()
        df_edit = df.astype(object)
        for i, col in enumerate(df_edit.columns):
            if i < len(linha):
                df_edit.at[idx, col] = linha[i]
        reescrever_aba("Leite Alimentação", df_edit)
        flash("Produto atualizado com sucesso!", "success")
        return redirect(url_for("alimentacao_leite"))

    row = df.iloc[idx].to_dict()
    return render_template("form_editar_produto.html", row=row, idx=idx)


@app.route("/produtos/excluir/<int:idx>", methods=["POST"])
@login_required
def excluir_produto_nutricao(idx):
    _validar_csrf()
    from routes_animais import fazer_backup_seguro
    from db import reescrever_aba
    fazer_backup_seguro()
    df = carregar_aba("Leite Alimentação")
    if not df.empty and idx < len(df):
        df = df.drop(df.index[idx]).reset_index(drop=True)
        reescrever_aba("Leite Alimentação", df)
        flash("Produto excluído com sucesso.", "warning")
    return redirect(url_for("alimentacao_leite"))


@app.route("/leite/necessidades", methods=["POST"])
@login_required
def necessidade_leite():
    _validar_csrf()
    f = request.form
    salvar_linha("Leite Necessidades", [
        f.get("categoria", ""), f.get("item", ""), f.get("valor", ""), f.get("unidade", ""),
        f.get("fonte", ""), f.get("data_revisao", ""), f.get("observacao", ""), "Sim",
    ])
    flash("Necessidade diária cadastrada.", "success")
    return redirect(url_for("alimentacao_leite"))


@app.route("/leite/calculador", methods=["GET", "POST"])
@login_required
def calculador_leite():
    """Calculador de ração com balanceamento simplificado."""
    from racao import (
        calcular_necessidades,
        carregar_ingredientes_ativos,
        balancear_racao,
        fazer_comparativo,
    )

    categorias = ["Lactação", "Seca", "Novilha", "Bezerro"]
    resultado = None
    necessidades = None
    erro = None

    if request.method == "POST":
        _validar_csrf()
        f = request.form
        try:
            categoria = str(f.get("categoria", "")).strip()
            peso_kg = float(str(f.get("peso_vivo", "0")).replace(",", "."))
            producao_litros = 0.0

            if categoria == "Lactação":
                producao_litros = float(str(f.get("producao_litros", "0")).replace(",", "."))

            if not categoria or categoria not in categorias or peso_kg <= 0:
                erro = "Categoria ou peso inválido."
            else:
                # Calcula necessidades
                necessidades = calcular_necessidades(categoria, peso_kg, producao_litros)

                # Tenta balancear
                ingredientes = carregar_ingredientes_ativos()
                if not ingredientes:
                    erro = "Nenhum produto cadastrado em 'Leite Alimentação'. Adicione produtos primeiro."
                else:
                    sugestao = balancear_racao(necessidades, ingredientes)
                    if sugestao:
                        resultado = {
                            "necessidades": necessidades,
                            "sugestao": sugestao,
                            "comparativo": fazer_comparativo(necessidades, sugestao),
                            "categoria": categoria,
                            "peso_kg": peso_kg,
                            "producao_litros": producao_litros,
                        }
                    else:
                        erro = "Não foi possível balancear a ração com os produtos disponíveis."
        except (ValueError, KeyError) as e:
            erro = f"Erro no cálculo: {str(e)}"

    return render_template("leite_calculador.html",
                         categorias=categorias,
                         resultado=resultado,
                         erro=erro,
                         hoje=_agora().strftime("%Y-%m-%d"))
def _definicoes_operacao():
    """tipo → (aba, título, campos da tela, nomes de campos para leitura do form)."""
    return {
        "tratamentos": ("Leite Tratamentos", "Tratamentos", [
            {"nome": "vaca_id", "label": "Vaca ID", "required": False},
            {"nome": "brinco", "label": "Brinco", "required": False},
            {"nome": "tipo", "label": "Tipo", "required": True},
            {"nome": "descricao", "label": "Descrição", "required": True},
            {"nome": "produto", "label": "Produto/Serviço", "required": False},
            {"nome": "quantidade", "label": "Quantidade", "required": False},
            {"nome": "unidade", "label": "Unidade", "required": False},
            {"nome": "custo", "label": "Custo (R$)", "required": False},
            {"nome": "responsavel", "label": "Responsável", "required": False},
            {"nome": "carencia", "label": "Período de carência", "required": False},
            {"nome": "observacao", "label": "Observação", "required": False},
            {"nome": "id_envio", "label": "", "required": False},
        ], ["vaca_id", "brinco", "tipo", "descricao", "produto", "quantidade", "unidade", "custo", "responsavel", "carencia", "observacao", "id_envio", "criado_em"]),
        "conforto": ("Leite Conforto", "Conforto térmico e descanso", [
            {"nome": "local", "label": "Local", "required": True},
            {"nome": "sombra", "label": "Sombra", "required": False},
            {"nome": "agua", "label": "Água disponível", "required": False},
            {"nome": "ventilacao", "label": "Ventilação", "required": False},
            {"nome": "area_descanso", "label": "Área de descanso", "required": False},
            {"nome": "lotacao", "label": "Lotação", "required": False},
            {"nome": "estresse", "label": "Estresse térmico", "required": False},
            {"nome": "descanso", "label": "Descanso observado", "required": False},
            {"nome": "estado_cocho", "label": "Estado do cocho", "required": False, "opcoes": ["Vazio", "Normal", "Cheio"]},
            {"nome": "observacao", "label": "Observação", "required": False},
            {"nome": "responsavel", "label": "Responsável", "required": False},
            {"nome": "id_envio", "label": "", "required": False},
        ], ["local", "sombra", "agua", "ventilacao", "area_descanso", "lotacao", "estresse", "descanso", "estado_cocho", "observacao", "responsavel", "id_envio", "criado_em"]),
        "colchao": ("Leite Colchão", "Colchão", [
            {"nome": "local", "label": "Local", "required": True},
            {"nome": "material", "label": "Material", "required": True},
            {"nome": "quantidade", "label": "Quantidade", "required": False},
            {"nome": "unidade", "label": "Unidade", "required": False},
            {"nome": "custo", "label": "Custo (R$)", "required": False},
            {"nome": "fornecedor", "label": "Fornecedor", "required": False},
            {"nome": "condicao", "label": "Condição", "required": True},
            {"nome": "estado", "label": "Estado", "required": False, "opcoes": ["Bom", "Regular", "Ruim"]},
            {"nome": "proxima_troca", "label": "Próxima troca", "required": False},
            {"nome": "observacao", "label": "Observação", "required": False},
            {"nome": "foto_antes", "label": "Foto antes", "required": False},
            {"nome": "foto_depois", "label": "Foto depois", "required": False},
            {"nome": "responsavel", "label": "Responsável", "required": False},
            {"nome": "id_envio", "label": "", "required": False},
        ], ["local", "material", "quantidade", "unidade", "custo", "fornecedor", "condicao", "estado", "proxima_troca", "observacao", "foto_antes", "foto_depois", "responsavel", "id_envio", "criado_em"]),
    }


def _operacao_leite(tipo, aba, titulo, campos, valores):
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        # valores é a lista de colunas após "Data"; cada campo está em valores (pela order).
        # Lê do form pelos nomes dos campos (snake_case).
        linha = [f.get("data", "")] + [f.get(campo["nome"], "") for campo in campos]

        # Validação especial para colchão: se não tem próxima troca, calcula +180 dias
        if tipo == "colchao":
            data_str = f.get("data", "").strip()
            proxima_str = f.get("proxima_troca", "").strip()
            if data_str and not proxima_str:
                data = _data(data_str)
                if data:
                    proxima = (data + timedelta(days=180)).strftime("%d/%m/%Y")
                    # Índice 8 é "proxima_troca" na ordem de _definicoes_operacao()["colchao"]
                    linha[8] = proxima

        salvar_linha(aba, linha)
        flash(f"{titulo} registrado.", "success")
        return redirect(url_for("operacao_leite", tipo=tipo))
    return render_template("leite_operacao.html", titulo=titulo, campos=campos,
                           hoje=_agora().strftime("%Y-%m-%d"))


@app.route("/leite/<tipo>", methods=["GET", "POST"])
@login_required
def operacao_leite(tipo):
    definicoes = _definicoes_operacao()
    if tipo not in definicoes:
        abort(404)
    aba, titulo, campos, valores = definicoes[tipo]
    return _operacao_leite(tipo, aba, titulo, campos, valores)


@app.route("/leite/editar/<int:indice>", methods=["GET", "POST"])
@login_required
def editar_ordenha(indice):
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        dados = {"Data": f.get("data"), "Vaca ID": f.get("vaca_id", ""),
                 "Modo Registro": f.get("modo_registro", ""), "Litros": f.get("litros", "")}
        erro = validar_producao(dados)
        if erro:
            flash(erro, "error")
            return redirect(url_for("editar_ordenha", indice=indice))

        if indice >= len(carregar_aba("Leite Produção")):
            abort(404)
        fazer_backup()
        _limpar_backups_antigos()

        def mudar(df):
            # Lido e gravado sob a mesma trava: um cadastro feito agora não some.
            # object evita rejeitar texto vazio ao corrigir um registro antigo (pandas põe float).
            df = df.astype(object)
            modo = str(f.get("modo_registro") or "").strip().lower()
            linha = df.iloc[indice].copy()
            linha["Data"] = f.get("data", "")
            linha["Vaca ID"] = f.get("vaca_id", "") if modo == "individual" else ""
            linha["Brinco"] = f.get("brinco", "")
            linha["Modo Registro"] = modo
            linha["Ordenha"] = f.get("ordenha", "")
            linha["Litros"] = parse_valor(f.get("litros"))
            for campo, nome in (("ccs", "CCS (células/mL)"), ("cpp", "CPP (UFC/mL)"),
                                ("qualidade", "Qualidade"), ("temperatura", "Temperatura"),
                                ("observacao", "Observação"), ("responsavel", "Responsável")):
                linha[nome] = f.get(campo, "")
            df.iloc[indice] = linha
            return df

        alterar_aba("Leite Produção", mudar)
        flash("Ordenha atualizada.", "success")
        return redirect(url_for("painel_leite"))

    df = carregar_aba("Leite Produção")
    if indice < 0 or indice >= len(df):
        abort(404)
    linha = df.iloc[indice].to_dict()
    return render_template("leite_editar.html", linha=linha, indice=indice,
                           hoje=_agora().strftime("%Y-%m-%d"))


@app.route("/leite/excluir/<int:indice>", methods=["POST"])
@login_required
def excluir_ordenha(indice):
    _validar_csrf()
    if indice >= len(carregar_aba("Leite Produção")):
        abort(404)
    fazer_backup()
    _limpar_backups_antigos()
    alterar_aba("Leite Produção", lambda df: df.drop(df.index[indice]).reset_index(drop=True))
    flash("Registro de ordenha excluído.", "warning")
    return redirect(url_for("painel_leite"))


def _periodo_relatorio():
    hoje = _agora().date()
    inicio = _data(request.args.get("inicio")) or hoje.replace(day=1)
    fim = _data(request.args.get("fim")) or hoje
    return inicio, fim


@app.route("/leite/relatorios")
@login_required
def relatorios_leite():
    inicio, fim = _periodo_relatorio()
    df = carregar_aba("Leite Produção")
    serie = serie_diaria(df, inicio, fim)
    total = sum(litros for _, litros in serie)

    # CCS e CPP (Contagem de Células Somáticas e Contagem Padrão de Placa)
    df_filtrado = df.copy()
    df_filtrado["Data"] = pd.to_datetime(df_filtrado.get("Data"), format="%d/%m/%Y", errors="coerce")
    df_filtrado = df_filtrado[(df_filtrado["Data"] >= pd.Timestamp(inicio)) &
                               (df_filtrado["Data"] <= pd.Timestamp(fim))]

    # Série diária de CCS e CPP
    ccs_serie = {}
    cpp_serie = {}
    for _, row in df_filtrado.iterrows():
        data = row.get("Data")
        if pd.isna(data):
            continue
        data_str = data.strftime("%Y-%m-%d")

        # Acumula CCS (média das leituras)
        ccs = row.get("CCS (células/mL)")
        if ccs and str(ccs).strip():
            try:
                ccs_val = float(str(ccs).replace(",", "."))
                if data_str not in ccs_serie:
                    ccs_serie[data_str] = []
                ccs_serie[data_str].append(ccs_val)
            except (ValueError, TypeError):
                pass

        # Acumula CPP
        cpp = row.get("CPP (UFC/mL)")
        if cpp and str(cpp).strip():
            try:
                cpp_val = float(str(cpp).replace(",", "."))
                if data_str not in cpp_serie:
                    cpp_serie[data_str] = []
                cpp_serie[data_str].append(cpp_val)
            except (ValueError, TypeError):
                pass

    # Médias diárias
    ccs_medias = {data: sum(vals) / len(vals) for data, vals in ccs_serie.items()}
    cpp_medias = {data: sum(vals) / len(vals) for data, vals in cpp_serie.items()}

    # Séries ordenadas para o gráfico
    ccs_datas = sorted(ccs_medias.keys())
    ccs_valores = [ccs_medias[d] for d in ccs_datas]
    cpp_datas = sorted(cpp_medias.keys())
    cpp_valores = [cpp_medias[d] for d in cpp_datas]

    return render_template("leite_relatorios.html", inicio=inicio, fim=fim, serie=serie,
                           total=total, por_vaca=producao_por_animal(df, inicio, fim),
                           ccs_datas=ccs_datas, ccs_valores=ccs_valores,
                           cpp_datas=cpp_datas, cpp_valores=cpp_valores)


@app.route("/leite/colchao")
@login_required
def listar_colchao():
    """Listagem de todos os colchões com status de troca."""
    hoje = _agora().date()
    df_colchao = carregar_aba("Leite Colchão")

    historicos = historico_colchao(df_colchao, referencia=hoje)

    # Contar por status
    contadores = {"urgente": 0, "aviso": 0, "ok": 0}
    for hist in historicos.values():
        status = hist.get("status", "ok")
        contadores[status] += 1

    # Montar lista para template (ordenar por dias para troca)
    colchoes = []
    for local, hist in historicos.items():
        if hist and hist.get("ultima_troca"):
            colchoes.append({
                "local": local,
                "material": hist["ultima_troca"].get("material", ""),
                "data_troca": hist["ultima_troca"].get("data"),
                "proxima_troca": hist.get("proxima_troca"),
                "dias_para_troca": hist.get("dias_para_troca"),
                "dias_desde_troca": hist.get("dias_desde_troca"),
                "status": hist.get("status", "ok"),
                "condicao": hist["ultima_troca"].get("condicao", ""),
            })

    # Ordenar: urgentes primeiro, depois aviso, depois ok
    colchoes.sort(key=lambda x: ({"urgente": 0, "aviso": 1, "ok": 2}.get(x["status"], 3),
                                  x.get("dias_para_troca") or 999))

    return render_template("leite_colchao.html", colchoes=colchoes, colchoes_alertas=contadores, hoje=hoje)


@app.route("/leite/relatorios/exportar")
@login_required
def exportar_leite():
    inicio, fim = _periodo_relatorio()
    serie = serie_diaria(carregar_aba("Leite Produção"), inicio, fim)
    wb = Workbook()
    ws = wb.active
    ws.title = "Leite por dia"
    ws.append(["Data", "Litros"])
    for dia, litros in serie:
        ws.append([dia.strftime("%d/%m/%Y"), round(litros, 2)])
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    nome = f"leite_{inicio:%Y%m%d}_{fim:%Y%m%d}.xlsx"
    return send_file(buffer, as_attachment=True, download_name=nome,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/leite/ordenha", methods=["GET", "POST"])
@login_required
def ordenha_leite():
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        dados = {
            "Data": f.get("data"),
            "Vaca ID": f.get("vaca_id", ""),
            "Modo Registro": f.get("modo_registro", ""),
            "Litros": f.get("litros", ""),
        }
        erro = validar_producao(dados)
        if erro:
            flash(erro, "error")
            return redirect(url_for("ordenha_leite"))
        envio = str(f.get("id_envio") or "").strip()
        if envio:
            existente = carregar_aba("Leite Produção")
            if not existente.empty and (existente["ID Envio"].astype(str) == envio).any():
                flash("Ordenha já registrada.", "info")
                return redirect(url_for("painel_leite"))
        modo = str(f.get("modo_registro") or "").strip().lower()
        salvar_linha("Leite Produção", [
            f.get("data", ""), f.get("vaca_id", "") if modo == "individual" else "",
            f.get("brinco", ""), modo, f.get("ordenha", ""), parse_valor(f.get("litros")),
            f.get("ccs", ""), f.get("cpp", ""), f.get("qualidade", ""),
            f.get("temperatura", ""), f.get("observacao", ""), f.get("responsavel", ""),
            envio, _agora().isoformat(timespec="seconds"),
        ])
        flash("Ordenha registrada.", "success")
        return redirect(url_for("painel_leite"))
    return render_template("leite_ordenha.html", hoje=_agora().strftime("%Y-%m-%d"))


@app.route("/leite/comparativo", methods=["GET", "POST"])
@login_required
def comparativo_leite():
    animais = A.carregar()
    vacas_opcoes = []
    for _, animal in animais.iterrows():
        id_animal = str(animal.get("ID", "")).strip()
        brinco = f"{animal.get('Brinco Cor', '')} {animal.get('Brinco Nº', '')}".strip()
        # Célula vazia no Excel chega como NaN (float) — str() evita o .lower() explodir.
        situacao = str(animal.get("Situação Leite") or "").strip().lower()
        if id_animal and situacao in {"lactação", "lactacao"}:
            vacas_opcoes.append({"id": id_animal, "brinco": brinco})

    resultado = {}
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        ids = [str(f.get(f"vaca_{i}", "")).strip() for i in range(1, 4)]
        ids = [v for v in ids if v]
        if ids:
            resultado = _comparar_vacas(ids)

    return render_template("leite_comparativo.html", vacas_opcoes=vacas_opcoes, resultado=resultado)


@app.route("/api/leite/comparativo")
@login_required
def api_comparativo_leite():
    from flask import jsonify
    ids = request.args.get("ids", "").split(",")
    ids = [v.strip() for v in ids if v.strip()]
    if not ids:
        return jsonify({"erro": "Nenhuma vaca informada"}), 400
    return jsonify(_comparar_vacas(ids))


# v5.10 Onda 1 — Mastite Prediction & Health Monitoring
@app.route("/leite/saude")
@login_required
def saude_leite():
    """Dashboard de saúde do leite com alertas de mastite."""
    from mastite_predicao import resumo_saude_leite, gerar_alertas_mastite

    resumo = resumo_saude_leite()
    alertas = gerar_alertas_mastite()

    # Agrupar por tipo
    alertas_urgentes = [a for a in alertas if a['tipo'] == 'urgente']
    alertas_aviso = [a for a in alertas if a['tipo'] == 'aviso']

    return render_template("leite_saude.html",
                          resumo=resumo,
                          alertas_urgentes=alertas_urgentes,
                          alertas_aviso=alertas_aviso)


# v5.8 — Acesso direto a Nutrição e Consumo
@app.route("/leite/consumo")
@login_required
def consumo_leite():
    """Lista consumo de rações e insumos com histórico e monitoramento."""
    df_consumo = carregar_aba("Ração Consumo")

    if df_consumo is None or df_consumo.empty:
        consumos = []
        resumo = {"total_oferecido": 0, "taxa_media": 0, "desperdicio_total": 0, "custo_total": 0}
    else:
        # Últimas 30 registros
        consumos = df_consumo.tail(30).to_dict('records')

        # Resumo geral
        resumo = {
            "total_oferecido": float(df_consumo.get("Quantidade Oferecida (kg)", [0]).sum() or 0),
            "taxa_media": float(df_consumo.get("Taxa Consumo (%)", [0]).mean() or 0),
            "desperdicio_total": float(df_consumo.get("Desperdício (kg)", [0]).sum() or 0),
            "custo_total": float(df_consumo.get("Custo Total Oferecido (R$)", [0]).sum() or 0),
        }

    return render_template("leite_consumo.html",
                          consumos=consumos,
                          resumo=resumo,
                          MEMBROS=MEMBROS,
                          NOMES=NOMES_MEMBROS)


@app.route("/leite/nutricao")
@login_required
def nutricao_leite():
    """Lista necessidades nutricionais por categoria com rastreamento."""
    df_necessidades = carregar_aba("Leite Necessidades")
    df_alimentacao = carregar_aba("Leite Alimentação")

    # Agrupar necessidades por categoria
    necessidades = {}
    if df_necessidades is not None and not df_necessidades.empty:
        for _, linha in df_necessidades.iterrows():
            cat = str(linha.get("Categoria", "Geral")).strip()
            if cat not in necessidades:
                necessidades[cat] = []
            necessidades[cat].append({
                "item": linha.get("Item", ""),
                "valor": linha.get("Valor", ""),
                "unidade": linha.get("Unidade", ""),
                "fonte": linha.get("Fonte", ""),
            })

    # Produtos disponíveis
    produtos = []
    if df_alimentacao is not None and not df_alimentacao.empty:
        for _, linha in df_alimentacao.iterrows():
            produtos.append({
                "produto": linha.get("Produto", ""),
                "proteina": linha.get("Proteína Bruta (%)", ""),
                "energia": linha.get("NDT/Energia (%)", ""),
                "categoria": linha.get("Categoria", ""),
                "consumo": linha.get("Consumo/dia (kg)", ""),
            })

    return render_template("leite_nutricao.html",
                          necessidades=necessidades,
                          produtos=produtos,
                          MEMBROS=MEMBROS,
                          NOMES=NOMES_MEMBROS)
