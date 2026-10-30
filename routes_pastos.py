#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas dos Pastos com mapa — Sítio Santo Antonio v5.2
"""
import json

import pandas as pd
from flask import render_template, request, redirect, url_for, flash

import animais as A
import pastos as PA
import pesagem as P
from calculos import calcular_estoque
from extensions import (app, _agora, _validar_csrf, login_required, _get_dados_cache,
                        _ler_sitio_config_disco)
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
    animais_por_pasto = {}
    if df_manejo.empty or "Pasto" not in df_manejo.columns:
        return animais_por_pasto

    # Dicionário de cores por dono (de df_animais se disponível)
    dono_cores = {}
    if df_animais is not None and not df_animais.empty:
        for _, animal in df_animais.iterrows():
            partes = []
            for campo in ("Brinco Cor", "Brinco Nº"):
                valor = animal.get(campo, "")
                if pd.notna(valor) and str(valor).strip().lower() != "nan":
                    partes.append(str(valor).strip())
            brinco = " ".join(partes)
            cor = animal.get("Cor Dono", "#999")
            if brinco:
                dono_cores[brinco] = cor

    # Últimas movimentações de pasto
    df_mov = df_manejo[df_manejo["Pasto"].notna() & (df_manejo["Pasto"] != "")].copy()
    if df_mov.empty:
        return animais_por_pasto

    for pasto_id, grup in df_mov.groupby("Pasto"):
        if "Brincos" in grup.columns:
            brincos_set = set()
            for _, row in grup.sort_values("Data", ascending=False, na_position="last").iterrows():
                brincos_str = str(row.get("Brincos", "")).strip()
                if brincos_str and brincos_str != "":
                    for brinco in brincos_str.split(","):
                        brinco_limpo = brinco.strip().split("#")[0].strip()
                        if brinco_limpo and brinco_limpo.lower() != "nan":
                            brincos_set.add(brinco_limpo)
            if brincos_set:
                brincos_list = sorted(list(brincos_set))
                dados = [{"brinco": b, "cor": dono_cores.get(b, "#999")} for b in brincos_list]
                animais_por_pasto[pasto_id] = {
                    "brincos": brincos_list,
                    "dados": dados,
                    "total": len(brincos_list)
                }

    return animais_por_pasto

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
                           hoje=pd.Timestamp(_agora()).strftime("%Y-%m-%d"))


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
