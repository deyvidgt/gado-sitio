#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas de Visitas ao Sítio — Sítio Santo Antonio
"""
import os
import re
import threading
import time
from contextlib import contextmanager

from flask import render_template, request, redirect, url_for, flash, session, jsonify
from db import carregar_aba, fazer_backup
from calculos import calcular_estoque, calcular_estoque_ate_data
from config import MEMBROS, NOMES_MEMBROS
from extensions import (
    app, _agora, _validar_csrf, _gerar_csrf, login_required,
    _get_dados_cache, salvar_linha, reescrever_aba,
    _limpar_backups_antigos, fmt_data,
)


def _int_seguro(v) -> int:
    """Inteiro do formulário; vazio/inválido vira 0 em vez de erro 500."""
    try:
        return max(0, int(float(str(v).strip().replace(",", "."))))
    except (TypeError, ValueError):
        return 0


# ── Sugestões automáticas ─────────────────────────────────────────────────────

def _gerar_sugestoes_visita(f, estoque_esperado):
    sug = []
    gado_contado = _int_seguro(f.get("gado_contado"))
    if gado_contado > 0 and estoque_esperado > 0:
        if gado_contado < estoque_esperado:
            falt = estoque_esperado - gado_contado
            sug.append(f"⚠️ ALERTA: {falt} cabeça(s) não localizada(s)! Verificar pastagens vizinhas e cercas.")
        elif gado_contado > estoque_esperado:
            sug.append(f"ℹ️ {gado_contado - estoque_esperado} cabeça(s) a mais — possível animal de terceiro.")

    sal = f.get("sal_racao", "OK")
    if sal == "Baixo":       sug.append("🧂 Sal baixo — reabastecer nos próximos 2 a 3 dias.")
    elif sal in ("Vazio", "Meio Saco"):
        sug.append("🚨 Sal ESGOTADO — abastecer com urgência!" if sal == "Vazio" else "🧂 Sal no fim — reabastecer em breve.")

    racao = f.get("racao", "OK")
    if racao == "Baixo":     sug.append("🌾 Ração baixa — reabastecer nos próximos 2 a 3 dias.")
    elif racao in ("Vazio", "Meio Saco"):
        sug.append("🚨 Ração ESGOTADA — abastecer com urgência!" if racao == "Vazio" else "🌾 Ração no fim — reabastecer em breve.")

    prot = f.get("proteinado", "OK")
    if prot == "Baixo":      sug.append("🟡 Proteinado baixo — repor em breve.")
    elif prot in ("Vazio", "Meio Saco"):
        sug.append("🚨 Proteinado ESGOTADO — comprar urgente!" if prot == "Vazio" else "🟡 Proteinado no fim — repor em breve.")

    mato = f.get("mato", "Limpo")
    if mato == "Precisa Capinar": sug.append("🌿 Vegetação crescida — programar roçagem.")
    elif mato == "Muito Mato":    sug.append("🌿 Mato excessivo — roçagem urgente!")

    grama = f.get("grama", "Boa")
    if grama in ("Amarelando/Secando",): sug.append("🌾 Pastagem amarelando — monitorar.")
    elif grama == "Regular":  sug.append("🌱 Pastagem regular — considerar rotação ou adubação.")
    elif grama == "Escassa":  sug.append("🚨 Pastagem escassa — rotacionar IMEDIATAMENTE.")

    corrego = f.get("corrego", "Normal")
    if corrego == "Baixo":    sug.append("💧 Água baixa — monitorar e preparar alternativa.")
    elif corrego == "Seco":   sug.append("🚨 SEM ÁGUA — providenciar abastecimento urgente!")

    quintal = f.get("quintal", "OK")
    if quintal == "Precisa Atenção": sug.append("🏡 Quintal necessita atenção.")

    # Cisterna, caixa d'água e conteiner: apenas registrados (status + litros).
    # Por preferência da família, o sistema NÃO gera sugestão de reabastecimento
    # para esses reservatórios.

    choveu = f.get("choveu", "nao") == "sim"
    try:
        mm = float(str(f.get("chuva_mm", "0") or "0").replace(",", "."))
    except Exception:
        mm = 0.0

    if choveu and mm >= 50:   sug.append(f"🌧️ Chuva forte ({mm:g}mm) — verificar erosão e cercas.")
    elif choveu and mm >= 15: sug.append(f"🌦️ Boa chuva ({mm:g}mm) — pastagem deve se recuperar.")
    elif choveu and mm > 0:   sug.append(f"🌂 Chuva leve ({mm:g}mm).")
    elif choveu:              sug.append("🌧️ Chuva registrada — anotar os mm na próxima vez.")
    else:                     sug.append("☀️ Sem chuva — acompanhar estiagem.")

    colchao = f.get("estado_colchao", "")
    if colchao == "Alerta":    sug.append("🛏️ Colchão em alerta — programar troca em breve.")
    elif colchao == "Crítico": sug.append("🚨 Colchão crítico — TROCAR COM URGÊNCIA!")

    if not sug:
        sug.append("✅ Visita sem pendências — sítio em boas condições!")
    return " | ".join(sug)


# ── Notificação WhatsApp ao registrar visita ──────────────────────────────────

def _enviar_avisos_depois(resposta):
    """
    Envia os avisos de visita pendentes DEPOIS que a resposta saiu para o celular
    (response.call_on_close): quem registrou não espera, e roda no próprio
    processo do servidor (antes era uma thread, que o PythonAnywhere não garante).
    O aviso fica gravado em avisos_pendentes.json até sair — se a conexão cair,
    a próxima requisição de visita (ou a Task diária) envia.
    """
    import sitios
    slug = sitios.atual()   # a fila é do sítio deste pedido; o envio roda depois

    def _enviar():
        from extensions import _trava_sitio
        # Sem esperar muito: se a trava estiver ocupada, o aviso fica na fila e sai
        # no próximo envio (ou na Task diária).
        if not _trava_sitio.acquire(timeout=30):
            return
        try:
            sitios.ativar(slug)
            from alertas_whatsapp import enviar_avisos_pendentes
            n = enviar_avisos_pendentes()
            if n:
                app.logger.info(f"Aviso enviado para {n} destinatário(s)")
        except Exception as e:
            app.logger.error(f"Erro ao notificar via WhatsApp: {e}")
        finally:
            _trava_sitio.release()

    resposta.call_on_close(_enviar)
    return resposta


# ── Listar visitas ────────────────────────────────────────────────────────────

@app.route("/visitas")
@login_required
def visitas():
    df = carregar_aba("Visitas")
    ordem = request.args.get("ordem", "desc")
    if not df.empty and "Data" in df.columns:
        df = df.sort_values("Data", ascending=(ordem == "asc"), na_position="last")

    alertas = []
    if not df.empty:
        ultima = df.iloc[0] if ordem == "desc" else df.iloc[-1]
        try:
            falt = int(ultima.get("Gado Faltando") or 0)
        except Exception:
            falt = 0
        if falt > 0:
            alertas.append(("danger", f"⚠️ Na última visita, {falt} cabeça(s) estavam faltando!"))
        for campo, label in [("Sal/Ração", "Sal/Ração"), ("Proteinado", "Proteinado")]:
            v = str(ultima.get(campo, "OK") or "OK")
            if v == "Vazio":   alertas.append(("danger",  f"🚨 {label} ESGOTADO conforme última visita!"))
            elif v == "Baixo": alertas.append(("warning", f"⚠️ {label} está baixo — repor em breve."))
        corrego = str(ultima.get("Córrego/Água", "Normal") or "Normal")
        if corrego == "Seco":    alertas.append(("danger",  "🚨 Córrego/bebedouro SECO na última visita!"))
        elif corrego == "Baixo": alertas.append(("warning", "💧 Água no córrego estava baixa — verificar."))

    rows = []
    for real_idx, row in (df.iterrows() if not df.empty else []):
        d = row.to_dict()
        d["Data"] = fmt_data(d.get("Data"))
        d["_idx"] = int(real_idx)
        try:
            d["Gado Faltando"] = int(d.get("Gado Faltando") or 0)
        except Exception:
            d["Gado Faltando"] = 0
        rows.append(d)

    return render_template("lista_visitas.html", rows=rows, ordem=ordem, alertas=alertas)


# ── Nova visita ───────────────────────────────────────────────────────────────

def _id_envio_valido(v) -> str:
    v = (v or "").strip()
    return v if re.fullmatch(r"[0-9a-fA-F-]{8,64}", v) else ""


@contextmanager
def _trava_visitas(espera_max: float = 15.0):
    """
    Uma visita por vez entre "esse ID Envio já existe?" e a gravação. Sem isso,
    duas abas do celular reenviando a mesma visita ao mesmo tempo passavam as
    duas pela checagem e gravavam em dobro. Arquivo de trava na pasta de dados
    (vale para mais de um processo do servidor) + lock da thread.
    """
    from db import DATA_DIR
    caminho = os.path.join(DATA_DIR, ".visitas.lock")
    with _lock_visitas:
        inicio = time.time()
        while True:
            try:
                fd = os.open(caminho, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                try:   # trava esquecida por um processo que caiu
                    if time.time() - os.path.getmtime(caminho) > 60:
                        os.remove(caminho)
                        continue
                except OSError:
                    continue
                if time.time() - inicio > espera_max:
                    raise TimeoutError("Trava de visitas ocupada")
                time.sleep(0.05)
        try:
            yield
        finally:
            os.close(fd)
            try:
                os.remove(caminho)
            except OSError:
                pass


_lock_visitas = threading.Lock()


def _estoque_na_data(dados, data) -> int:
    """Gado esperado no dia da visita. A visita guardada offline pode chegar dias
    depois — se houve venda/compra no meio, o estoque de HOJE acusava cabeças
    "faltando" (ou sobrando) que não faltavam no dia."""
    import pandas as pd
    hoje = pd.Timestamp(_agora()).normalize()
    dia = pd.to_datetime(data, dayfirst=not re.match(r"\d{4}-", str(data or "")),
                         errors="coerce") if data else pd.NaT
    if pd.isna(dia) or dia.normalize() >= hoje:
        return calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    return calcular_estoque_ate_data(dados["Compras"], dados["Vendas"], dados["Manejo"],
                                     dia.normalize())


def _registrar_visita(f) -> dict:
    with _trava_visitas():
        return _registrar_visita_sem_trava(f)


def _registrar_visita_sem_trava(f) -> dict:
    """
    Grava uma visita a partir do formulário (enviado na hora ou guardado no
    celular sem internet). Retorna {"duplicada", "row", "estoque", "gado_falt"}.
    Se o mesmo "ID Envio" já existir (o celular reenviou porque não recebeu a
    confirmação), não grava de novo.
    """
    dados   = _get_dados_cache()
    estoque = _estoque_na_data(dados, f.get("data"))

    # Gravado como "id:<código>": um código só de dígitos virava NÚMERO na leitura
    # da planilha (pandas) e a checagem de duplicata falhava.
    id_envio = _id_envio_valido(f.get("id_envio"))
    chave_envio = f"id:{id_envio}" if id_envio else None
    if chave_envio:
        df_vis = carregar_aba("Visitas")
        if "ID Envio" in df_vis.columns and (df_vis["ID Envio"].astype(str) == chave_envio).any():
            return {"duplicada": True, "row": None, "estoque": estoque, "gado_falt": 0}

    data        = f.get("data") or _agora().strftime("%d/%m/%Y")
    responsavel = f.get("responsavel", "")
    gado_cnt    = _int_seguro(f.get("gado_contado"))
    gado_esp    = estoque
    gado_falt   = max(0, gado_esp - gado_cnt) if gado_cnt > 0 else 0

    sal      = f.get("sal_racao",  "OK")
    racao    = f.get("racao",      "OK")
    prot     = f.get("proteinado", "OK")
    mato     = f.get("mato",       "Limpo")
    grama    = f.get("grama",      "Boa")
    corrego  = f.get("corrego",    "Normal")
    quintal  = f.get("quintal",    "OK")
    cisterna = f.get("cisterna",   "OK")
    caixa_agua = f.get("caixa_agua", "Cheia")
    conteiner  = f.get("conteiner",  "Cheio")
    choveu   = "Sim" if f.get("choveu") == "sim" else "Não"
    estado_colchao = f.get("estado_colchao", "")
    colcho   = f.get("colcho", "")

    def _litros_safe(v):
        try:
            s = str(v).strip().replace(",", ".")
            return round(float(s), 1) if s else None
        except Exception:
            return None

    caixa_agua_litros = _litros_safe(f.get("caixa_agua_litros"))
    conteiner_litros  = _litros_safe(f.get("conteiner_litros"))

    try:
        chuva_mm = float(str(f.get("chuva_mm", "0") or "0").replace(",", "."))
    except Exception:
        chuva_mm = 0.0

    obs       = f.get("observacoes", "").strip()
    sugestoes = _gerar_sugestoes_visita(f, estoque)

    def _int_safe(v):
        try:
            return int(str(v).strip()) if v and str(v).strip() else None
        except Exception:
            return None

    sacos_sal   = _int_safe(f.get("sacos_sal"))
    sacos_racao = _int_safe(f.get("sacos_racao"))
    sacos_prot  = _int_safe(f.get("sacos_prot"))

    salvar_linha("Visitas", [
        data, responsavel,
        gado_cnt, gado_esp, gado_falt,
        sal, prot, mato, grama, corrego,
        quintal, cisterna,
        choveu, chuva_mm if chuva_mm > 0 else None,
        obs, sugestoes,
        sacos_sal, sacos_prot,
        caixa_agua, caixa_agua_litros,
        conteiner, conteiner_litros,
        racao, sacos_racao,
        chave_envio,
        estado_colchao or None,
        colcho or None,
    ])

    row = {
        "Responsável":    responsavel,
        "Data":           data,
        "Gado Contado":   gado_cnt,
        "Gado Esperado":  gado_esp,
        "Gado Faltando":  gado_falt,
        "Sal/Ração":      sal,
        "Ração":          racao,
        "Proteinado":     prot,
        "Mato/Vegetação": mato,
        "Grama/Pastagem": grama,
        "Córrego/Água":   corrego,
        "Quintal":        quintal,
        "Cisterna":       cisterna,
        "Choveu":         choveu,
        "Chuva mm":       chuva_mm if chuva_mm > 0 else 0,
        "Observações":    obs,
        "Sugestões":      sugestoes,
        "Estado Colchão": estado_colchao or "Não verificado",
    }
    try:
        from alertas_whatsapp import montar_msg_nova_visita, guardar_aviso_pendente
        guardar_aviso_pendente(montar_msg_nova_visita(row, estoque))
    except Exception as e:
        app.logger.error(f"Não foi possível guardar o aviso da visita: {e}")
    return {"duplicada": False, "row": row, "estoque": estoque, "gado_falt": gado_falt}


@app.route("/visitas/nova", methods=["GET", "POST"])
@login_required
def nova_visita():
    if request.method == "POST":
        # Caminho sem JavaScript (normalmente o formulário envia por /api/visitas).
        _validar_csrf()
        r = _registrar_visita(request.form)
        if r["duplicada"]:
            flash("Esta visita já tinha sido registrada.", "info")
            return _enviar_avisos_depois(redirect(url_for("visitas")))
        if r["gado_falt"] > 0:
            flash(f"⚠️ Visita salva — mas {r['gado_falt']} cabeça(s) estão faltando!", "warning")
        else:
            flash("✅ Visita registrada! Avisando a família pelo WhatsApp…", "success")
        return _enviar_avisos_depois(redirect(url_for("visitas")))

    dados   = _get_dados_cache()
    estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])
    return render_template("form_visita.html", estoque=estoque,
                           MEMBROS=MEMBROS, NOMES=NOMES_MEMBROS,
                           hoje=_agora().strftime("%Y-%m-%d"))


@app.route("/api/csrf")
def api_csrf():
    """Token CSRF da sessão atual — o celular usa ao enviar visitas guardadas
    offline (a página guardada pode ter o token de uma sessão antiga)."""
    if not session.get("logado"):
        return jsonify({"ok": False, "erro": "login"}), 401
    return jsonify({"ok": True, "csrf_token": _gerar_csrf()})


@app.route("/api/visitas", methods=["POST"])
def api_registrar_visita():
    """
    Recebe a visita do celular — na hora, ou depois, quando estava sem internet.
    Responde sempre em JSON (nunca redireciona para o login): o celular precisa
    saber se tira a visita da fila ou tenta de novo mais tarde.
    """
    if not session.get("logado"):
        return jsonify({"ok": False, "erro": "login"}), 401
    token = request.form.get("csrf_token", "")
    if not token or token != session.get("csrf_token"):
        return jsonify({"ok": False, "erro": "csrf"}), 403
    r = _registrar_visita(request.form)
    # Também no reenvio duplicado: se a 1ª conexão caiu antes de avisar, avisa agora.
    return _enviar_avisos_depois(jsonify({"ok": True, "duplicada": r["duplicada"],
                                          "gado_faltando": r["gado_falt"]}))


# ── Excluir visita ────────────────────────────────────────────────────────────

@app.route("/visitas/excluir/<int:idx>", methods=["POST"])
@login_required
def excluir_visita(idx):
    _validar_csrf()
    fazer_backup()
    _limpar_backups_antigos()
    df = carregar_aba("Visitas")
    if df.empty or idx not in df.index:
        flash("Registro não encontrado.", "error")
        return redirect(url_for("visitas"))
    df = df.drop(index=idx).reset_index(drop=True)
    reescrever_aba("Visitas", df)
    flash("Visita excluída.", "success")
    return redirect(url_for("visitas"))
