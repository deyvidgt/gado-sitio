#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_api_extras.py — Sítio Santo Antonio
APIs que estavam faltando no routes_api.py:
  - /api/calendario-manejo
  - /api/config-whatsapp  (GET e POST)
  - /api/enviar-lembrete-whatsapp
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from flask import request, jsonify
from db import carregar_aba
from config import ALERTAS_SAUDE, MEMBROS, NOMES_MEMBROS
from extensions import (
    app, _agora, login_required,
    _carregar_usuarios, _salvar_usuarios, BASE_DIR,
)

# ── Helpers internos ──────────────────────────────────────────────────────────

def _fmt_data_iso(ts) -> str | None:
    """Converte Timestamp para string YYYY-MM-DD (formato que o JS espera)."""
    if ts is None or (isinstance(ts, float) and pd.isna(ts)):
        return None
    if isinstance(ts, pd.Timestamp) and pd.notna(ts):
        return ts.strftime("%Y-%m-%d")
    return None

def _fmt_data_br(ts) -> str:
    if isinstance(ts, pd.Timestamp) and pd.notna(ts):
        return ts.strftime("%d/%m/%Y")
    return "—"


# ── /api/calendario-manejo ────────────────────────────────────────────────────

@app.route("/api/calendario-manejo")
@login_required
def api_calendario_manejo():
    """
    Retorna:
      hoje        — data atual YYYY-MM-DD
      eventos     — lista de manejos registrados (para o mini-calendário)
      proximas    — próximas intervenções previstas com status
    """
    hoje = _agora()
    df_man = carregar_aba("Manejo")

    # ── Eventos registrados (últimos 6 meses) ─────────────────────────
    eventos = []
    if not df_man.empty and "Data" in df_man.columns:
        corte = pd.Timestamp(hoje - timedelta(days=180))
        df_rec = df_man[df_man["Data"].notna() & (df_man["Data"] >= corte)]
        for _, row in df_rec.iterrows():
            data_iso = _fmt_data_iso(row.get("Data"))
            if data_iso:
                eventos.append({
                    "data":     data_iso,
                    "tipo":     str(row.get("Tipo", "") or ""),
                    "cabecas":  int(row.get("Qtd Cabeças", 0) or 0),
                    "desc":     str(row.get("Descrição", "") or ""),
                    "resp":     str(row.get("Responsável", "") or ""),
                })

    # ── Próximas intervenções previstas ───────────────────────────────
    proximas = []
    for tipo, intervalo_dias in ALERTAS_SAUDE.items():
        ultima_data = None
        ultima_data_br = None
        dias_restantes = None
        status = "sem_registro"
        data_prevista = None

        if not df_man.empty and "Tipo" in df_man.columns:
            df_tipo = df_man[df_man["Tipo"] == tipo]
            if not df_tipo.empty:
                ultima_ts = df_tipo["Data"].dropna().max()
                if pd.notna(ultima_ts):
                    ultima_data    = _fmt_data_iso(ultima_ts)
                    ultima_data_br = _fmt_data_br(ultima_ts)
                    proxima_ts     = ultima_ts + timedelta(days=intervalo_dias)
                    data_prevista  = _fmt_data_iso(proxima_ts)
                    dias_rest      = (proxima_ts.to_pydatetime() - hoje).days
                    dias_restantes = dias_rest

                    if dias_rest < 0:
                        status = "atrasado"
                    elif dias_rest <= 7:
                        status = "urgente"
                    elif dias_rest <= 21:
                        status = "proximo"
                    else:
                        status = "ok"

        proximas.append({
            "tipo":           tipo,
            "intervalo_dias": intervalo_dias,
            "ultima_data":    ultima_data_br,
            "ultima_data_iso": ultima_data,
            "data_prevista":  data_prevista,
            "dias_restantes": dias_restantes,
            "status":         status,
        })

    return jsonify({
        "hoje":    hoje.strftime("%Y-%m-%d"),
        "eventos": eventos,
        "proximas": proximas,
    })


# ── /api/config-whatsapp (GET + POST) ─────────────────────────────────────────

@app.route("/api/config-whatsapp", methods=["GET", "POST"])
@login_required
def api_config_whatsapp():
    from flask import session
    usuario = session.get("usuario", "")

    if request.method == "GET":
        usuarios = _carregar_usuarios()
        cfg = usuarios.get(usuario, {}).get("whatsapp", {})
        tem_apikey = bool(cfg.get("apikey", "").strip())
        return jsonify({
            "ok":               True,
            "telefone":         cfg.get("telefone", ""),
            "apikey_configurada": tem_apikey,
            "alertas_ativos":   cfg.get("alertas_ativos", True),
        })

    # POST — salvar configuração
    data = request.get_json(silent=True) or {}
    telefone = str(data.get("telefone", "")).strip().replace(" ", "").replace("-", "")
    apikey   = str(data.get("apikey", "")).strip()
    ativo    = bool(data.get("alertas_ativos", True))

    if not telefone or not apikey:
        return jsonify({"ok": False, "erro": "Telefone e API Key são obrigatórios."})

    usuarios = _carregar_usuarios()
    if usuario not in usuarios:
        return jsonify({"ok": False, "erro": "Usuário não encontrado."})

    usuarios[usuario]["whatsapp"] = {
        "telefone":      telefone,
        "apikey":        apikey,
        "alertas_ativos": ativo,
    }
    _salvar_usuarios(usuarios)
    return jsonify({"ok": True, "msg": "Configuração salva!"})


# ── /api/enviar-lembrete-whatsapp ─────────────────────────────────────────────

@app.route("/api/enviar-lembrete-whatsapp", methods=["POST"])
@login_required
def api_enviar_lembrete_whatsapp():
    """
    Envia uma mensagem via CallMeBot.
    Body JSON: { telefone, apikey, msg }
    """
    data     = request.get_json(silent=True) or {}
    telefone = str(data.get("telefone", "")).strip()
    apikey   = str(data.get("apikey",   "")).strip()
    msg      = str(data.get("msg",      "")).strip()

    if not telefone or not apikey or not msg:
        return jsonify({"ok": False, "erro": "telefone, apikey e msg são obrigatórios."})

    try:
        import requests as req
        resp = req.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": telefone, "text": msg, "apikey": apikey},
            timeout=20,
        )
        ok = resp.status_code == 200 and "message queued" in resp.text.lower()
        if ok:
            return jsonify({"ok": True,  "msg": "Mensagem enviada!"})
        else:
            return jsonify({"ok": False, "erro": f"CallMeBot: {resp.text[:200]}"})
    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)})
