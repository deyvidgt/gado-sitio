#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_api_extras.py — Sítio Santo Antonio
APIs extras: calendário de manejo, configuração e envio WhatsApp.
"""
import pandas as pd
from datetime import timedelta
from flask import request, jsonify, session
from db import carregar_aba
from config import ALERTAS_SAUDE
from extensions import app, _agora, login_required, _carregar_usuarios, _salvar_usuarios


def _iso(ts):
    if isinstance(ts, pd.Timestamp) and pd.notna(ts):
        return ts.strftime("%Y-%m-%d")
    return None


def _br(ts):
    if isinstance(ts, pd.Timestamp) and pd.notna(ts):
        return ts.strftime("%d/%m/%Y")
    return "—"


@app.route("/api/calendario-manejo")
@login_required
def api_calendario_manejo():
    hoje = _agora()
    df_man = carregar_aba("Manejo")
    eventos = []
    if not df_man.empty and "Data" in df_man.columns:
        corte = pd.Timestamp(hoje - timedelta(days=180))
        mask = df_man["Data"].notna() & (df_man["Data"] >= corte)
        for _, row in df_man[mask].iterrows():
            d = _iso(row.get("Data"))
            if d:
                eventos.append({
                    "data":    d,
                    "tipo":    str(row.get("Tipo", "") or ""),
                    "cabecas": int(row.get("Qtd Cabeças", 0) or 0),
                    "desc":    str(row.get("Descrição", "") or ""),
                })

    proximas = []
    for tipo, intervalo in ALERTAS_SAUDE.items():
        status    = "sem_registro"
        ultima_br = None
        dias_rest = None
        prevista  = None
        if not df_man.empty and "Tipo" in df_man.columns:
            df_t = df_man[df_man["Tipo"] == tipo]
            if not df_t.empty:
                ult = df_t["Data"].dropna().max()
                if pd.notna(ult):
                    ultima_br = _br(ult)
                    prox = ult + timedelta(days=intervalo)
                    prevista  = _iso(prox)
                    dias_rest = (prox.to_pydatetime() - hoje).days
                    status = (
                        "atrasado" if dias_rest < 0 else
                        "urgente"  if dias_rest <= 7 else
                        "proximo"  if dias_rest <= 21 else "ok"
                    )
        proximas.append({
            "tipo":           tipo,
            "intervalo_dias": intervalo,
            "ultima_data":    ultima_br,
            "data_prevista":  prevista,
            "dias_restantes": dias_rest,
            "status":         status,
        })

    return jsonify({
        "hoje":    hoje.strftime("%Y-%m-%d"),
        "eventos": eventos,
        "proximas": proximas,
    })


@app.route("/api/config-whatsapp", methods=["GET", "POST"])
@login_required
def api_config_whatsapp():
    usuario = session.get("usuario", "")
    if request.method == "GET":
        cfg = _carregar_usuarios().get(usuario, {}).get("whatsapp", {})
        return jsonify({
            "ok":                True,
            "telefone":          cfg.get("telefone", ""),
            "apikey_configurada": bool(cfg.get("apikey", "").strip()),
            "alertas_ativos":    cfg.get("alertas_ativos", True),
        })

    data = request.get_json(silent=True) or {}
    tel  = str(data.get("telefone", "")).strip().replace(" ", "").replace("-", "")
    key  = str(data.get("apikey",   "")).strip()
    if not tel or not key:
        return jsonify({"ok": False, "erro": "Telefone e API Key obrigatórios."})

    usuarios = _carregar_usuarios()
    if usuario not in usuarios:
        return jsonify({"ok": False, "erro": "Usuário não encontrado."})

    usuarios[usuario]["whatsapp"] = {
        "telefone":      tel,
        "apikey":        key,
        "alertas_ativos": bool(data.get("alertas_ativos", True)),
    }
    _salvar_usuarios(usuarios)
    return jsonify({"ok": True, "msg": "Configuração salva!"})


@app.route("/api/enviar-lembrete-whatsapp", methods=["POST"])
@login_required
def api_enviar_lembrete_whatsapp():
    data = request.get_json(silent=True) or {}
    tel  = str(data.get("telefone", "")).strip()
    key  = str(data.get("apikey",   "")).strip()
    msg  = str(data.get("msg",      "")).strip()

    if not tel or not key or not msg:
        return jsonify({"ok": False, "erro": "telefone, apikey e msg são obrigatórios."})

    try:
        import requests as req
        r = req.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": tel, "text": msg, "apikey": key},
            timeout=20,
        )
        ok = r.status_code == 200 and "message queued" in r.text.lower()
        return jsonify({"ok": ok, "erro": None if ok else r.text[:200]})
    except Exception as e:
        msg_erro = str(e)
        # Detectar falha de proxy/rede no PythonAnywhere
        if any(k in msg_erro for k in ("ProxyError", "Max retries", "ConnectionError",
                                        "Tunnel connection", "403", "timeout")):
            msg_erro = ("Servidor sem acesso ao CallMeBot (restrição de rede). "
                        "Tente novamente ou use o alertas_whatsapp.py localmente.")
        return jsonify({"ok": False, "erro": msg_erro})


@app.route("/api/enviar-alertas-familia", methods=["POST"])
@login_required
def api_enviar_alertas_familia():
    """
    Monta os alertas reais do sistema (manejo, visita, financeiro)
    e envia para TODOS os usuários com WhatsApp configurado.
    Roda em background thread para não travar a resposta.
    """
    import threading

    def _disparar():
        try:
            from alertas_whatsapp import montar_alertas, montar_mensagem_alertas, enviar_para_familia
            alertas  = montar_alertas()
            msg      = montar_mensagem_alertas(alertas)
            enviados = enviar_para_familia(msg)
            app.logger.info(f"Alertas manuais enviados para {enviados} destinatário(s)")
            return enviados
        except Exception as e:
            app.logger.error(f"Erro ao enviar alertas família: {e}")
            return 0

    # Executa em thread para responder imediatamente ao browser
    resultado = {"enviados": 0, "erro": None}
    ev = threading.Event()

    def _run():
        try:
            resultado["enviados"] = _disparar()
        except Exception as e:
            resultado["erro"] = str(e)
        finally:
            ev.set()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    ev.wait(timeout=30)   # aguarda até 30s para dar feedback real

    if resultado["erro"]:
        return jsonify({"ok": False, "erro": resultado["erro"]})
    if resultado["enviados"] == 0:
        return jsonify({"ok": False, "erro": "Nenhum WhatsApp configurado ou nenhum usuário com alertas ativos."})
    return jsonify({"ok": True, "enviados": resultado["enviados"],
                    "msg": f"Alertas enviados para {resultado['enviados']} destinatário(s)!"})
