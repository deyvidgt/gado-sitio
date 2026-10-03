#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas de Compras, Gastos, Vendas, Manejo, Excluir — Sítio Santo Antonio
Gerado automaticamente — não editar diretamente.
"""
from flask import render_template, request, redirect, url_for, flash
import pandas as pd
from db import carregar_aba, carregar_todas, fazer_backup
from calculos import (
    calcular_estoque, calcular_cmp, calcular_gpcab, custo_medio_movel_venda,
)
from config import (TIPOS_GASTO, TIPOS_MANEJO, MEMBROS, NOMES_MEMBROS, COLUNAS_VENDAS,
                    TIPOS_COM_PRODUTO)
from extensions import (
    app, _agora, _validar_csrf, login_required,
    _get_dados_cache, _get_resumo_cache,
    salvar_linha, reescrever_aba,
    _limpar_backups_antigos,
    fmt_brl, fmt_data, parse_valor,
    BASE_DIR,
)

def _anos_de(df):
    if df.empty or "Data" not in df.columns:
        return []
    return sorted(df["Data"].dropna().dt.year.astype(int).unique().tolist(), reverse=True)

def _tipos_de(df, coluna="Tipo"):
    if df.empty or coluna not in df.columns:
        return []
    return sorted(df[coluna].dropna().unique().tolist())

def _total_valor(df):
    if df.empty or "Valor Total (R$)" not in df.columns:
        return 0.0
    return float(df["Valor Total (R$)"].sum())

def _total_cab(df):
    if df.empty or "Qtd Cabeças" not in df.columns:
        return 0
    return int(df["Qtd Cabeças"].sum())

def _pessoas_de(df, *colunas):
    """Lista de pessoas distintas presentes em qualquer das colunas dadas
    (ex.: 'Responsável', 'Registrado Por') — para o filtro das listagens."""
    if df.empty:
        return []
    nomes = set()
    for col in colunas:
        if col in df.columns:
            for v in df[col].dropna().tolist():
                s = str(v).strip()
                if s and s.lower() != "nan":
                    nomes.add(s)
    return sorted(nomes)

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
                           rows=rows, ordem=ordem,
                           anos_disponiveis=_anos_de(df),
                           total_valor=_total_valor(df), total_cabecas=_total_cab(df))

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
                           rows=rows, ordem=ordem,
                           anos_disponiveis=_anos_de(df),
                           tipos_disponiveis=_tipos_de(df),
                           pessoas_disponiveis=_pessoas_de(df, "Registrado Por"),
                           total_valor=_total_valor(df), total_cabecas=_total_cab(df))

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
#  FUNÇÃO AUXILIAR DE VENDAS (Adicione esta função aqui)
# ══════════════════════════════════════════════════════════════════════════════

def _salvar_venda(form, dados, idx=None):
    """
    Processa e salva venda do formulário web.
    Calcula CMP + GPCab no momento da venda e preenche TODAS as 19 colunas,
    igual ao CLI em registros.py.
    """
    data         = form.get("data", _agora().strftime("%d/%m/%Y"))
    cabecas      = int(form.get("cabecas", 0) or 0)
    valor_total  = parse_valor(form.get("valor", 0))
    valor_arroba = parse_valor(form.get("valor_arroba", 0))
    desc         = form.get("descricao", "").strip()

    q_mae    = int(form.get("qtd_mae",    0) or 0)
    q_deyvid = int(form.get("qtd_deyvid", 0) or 0)
    q_nilson = int(form.get("qtd_nilson", 0) or 0)

    soma_q = q_mae + q_deyvid + q_nilson
    if soma_q == 0:
        base = cabecas // 3
        q_mae = q_deyvid = base
        q_nilson = cabecas - base * 2
    elif soma_q != cabecas:
        fator    = cabecas / soma_q
        q_mae    = round(q_mae    * fator)
        q_deyvid = round(q_deyvid * fator)
        q_nilson = cabecas - q_mae - q_deyvid

    val_cab  = round(valor_total / cabecas, 2) if cabecas > 0 else 0
    v_mae    = round(q_mae    * val_cab, 2)
    v_deyvid = round(q_deyvid * val_cab, 2)
    v_nilson = round(valor_total - v_mae - v_deyvid, 2)

    # Custo por cabeça no momento da venda — MÉDIA MÓVEL (v4.0), coerente com o
    # que o dashboard/relatórios recomputam. A venda entra na simulação posicionada
    # pela sua data; o idx (modo edição) evita duplicá-la.
    data_ts = pd.to_datetime(data, dayfirst=True, errors="coerce")
    cmp_v, gpcab_v = custo_medio_movel_venda(
        dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"],
        data_ts, cabecas, idx=idx,
    )
    ctcab_v = cmp_v + gpcab_v

    def custo_m(qtd):        return round(qtd * ctcab_v, 2)
    def result_m(val, qtd):  return round(val - custo_m(qtd), 2)

    c_mae    = custo_m(q_mae)
    c_deyvid = custo_m(q_deyvid)
    c_nilson = custo_m(q_nilson)
    r_mae    = result_m(v_mae,    q_mae)
    r_deyvid = result_m(v_deyvid, q_deyvid)
    r_nilson = result_m(v_nilson, q_nilson)

    # 19 colunas alinhadas com COLUNAS_VENDAS
    linha = [
        data, cabecas, valor_total, val_cab, valor_arroba,
        q_mae, q_deyvid, q_nilson,
        v_mae, v_deyvid, v_nilson,
        c_mae, c_deyvid, c_nilson,
        r_mae, r_deyvid, r_nilson,
        round(ctcab_v, 2),
        desc,
    ]

    if idx is None:
        salvar_linha("Vendas", linha)
    else:
        df = carregar_aba("Vendas")
        linha[0] = data_ts  # usar Timestamp para edição no DataFrame
        for col, val in zip(COLUNAS_VENDAS, linha):
            if col in df.columns:
                df.at[idx, col] = val
            else:
                df[col] = None
                df.at[idx, col] = val
        reescrever_aba("Vendas", df)


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
                           rows=rows, ordem=ordem,
                           anos_disponiveis=_anos_de(df),
                           total_valor=_total_valor(df), total_cabecas=_total_cab(df))

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
                           colunas=["Data","Tipo","Qtd Cabeças","Produto","Descrição","Responsável","Perda De","Nascimento De"],
                           rows=rows,
                           anos_disponiveis=_anos_de(df),
                           tipos_disponiveis=_tipos_de(df),
                           pessoas_disponiveis=_pessoas_de(df, "Responsável", "Perda De", "Nascimento De"))

def _produtos_sugeridos(usados: dict) -> dict:
    """Já usados (mais recentes primeiro) + exemplos do mercado que ainda não estão na lista."""
    from saude import SUGESTOES_PRODUTO
    return {t: usados.get(t, []) + [p for p in SUGESTOES_PRODUTO.get(t, []) if p not in usados.get(t, [])]
            for t in TIPOS_COM_PRODUTO}


def _produtos_usados(df_man: pd.DataFrame) -> dict:
    """{tipo: [produtos já usados, do mais recente ao mais antigo]} — sugestões do formulário."""
    out = {t: [] for t in TIPOS_COM_PRODUTO}
    if df_man.empty or "Produto" not in df_man.columns:
        return out
    df = df_man[df_man["Tipo"].isin(TIPOS_COM_PRODUTO) & df_man["Produto"].notna()]
    for _, r in df.sort_values("Data", ascending=False, na_position="last").iterrows():
        prod = str(r["Produto"]).strip()
        if prod and prod not in out[r["Tipo"]]:
            out[r["Tipo"]].append(prod)
    return out


def _produto_do_form(f) -> str:
    return f.get("produto", "").strip() if f.get("tipo") in TIPOS_COM_PRODUTO else ""


@app.route("/manejo/novo", methods=["GET", "POST"])
@login_required
def novo_manejo():
    dados   = _get_dados_cache()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        # "Perda De" só faz sentido quando o manejo é Morte/Perda
        perda_de = f.get("perda_de", "") if f.get("tipo") == "Morte/Perda" else ""
        nasc_de  = f.get("nascimento_de", "") if f.get("tipo") == "Nascimento" else ""
        produto = _produto_do_form(f)
        if f.get("tipo") in TIPOS_COM_PRODUTO and not produto:
            flash("Informe qual remédio/produto foi usado.", "error")
            return redirect(url_for("novo_manejo"))
        salvar_linha("Manejo", [f.get("data"), f.get("tipo"), int(f.get("cabecas", 0) or 0),
                                f.get("descricao", "").strip(), f.get("responsavel", ""),
                                perda_de, produto, nasc_de])
        flash(f"Manejo registrado! ({f.get('tipo')})", "success")
        return redirect(url_for("manejo"))
    return render_template("form_manejo.html", estoque=estoque, TIPOS=TIPOS_MANEJO,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           TIPOS_COM_PRODUTO=TIPOS_COM_PRODUTO,
                           produtos_usados=_produtos_usados(dados["Manejo"]),
                           produtos_sugeridos=_produtos_sugeridos(_produtos_usados(dados["Manejo"])),
                           hoje=_agora().strftime("%Y-%m-%d"))


@app.route("/manejo/editar/<int:idx>", methods=["GET", "POST"])
@login_required
def editar_manejo(idx):
    dados   = _get_dados_cache()
    df      = carregar_aba("Manejo")
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    if df.empty or idx >= len(df):
        flash("Registro não encontrado.", "error")
        return redirect(url_for("manejo"))
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        fazer_backup()
        _limpar_backups_antigos()
        updates = {
            "Data":        pd.to_datetime(f.get("data",""), dayfirst=True, errors="coerce"),
            "Tipo":        f.get("tipo",""),
            "Qtd Cabeças": int(f.get("cabecas", 0) or 0),
            "Descrição":   f.get("descricao","").strip(),
            "Responsável": f.get("responsavel",""),
            "Perda De":    f.get("perda_de", "") if f.get("tipo") == "Morte/Perda" else "",
            "Produto":     _produto_do_form(f),
            "Nascimento De": f.get("nascimento_de", "") if f.get("tipo") == "Nascimento" else "",
        }
        for col, val in updates.items():
            if col in df.columns:
                df.at[idx, col] = val
            else:
                df[col] = None; df.at[idx, col] = val
        reescrever_aba("Manejo", df)
        flash("Manejo atualizado!", "success")
        return redirect(url_for("manejo"))
    row = df.iloc[idx].to_dict()
    row["data_input"] = df.iloc[idx]["Data"].strftime("%Y-%m-%d") if pd.notna(df.iloc[idx].get("Data")) else ""
    if pd.isna(row.get("Produto")):
        row["Produto"] = ""
    return render_template("form_manejo.html", modo="editar", row=row, idx=idx,
                           estoque=estoque, TIPOS=TIPOS_MANEJO,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           TIPOS_COM_PRODUTO=TIPOS_COM_PRODUTO,
                           produtos_usados=_produtos_usados(df),
                           produtos_sugeridos=_produtos_sugeridos(_produtos_usados(df)),
                           hoje=_agora().strftime("%Y-%m-%d"))


# ══════════════════════════════════════════════════════════════════════════════
#  RELATÓRIOS
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
