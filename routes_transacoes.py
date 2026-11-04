#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas unificadas de Comercialização (Compras e Vendas) — Sítio Santo Antonio v5.19
"""
from flask import render_template, request, redirect, url_for, flash
import pandas as pd
from db import carregar_aba, carregar_todas, fazer_backup
from calculos import (
    calcular_estoque, calcular_cmp, calcular_gpcab, custo_medio_movel_venda,
    dividir_cotas,
)
from config import (MEMBROS, NOMES_MEMBROS, COLUNAS_VENDAS, COLUNAS_COMPRAS)
from extensions import (
    app, _agora, _validar_csrf, login_required,
    _get_dados_cache, _get_resumo_cache,
    salvar_linha, reescrever_aba,
    _limpar_backups_antigos,
    fmt_brl, fmt_data, parse_valor, _agora,
)
from routes_registros import (
    _anos_de, _int_form, _data_form, _aplicar_updates,
    _cotas_do_form, gravar_compra, _salvar_venda, _brincos_do_form,
    _brincos_legiveis, _avisar_animais_revertidos
)
import planejamento as PL

@app.route("/transacoes")
@login_required
def transacoes():
    """Página unificada de Comercialização (Compras e Vendas)."""
    dados = _get_dados_cache()
    df_compras = dados.get("Compras", pd.DataFrame())
    df_vendas = dados.get("Vendas", pd.DataFrame())

    filtro = request.args.get("filtro", "todos")
    ano = request.args.get("ano", "")
    busca = request.args.get("busca", "").strip().lower()

    lista = []

    # Processa Compras
    if not df_compras.empty and "Data" in df_compras.columns:
        for real_idx, row in df_compras.iterrows():
            d = row.to_dict()
            dt = d.get("Data")
            if pd.isna(dt):
                continue
            if ano and str(dt.year) != str(ano):
                continue
            desc = str(d.get("Descrição", ""))
            if busca and busca not in desc.lower():
                continue

            # Valores para soma
            val = float(d.get("Valor Total (R$)", 0) or 0)
            cab = int(d.get("Qtd Cabeças", 0) or 0)

            lista.append({
                "tipo": "COMPRA",
                "tipo_cor": "compra",
                "data_ts": dt,
                "data": fmt_data(dt),
                "qtd_cabecas": cab,
                "valor_total": val,
                "valor_cabeca": float(d.get("Valor/Cabeça (R$)", 0) or 0),
                "descricao": desc,
                "registrado_por": d.get("Registrado Por", ""),
                "cotas": {m: int(d.get(f"Qtd {m}", 0) or 0) for m in MEMBROS},
                "valores_socios": {m: float(d.get(f"Valor {m} (R$)", 0) or 0) for m in MEMBROS if f"Valor {m} (R$)" in d},
                "origem": "compras",
                "idx": int(real_idx),
                "editar_url": url_for("editar_compra", idx=int(real_idx)),
                "deletar_url": "#"
            })

    # Processa Vendas
    if not df_vendas.empty and "Data" in df_vendas.columns:
        for real_idx, row in df_vendas.iterrows():
            d = row.to_dict()
            dt = d.get("Data")
            if pd.isna(dt):
                continue
            if ano and str(dt.year) != str(ano):
                continue
            desc = str(d.get("Descrição", ""))
            if busca and busca not in desc.lower():
                continue

            val = float(d.get("Valor Total (R$)", 0) or 0)
            cab = int(d.get("Qtd Cabeças", 0) or 0)

            cotas = {m: int(d.get(f"Qtd {m}", 0) or 0) for m in MEMBROS}
            vals_soc = {m: float(d.get(f"Valor {m} (R$)", 0) or 0) for m in MEMBROS}

            lista.append({
                "tipo": "VENDA",
                "tipo_cor": "venda",
                "data_ts": dt,
                "data": fmt_data(dt),
                "qtd_cabecas": cab,
                "valor_total": val,
                "valor_cabeca": float(d.get("Valor/Cabeça (R$)", 0) or 0),
                "descricao": desc,
                "brincos": _brincos_legiveis(d.get("Brincos", "")),
                "cotas": cotas,
                "valores_socios": vals_soc,
                "origem": "vendas",
                "idx": int(real_idx),
                "editar_url": url_for("editar_venda", idx=int(real_idx)),
                "deletar_url": "#"
            })

    # Ordena por data (mais recente primeiro)
    lista.sort(key=lambda x: x["data_ts"], reverse=True)

    # Filtra por tipo (todos, compras, vendas)
    if filtro == "compras":
        lista = [x for x in lista if x["tipo"] == "COMPRA"]
    elif filtro == "vendas":
        lista = [x for x in lista if x["tipo"] == "VENDA"]

    # Totais para os cards
    total_comprado_val = sum(x["valor_total"] for x in lista if x["tipo"] == "COMPRA")
    total_comprado_cab = sum(x["qtd_cabecas"] for x in lista if x["tipo"] == "COMPRA")

    total_vendido_val = sum(x["valor_total"] for x in lista if x["tipo"] == "VENDA")
    total_vendido_cab = sum(x["qtd_cabecas"] for x in lista if x["tipo"] == "VENDA")

    # Se houver filtro de ano ou tipo aplicado sobre a lista toda para os cards globais:
    # Vamos calcular os globais gerais também para o resumo:
    global_comprado_val = df_compras["Valor Total (R$)"].sum() if not df_compras.empty else 0.0
    global_comprado_cab = df_compras["Qtd Cabeças"].sum() if not df_compras.empty else 0
    global_vendido_val = df_vendas["Valor Total (R$)"].sum() if not df_vendas.empty else 0.0
    global_vendido_cab = df_vendas["Qtd Cabeças"].sum() if not df_vendas.empty else 0
    saldo = global_vendido_val - global_comprado_val

    anos_disponiveis = sorted(list(set(_anos_de(df_compras) + _anos_de(df_vendas))), reverse=True)
    contas_proximas = PL.contas_proximas(carregar_aba("Contas Futuras"), _agora().date())
    for conta in contas_proximas:
        conta["valor_formatado"] = fmt_brl(parse_valor(conta.get("Valor (R$)")))

    return render_template(
        "transacoes.html",
        transacoes=lista,
        filtro=filtro,
        ano_selecionado=ano,
        busca=busca,
        anos_disponiveis=anos_disponiveis,
        total_comprado_val=global_comprado_val,
        total_comprado_cab=global_comprado_cab,
        total_vendido_val=global_vendido_val,
        total_vendido_cab=global_vendido_cab,
        saldo=saldo,
        contas_proximas=contas_proximas,
        MEMBROS=MEMBROS,
        NOMES=NOMES_MEMBROS,
        fmt_brl=fmt_brl
    )
