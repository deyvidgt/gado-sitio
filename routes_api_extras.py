#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_api_extras.py — Sítio Santo Antonio
APIs extras: calendário de manejo, configuração e envio WhatsApp.
"""
import pandas as pd
from datetime import timedelta
from flask import request, jsonify, session
from db import carregar_aba, get_alertas_saude
from saude import ultima_data, brucelose_proxima
from alertas_whatsapp import TIPOS_RECEBER, receber_de
from extensions import app, _agora, login_required, _safe, _carregar_usuarios, _salvar_usuarios


def _iso(ts):
    if isinstance(ts, pd.Timestamp) and pd.notna(ts):
        return ts.strftime("%Y-%m-%d")
    return None


def _br(ts):
    if isinstance(ts, pd.Timestamp) and pd.notna(ts):
        return ts.strftime("%d/%m/%Y")
    return "—"


def _txt(v) -> str:
    """Texto de célula sem 'nan'/None."""
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()


@app.route("/api/calendario-manejo")
@login_required
def api_calendario_manejo():
    hoje = _agora()
    corte = pd.Timestamp(hoje - timedelta(days=365))
    eventos = []

    # ── Manejo ──────────────────────────────────────────────────────────────
    df_man = carregar_aba("Manejo")
    if not df_man.empty and "Data" in df_man.columns:
        for _, row in df_man[df_man["Data"].notna() & (df_man["Data"] >= corte)].iterrows():
            d = _iso(row.get("Data"))
            if d:
                eventos.append({
                    "data":    d,
                    "categoria": "manejo",
                    "tipo":    str(row.get("Tipo", "") or ""),
                    "cabecas": int(_safe(row.get("Qtd Cabeças"))),
                    "desc":    " · ".join(x for x in (
                                   _txt(row.get("Produto")), _txt(row.get("Descrição"))) if x),
                    "resumo":  str(row.get("Tipo", "") or "Manejo"),
                })

    # ── Visitas ──────────────────────────────────────────────────────────────
    df_vis = carregar_aba("Visitas")
    if not df_vis.empty and "Data" in df_vis.columns:
        for _, row in df_vis[df_vis["Data"].notna() & (df_vis["Data"] >= corte)].iterrows():
            d = _iso(row.get("Data"))
            if d:
                resp  = str(row.get("Responsável", "") or "")
                cont  = int(_safe(row.get("Gado Contado")))
                esper = int(_safe(row.get("Gado Esperado")))
                chuva = str(row.get("Chuva mm", "") or "")
                choveu= str(row.get("Choveu", "") or "")
                grama = str(row.get("Grama/Pastagem", "") or "")
                agua  = str(row.get("Córrego/Água", "") or "")
                sal   = str(row.get("Sal/Ração", "") or "")
                obs   = str(row.get("Observações", "") or "")
                # Montar descrição resumida
                chuva_txt = f"{chuva}mm" if chuva and chuva not in ("nan","") else ("Sim" if choveu=="Sim" else "Não")
                partes = []
                if cont:    partes.append(f"{cont}/{esper} cab.")
                if grama:   partes.append(f"Pasto: {grama}")
                if agua:    partes.append(f"Água: {agua}")
                if sal:     partes.append(f"Sal: {sal}")
                if chuva_txt: partes.append(f"Chuva: {chuva_txt}")
                eventos.append({
                    "data":        d,
                    "categoria":   "visita",
                    "tipo":        "Visita",
                    "resumo":      f"Visita — {resp}" if resp else "Visita",
                    "cabecas":     cont,
                    "desc":        " | ".join(partes),
                    "responsavel": resp,
                    "chuva":       chuva_txt,
                    "grama":       grama,
                    "obs":         obs,
                })

    # ── Compras ──────────────────────────────────────────────────────────────
    df_comp = carregar_aba("Compras")
    if not df_comp.empty and "Data" in df_comp.columns:
        for _, row in df_comp[df_comp["Data"].notna() & (df_comp["Data"] >= corte)].iterrows():
            d = _iso(row.get("Data"))
            if d:
                qtd  = int(_safe(row.get("Qtd Cabeças")))
                val  = _safe(row.get("Valor Total (R$)"))
                vpcab= _safe(row.get("Valor/Cabeça (R$)"))
                desc = str(row.get("Descrição", "") or "")
                desc = "" if desc == "nan" else desc
                val_fmt = f"R$ {val:,.2f}".replace(",","X").replace(".",",").replace("X",".")
                eventos.append({
                    "data":      d,
                    "categoria": "compra",
                    "tipo":      "Compra",
                    "resumo":    f"Compra — {qtd} cab.",
                    "cabecas":   qtd,
                    "desc":      f"{qtd} cab. · {val_fmt}" + (f" · {desc}" if desc else ""),
                    "valor":     round(val, 2),
                })

    # ── Vendas ───────────────────────────────────────────────────────────────
    df_vend = carregar_aba("Vendas")
    if not df_vend.empty and "Data" in df_vend.columns:
        for _, row in df_vend[df_vend["Data"].notna() & (df_vend["Data"] >= corte)].iterrows():
            d = _iso(row.get("Data"))
            if d:
                qtd  = int(_safe(row.get("Qtd Cabeças")))
                val  = _safe(row.get("Valor Total (R$)"))
                arr  = _safe(row.get("Valor Arroba (R$)"))
                desc = str(row.get("Descrição", "") or "")
                desc = "" if desc == "nan" else desc
                val_fmt = f"R$ {val:,.2f}".replace(",","X").replace(".",",").replace("X",".")
                arr_txt = f" · @R$ {arr:,.2f}".replace(",","X").replace(".",",").replace("X",".") if arr else ""
                eventos.append({
                    "data":      d,
                    "categoria": "venda",
                    "tipo":      "Venda",
                    "resumo":    f"Venda — {qtd} cab.",
                    "cabecas":   qtd,
                    "desc":      f"{qtd} cab. · {val_fmt}{arr_txt}" + (f" · {desc}" if desc else ""),
                    "valor":     round(val, 2),
                })

    # ── Gastos ───────────────────────────────────────────────────────────────
    df_gast = carregar_aba("Gastos")
    if not df_gast.empty and "Data" in df_gast.columns:
        for _, row in df_gast[df_gast["Data"].notna() & (df_gast["Data"] >= corte)].iterrows():
            d = _iso(row.get("Data"))
            if d:
                val  = _safe(row.get("Valor Total (R$)"))
                desc = str(row.get("Descrição", "") or "")
                desc = "" if desc in ("nan", "None") else desc
                tipo = str(row.get("Tipo", "") or "")
                tipo = "" if tipo in ("nan", "None") else tipo
                if not desc and not tipo and val == 0:
                    continue  # pular linha vazia
                val_fmt = f"R$ {val:,.2f}".replace(",","X").replace(".",",").replace("X",".")
                label = tipo or desc or "Gasto"
                resumo = f"{label[:25]}" if label else "Gasto"
                eventos.append({
                    "data":      d,
                    "categoria": "gasto",
                    "tipo":      "Gasto",
                    "resumo":    resumo,
                    "cabecas":   0,
                    "desc":      f"{tipo}" + (f" · {desc}" if desc and desc != tipo else "") + f" · {val_fmt}",
                    "valor":     round(val, 2),
                })

    # ── Próximas intervenções de saúde ──────────────────────────────────────
    proximas = []
    for tipo, intervalo in get_alertas_saude().items():
        status    = "sem_registro"
        ultima_br = None
        dias_rest = None
        prevista  = None
        ult = ultima_data(df_man, tipo)
        if ult is not None:
            ultima_br = _br(ult)
            prox = ult + timedelta(days=intervalo)
            prevista  = _iso(prox)
            # Compara DATAS (sem hora): com a hora atual, no próprio dia do
            # vencimento dava −1 ("atrasado") e na véspera dava 0.
            dias_rest = (prox.normalize() - pd.Timestamp(hoje).normalize()).days
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

    proximas.append(brucelose_proxima(df_man, hoje))

    return jsonify({
        "hoje":    hoje.strftime("%Y-%m-%d"),
        "eventos": eventos,
        "proximas": proximas,
    })


@app.route("/api/config-whatsapp-todos")
@login_required
def api_config_whatsapp_todos():
    """Retorna a config de WhatsApp de todos os usuários (sem expor as keys)."""
    todos = _carregar_usuarios()
    resultado = []
    for u, info in todos.items():
        wpp = info.get("whatsapp", {})
        resultado.append({
            "usuario":    u,
            "telefone":   wpp.get("telefone", ""),
            "bot_number": wpp.get("bot_number", ""),
            "configurado": bool(wpp.get("apikey", "").strip() and wpp.get("telefone", "").strip()),
            "alertas_ativos": wpp.get("alertas_ativos", True),
            "receber":    receber_de(wpp),
        })
    return jsonify({"ok": True, "usuarios": resultado})



@app.route("/api/config-whatsapp", methods=["GET", "POST"])
@login_required
def api_config_whatsapp():
    usuario = session.get("usuario", "")
    if request.method == "GET":
        cfg = _carregar_usuarios().get(usuario, {}).get("whatsapp", {})
        return jsonify({
            "ok":                True,
            "telefone":          cfg.get("telefone", ""),
            "bot_number":        cfg.get("bot_number", "+34644663262"),
            "apikey_configurada": bool(cfg.get("apikey", "").strip()),
            "alertas_ativos":    cfg.get("alertas_ativos", True),
            "receber":           receber_de(cfg),
        })

    data = request.get_json(silent=True) or {}
    tel      = str(data.get("telefone",   "")).strip().replace(" ", "").replace("-", "")
    key      = str(data.get("apikey",     "")).strip()
    bot_num  = str(data.get("bot_number", "")).strip().replace(" ", "")
    if not tel:
        return jsonify({"ok": False, "erro": "Telefone obrigatório."})

    usuarios = _carregar_usuarios()
    if usuario not in usuarios:
        return jsonify({"ok": False, "erro": "Usuário não encontrado."})

    cfg_atual = usuarios[usuario].get("whatsapp", {})

    # Se a key não foi enviada, manter a que já está salva
    key_salva = key if key else cfg_atual.get("apikey", "")
    if not key_salva:
        return jsonify({"ok": False, "erro": "API Key obrigatória na primeira configuração."})

    # Só as 6 chaves conhecidas, como bool; sem "receber" no corpo, mantém o salvo
    # (este dicionário é recriado do zero, então senão a escolha se perderia).
    if isinstance(data.get("receber"), dict):
        receber = {t: bool(data["receber"].get(t, True)) for t in TIPOS_RECEBER}
    else:
        receber = receber_de(cfg_atual)
        if "receber" not in cfg_atual:
            receber = None

    usuarios[usuario]["whatsapp"] = {
        "telefone":      tel,
        "apikey":        key_salva,
        "bot_number":    bot_num or cfg_atual.get("bot_number", "+34644663262"),
        "alertas_ativos": bool(data.get("alertas_ativos", True)),
    }
    if receber is not None:
        usuarios[usuario]["whatsapp"]["receber"] = receber
    _salvar_usuarios(usuarios)
    return jsonify({"ok": True, "msg": "Configuração salva!"})


def _enviar_callmebot(tel: str, key: str, msg: str) -> dict:
    """
    Utilitário central de envio via CallMeBot.
    Retorna {"ok": bool, "erro": str|None} com mensagens de erro claras.
    """
    try:
        import requests as req
        r = req.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": tel, "text": msg, "apikey": key},
            timeout=20,
        )
        texto = r.text.lower()
        ok = r.status_code == 200 and "message queued" in texto

        if not ok:
            # Detectar erros específicos do CallMeBot
            if "phone number not correct" in texto or "incorrect phone" in texto:
                erro = (
                    "Número de telefone inválido ou não autorizado. "
                    "Verifique se você enviou 'I allow callmebot to send me messages' "
                    "para o número do bot e se o telefone está correto."
                )
            elif "apikey" in texto or "api key" in texto or "not found" in texto:
                erro = (
                    "API Key inválida ou expirada. "
                    "O número do bot CallMeBot pode ter mudado — "
                    "verifique em callmebot.com e atualize o número do bot em ⚙️ Configurações → WhatsApp."
                )
            elif r.status_code == 403:
                erro = (
                    "Acesso negado pelo CallMeBot (erro 403). "
                    "Possível mudança no número do bot — "
                    "confira o número atual em callmebot.com e atualize em ⚙️ Configurações → WhatsApp."
                )
            else:
                erro = f"CallMeBot retornou erro: {r.text[:200]}"
            return {"ok": False, "erro": erro}

        return {"ok": True, "erro": None}

    except Exception as e:
        msg_e = str(e)
        if any(k in msg_e for k in ("ProxyError", "Max retries", "ConnectionError",
                                     "Tunnel connection", "timeout")):
            return {
                "ok": False,
                "erro": (
                    "Servidor sem acesso ao CallMeBot (restrição de rede do PythonAnywhere). "
                    "O envio funciona normalmente pelo celular ou pelo script alertas_whatsapp.py local."
                ),
            }
        return {"ok": False, "erro": f"Erro inesperado: {msg_e}"}


@app.route("/api/enviar-lembrete-whatsapp", methods=["POST"])
@login_required
def api_enviar_lembrete_whatsapp():
    data = request.get_json(silent=True) or {}
    tel  = str(data.get("telefone", "")).strip()
    key  = str(data.get("apikey",   "")).strip()
    msg  = str(data.get("msg",      "")).strip()

    if not tel or not key or not msg:
        return jsonify({"ok": False, "erro": "telefone, apikey e msg são obrigatórios."})

    return jsonify(_enviar_callmebot(tel, key, msg))


@app.route("/api/enviar-teste-whatsapp", methods=["POST"])
@login_required
def api_enviar_teste_whatsapp():
    """
    Envia mensagem de teste para o usuário logado usando a API Key
    já salva no servidor — sem precisar que o frontend a conheça.
    """
    usuario = session.get("usuario", "")
    cfg     = _carregar_usuarios().get(usuario, {}).get("whatsapp", {})
    tel     = cfg.get("telefone",   "").strip()
    key     = cfg.get("apikey",     "").strip()
    ativo   = cfg.get("alertas_ativos", True)

    if not tel or not key:
        return jsonify({
            "ok":   False,
            "erro": "WhatsApp não configurado. Vá em ⚙️ Configurações → WhatsApp e salve primeiro."
        })

    from extensions import _agora
    msg = (
        f"🐄 *Sítio Santo Antonio*\n"
        f"📤 Teste de notificação — {_agora().strftime('%d/%m/%Y %H:%M')}\n"
        f"✅ Sistema funcionando! Alertas {'ativos' if ativo else 'pausados'}."
    )
    return jsonify(_enviar_callmebot(tel, key, msg))


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
    if not ev.wait(timeout=30):   # aguarda até 30s para dar feedback real
        # Ainda enviando (CallMeBot lento): antes caía no "nenhum WhatsApp configurado".
        return jsonify({"ok": True, "enviados": None,
                        "msg": "Enviando os alertas… pode levar alguns minutos para chegar."})
    if resultado["erro"]:
        return jsonify({"ok": False, "erro": resultado["erro"]})
    if resultado["enviados"] == 0:
        return jsonify({"ok": False, "erro": "Nenhum WhatsApp configurado ou nenhum usuário com alertas ativos."})
    return jsonify({"ok": True, "enviados": resultado["enviados"],
                    "msg": f"Alertas enviados para {resultado['enviados']} destinatário(s)!"})
