#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas dos Pastos com mapa — Sítio Santo Antonio v5.2
"""
import json
import math

import pandas as pd
from flask import render_template, request, redirect, url_for, flash

import animais as A
import pastos as PA
import pastos_ms as PMS
import pesagem as P
import planejamento as PL
import db
from calculos import calcular_estoque
from extensions import (app, _agora, _validar_csrf, login_required, _get_dados_cache,
                        _ler_sitio_config_disco, parse_valor, fmt_brl)
from routes_animais import _membro_logado, fazer_backup_seguro


def _peso_medio(df_animais, df_man) -> float:
    """Pesados → Configurações → 0 (o pastos.situacao usa 450 kg)."""
    medio = P.peso_medio_vivos(df_animais, df_man)[0]
    if medio > 0:
        return medio
    try:
        return float(_ler_sitio_config_disco().get("peso_medio", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _capacidade_ua_ha() -> float:
    """UA/ha que o pasto suporta (Configurações → Rebanho). 0 = sem semáforo."""
    try:
        return float(_ler_sitio_config_disco().get("capacidade_ua_ha", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _grafico_ocupacao_pastos(df_pastos, df_animais, df_manejo):
    """Gráfico barras: Ocupação por pasto (UA/ha vs capacidade ideal).

    Onda 8.4.1 — Pastos
    """
    try:
        import pastos as PA
        sit = PA.situacao(df_pastos, df_animais, df_manejo, 0, 0)
        if not sit:
            return None

        labels = []
        data = []
        capacidade = _capacidade_ua_ha()

        for pasto_id, pasto_sit in sit.items():
            ua_ha = pasto_sit.get("ua_ha", 0)
            labels.append(pasto_id[:15])  # Trunca se muito longo
            data.append(ua_ha)

        if not labels:
            return None

        return {"labels": labels, "data": data, "capacidade": capacidade}
    except Exception as e:
        app.logger.debug(f"Gráfico ocupação pastos falhou: {e}")
        return None


def _grafico_evolucao_lotacao(df_manejo):
    """Gráfico área: Evolução lotação últimos 30 dias.

    Onda 8.4.2 — Pastos
    """
    try:
        from datetime import timedelta
        hoje = _agora().date()
        inicio = hoje - timedelta(days=30)

        lotacao_dia = {}

        for _, row in df_manejo.iterrows():
            try:
                data = pd.to_datetime(row.get("Data")).date()
                if data < inicio or pd.isna(data):
                    continue
                data_str = data.isoformat()
                if data_str not in lotacao_dia:
                    lotacao_dia[data_str] = 0
                # Conta cabeças (assume 1 cab por linha de manejo)
                lotacao_dia[data_str] += 1
            except Exception:
                pass

        if not lotacao_dia:
            return None

        datas = sorted(lotacao_dia.keys())
        labels = [pd.to_datetime(d).strftime("%d/%m") for d in datas]
        data = [lotacao_dia[d] for d in datas]

        return {"labels": labels, "data": data}
    except Exception as e:
        app.logger.debug(f"Gráfico evolução lotação falhou: {e}")
        return None


def _calcular_centroid(geojson):
    """Calcula centroid de um polígono GeoJSON."""
    try:
        if geojson.get("type") == "Polygon":
            coords = geojson.get("coordinates", [[]])[0]  # Exterior ring
            if not coords:
                return None
            lat_sum = sum(c[1] for c in coords)
            lng_sum = sum(c[0] for c in coords)
            return [lat_sum / len(coords), lng_sum / len(coords)]
    except:
        pass
    return None


def _extrair_animais_por_pasto(df_manejo, df_animais=None):
    """Extrai animais registrados em cada pasto com dados enriquecidos.

    Retorna dict: {pasto_id: {"brincos": [...], "dados": [{brinco, dono_cor}, ...]}}
    """
    return {
        pasto_id: {
            "brincos": [animal["brinco"] for animal in animais],
            "dados": animais,
            "total": len(animais),
        }
        for pasto_id, animais in PA.animais_por_pasto(df_manejo, df_animais).items()
    }

@app.route("/pastos")
@login_required
def pastos():
    dados = _get_dados_cache()
    df_p, df_a = PA.carregar(), A.carregar()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    sit = PA.situacao(df_p, df_a, dados["Manejo"], estoque,
                      _peso_medio(df_a, dados["Manejo"]), hoje=_agora())
    capacidade = _capacidade_ua_ha()

    # Extrai animais por pasto (enriquecido com cores de dono)
    animais_por_pasto = _extrair_animais_por_pasto(dados["Manejo"], df_a)

    lista = []
    for _, p in PA.ativos(df_p).iterrows():
        geo = json.loads(p["Contorno"])
        centroid = _calcular_centroid(geo)
        animais_info = animais_por_pasto.get(p["ID"], {})

        lista.append({
            "id": p["ID"],
            "nome": p["Nome"],
            "area": float(p["Área (ha)"]),
            "cor": p["Cor"],
            "geo": geo,
            "centroid": centroid,
            **sit[p["ID"]],
            "nivel": PA.nivel(sit[p["ID"]]["ua_ha"], capacidade),
            "animais": animais_info.get("brincos", []),
            "animais_dados": animais_info.get("dados", []),
            "total_animais": animais_info.get("total", 0)
        })

    return render_template("pastos.html", pastos=lista, sem_pasto=sit[None],
                           capacidade=capacidade, composicao=A.composicao(df_a, estoque),
                           grafico_ocupacao=_grafico_ocupacao_pastos(df_p, df_a, dados["Manejo"]),
                           grafico_evolucao=_grafico_evolucao_lotacao(dados["Manejo"]),
                           hoje=pd.Timestamp(_agora()).strftime("%Y-%m-%d"))


@app.route("/pastos/medicoes", methods=["GET", "POST"])
@login_required
def medicoes_pastos():
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        try:
            estimativa = PMS.registrar(
                f.get("pasto_id"), f.get("data"), f.get("altura"),
                f.get("coeficiente"), f.get("observacoes", ""), _membro_logado(),
            )
            flash(
                f"Medição registrada: {estimativa['altura_cm']:g} cm; "
                f"MS estimada em {estimativa['ms_kg_ha']:g} kg/ha.",
                "success",
            )
        except ValueError as e:
            flash(str(e), "error")
        return redirect(url_for("medicoes_pastos"))

    df = PMS.carregar()
    if not df.empty:
        df = df.sort_values("Data", ascending=False, na_position="last")
    return render_template(
        "pastos_medicoes.html",
        pastos=PA.ativos(PA.carregar()).to_dict("records"),
        coeficientes=PMS.coeficientes_atuais(),
        medicoes=df.head(50).to_dict("records"),
        hoje=_agora().strftime("%Y-%m-%d"),
    )


@app.route("/pastos/novo", methods=["POST"])
@login_required
def novo_pasto():
    _validar_csrf()
    try:
        PA.criar(request.form.get("nome"), request.form.get("contorno", ""), _membro_logado())
        flash("🗺️ Pasto salvo!", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("pastos"))


@app.route("/pastos/novo-simples", methods=["POST"])
@login_required
def novo_pasto_simples():
    _validar_csrf()
    try:
        nome = request.form.get("nome")
        area = float(request.form.get("area_ha", 0))
        PA.criar_simples(nome, area, _membro_logado())
        flash(f"✅ Pasto {nome} criado!", "success")
    except Exception as e:
        flash(f"Erro: {str(e)}", "error")
    return redirect(url_for("pastos"))


@app.route("/pastos/importar-kmz", methods=["POST"])
@login_required
def importar_kmz():
    _validar_csrf()
    arquivo = request.files.get("arquivo_kmz")
    if not arquivo or not arquivo.filename:
        flash("Selecione um arquivo .kmz ou .kml para enviar.", "error")
        return redirect(url_for("pastos"))
    nome = arquivo.filename.lower()
    if not (nome.endswith(".kmz") or nome.endswith(".kml")):
        flash("Formato não suportado. Envie um arquivo .kmz ou .kml.", "error")
        return redirect(url_for("pastos"))
    try:
        conteudo = arquivo.read()
        if len(conteudo) > 15 * 1024 * 1024:
            flash("Arquivo muito grande (máximo 15 MB).", "error")
            return redirect(url_for("pastos"))
        fazer_backup_seguro()
        criados = PA.importar_kmz(conteudo, arquivo.filename, _membro_logado())
        total_ha = sum(p["area"] for p in criados)
        flash(f"🗺️ {len(criados)} pasto(s) importado(s) com sucesso ({total_ha:.2f} ha no total)!", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        flash(f"Erro ao processar arquivo KMZ: {e}", "error")
    return redirect(url_for("pastos"))


@app.route("/pastos/<id_>/editar", methods=["POST"])
@login_required
def editar_pasto(id_):
    _validar_csrf()
    f = request.form
    try:
        fazer_backup_seguro()
        PA.editar(id_, nome=f.get("nome"), contorno_json=f.get("contorno") or None)
        flash("Pasto atualizado.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("pastos"))


@app.route("/pastos/<id_>/excluir", methods=["POST"])
@login_required
def excluir_pasto(id_):
    _validar_csrf()
    try:
        fazer_backup_seguro()
        PA.excluir(id_)
        flash("Pasto excluído do mapa (o histórico continua no Manejo).", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("pastos"))


@app.route("/pastos/mover", methods=["POST"])
@login_required
def mover_gado():
    _validar_csrf()
    f = request.form
    dados = _get_dados_cache()
    refs = None
    if f.get("quem") != "todos":
        refs, erros = A.resolver_texto(f.get("brincos", ""))
        if erros or not refs:
            flash("; ".join(erros) or "Diga quais brincos vão mudar de pasto.", "error")
            return redirect(url_for("pastos"))
    try:
        PA.mover(f.get("pasto"), f.get("data"), refs,
                 calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"]),
                 _membro_logado())
        flash("🐄 Gado movido!", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("pastos"))


@app.route("/pastos/aplicacoes", methods=["GET", "POST"])
@login_required
def aplicacoes_pastos():
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        try:
            data = PL.normalizar_data(f.get("data"))
            pastos_ativos = PA.ativos(PA.carregar())
            pasto_id = (f.get("pasto_id") or "").strip()
            pasto = pastos_ativos[pastos_ativos["ID"].astype(str) == pasto_id]
            tipo_insumo = (f.get("tipo_insumo") or "").strip()
            produto = (f.get("produto") or "").strip()
            unidade = (f.get("unidade") or "").strip()
            quantidade = parse_valor(f.get("quantidade"))
            custo = parse_valor(f.get("custo"))
            if pd.isna(data):
                raise ValueError("Informe uma data válida.")
            if pasto.empty:
                raise ValueError("Selecione um pasto ativo.")
            if tipo_insumo not in PL.TIPOS_INSUMO_PASTO:
                raise ValueError("Selecione um tipo de insumo válido.")
            if not produto:
                raise ValueError("Informe o produto aplicado.")
            if (not math.isfinite(quantidade) or not math.isfinite(custo)
                    or quantidade <= 0 or custo <= 0):
                raise ValueError("Quantidade e custo total devem ser maiores que zero.")
            if unidade not in PL.UNIDADES_INSUMO:
                raise ValueError("Selecione uma unidade válida.")

            app_id = PL.novo_id("AP")
            responsavel = (f.get("responsavel") or _membro_logado()).strip()
            categoria_gasto = {
                "Calcário": "Calcário/Adubação",
                "Ureia": "Calcário/Adubação",
                "Superfosfato": "Calcário/Adubação",
                "Defensivo": "Veneno/Defensivo",
                "Outro": "Manutenção/Outros",
            }[tipo_insumo]
            categoria_financeira = "Sanidade" if tipo_insumo == "Defensivo" else (
                "Manutenção" if tipo_insumo == "Outro" else "Nutrição")
            descricao = f"Aplicação em {pasto_id}: {tipo_insumo} — {produto} (#{app_id})"
            dados = _get_dados_cache()
            cabecas = calcular_estoque(
                dados["Compras"], dados["Vendas"], dados["Manejo"]
            )
            cabecas = max(1, cabecas)
            data_iso = data.strftime("%Y-%m-%d")
            linha_aplicacao = [
                app_id, data_iso, pasto_id, tipo_insumo, produto, quantidade,
                unidade, custo, responsavel,
            ]
            linha_gasto = [
                data_iso, categoria_gasto, descricao, custo, cabecas,
                round(custo / cabecas, 4), responsavel, "", None, pasto_id, app_id,
                categoria_financeira,
            ]
            fazer_backup_seguro()
            db.salvar_linhas_atomicas({
                "Pastos Aplicações": [linha_aplicacao],
                "Gastos": [linha_gasto],
            })
            flash("Aplicação registrada e vinculada aos Gastos.", "success")
            return redirect(url_for("aplicacoes_pastos"))
        except ValueError as e:
            flash(str(e), "error")
        except Exception as e:
            app.logger.exception("Falha ao salvar aplicação de pasto e gasto vinculado")
            flash(f"Erro ao registrar aplicação: {e}", "error")
        return redirect(url_for("aplicacoes_pastos"))

    df_pastos = PA.carregar()
    df_aplicacoes = db.carregar_aba("Pastos Aplicações")
    aplicacoes = PL.listar_aplicacoes(df_aplicacoes, df_pastos)
    total_custo = sum(parse_valor(a.get("Custo Total (R$)")) for a in aplicacoes)
    return render_template(
        "pastos_aplicacoes.html",
        pastos=PA.ativos(df_pastos).to_dict("records") if not df_pastos.empty else [],
        aplicacoes=aplicacoes,
        tipos_insumo=PL.TIPOS_INSUMO_PASTO,
        unidades=PL.UNIDADES_INSUMO,
        total_custo=total_custo,
        hoje=_agora().strftime("%Y-%m-%d"),
        responsavel=_membro_logado(),
        fmt_brl=fmt_brl,
    )


@app.route("/estoque")
@login_required
def estoque_animais():
    """Exibe animais no rebanho com indicação de em qual pasto estão (mapa com pins)."""
    dados = _get_dados_cache()
    df_p, df_a = PA.carregar(), A.carregar()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    sit = PA.situacao(df_p, df_a, dados["Manejo"], estoque,
                      _peso_medio(df_a, dados["Manejo"]), hoje=_agora())
    capacidade = _capacidade_ua_ha()

    # Pastos com informações de lotação
    pastos_lista = [{"id": p["ID"], "nome": p["Nome"], "area": float(p["Área (ha)"]), "cor": p["Cor"],
                      "geo": json.loads(p["Contorno"]), **sit[p["ID"]],
                      "nivel": PA.nivel(sit[p["ID"]]["ua_ha"], capacidade)}
                     for _, p in PA.ativos(df_p).iterrows()]

    # Animais por pasto (para contar cabeças)
    animais_por_pasto = PA.animais_por_pasto(dados["Manejo"], df_a)

    # Contagem de cabeças por pasto
    contagem = {pasto_id: len(animais) for pasto_id, animais in animais_por_pasto.items()}

    # Adiciona contagem aos dados dos pastos
    for p in pastos_lista:
        p["contagem"] = contagem.get(p["id"], 0)

    return render_template("estoque.html", pastos=pastos_lista,
                           capacidade=capacidade,
                           composicao=A.composicao(df_a, estoque),
                           sem_pasto=sit[None],
                           hoje=pd.Timestamp(_agora()).strftime("%Y-%m-%d"))


@app.route("/api/pastos/animais")
@login_required
def api_pastos_animais():
    """Retorna lista de animais por pasto para mostrar no mapa.
    JSON: {pasto_id: [{id, brinco, nome, cor}, ...], ...}"""
    from flask import jsonify
    dados = _get_dados_cache()
    df_a = A.carregar()
    animais = PA.animais_por_pasto(dados["Manejo"], df_a)
    return jsonify(animais), 200
