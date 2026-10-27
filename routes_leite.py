# -*- coding: utf-8 -*-
"""Rotas iniciais do módulo leiteiro."""

from datetime import timedelta
from io import BytesIO

from flask import abort, flash, redirect, render_template, request, send_file, url_for
from openpyxl import Workbook

import animais as A
from config import COLUNAS_LEITE_COLCHAO, COLUNAS_LEITE_CONFORTO, COLUNAS_LEITE_TRATAMENTOS
from db import alterar_aba, carregar_aba, fazer_backup
from extensions import _agora, _limpar_backups_antigos, _validar_csrf, app, login_required, salvar_linha, parse_valor
from leite import _data, _numero, acumulados, contagens_rebanho, dias_em_lactacao, medias_periodo, producao_por_animal, serie_diaria, validar_producao, historico_colchao
from comparativo import comparar_vacas


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

    # Alertas de colchão: conta urgentes e avisos
    df_colchao = carregar_aba("Leite Colchão")
    colchoes_alertas = {"urgente": 0, "aviso": 0, "ok": 0}
    if df_colchao is not None and not df_colchao.empty:
        historicos = historico_colchao(df_colchao, referencia=hoje)
        for hist in historicos.values():
            status = hist.get("status", "ok")
            colchoes_alertas[status] += 1

    return render_template("leite.html", acumulado=acumulado, medias=medias,
                           contagens=contagens, registros=len(df), hoje=hoje,
                           colchoes_alertas=colchoes_alertas)


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
    if not df_producao.empty:
        registros = df_producao[df_producao.get("Vaca ID", "").astype(str).str.strip() == str(animal_id).strip()]
        for _, registro in registros.iterrows():
            data = _data(registro.get("Data"))
            litros = _numero(registro.get("Litros"))
            if data is not None and litros is not None:
                historico.append({"data": data, "litros": litros, "ordenha": registro.get("Ordenha", "")})
        historico.sort(key=lambda item: item["data"], reverse=True)
    carencias = []
    df_tratamentos = carregar_aba("Leite Tratamentos")
    if not df_tratamentos.empty:
        for _, tratamento in df_tratamentos.iterrows():
            if str(tratamento.get("Vaca ID", "")).strip() != str(animal_id).strip():
                continue
            inicio = _data(tratamento.get("Data"))
            dias = _numero(tratamento.get("Período de Carência"))
            if inicio and dias and dias > 0 and inicio <= hoje < inicio + timedelta(days=int(dias)):
                carencias.append({"descricao": tratamento.get("Descrição") or "Tratamento", "fim": inicio + timedelta(days=int(dias))})
    parto = linha.get("Último Parto", "")
    return render_template("leite_animal.html", animal={
        "id": animal_id,
        "brinco": f"{linha.get('Brinco Cor', '')} {linha.get('Brinco Nº', '')}".strip(),
        "situacao": linha.get("Situação Leite", "não informado"),
        "parto": parto,
        "dias": dias_em_lactacao(parto, hoje),
    }, historico=historico, total=sum(item["litros"] for item in historico), carencias=carencias)


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
        salvar_linha("Leite Alimentação", [
            produto, f.get("fabricante", ""), f.get("categoria", ""), f.get("peso_saco", ""),
            f.get("proteina", ""), f.get("ndt", ""), f.get("fibra", ""), f.get("calcio", ""),
            f.get("fosforo", ""), f.get("consumo", ""), f.get("preco", ""), f.get("lote", ""),
            f.get("validade", ""), f.get("observacao", ""), "Sim",
        ])
        flash("Produto leiteiro cadastrado.", "success")
        return redirect(url_for("alimentacao_leite"))
    df = carregar_aba("Leite Alimentação")
    produtos = []
    for _, linha in df.iterrows():
        produtos.append({"produto": linha.get("Produto", ""), "proteina": linha.get("Proteína Bruta (%)", ""), "ndt": linha.get("NDT/Energia (%)", "")})
    return render_template("leite_alimentacao.html", produtos=produtos)


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
            {"nome": "observacao", "label": "Observação", "required": False},
            {"nome": "responsavel", "label": "Responsável", "required": False},
            {"nome": "id_envio", "label": "", "required": False},
        ], ["local", "sombra", "agua", "ventilacao", "area_descanso", "lotacao", "estresse", "descanso", "observacao", "responsavel", "id_envio", "criado_em"]),
        "colchao": ("Leite Colchão", "Colchão", [
            {"nome": "local", "label": "Local", "required": True},
            {"nome": "material", "label": "Material", "required": True},
            {"nome": "quantidade", "label": "Quantidade", "required": False},
            {"nome": "unidade", "label": "Unidade", "required": False},
            {"nome": "custo", "label": "Custo (R$)", "required": False},
            {"nome": "fornecedor", "label": "Fornecedor", "required": False},
            {"nome": "condicao", "label": "Condição", "required": True},
            {"nome": "proxima_troca", "label": "Próxima troca", "required": False},
            {"nome": "observacao", "label": "Observação", "required": False},
            {"nome": "foto_antes", "label": "Foto antes", "required": False},
            {"nome": "foto_depois", "label": "Foto depois", "required": False},
            {"nome": "responsavel", "label": "Responsável", "required": False},
            {"nome": "id_envio", "label": "", "required": False},
        ], ["local", "material", "quantidade", "unidade", "custo", "fornecedor", "condicao", "proxima_troca", "observacao", "foto_antes", "foto_depois", "responsavel", "id_envio", "criado_em"]),
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
    return render_template("leite_relatorios.html", inicio=inicio, fim=fim, serie=serie,
                           total=total, por_vaca=producao_por_animal(df, inicio, fim))


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
        situacao = animal.get("Situação Leite", "")
        if id_animal and situacao and situacao.lower() in {"lactação", "lactacao"}:
            vacas_opcoes.append({"id": id_animal, "brinco": brinco})

    resultado = {}
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        ids = [str(f.get(f"vaca_{i}", "")).strip() for i in range(1, 4)]
        ids = [v for v in ids if v]
        if ids:
            resultado = comparar_vacas(ids)

    return render_template("leite_comparativo.html", vacas_opcoes=vacas_opcoes, resultado=resultado)


@app.route("/api/leite/comparativo")
@login_required
def api_comparativo_leite():
    from flask import jsonify
    ids = request.args.get("ids", "").split(",")
    ids = [v.strip() for v in ids if v.strip()]
    if not ids:
        return jsonify({"erro": "Nenhuma vaca informada"}), 400
    return jsonify(comparar_vacas(ids))
