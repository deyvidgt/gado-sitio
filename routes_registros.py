#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas de Compras, Gastos, Vendas, Manejo, Excluir — Sítio Santo Antonio
Gerado automaticamente — não editar diretamente.
"""
from flask import render_template, request, redirect, url_for, flash, session, send_file, jsonify
import os, tempfile
import pandas as pd
from datetime import datetime, timedelta
from db import carregar_aba, carregar_todas, inicializar, fazer_backup
from calculos import (
    calcular_estoque, calcular_resumo_financeiro, calcular_todos_membros,
    calcular_fluxo_caixa, calcular_cmp_ate_data, calcular_gpcab_ate_data,
    calcular_cmp, calcular_gpcab, calcular_estoque_por_membro,
    calcular_indicadores_extras, calcular_gasto_por_tipo, calcular_evolucao_cmp,
)
from config import (TIPOS_GASTO, TIPOS_MANEJO, MEMBROS, NOMES_MEMBROS,
                    EMOJIS_MEMBROS, OPCOES_VISITA)
from extensions import (
    app, _agora, _validar_csrf, login_required,
    _get_dados_cache, _get_resumo_cache,
    salvar_linha, reescrever_aba,
    _fazer_backup_inteligente, _limpar_backups_antigos,
    _carregar_usuarios, _salvar_usuarios,
    _sha256, _hash_bcrypt, _bcrypt_disponivel, _verificar_hash,
    fmt_brl, fmt_data, parse_valor,
    _gerar_alertas, _calc_anual, BASE_DIR,
)

# ══════════════════════════════════════════════════════════════════════════════

@app.route("/compras")
@login_required
def compras():
    dados = _get_dados_cache()
    df = dados["Compras"]
    ordem = request.args.get("ordem", "desc")
    if not df.empty and "Data" in df.columns:
        df = df.sort_values("Data", ascending=(ordem == "asc"), na_position="last")
    rows = []
    for real_idx, row in (df.iterrows() if not df.empty else []):
        d = row.to_dict()
        d["Data"] = fmt_data(d.get("Data"))
        d["_idx"] = int(real_idx)
        rows.append(d)
    return render_template("lista.html", titulo="Compras 🛒", secao="compras", aba="Compras",
                           colunas=["Data","Qtd Cabeças","Valor Total (R$)","Valor/Cabeça (R$)",
                                    "Qtd Mae","Qtd Deyvid","Qtd Nilson","Descrição","Registrado Por"],
                           rows=rows, ordem=ordem)

@app.route("/compras/nova", methods=["GET", "POST"])
@login_required
def nova_compra():
    dados = _get_dados_cache()
    cmp_atual = calcular_cmp(dados["Compras"])
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        data    = f.get("data", _agora().strftime("%d/%m/%Y"))
        cabecas = int(f.get("cabecas", 0) or 0)
        valor   = parse_valor(f.get("valor", 0))
        desc    = f.get("descricao", "").strip()
        membro  = f.get("membro", "")
        if cabecas <= 0:
            flash("Informe ao menos 1 cabeça.", "error")
            return redirect(url_for("nova_compra"))
        qtd_mae    = int(f.get("qtd_mae",    0) or 0)
        qtd_deyvid = int(f.get("qtd_deyvid", 0) or 0)
        qtd_nilson = int(f.get("qtd_nilson", 0) or 0)
        soma = qtd_mae + qtd_deyvid + qtd_nilson
        if soma == 0:
            base = cabecas // 3
            qtd_mae = qtd_deyvid = base
            qtd_nilson = cabecas - base * 2
        elif soma != cabecas:
            fator = cabecas / soma
            qtd_mae    = round(qtd_mae    * fator)
            qtd_deyvid = round(qtd_deyvid * fator)
            qtd_nilson = cabecas - qtd_mae - qtd_deyvid
        val_cab = round(valor / cabecas, 2) if cabecas > 0 else 0
        salvar_linha("Compras", [data, cabecas, valor, val_cab, qtd_mae, qtd_deyvid, qtd_nilson, desc, membro])
        flash(f"Compra registrada! {cabecas} cabeças por {fmt_brl(valor)}", "success")
        return redirect(url_for("compras"))
    return render_template("form_compra.html", modo="nova", cmp_atual=cmp_atual,
                           row=None, idx=None, MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))

@app.route("/compras/editar/<int:idx>", methods=["GET", "POST"])
@login_required
def editar_compra(idx):
    df = carregar_aba("Compras")
    if df.empty or idx >= len(df):
        flash("Registro não encontrado.", "error")
        return redirect(url_for("compras"))
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        data    = f.get("data", "")
        cabecas = int(f.get("cabecas", 0) or 0)
        valor   = parse_valor(f.get("valor", 0))
        desc    = f.get("descricao", "").strip()
        membro  = f.get("membro", "")
        if cabecas <= 0:
            flash("Informe ao menos 1 cabeça.", "error")
            return redirect(url_for("editar_compra", idx=idx))
        qtd_mae    = int(f.get("qtd_mae",    0) or 0)
        qtd_deyvid = int(f.get("qtd_deyvid", 0) or 0)
        qtd_nilson = int(f.get("qtd_nilson", 0) or 0)
        soma = qtd_mae + qtd_deyvid + qtd_nilson
        if soma == 0:
            base = cabecas // 3
            qtd_mae = qtd_deyvid = base
            qtd_nilson = cabecas - base * 2
        elif soma != cabecas:
            fator = cabecas / soma
            qtd_mae    = round(qtd_mae    * fator)
            qtd_deyvid = round(qtd_deyvid * fator)
            qtd_nilson = cabecas - qtd_mae - qtd_deyvid
        val_cab = round(valor / cabecas, 2) if cabecas > 0 else 0
        fazer_backup()
        _limpar_backups_antigos()
        updates = {"Data": pd.to_datetime(data, dayfirst=True, errors="coerce"),
                   "Qtd Cabeças": cabecas, "Valor Total (R$)": valor,
                   "Valor/Cabeça (R$)": val_cab, "Qtd Mae": qtd_mae,
                   "Qtd Deyvid": qtd_deyvid, "Qtd Nilson": qtd_nilson,
                   "Descrição": desc, "Registrado Por": membro}
        for col, val in updates.items():
            if col in df.columns:
                df.at[idx, col] = val
            else:
                df[col] = None; df.at[idx, col] = val
        reescrever_aba("Compras", df)
        flash("Compra atualizada!", "success")
        return redirect(url_for("compras"))
    row = df.iloc[idx].to_dict()
    row["Data"] = fmt_data(row.get("Data"))
    row["data_input"] = df.iloc[idx]["Data"].strftime("%Y-%m-%d") if pd.notna(df.iloc[idx]["Data"]) else ""
    # Fix: coluna correta para o template
    row["Qtd Geane"] = row.get("Qtd Mae", 0)
    return render_template("form_compra.html", modo="editar", row=row, idx=idx,
                           cmp_atual=calcular_cmp(df), MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))


# ══════════════════════════════════════════════════════════════════════════════
#  GASTOS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/gastos")
@login_required
def gastos():
    dados = _get_dados_cache()
    df = dados["Gastos"]
    ordem = request.args.get("ordem", "desc")
    if not df.empty and "Data" in df.columns:
        df = df.sort_values("Data", ascending=(ordem == "asc"), na_position="last")
    rows = []
    for real_idx, row in (df.iterrows() if not df.empty else []):
        d = row.to_dict()
        d["Data"] = fmt_data(d.get("Data"))
        d["_idx"] = int(real_idx)
        rows.append(d)
    return render_template("lista.html", titulo="Gastos 💸", secao="gastos", aba="Gastos",
                           colunas=["Data","Tipo","Descrição","Valor Total (R$)",
                                    "Qtd Cabeças","Valor/Cabeça (R$)","Registrado Por"],
                           rows=rows, ordem=ordem)

@app.route("/gastos/novo", methods=["GET", "POST"])
@login_required
def novo_gasto():
    dados = _get_dados_cache()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    gpcab   = calcular_gpcab(dados["Gastos"], dados["Compras"], dados["Vendas"], dados["Manejo"])
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        data   = f.get("data", _agora().strftime("%d/%m/%Y"))
        tipo   = f.get("tipo", "")
        desc   = f.get("descricao", "").strip()
        valor  = parse_valor(f.get("valor", 0))
        cab    = int(f.get("cabecas", estoque) or estoque)
        membro = f.get("membro", "")
        if cab <= 0:
            cab = max(1, estoque)
        v_cab = round(valor / cab, 4) if cab > 0 else 0
        salvar_linha("Gastos", [data, tipo, desc, valor, cab, v_cab, membro])
        flash(f"Gasto registrado! {fmt_brl(valor)} ({tipo})", "success")
        return redirect(url_for("gastos"))
    return render_template("form_gasto.html", estoque=estoque, gpcab=gpcab,
                           TIPOS=TIPOS_GASTO, MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))

@app.route("/gastos/editar/<int:idx>", methods=["GET", "POST"])
@login_required
def editar_gasto(idx):
    dados   = _get_dados_cache()
    df      = carregar_aba("Gastos")
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    gpcab   = calcular_gpcab(dados["Gastos"], dados["Compras"], dados["Vendas"], dados["Manejo"])
    if df.empty or idx >= len(df):
        flash("Registro não encontrado.", "error")
        return redirect(url_for("gastos"))
    if request.method == "POST":
        _validar_csrf()
        f      = request.form
        data   = f.get("data", "")
        tipo   = f.get("tipo", "")
        desc   = f.get("descricao", "").strip()
        valor  = parse_valor(f.get("valor", 0))
        cab    = int(f.get("cabecas", estoque) or estoque)
        membro = f.get("membro", "")
        if cab <= 0:
            cab = max(1, estoque)
        v_cab = round(valor / cab, 4) if cab > 0 else 0
        fazer_backup()
        _limpar_backups_antigos()
        updates = {"Data": pd.to_datetime(data, dayfirst=True, errors="coerce"),
                   "Tipo": tipo, "Descrição": desc,
                   "Valor Total (R$)": valor, "Qtd Cabeças": cab,
                   "Valor/Cabeça (R$)": v_cab, "Registrado Por": membro}
        for col, val in updates.items():
            if col in df.columns:
                df.at[idx, col] = val
            else:
                df[col] = None; df.at[idx, col] = val
        reescrever_aba("Gastos", df)
        flash("Gasto atualizado!", "success")
        return redirect(url_for("gastos"))
    row = df.iloc[idx].to_dict()
    row["Data"] = fmt_data(row.get("Data"))
    row["data_input"] = df.iloc[idx]["Data"].strftime("%Y-%m-%d") if pd.notna(df.iloc[idx].get("Data")) else ""
    return render_template("form_gasto.html", modo="editar", row=row, idx=idx,
                           estoque=estoque, gpcab=gpcab,
                           TIPOS=TIPOS_GASTO, MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))


# ══════════════════════════════════════════════════════════════════════════════
#  VENDAS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/vendas")
@login_required
def vendas():
    dados = _get_dados_cache()
    df = dados["Vendas"]
    ordem = request.args.get("ordem", "desc")
    if not df.empty and "Data" in df.columns:
        df = df.sort_values("Data", ascending=(ordem == "asc"), na_position="last")
    rows = []
    for real_idx, row in (df.iterrows() if not df.empty else []):
        d = row.to_dict()
        d["Data"] = fmt_data(d.get("Data"))
        d["_idx"] = int(real_idx)
        rows.append(d)
    return render_template("lista.html", titulo="Vendas 🤝", secao="vendas", aba="Vendas",
                           colunas=["Data","Qtd Cabeças","Valor Total (R$)","Valor/Cabeça (R$)",
                                    "Valor Arroba (R$)","Qtd Mae","Qtd Deyvid","Qtd Nilson",
                                    "Valor Mae (R$)","Valor Deyvid (R$)","Valor Nilson (R$)","Descrição"],
                           rows=rows, ordem=ordem)

@app.route("/vendas/nova", methods=["GET", "POST"])
@login_required
def nova_venda():
    dados = _get_dados_cache()
    r_fin = _get_resumo_cache()
    if request.method == "POST":
        _validar_csrf()
        cabecas = int(request.form.get("cabecas", 0) or 0)
        if cabecas <= 0:
            flash("Informe ao menos 1 cabeça.", "error")
            return redirect(url_for("nova_venda"))
        _salvar_venda(request.form, dados)
        flash("Venda registrada!", "success")
        return redirect(url_for("vendas"))
    return render_template("form_venda.html", modo="nova", row=None, idx=None, r_fin=r_fin,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))

@app.route("/vendas/editar/<int:idx>", methods=["GET", "POST"])
@login_required
def editar_venda(idx):
    dados = _get_dados_cache()
    df    = carregar_aba("Vendas")
    if df.empty or idx >= len(df):
        flash("Registro não encontrado.", "error")
        return redirect(url_for("vendas"))
    r_fin = _get_resumo_cache()
    if request.method == "POST":
        _validar_csrf()
        fazer_backup()
        _limpar_backups_antigos()
        _salvar_venda(request.form, dados, idx=idx)
        flash("Venda atualizada!", "success")
        return redirect(url_for("vendas"))
    row = df.iloc[idx].to_dict()
    row["Data"] = fmt_data(row.get("Data"))
    row["data_input"] = df.iloc[idx]["Data"].strftime("%Y-%m-%d") if pd.notna(df.iloc[idx]["Data"]) else ""
    return render_template("form_venda.html", modo="editar", row=row, idx=idx, r_fin=r_fin,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))


# ══════════════════════════════════════════════════════════════════════════════
#  MANEJO
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/manejo")
@login_required
def manejo():
    dados = _get_dados_cache()
    df = dados["Manejo"]
    rows = []
    for real_idx, row in (df.iterrows() if not df.empty else []):
        d = row.to_dict()
        d["Data"] = fmt_data(d.get("Data"))
        d["_idx"] = int(real_idx)
        rows.append(d)
    return render_template("lista.html", titulo="Manejo 🩺", secao="manejo", aba="Manejo",
                           colunas=["Data","Tipo","Qtd Cabeças","Descrição","Responsável"],
                           rows=rows)

@app.route("/manejo/novo", methods=["GET", "POST"])
@login_required
def novo_manejo():
    dados   = _get_dados_cache()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        salvar_linha("Manejo", [f.get("data"), f.get("tipo"), int(f.get("cabecas", 0) or 0),
                                f.get("descricao", "").strip(), f.get("responsavel", "")])
        flash(f"Manejo registrado! ({f.get('tipo')})", "success")
        return redirect(url_for("manejo"))
    return render_template("form_manejo.html", estoque=estoque, TIPOS=TIPOS_MANEJO,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))


# ══════════════════════════════════════════════════════════════════════════════
#  RELATÓRIOS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/relatorios")
@login_required
def relatorios():
    dados = _get_dados_cache()
    r_fin = _get_resumo_cache()
    mbr   = calcular_todos_membros(dados["Vendas"], dados["Compras"], dados["Gastos"], dados["Manejo"])
    gastos_tipo = calcular_gasto_por_tipo(dados["Gastos"])
    extras      = calcular_indicadores_extras(
        dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"], r_fin["ctcab"]
    )
    return render_template("relatorios.html", r=r_fin, mbr=mbr,
                           alertas=_gerar_alertas(dados), anual=_calc_anual(dados),
                           gastos_tipo=gastos_tipo, extras=extras,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS, EMOJIS=EMOJIS_MEMBROS)


# ══════════════════════════════════════════════════════════════════════════════
#  EXCLUIR
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/excluir/<aba>/<int:idx>", methods=["POST"])
@login_required
def excluir(aba, idx):
    _validar_csrf()
    fazer_backup()
    _limpar_backups_antigos()
    df = carregar_aba(aba)
    if not df.empty and idx < len(df):
        df = df.drop(df.index[idx]).reset_index(drop=True)
        reescrever_aba(aba, df)
        flash("Registro excluído.", "warning")
    return redirect(url_for({"Compras": "compras", "Gastos": "gastos",
                              "Vendas": "vendas", "Manejo": "manejo"}.get(aba, "dashboard")))


# ══════════════════════════════════════════════════════════════════════════════
#  IMPORTAR
# ══════════════════════════════════════════════════════════════════════════════
