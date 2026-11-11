#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas de Compras, Gastos, Vendas, Manejo, Excluir — Sítio Santo Antonio
Gerado automaticamente — não editar diretamente.
"""
from flask import render_template, request, redirect, url_for, flash
import pandas as pd
from db_adapter import carregar_aba, carregar_todas, salvar_linha, reescrever_aba, fazer_backup
from calculos import (
    calcular_estoque, calcular_cmp, calcular_gpcab, custo_medio_movel_venda,
    dividir_cotas,
)
from config import (TIPOS_GASTO, TIPOS_MANEJO, MEMBROS, NOMES_MEMBROS, COLUNAS_VENDAS, COLUNAS_COMPRAS,
                    TIPOS_COM_PRODUTO, INSUMOS, CATEGORIAS_GASTO, CAUSAS_MORTIS)
from gastos import categoria_legada
from extensions import (
    app, _agora, _validar_csrf, login_required,
    _get_dados_cache, _get_resumo_cache,
    _limpar_backups_antigos,
    fmt_brl, fmt_data, parse_valor,
    BASE_DIR,
)
from indicadores_coleta import processar_manejo_automatico  # v5.8 — coleta automática
import estoque_medicamentos

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


def _int_form(v, padrao=0) -> int:
    """Inteiro vindo do formulário; texto inválido ("abc", "") vira `padrao`
    em vez de erro 500. Aceita "1,5"/"1.5" (trunca)."""
    try:
        return int(float(str(v).strip().replace(",", ".")))
    except (TypeError, ValueError):
        return padrao


def _data_form(v):
    """Data do formulário: "2026-05-10" (campo date do navegador) ou "10/05/2026"
    (voz/digitado). Passar dayfirst=True numa data ISO enchia o log de avisos."""
    s = str(v or "").strip()
    iso = len(s) >= 10 and s[4:5] == "-" and s[7:8] == "-"
    return pd.to_datetime(s, dayfirst=not iso, errors="coerce")


def _aplicar_updates(df, idx, updates):
    """Grava os campos editados na linha `idx`. Converte a coluna para object antes
    de pôr texto numa coluna lida como float (ex.: "Perda De" toda vazia) — o pandas
    avisa que isso vira erro. Data inválida/vazia mantém a data original."""
    for col, val in updates.items():
        if col == "Data" and pd.isna(val):
            continue
        if col not in df.columns:
            df[col] = None
        if isinstance(val, str) and df[col].dtype != object:
            df[col] = df[col].astype(object)
        df.at[idx, col] = val

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
                           colunas=COLUNAS_COMPRAS,
                           rows=rows, ordem=ordem,
                           anos_disponiveis=_anos_de(df),
                           total_valor=_total_valor(df), total_cabecas=_total_cab(df))

def _cotas_do_form(f, cabecas: int) -> tuple:
    """Campos qtd_<dono> (qtd_mae, qtd_deyvid…) → cotas ajustadas, na ordem de MEMBROS."""
    return dividir_cotas(cabecas, *[_int_form(f.get(f"qtd_{m.lower()}")) for m in MEMBROS])


def gravar_compra(f) -> int:
    """Grava a compra do formulário (ou do comando de voz). Devolve o índice da
    linha nova na aba Compras — usado para pôr brinco nos animais dela."""
    data    = f.get("data") or _agora().strftime("%d/%m/%Y")
    cabecas = _int_form(f.get("cabecas"))
    valor   = parse_valor(f.get("valor", 0))
    desc    = f.get("descricao", "").strip()
    membro  = f.get("membro", "")
    if cabecas <= 0:
        raise ValueError("Informe ao menos 1 cabeça.")
    cotas = _cotas_do_form(f, cabecas)
    val_cab = round(valor / cabecas, 2) if cabecas > 0 else 0
    salvar_linha("Compras", [data, cabecas, valor, val_cab, *cotas, desc, membro])
    return len(carregar_aba("Compras")) - 1


@app.route("/compras/nova", methods=["GET", "POST"])
@login_required
def nova_compra():
    dados = _get_dados_cache()
    cmp_atual = calcular_cmp(dados["Compras"])
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        try:
            idx = gravar_compra(f)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("nova_compra"))
        flash(f"Compra registrada! {_int_form(f.get('cabecas'))} cabeças por "
              f"{fmt_brl(parse_valor(f.get('valor', 0)))}", "success")
        if f.get("brincar"):
            return redirect(url_for("brincar_compra", idx=idx))
        return redirect(url_for("transacoes"))
    return render_template("form_compra.html", modo="nova", cmp_atual=cmp_atual,
                           row=None, idx=None, MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))

@app.route("/compras/editar/<int:idx>", methods=["GET", "POST"])
@login_required
def editar_compra(idx):
    df = carregar_aba("Compras")
    if df.empty or idx >= len(df):
        flash("Registro não encontrado.", "error")
        return redirect(url_for("transacoes"))
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        data    = f.get("data", "")
        cabecas = _int_form(f.get("cabecas"))
        valor   = parse_valor(f.get("valor", 0))
        desc    = f.get("descricao", "").strip()
        membro  = f.get("membro", "")
        if cabecas <= 0:
            flash("Informe ao menos 1 cabeça.", "error")
            return redirect(url_for("editar_compra", idx=idx))
        cotas = _cotas_do_form(f, cabecas)
        val_cab = round(valor / cabecas, 2) if cabecas > 0 else 0
        fazer_backup()
        _limpar_backups_antigos()
        updates = {"Data": _data_form(data),
                   "Qtd Cabeças": cabecas, "Valor Total (R$)": valor,
                   "Valor/Cabeça (R$)": val_cab,
                   **{f"Qtd {m}": q for m, q in zip(MEMBROS, cotas)},
                   "Descrição": desc, "Registrado Por": membro}
        _aplicar_updates(df, idx, updates)
        reescrever_aba("Compras", df)
        flash("Compra atualizada!", "success")
        return redirect(url_for("transacoes"))
    row = df.iloc[idx].to_dict()
    row["Data"] = fmt_data(row.get("Data"))
    row["data_input"] = df.iloc[idx]["Data"].strftime("%Y-%m-%d") if pd.notna(df.iloc[idx]["Data"]) else ""
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
                                    "Qtd Cabeças","Valor/Cabeça (R$)","Registrado Por",
                                    "Categoria","Produto","Qtd Sacos"],
                           rows=rows, ordem=ordem,
                           anos_disponiveis=_anos_de(df),
                           tipos_disponiveis=_tipos_de(df),
                           pessoas_disponiveis=_pessoas_de(df, "Registrado Por"),
                           total_valor=_total_valor(df), total_cabecas=_total_cab(df))

def _insumo_do_form(f):
    """(produto, sacos) de uma compra de Sal/Proteinado; vazio nos outros tipos."""
    produto = f.get("produto", "").strip()
    if f.get("tipo") != "Sal/Proteínado" or produto not in INSUMOS:
        return "", None
    sacos = _int_form(f.get("qtd_sacos"), 0)
    return produto, (sacos if sacos > 0 else None)


def gravar_gasto(f, estoque: int):
    """Grava o gasto do formulário (ou do comando de voz)."""
    data   = f.get("data") or _agora().strftime("%d/%m/%Y")
    tipo   = f.get("tipo", "")
    desc   = f.get("descricao", "").strip()
    valor  = parse_valor(f.get("valor", 0))
    cab    = _int_form(f.get("cabecas"), estoque)
    membro = f.get("membro", "")
    if cab <= 0:
        cab = max(1, estoque)
    v_cab = round(valor / cab, 4) if cab > 0 else 0
    produto, sacos = _insumo_do_form(f)
    categoria = f.get("categoria", "").strip()
    if categoria not in CATEGORIAS_GASTO:
        categoria = categoria_legada(tipo, desc)
    salvar_linha("Gastos", [data, tipo, desc, valor, cab, v_cab, membro, produto, sacos,
                            "", "", categoria])


@app.route("/gastos/novo", methods=["GET", "POST"])
@login_required
def novo_gasto():
    dados = _get_dados_cache()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    gpcab   = calcular_gpcab(dados["Gastos"], dados["Compras"], dados["Vendas"], dados["Manejo"])
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        gravar_gasto(f, estoque)
        flash(f"Gasto registrado! {fmt_brl(parse_valor(f.get('valor', 0)))} ({f.get('tipo', '')})", "success")
        return redirect(url_for("gastos"))
    return render_template("form_gasto.html", estoque=estoque, gpcab=gpcab, INSUMOS=INSUMOS,
                       TIPOS=TIPOS_GASTO, CATEGORIAS_GASTO=CATEGORIAS_GASTO,
                       MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
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
        cab    = _int_form(f.get("cabecas"), estoque)
        membro = f.get("membro", "")
        if cab <= 0:
            cab = max(1, estoque)
        v_cab = round(valor / cab, 4) if cab > 0 else 0
        fazer_backup()
        _limpar_backups_antigos()
        produto, sacos = _insumo_do_form(f)
        updates = {"Data": _data_form(data),
                   "Tipo": tipo, "Descrição": desc,
                   "Valor Total (R$)": valor, "Qtd Cabeças": cab,
                   "Valor/Cabeça (R$)": v_cab, "Registrado Por": membro,
                   "Produto": produto, "Qtd Sacos": sacos,
                   "Categoria": (f.get("categoria", "").strip()
                                 if f.get("categoria", "").strip() in CATEGORIAS_GASTO
                                 else categoria_legada(tipo, desc))}
        _aplicar_updates(df, idx, updates)
        reescrever_aba("Gastos", df)
        flash("Gasto atualizado!", "success")
        return redirect(url_for("gastos"))
    row = df.iloc[idx].to_dict()
    row["Data"] = fmt_data(row.get("Data"))
    row["data_input"] = df.iloc[idx]["Data"].strftime("%Y-%m-%d") if pd.notna(df.iloc[idx].get("Data")) else ""
    return render_template("form_gasto.html", modo="editar", row=row, idx=idx,
                           estoque=estoque, gpcab=gpcab, INSUMOS=INSUMOS,
                           TIPOS=TIPOS_GASTO, CATEGORIAS_GASTO=CATEGORIAS_GASTO,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
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
    data         = form.get("data") or _agora().strftime("%d/%m/%Y")
    cabecas      = _int_form(form.get("cabecas"))
    valor_total  = parse_valor(form.get("valor", 0))
    valor_arroba = parse_valor(form.get("valor_arroba", 0))
    desc         = form.get("descricao", "").strip()
    brincos      = form.get("brincos_refs", "")   # já resolvido em _brincos_do_form

    cotas = _cotas_do_form(form, cabecas)

    val_cab  = round(valor_total / cabecas, 2) if cabecas > 0 else 0
    # O último dono fica com o centavo que sobra: a soma bate com o valor total.
    valores  = [round(q * val_cab, 2) for q in cotas[:-1]]
    valores.append(round(valor_total - sum(valores), 2))

    # Custo por cabeça no momento da venda — MÉDIA MÓVEL (v4.0), coerente com o
    # que o dashboard/relatórios recomputam. A venda entra na simulação posicionada
    # pela sua data; o idx (modo edição) evita duplicá-la.
    data_ts = _data_form(data)
    cmp_v, gpcab_v = custo_medio_movel_venda(
        dados["Compras"], dados["Gastos"], dados["Vendas"], dados["Manejo"],
        data_ts, cabecas, idx=idx,
    )
    ctcab_v = cmp_v + gpcab_v

    def custo_m(qtd):        return round(qtd * ctcab_v, 2)
    def result_m(val, qtd):  return round(val - custo_m(qtd), 2)

    # Colunas alinhadas com COLUNAS_VENDAS (Qtd/Valor/Custo/Resultado por dono + Brincos)
    linha = [
        data, cabecas, valor_total, val_cab, valor_arroba,
        *cotas,
        *valores,
        *[custo_m(q) for q in cotas],
        *[result_m(v, q) for v, q in zip(valores, cotas)],
        round(ctcab_v, 2),
        desc,
        brincos,
    ]

    import animais
    if brincos:
        # Os animais com brinco saem do cadastro como Vendidos (libera o brinco).
        animais.baixa_por_refs(brincos, "Vendido", data_ts if pd.notna(data_ts) else None)

    if idx is None:
        salvar_linha("Vendas", linha)
        return [], []
    df = carregar_aba("Vendas")
    antes = animais.ids_de(df.at[idx, "Brincos"]) if "Brincos" in df.columns else []
    linha[0] = data_ts  # usar Timestamp para edição no DataFrame
    _aplicar_updates(df, idx, dict(zip(COLUNAS_VENDAS, linha)))
    reescrever_aba("Vendas", df)
    # Brinco tirado da venda na edição: o animal volta a Vivo.
    tirados = [i for i in antes if i not in animais.ids_de(brincos)]
    return animais.reverter_baixa(tirados, "Vendido")


def _brincos_do_form(form, refs_antigas=None):
    """Campo "Brincos" digitado/ditado ('amarelo 21, azul 12') → (form com
    'brincos_refs' resolvido, erro). Refs ficam no formato 'Amarelo 21 #A0003'.
    refs_antigas: coluna Brincos do registro sendo editado — esses animais valem
    mesmo já vendidos/mortos (senão a edição recusava o próprio brinco)."""
    texto = (form.get("brincos") or "").strip()
    novo = dict(form.items())
    novo["brincos_refs"] = ""
    if not texto:
        return novo, None
    import animais
    refs, erros = animais.resolver_texto(texto, preferidos=animais.ids_de(refs_antigas))
    if erros:
        return novo, " ".join(erros)
    novo["brincos_refs"] = "; ".join(refs)
    return novo, None


def _avisar_animais_revertidos(voltaram, conflitos):
    if voltaram:
        flash("Voltaram para o rebanho (Vivo): " + ", ".join(voltaram), "info")
    if conflitos:
        flash("Continuam como Vendido porque o brinco já está em outro animal vivo: "
              + ", ".join(conflitos) + " — ajuste na página Animais.", "warning")


def _brincos_legiveis(v) -> str:
    """'Amarelo 21 #A0003; Azul 12 #A0007' → 'Amarelo 21, Azul 12' (campo do formulário)."""
    import re as _re
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return ", ".join(p.strip() for p in _re.sub(r"\s*#A\d+", "", str(v)).split(";") if p.strip())


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
        d["Brincos"] = _brincos_legiveis(d.get("Brincos"))
        d["_idx"] = int(real_idx)
        rows.append(d)
    return render_template("lista.html", titulo="Vendas 🤝", secao="vendas", aba="Vendas",
                           colunas=["Data","Qtd Cabeças","Valor Total (R$)","Valor/Cabeça (R$)",
                                    "Valor Arroba (R$)", *[f"Qtd {m}" for m in MEMBROS],
                                    *[f"Valor {m} (R$)" for m in MEMBROS], "Descrição","Brincos"],
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
        cabecas = _int_form(request.form.get("cabecas"))
        if cabecas <= 0:
            flash("Informe ao menos 1 cabeça.", "error")
            return redirect(url_for("nova_venda"))
        form, erro = _brincos_do_form(request.form)
        if erro:
            flash(erro, "error")
            return redirect(url_for("nova_venda"))

        # v5.10 Onda 2 — Validar carência antes de vender (fonte única: 3 abas)
        try:
            from doencas_carencia import status_por_animal, validar_venda
            import re
            texto_brincos = (form.get("brincos_refs") or "").strip()
            if texto_brincos:
                status = status_por_animal("carne")
                # Extrai IDs dos brincos (format: "Amarelo 21 #A0003; Azul 12 #A0007")
                for animal_id in re.findall(r'#([A-Z0-9]+)', texto_brincos):
                    s = status.get(animal_id)
                    if not s:
                        continue
                    pode_vender, motivo = validar_venda(animal_id, "carne", s)
                    if not pode_vender:
                        flash(f"{animal_id}: {motivo} — não pode ser vendido.", "warning")
        except Exception as e:
            app.logger.warning(f"Validação de carência: {e}")
        _salvar_venda(form, dados)
        flash("Venda registrada!", "success")
        if cabecas > r_fin["estoque"]:
            # Não bloqueia (pode faltar lançar uma compra/nascimento), mas avisa:
            # cabeça vendida sem ter entrado no rebanho sai com custo zero.
            flash(f"Atenção: a venda tem {cabecas} cabeças, mas o rebanho registrado tinha "
                  f"{r_fin['estoque']}. Falta lançar alguma compra ou nascimento?", "warning")
        return redirect(url_for("transacoes"))
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
        return redirect(url_for("transacoes"))
    r_fin = _get_resumo_cache()
    if request.method == "POST":
        _validar_csrf()
        if _int_form(request.form.get("cabecas")) <= 0:
            flash("Informe ao menos 1 cabeça.", "error")
            return redirect(url_for("editar_venda", idx=idx))
        form, erro = _brincos_do_form(request.form, df.iloc[idx].get("Brincos"))
        if erro:
            flash(erro, "error")
            return redirect(url_for("editar_venda", idx=idx))
        fazer_backup()
        _limpar_backups_antigos()
        voltaram, conflitos = _salvar_venda(form, dados, idx=idx)
        flash("Venda atualizada!", "success")
        _avisar_animais_revertidos(voltaram, conflitos)
        return redirect(url_for("vendas"))
    row = df.iloc[idx].to_dict()
    row["Data"] = fmt_data(row.get("Data"))
    row["data_input"] = df.iloc[idx]["Data"].strftime("%Y-%m-%d") if pd.notna(df.iloc[idx]["Data"]) else ""
    row["brincos_txt"] = _brincos_legiveis(row.get("Brincos"))
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
    ordem = request.args.get("ordem", "desc")
    if not df.empty and "Data" in df.columns:
        df = df.sort_values("Data", ascending=(ordem == "asc"), na_position="last")

    rows = []
    for real_idx, row in (df.iterrows() if not df.empty else []):
        d = row.to_dict()
        d["Data"] = fmt_data(d.get("Data"))
        d["Brincos"] = _brincos_legiveis(d.get("Brincos"))
        d["_idx"] = int(real_idx)
        rows.append(d)

    return render_template("lista.html", titulo="Manejo 🩺", secao="manejo", aba="Manejo",
                           colunas=["Data","Tipo","Qtd Cabeças","Produto","Brincos","Descrição",
                                    "Causa Mortis","Laudo/Observações","Responsável",
                                    "Perda De","Nascimento De"],
                           rows=rows, ordem=ordem,
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
    lotes_ativos = [l for l in estoque_medicamentos.lotes_ativos() if not l["vencido"]]
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        # "Perda De" só faz sentido quando o manejo é Morte/Perda
        perda_de = f.get("perda_de", "") if f.get("tipo") == "Morte/Perda" else ""
        nasc_de  = f.get("nascimento_de", "") if f.get("tipo") == "Nascimento" else ""
        causa_mortis = f.get("causa_mortis", "") if f.get("tipo") == "Morte/Perda" else ""
        laudo = f.get("laudo", "").strip() if f.get("tipo") == "Morte/Perda" else ""
        if f.get("tipo") == "Morte/Perda" and causa_mortis not in CAUSAS_MORTIS:
            flash("Selecione a causa da morte.", "error")
            return redirect(url_for("novo_manejo"))
        produto = _produto_do_form(f)
        if f.get("tipo") in TIPOS_COM_PRODUTO and not produto:
            flash("Informe qual remédio/produto foi usado.", "error")
            return redirect(url_for("novo_manejo"))
        form, erro = _brincos_do_form(f)
        if erro:
            flash(erro, "error")
            return redirect(url_for("novo_manejo"))

        lote_id = f.get("lote_id", "").strip()
        quantidade_uso = parse_valor(f.get("quantidade_uso", 0))

        if lote_id and quantidade_uso > 0:
            try:
                estoque_medicamentos.registrar_movimento(
                    movimento="Saída",
                    data=f.get("data") or _agora(),
                    lote_id=lote_id,
                    quantidade=quantidade_uso,
                    observacoes=f"Aplicação em Manejo ({f.get('tipo')}): {f.get('descricao','')}",
                    responsavel=f.get("responsavel", "Sistema")
                )
                flash("Baixa automática realizada no estoque de medicamentos.", "success")
            except ValueError as err:
                flash(f"Atenção no estoque: {err}", "warning")

        salvar_linha("Manejo", [f.get("data") or _agora().strftime("%d/%m/%Y"), f.get("tipo"), _int_form(f.get("cabecas")),
                                f.get("descricao", "").strip(), f.get("responsavel", ""),
                                perda_de, produto, nasc_de, form["brincos_refs"], "", "",
                                causa_mortis, laudo, lote_id, quantidade_uso])
        # v5.8 — coleta automática de dados para indicadores
        processar_manejo_automatico(
            tipo_manejo=f.get("tipo", ""),
            brincos_str=form["brincos_refs"],
            descricao=f.get("descricao", "").strip(),
            pasto_id=f.get("pasto", ""),
            qtd_cabecas=_int_form(f.get("cabecas"))
        )
        from alertas_whatsapp import avisar_manejo
        from routes_visitas import _enviar_avisos_depois
        from routes_animais import _membro_logado
        avisar_manejo(f.get("tipo", ""), _int_form(f.get("cabecas")), form["brincos_refs"],
                      perda_de or nasc_de, f.get("descricao", ""),
                      registrado_por=_membro_logado() or f.get("responsavel", ""))
        flash(f"Manejo registrado! ({f.get('tipo')})", "success")
        return _enviar_avisos_depois(redirect(url_for("manejo")))
    return render_template("form_manejo.html", estoque=estoque, TIPOS=TIPOS_MANEJO,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           TIPOS_COM_PRODUTO=TIPOS_COM_PRODUTO,
                           CAUSAS_MORTIS=CAUSAS_MORTIS,
                           lotes_ativos=lotes_ativos,
                           produtos_usados=_produtos_usados(dados["Manejo"]),
                           produtos_sugeridos=_produtos_sugeridos(_produtos_usados(dados["Manejo"])),
                           hoje=_agora().strftime("%Y-%m-%d"))


@app.route("/manejo/editar/<int:idx>", methods=["GET", "POST"])
@login_required
def editar_manejo(idx):
    dados   = _get_dados_cache()
    df      = carregar_aba("Manejo")
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    lotes_ativos = [l for l in estoque_medicamentos.lotes_ativos() if not l["vencido"]]
    if df.empty or idx >= len(df):
        flash("Registro não encontrado.", "error")
        return redirect(url_for("manejo"))
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        form, erro = _brincos_do_form(f, df.iloc[idx].get("Brincos"))
        if erro:
            flash(erro, "error")
            return redirect(url_for("editar_manejo", idx=idx))
        fazer_backup()
        _limpar_backups_antigos()
        lote_id = f.get("lote_id", "").strip()
        quantidade_uso = parse_valor(f.get("quantidade_uso", 0))

        if lote_id and quantidade_uso > 0:
            try:
                estoque_medicamentos.registrar_movimento(
                    movimento="Saída",
                    data=f.get("data") or _agora(),
                    lote_id=lote_id,
                    quantidade=quantidade_uso,
                    observacoes=f"Atualização Manejo ({f.get('tipo')})",
                    responsavel=f.get("responsavel", "Sistema")
                )
            except ValueError as err:
                flash(f"Atenção no estoque: {err}", "warning")

        updates = {
            "Brincos":     form["brincos_refs"],
            "Data":        _data_form(f.get("data", "")),
            "Tipo":        f.get("tipo",""),
            "Qtd Cabeças": _int_form(f.get("cabecas")),
            "Descrição":   f.get("descricao","").strip(),
            "Responsável": f.get("responsavel",""),
            "Perda De":    f.get("perda_de", "") if f.get("tipo") == "Morte/Perda" else "",
            "Produto":     _produto_do_form(f),
            "Nascimento De": f.get("nascimento_de", "") if f.get("tipo") == "Nascimento" else "",
            "Causa Mortis": f.get("causa_mortis", "") if f.get("tipo") == "Morte/Perda" else "",
            "Laudo/Observações": f.get("laudo", "").strip() if f.get("tipo") == "Morte/Perda" else "",
            "Lote ID Usado": lote_id,
            "Qtd Usada":     quantidade_uso,
        }
        if f.get("tipo") == "Morte/Perda" and updates["Causa Mortis"] not in CAUSAS_MORTIS:
            flash("Selecione a causa da morte.", "error")
            return redirect(url_for("editar_manejo", idx=idx))
        _aplicar_updates(df, idx, updates)
        reescrever_aba("Manejo", df)
        # v5.8 — coleta automática de dados para indicadores (edição)
        processar_manejo_automatico(
            tipo_manejo=f.get("tipo", ""),
            brincos_str=form["brincos_refs"],
            descricao=f.get("descricao", "").strip(),
            pasto_id=f.get("pasto", ""),
            qtd_cabecas=_int_form(f.get("cabecas"))
        )
        flash("Manejo atualizado!", "success")
        return redirect(url_for("manejo"))
    row = df.iloc[idx].to_dict()
    row["data_input"] = df.iloc[idx]["Data"].strftime("%Y-%m-%d") if pd.notna(df.iloc[idx].get("Data")) else ""
    if pd.isna(row.get("Produto")):
        row["Produto"] = ""
    if pd.isna(row.get("Causa Mortis")) or not str(row.get("Causa Mortis") or "").strip():
        row["Causa Mortis"] = "Desconhecida"
    if pd.isna(row.get("Laudo/Observações")):
        row["Laudo/Observações"] = ""
    row["brincos_txt"] = _brincos_legiveis(row.get("Brincos"))
    return render_template("form_manejo.html", modo="editar", row=row, idx=idx,
                           estoque=estoque, TIPOS=TIPOS_MANEJO,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           TIPOS_COM_PRODUTO=TIPOS_COM_PRODUTO,
                           CAUSAS_MORTIS=CAUSAS_MORTIS,
                           lotes_ativos=lotes_ativos,
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
    if aba not in ("Compras", "Gastos", "Vendas", "Manejo"):
        flash("Aba inválida.", "error")
        return redirect(url_for("dashboard"))
    fazer_backup()
    _limpar_backups_antigos()
    df = carregar_aba(aba)
    if not df.empty and idx < len(df):
        brincos = df.iloc[idx].get("Brincos") if aba == "Vendas" else None
        df = df.drop(df.index[idx]).reset_index(drop=True)
        reescrever_aba(aba, df)
        flash("Registro excluído.", "warning")
        if brincos is not None:
            # Venda apagada: os animais dela não foram vendidos — voltam a Vivo.
            import animais
            _avisar_animais_revertidos(*animais.reverter_baixa(animais.ids_de(brincos), "Vendido"))
    return redirect(url_for({"Compras": "transacoes", "Gastos": "gastos",
                              "Vendas": "transacoes", "Manejo": "manejo"}.get(aba, "dashboard")))


# ══════════════════════════════════════════════════════════════════════════════
#  IMPORTAR
# ══════════════════════════════════════════════════════════════════════════════
