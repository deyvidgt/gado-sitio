from agora import agora
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cron_alertas.py — Verifica lotação de pastos e calendário sanitário, e enfileira alertas WhatsApp.
"""
import logging
from datetime import datetime
from pastos_ocupacao import gerar_alertas_lotacao
from alertas_whatsapp import guardar_aviso_pendente, enviar_avisos_pendentes
from saude import lembretes_sazonais
from db import carregar_todas

def executar_alertas_diarios():
    linhas = []

    # 1. Alertas de Lotação
    alertas_lotacao = gerar_alertas_lotacao()
    lotacao_relevante = [a for a in alertas_lotacao if a['tipo'] in ['critico', 'aviso']]

    if lotacao_relevante:
        linhas.append("🐄 *Alerta de Lotação de Pastos*")
        for a in lotacao_relevante:
            linhas.append(f"⚠️ *{a['nome_pasto']}:* {a['motivo']}")
            linhas.append(f"   {a['recomendacao']}")
        linhas.append("")

    # 2. Alertas de Saúde
    try:
        dados = carregar_todas()
        hoje = agora()
        alertas_saude = lembretes_sazonais(dados.get("Manejo", None), hoje)

        # Filtra alertas urgentes
        urgentes_saude = [a for a in alertas_saude if a.get('nivel') == 'warning']

        if urgentes_saude:
            linhas.append("🩺 *Alerta Sanitário*")
            for a in urgentes_saude:
                linhas.append(f"⚠️ {a['msg']}")
            linhas.append("")
    except Exception as e:
        logging.error(f"Erro ao processar alertas de saúde no cron: {e}")

    if not linhas:
        return

    msg = "\n".join(linhas)

    # Enfileira para envio
    guardar_aviso_pendente(msg, tipo="eventos")

    # Tenta enviar imediatamente
    enviar_avisos_pendentes()

if __name__ == "__main__":
    executar_alertas_diarios()
