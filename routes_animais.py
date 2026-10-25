#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas de Animais (brincos) e Comando de Voz — Sítio Santo Antonio v4.3
"""
from datetime import datetime

import pandas as pd
from flask import render_template, request, redirect, url_for, flash, jsonify, session

import animais as A
import comando_voz as V
import drive
import fotos as F
import pesagem as P
from calculos import calcular_estoque, calcular_estoque_por_membro
from config import (MEMBROS, NOMES_MEMBROS, CORES_BRINCO, CATEGORIAS_ANIMAL,
                    ORIGENS_ANIMAL, COLUNAS_MANEJO, TIPOS_COM_PRODUTO, TIPOS_FOTO)
from db import fazer_backup
from extensions import (app, _agora, _validar_csrf, login_required, _get_dados_cache,
                        salvar_linha, fmt_data, _limpar_backups_antigos, _ler_sitio_config_disco)


def fazer_backup_seguro():
    """Backup antes de reescrever a aba (edição/baixa/exclusão), como no resto do site."""
    fazer_backup()
    _limpar_backups_antigos()


def _membro_logado() -> str:
    """Usuário do login → membro (Mae/Deyvid/Nilson) para 'Responsável'/'Registrado Por'."""
    u = str(session.get("usuario") or "").strip().lower()
    return {"geane": "Mae", "mae": "Mae", "deyvid": "Deyvid", "nilson": "Nilson"}.get(u, "")


def _ctx_templates():
    return dict(MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS, CORES=CORES_BRINCO,
                CATEGORIAS=list(CATEGORIAS_ANIMAL), ORIGENS=ORIGENS_ANIMAL,
                COR_HEX=A.COR_HEX, cores_dono=A.cores_brinco(),
                hoje=_agora().strftime("%Y-%m-%d"))


def _dados_form(f) -> dict:
    num = str(f.get("numero") or "").strip()
    return {
        "Brinco Cor": f.get("cor", ""), "Brinco Nº": int(num) if num.isdigit() else None,
        "Dono": f.get("dono", ""), "Categoria": f.get("categoria", ""),
        "Sexo": f.get("sexo", ""), "Raça": f.get("raca", ""), "Pelagem": f.get("pelagem", ""),
        "Sinais": f.get("sinais", ""), "Nascimento": f.get("nascimento", ""),
        "Entrada": f.get("entrada", ""), "Origem": f.get("origem", ""),
        "Ref Compra": f.get("ref_compra", ""), "Mãe": _mae_do_form(f.get("mae", "")),
        "Observações": f.get("observacoes", ""),
    }


def _mae_do_form(txt: str) -> str:
    """'amarelo 08' → ref do animal cadastrado (se achar um só); senão o texto."""
    txt = str(txt or "").strip()
    if not txt or A.ids_de(txt):
        return txt
    refs, erros = A.resolver_texto(txt)
    return refs[0] if len(refs) == 1 and not erros else txt


def _rendimento() -> float:
    """Rendimento de carcaça das Configurações (52% se não tiver)."""
    try:
        return float(_ler_sitio_config_disco().get("rendimento", 52) or 52) / 100.0
    except (TypeError, ValueError):
        return 0.52


def _linha_animal(a, hoje):
    return {"id": a["ID"], "cor": a["Brinco Cor"], "num": a["Brinco Nº"],
            "brinco": A.fmt_brinco(a["Brinco Cor"], a["Brinco Nº"]),
            "hex": A.COR_HEX.get(a["Brinco Cor"], "#999"),
            "dono": a["Dono"], "categoria": a["Categoria"], "sexo": a["Sexo"],
            "raca": a["Raça"], "pelagem": a["Pelagem"], "sinais": a["Sinais"],
            "idade": A.idade_txt(a["Nascimento"], hoje), "origem": a["Origem"],
            "status": a["Status"], "saida": fmt_data(a["Data Saída"]) if pd.notna(a["Data Saída"]) else "",
            "entrada": fmt_data(a["Entrada"]) if pd.notna(a["Entrada"]) else ""}


# ══════════════════════════════════════════════════════════════════════════════
#  ANIMAIS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/animais")
@login_required
def animais():
    dados = _get_dados_cache()
    df = A.carregar()
    hoje = _agora()
    status = request.args.get("status", "Vivo")
    lista = df if status == "todos" else df[df["Status"] == status]
    lista = lista.sort_values(["Brinco Cor", "Brinco Nº"], na_position="last")
    est_m = calcular_estoque_por_membro(dados["Compras"], dados["Vendas"], dados["Manejo"])
    proximos = {m: A.proximo_numero(df, c) for m, c in A.cores_brinco().items()}
    pesos = P.todas(dados["Manejo"])
    rows = [{**_linha_animal(a, hoje), "peso": P.resumo(pesos.get(a["ID"], []))}
            for _, a in lista.iterrows()]
    return render_template("animais.html", rows=rows,
                           status=status, total_vivos=len(A.vivos(df)),
                           conferencia=A.conferencia(df, est_m),
                           brucelose=[{**_linha_animal(b["animal"], hoje), "msg": b["msg"],
                                       "situacao": b["situacao"]}
                                      for b in A.janela_brucelose(df, dados["Manejo"], hoje)],
                           proximos=proximos, fotos_principais=F.principais(),
                           **_ctx_templates())


@app.route("/animais/cores", methods=["POST"])
@login_required
def animais_cores():
    _validar_csrf()
    cores = {m: request.form.get(f"cor_{m}", "") for m in MEMBROS}
    if len(set(cores.values())) < len(cores):
        flash("Cada dono precisa de uma cor diferente.", "error")
    else:
        A.salvar_cores_brinco(cores)
        flash("Cores dos brincos salvas.", "success")
    return redirect(url_for("animais"))


@app.route("/animais/novo", methods=["GET", "POST"])
@login_required
def novo_animal():
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        try:
            feitos = A.cadastrar([_dados_form(f)], registrado_por=_membro_logado(),
                                 responsavel=_membro_logado())
        except ValueError as e:
            flash(str(e), "error")
            return render_template("form_animal.html", modo="novo", row=None, form=f,
                                   **_ctx_templates())
        reg = feitos[0]
        for av in reg["avisos"]:
            flash(av, "warning")
        extra = " e o Nascimento no Manejo" if reg["Origem"] == "Nascimento" else ""
        flash(f"🏷️ {A.fmt_brinco(reg['Brinco Cor'], reg['Brinco Nº'])} cadastrado{extra}!", "success")
        if f.get("outro"):
            return redirect(url_for("novo_animal", dono=reg["Dono"], categoria=reg["Categoria"],
                                    origem=reg["Origem"], raca=reg["Raça"]))
        return redirect(url_for("ficha_animal", id_=reg["ID"]))
    return render_template("form_animal.html", modo="novo", row=None, form=request.args,
                           **_ctx_templates())


@app.route("/api/animais/proximo")
@login_required
def api_proximo_brinco():
    """Próximo nº livre da cor (o formulário mostra ao escolher dono/cor)."""
    cor = request.args.get("cor", "")
    if cor not in CORES_BRINCO:
        return jsonify({"ok": False}), 400
    return jsonify({"ok": True, "numero": A.proximo_numero(A.carregar(), cor)})


@app.route("/animais/compra/<int:idx>", methods=["GET", "POST"])
@login_required
def brincar_compra(idx):
    """Põe brinco nos animais de uma compra: uma linha por cabeça, dono e nº já
    sugeridos (a cor de cada dono, números seguidos)."""
    dados = _get_dados_cache()
    df_c = dados["Compras"]
    if df_c.empty or idx >= len(df_c):
        flash("Compra não encontrada.", "error")
        return redirect(url_for("compras"))
    compra = df_c.iloc[idx]
    ref_compra = f"{fmt_data(compra.get('Data'))} · {int(compra.get('Qtd Cabeças') or 0)} cab."
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        lista = []
        for i in range(int(f.get("qtd", 0) or 0)):
            if not f.get(f"incluir_{i}"):
                continue
            lista.append({
                "Dono": f.get(f"dono_{i}", ""), "Brinco Cor": f.get(f"cor_{i}", ""),
                "Brinco Nº": int(f.get(f"numero_{i}")) if str(f.get(f"numero_{i}", "")).isdigit() else None,
                "Categoria": f.get(f"categoria_{i}", ""), "Raça": f.get(f"raca_{i}", ""),
                "Pelagem": f.get(f"pelagem_{i}", ""), "Sinais": f.get(f"sinais_{i}", ""),
                "Origem": "Compra", "Ref Compra": ref_compra,
                "Entrada": compra.get("Data") if pd.notna(compra.get("Data")) else "",
            })
        if not lista:
            flash("Nenhum animal marcado.", "warning")
            return redirect(url_for("brincar_compra", idx=idx))
        try:
            feitos = A.cadastrar(lista, registrado_por=_membro_logado())
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("brincar_compra", idx=idx))
        for reg in feitos:
            for av in reg["avisos"]:
                flash(av, "warning")
        flash(f"🏷️ {len(feitos)} animal(is) com brinco cadastrados!", "success")
        return redirect(url_for("animais"))

    # Sugestão: uma linha por cabeça, na divisão da compra, nº seguido por cor.
    df = A.carregar()
    cores = A.cores_brinco()
    linhas, reservados = [], {}
    for m in MEMBROS:
        for _ in range(int(compra.get(f"Qtd {m}") or 0)):
            cor = cores[m]
            n = A.proximo_numero(df, cor, reservados.get(cor, ()))
            reservados.setdefault(cor, set()).add(n)
            linhas.append({"dono": m, "cor": cor, "numero": n})
    if not linhas:
        for _ in range(int(compra.get("Qtd Cabeças") or 0)):
            linhas.append({"dono": "", "cor": "", "numero": None})
    return render_template("brincar_compra.html", compra=compra, idx=idx, linhas=linhas,
                           ref_compra=ref_compra, **_ctx_templates())


@app.route("/animais/pesagem", methods=["GET", "POST"])
@login_required
def pesagem():
    """Pesagem no curral: um campo de peso por animal vivo; grava uma linha
    Pesagem no Manejo. ?id=A0003 mostra só esse animal (botão da ficha)."""
    df = A.carregar()
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        ids = [k[5:] for k in f if k.startswith("peso_")]
        try:
            pares = P.validar({i: f.get(f"peso_{i}") for i in ids}, df)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("pesagem", id=f.get("so_id") or None))
        P.registrar(pares, f.get("data"), responsavel=_membro_logado(),
                    obs=f.get("obs", "").strip())
        flash(f"⚖️ Pesagem de {len(pares)} animal(is) registrada!", "success")
        if len(pares) == 1:
            return redirect(url_for("ficha_animal", id_=A.ids_de(pares[0][0])[0]))
        return redirect(url_for("pesagem"))
    dados = _get_dados_cache()
    vivos = A.vivos(df).sort_values(["Brinco Cor", "Brinco Nº"], na_position="last")
    so_id = request.args.get("id", "")
    if so_id:
        vivos = vivos[vivos["ID"] == so_id]
    hoje = _agora()
    rend = _rendimento()
    pesos = P.todas(dados["Manejo"])
    rows = [{**_linha_animal(a, hoje), "peso": P.resumo(pesos.get(a["ID"], []), rend)}
            for _, a in vivos.iterrows()]
    medio, n = P.peso_medio_vivos(df, dados["Manejo"])
    return render_template("pesagem.html", rows=rows, so_id=so_id, peso_medio=medio,
                           n_pesados=n, rendimento=rend,
                           now_date=pd.Timestamp(hoje).normalize(), **_ctx_templates())


@app.route("/animais/<id_>")
@login_required
def ficha_animal(id_):
    dados = _get_dados_cache()
    df = A.carregar()
    a = A.por_id(df, id_)
    if a is None:
        flash("Animal não encontrado.", "error")
        return redirect(url_for("animais"))
    hoje = _agora()
    filhos = df[df["Mãe"].astype(str).str.contains(f"#{id_}", regex=False)]
    mae_id = (A.ids_de(a["Mãe"]) or [None])[0]
    hist_peso = P.todas(dados["Manejo"]).get(id_, [])
    return render_template("ficha_animal.html", a=_linha_animal(a, hoje), raw=a,
                           nascimento=fmt_data(a["Nascimento"]) if pd.notna(a["Nascimento"]) else "",
                           mae_txt=A._RE_ID.sub("", a["Mãe"]).strip(), mae_id=mae_id,
                           filhos=[_linha_animal(x, hoje) for _, x in filhos.iterrows()],
                           historico=A.historico(id_, dados["Manejo"], dados["Vendas"]),
                           pesos=hist_peso, peso=P.resumo(hist_peso, _rendimento()),
                           fotos=F.listar(id_), fotos_ativas=drive.configurado() or drive.cliente() is not None,
                           TIPOS_FOTO=TIPOS_FOTO, **_ctx_templates())


@app.route("/animais/<id_>/editar", methods=["GET", "POST"])
@login_required
def editar_animal(id_):
    df = A.carregar()
    a = A.por_id(df, id_)
    if a is None:
        flash("Animal não encontrado.", "error")
        return redirect(url_for("animais"))
    if request.method == "POST":
        _validar_csrf()
        dados = _dados_form(request.form)
        if not request.form.get("origem"):
            dados.pop("Origem")
        dados["Sexo"] = a["Sexo"]   # o form não tem mais sexo; sem categoria, mantém o antigo
        try:
            fazer_backup_seguro()
            for av in A.atualizar(id_, dados):
                flash(av, "warning")
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("editar_animal", id_=id_))
        flash("Cadastro atualizado!", "success")
        return redirect(url_for("ficha_animal", id_=id_))
    form = {"cor": a["Brinco Cor"], "numero": a["Brinco Nº"] if pd.notna(a["Brinco Nº"]) else "",
            "dono": a["Dono"], "categoria": a["Categoria"], "sexo": a["Sexo"], "raca": a["Raça"],
            "pelagem": a["Pelagem"], "sinais": a["Sinais"], "origem": a["Origem"],
            "nascimento": a["Nascimento"].strftime("%Y-%m-%d") if pd.notna(a["Nascimento"]) else "",
            "entrada": a["Entrada"].strftime("%Y-%m-%d") if pd.notna(a["Entrada"]) else "",
            "mae": a["Mãe"], "observacoes": a["Observações"], "ref_compra": a["Ref Compra"]}
    return render_template("form_animal.html", modo="editar", row=a, form=form, id_=id_,
                           **_ctx_templates())


@app.route("/animais/<id_>/baixa", methods=["POST"])
@login_required
def baixa_animal(id_):
    _validar_csrf()
    f = request.form
    status = f.get("status", "")
    try:
        fazer_backup_seguro()
        feitos = A.dar_baixa([id_], status, f.get("data") or None, responsavel=_membro_logado(),
                             registrar_morte=bool(f.get("registrar_morte")),
                             motivo=f.get("motivo", "").strip())
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("ficha_animal", id_=id_))
    if not feitos:
        flash("Esse animal já tinha saído.", "warning")
    elif status == "Morto":
        flash("Baixa por morte registrada" + (" (e a Morte/Perda no Manejo)." if f.get("registrar_morte") else "."), "success")
    else:
        flash("Marcado como vendido. Lembre de registrar o valor em Nova Venda.", "success")
    return redirect(url_for("ficha_animal", id_=id_))


@app.route("/animais/<id_>/excluir", methods=["POST"])
@login_required
def excluir_animal(id_):
    """Apaga um cadastro feito por engano (não mexe em Manejo/Vendas)."""
    _validar_csrf()
    df = A.carregar()
    if A.por_id(df, id_) is None:
        flash("Animal não encontrado.", "error")
        return redirect(url_for("animais"))
    fazer_backup_seguro()
    A._gravar(df[df["ID"] != id_])
    flash("Cadastro excluído.", "warning")
    return redirect(url_for("animais"))


# ══════════════════════════════════════════════════════════════════════════════
#  COMANDO DE VOZ
# ══════════════════════════════════════════════════════════════════════════════

def _ctx_voz():
    from routes_registros import _produtos_usados
    dados = _get_dados_cache()
    return {"df_animais": A.carregar(),
            "estoque": calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"]),
            "estoque_membro": calcular_estoque_por_membro(dados["Compras"], dados["Vendas"], dados["Manejo"]),
            "produtos_usados": _produtos_usados(dados["Manejo"]),
            "membro": _membro_logado()}


def _interpretar(corpo: dict) -> dict:
    texto = str(corpo.get("texto") or "")[:600]
    intencao = V.analisar(texto, _agora())
    resp = V.montar(intencao, _ctx_voz(), corpo.get("escolhas") or {})
    resp["pode_salvar"] = V.pode_salvar(resp)
    return resp


@app.route("/voz")
@login_required
def voz():
    return render_template("voz.html", cores_dono=A.cores_brinco(), NOMES=NOMES_MEMBROS)


def _json_auth():
    if not session.get("logado"):
        return jsonify({"ok": False, "erro": "login"}), 401
    token = request.headers.get("X-CSRF-Token") or (request.get_json(silent=True) or {}).get("csrf_token")
    if not token or token != session.get("csrf_token"):
        return jsonify({"ok": False, "erro": "csrf"}), 403
    return None


@app.route("/api/voz/interpretar", methods=["POST"])
def api_voz_interpretar():
    erro = _json_auth()
    if erro:
        return erro
    resp = _interpretar(request.get_json(silent=True) or {})
    resp.pop("payload", None)
    return jsonify({"ok": True, **resp})


@app.route("/api/voz/executar", methods=["POST"])
def api_voz_executar():
    """Reinterpreta o texto no servidor (não confia no que a tela mandou) e grava."""
    erro = _json_auth()
    if erro:
        return erro
    resp = _interpretar(request.get_json(silent=True) or {})
    if resp["acao"] == "ficha" and resp.get("payload"):
        return jsonify({"ok": True, "msg": "Abrindo ficha…",
                        "url": url_for("ficha_animal", id_=resp["payload"]["id"])})
    if not resp["pode_salvar"]:
        return jsonify({"ok": False, "erro": " ".join(resp["erros"]) or "Falta responder as perguntas.",
                        **{k: resp[k] for k in ("erros", "perguntas", "avisos")}}), 400
    try:
        msg, url = _executar(resp["payload"])
    except ValueError as e:
        return jsonify({"ok": False, "erro": str(e)}), 400
    return jsonify({"ok": True, "msg": msg, "url": url})


def _executar(p: dict):
    from routes_registros import gravar_compra, gravar_gasto, _salvar_venda, _brincos_do_form
    acao = p["acao"]
    membro = _membro_logado()
    if acao == "cadastro":
        reg = A.cadastrar([p["animal"]], registrado_por=membro, responsavel=membro)[0]
        extra = " + Nascimento no Manejo" if reg["Origem"] == "Nascimento" else ""
        return (f"🏷️ {A.fmt_brinco(reg['Brinco Cor'], reg['Brinco Nº'])} cadastrado{extra}.",
                url_for("ficha_animal", id_=reg["ID"]))
    if acao == "manejo":
        linha = p["linha"]
        salvar_linha("Manejo", [linha.get(c, "") for c in COLUNAS_MANEJO])
        return f"🩺 {linha['Tipo']} registrado ({linha['Qtd Cabeças']} cab.).", url_for("manejo")
    if acao == "morte":
        fazer_backup_seguro()
        feitos = A.dar_baixa(p["ids"], "Morto", p.get("data"), responsavel=membro,
                             registrar_morte=True, motivo=p.get("motivo", ""))
        return f"⚰️ Baixa de {len(feitos)} animal(is) registrada.", url_for("manejo")
    if acao == "compra":
        idx = gravar_compra(p["form"])
        if p["form"].get("brincar"):
            return "🛒 Compra registrada. Agora os brincos…", url_for("brincar_compra", idx=idx)
        return "🛒 Compra registrada.", url_for("compras")
    if acao == "venda":
        form = dict(p["form"])
        refs = form.pop("brincos", "")
        form["brincos_refs"] = refs
        if int(form.get("cabecas") or 0) <= 0:
            raise ValueError("Informe ao menos 1 cabeça.")
        _salvar_venda(form, _get_dados_cache())
        return "🤝 Venda registrada.", url_for("vendas")
    if acao == "gasto":
        dados = _get_dados_cache()
        gravar_gasto(p["form"], calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"]))
        return "💸 Gasto registrado.", url_for("gastos")
    raise ValueError("Ação desconhecida.")
