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
from alertas_whatsapp import TIPOS_RECEBER, receber_de, enviar_whatsapp_resultado
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
    """Retorna a config de WhatsApp dos usuários (sem expor as keys). Não-admin vê só
    quem tem acesso ao sítio atual — telefone de um sítio não aparece no outro."""
    from routes_usuarios import _usuarios_visiveis
    todos = _usuarios_visiveis(_carregar_usuarios())
    resultado = []
    for u, info in todos.items():
        wpp = info.get("whatsapp", {}) if isinstance(info, dict) else {}
        if not isinstance(wpp, dict):
            wpp = {}
        telefone = wpp.get("telefone")
        bot_number = wpp.get("bot_number")
        apikey = wpp.get("apikey")
        resultado.append({
            "usuario":    u,
            "telefone":   telefone if isinstance(telefone, str) else "",
            "bot_number": bot_number if isinstance(bot_number, str) else "",
            "configurado": bool(isinstance(apikey, str) and apikey.strip()
                                and isinstance(telefone, str) and telefone.strip()),
            "alertas_ativos": wpp.get("alertas_ativos") if isinstance(wpp.get("alertas_ativos"), bool) else True,
            "receber":    receber_de(wpp),
        })
    return jsonify({"ok": True, "usuarios": resultado})



@app.route("/api/config-whatsapp", methods=["GET", "POST"])
@login_required
def api_config_whatsapp():
    usuario = session.get("usuario", "")
    if request.method == "GET":
        registro = _carregar_usuarios().get(usuario, {})
        cfg = registro.get("whatsapp", {}) if isinstance(registro, dict) else {}
        if not isinstance(cfg, dict):
            cfg = {}
        api_key = cfg.get("apikey")
        bot_number = cfg.get("bot_number")
        return jsonify({
            "ok":                True,
            "telefone":          cfg.get("telefone", "") if isinstance(cfg.get("telefone"), str) else "",
            "bot_number":        bot_number if isinstance(bot_number, str) else "+34644663262",
            "apikey_configurada": bool(api_key.strip()) if isinstance(api_key, str) else False,
            "alertas_ativos":    cfg.get("alertas_ativos") if isinstance(cfg.get("alertas_ativos"), bool) else True,
            "receber":           receber_de(cfg),
        })

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"ok": False, "erro": "Envie uma configuração JSON válida."}), 400
    tel = str(data.get("telefone", "")).strip().replace(" ", "").replace("-", "")
    key = data.get("apikey", "")
    bot_num = str(data.get("bot_number", "")).strip().replace(" ", "")
    if not tel.isdigit() or not 8 <= len(tel) <= 15:
        return jsonify({"ok": False, "erro": "Telefone inválido. Use DDI + DDD + número, apenas dígitos."}), 400
    if bot_num and (not bot_num.startswith("+") or not bot_num[1:].isdigit()
                    or not 8 <= len(bot_num[1:]) <= 15):
        return jsonify({"ok": False, "erro": "Número do bot inválido. Informe o número internacional com +."}), 400
    if not isinstance(key, str):
        return jsonify({"ok": False, "erro": "API Key inválida."}), 400
    key = key.strip()
    if "alertas_ativos" in data and not isinstance(data["alertas_ativos"], bool):
        return jsonify({"ok": False, "erro": "A opção de alertas ativos precisa ser verdadeira ou falsa."}), 400

    usuarios = _carregar_usuarios()
    if usuario not in usuarios:
        return jsonify({"ok": False, "erro": "Usuário não encontrado."}), 404

    if not isinstance(usuarios[usuario], dict):
        usuarios[usuario] = {}
    cfg_atual = usuarios[usuario].get("whatsapp", {})
    if not isinstance(cfg_atual, dict):
        cfg_atual = {}

    # Se a key não foi enviada, manter a que já está salva
    key_salva = key if key else cfg_atual.get("apikey", "")
    if not isinstance(key_salva, str) or not key_salva.strip():
        return jsonify({"ok": False, "erro": "API Key obrigatória na primeira configuração."}), 400

    # Só as 6 chaves conhecidas, como bool; sem "receber" no corpo, mantém o salvo
    # (este dicionário é recriado do zero, então senão a escolha se perderia).
    if isinstance(data.get("receber"), dict):
        receber = receber_de(cfg_atual)
        for tipo in TIPOS_RECEBER:
            if tipo in data["receber"]:
                if not isinstance(data["receber"][tipo], bool):
                    return jsonify({"ok": False, "erro": f"A preferência '{tipo}' precisa ser verdadeira ou falsa."}), 400
                receber[tipo] = data["receber"][tipo]
    elif "receber" in data:
        return jsonify({"ok": False, "erro": "As preferências de recebimento precisam estar em um objeto."}), 400
    else:
        receber = receber_de(cfg_atual)

    alertas_ativos = cfg_atual.get("alertas_ativos")
    if not isinstance(alertas_ativos, bool):
        alertas_ativos = True
    alertas_ativos = data.get("alertas_ativos", alertas_ativos)
    bot_salvo = cfg_atual.get("bot_number")
    if not isinstance(bot_salvo, str) or not bot_salvo.strip():
        bot_salvo = "+34644663262"
    usuarios[usuario]["whatsapp"] = {
        "telefone":      tel,
        "apikey":        key_salva.strip(),
        "bot_number":    bot_num or bot_salvo,
        "alertas_ativos": alertas_ativos,
        "receber": receber,
    }
    _salvar_usuarios(usuarios)
    return jsonify({"ok": True, "msg": "Configuração salva!"})


def _enviar_callmebot(tel: str, key: str, msg: str) -> dict:
    """
    Utilitário central de envio via CallMeBot.
    Retorna {"ok": bool, "erro": str|None} com mensagens de erro claras.
    """
    return enviar_whatsapp_resultado(tel, key, msg)


@app.route("/api/enviar-lembrete-whatsapp", methods=["POST"])
@login_required
def api_enviar_lembrete_whatsapp():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"ok": False, "erro": "Envie os dados do lembrete em JSON."}), 400
    msg = data.get("msg")
    if not isinstance(msg, str) or not msg.strip() or len(msg) > 4000:
        return jsonify({"ok": False, "erro": "A mensagem é obrigatória e deve ter até 4.000 caracteres."}), 400

    usuario = _carregar_usuarios().get(session.get("usuario", ""), {})
    cfg = usuario.get("whatsapp", {}) if isinstance(usuario, dict) else {}
    if not isinstance(cfg, dict):
        cfg = {}
    tel = cfg.get("telefone")
    key = cfg.get("apikey")
    tel = tel.strip() if isinstance(tel, str) else ""
    key = key.strip() if isinstance(key, str) else ""
    if not tel or not key:
        return jsonify({"ok": False, "erro": "Configure seu WhatsApp antes de enviar lembretes."}), 400

    # Compatibilidade com clientes antigos sem permitir que usem a API Key salva
    # para enviar mensagens a telefones diferentes do próprio usuário.
    tel_solicitado = data.get("telefone")
    if tel_solicitado and str(tel_solicitado).strip().replace(" ", "").replace("-", "") != tel:
        return jsonify({"ok": False, "erro": "O lembrete só pode ser enviado ao telefone configurado."}), 403
    key_solicitada = data.get("apikey")
    if key_solicitada and str(key_solicitada).strip() != key:
        return jsonify({"ok": False, "erro": "A API Key deve ser a chave já configurada no servidor."}), 403
    return jsonify(_enviar_callmebot(tel, key, msg.strip()))


@app.route("/api/enviar-teste-whatsapp", methods=["POST"])
@login_required
def api_enviar_teste_whatsapp():
    """
    Envia mensagem de teste para o usuário logado usando a API Key
    já salva no servidor — sem precisar que o frontend a conheça.
    """
    usuario = session.get("usuario", "")
    dados_usuario = _carregar_usuarios().get(usuario, {})
    cfg = dados_usuario.get("whatsapp", {}) if isinstance(dados_usuario, dict) else {}
    if not isinstance(cfg, dict):
        cfg = {}
    tel = cfg.get("telefone")
    key = cfg.get("apikey")
    tel = tel.strip() if isinstance(tel, str) else ""
    key = key.strip() if isinstance(key, str) else ""
    ativo   = cfg.get("alertas_ativos", True)

    if not tel or not key:
        return jsonify({
            "ok":   False,
            "erro": "WhatsApp não configurado. Vá em ⚙️ Configurações → WhatsApp e salve primeiro."
        })

    from extensions import _agora
    from alertas_whatsapp import sitio_nome
    msg = (
        f"🐄 *{sitio_nome()}*\n"
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

    import sitios
    slug = sitios.atual()

    def _disparar():
        from extensions import _trava_sitio
        if not _trava_sitio.acquire(timeout=30):
            app.logger.error("Não foi possível adquirir a trava do sítio para enviar WhatsApp.")
            return
        anterior = None
        try:
            anterior = sitios.atual()
            sitios.ativar(slug)
            from alertas_whatsapp import montar_alertas, montar_mensagem_alertas, enviar_para_familia
            alertas  = montar_alertas()
            msg      = montar_mensagem_alertas(alertas)
            enviados = enviar_para_familia(msg, sitio=slug)
            app.logger.info("[%s] Alertas manuais enviados para %s destinatário(s)", slug, enviados)
        except Exception as e:
            app.logger.error(f"Erro ao enviar alertas família: {e}")
        finally:
            try:
                if anterior is not None:
                    sitios.ativar(anterior)
            finally:
                _trava_sitio.release()

    threading.Thread(target=_disparar, daemon=True).start()
    return jsonify({"ok": True, "enviados": None,
                    "msg": "Envio iniciado. As mensagens podem levar alguns instantes para chegar."})
