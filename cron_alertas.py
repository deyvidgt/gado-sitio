#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cron_alertas.py — Verifica lotação de pastos e enfileira alertas WhatsApp.
"""
import logging
from pastos_ocupacao import gerar_alertas_lotacao
from alertas_whatsapp import guardar_aviso_pendente, enviar_avisos_pendentes

def executar_alertas_diarios():
    alertas = gerar_alertas_lotacao()

    # Filtra alertas críticos ou de aviso
    alertas_relevantes = [a for a in alertas if a['tipo'] in ['critico', 'aviso']]

    if not alertas_relevantes:
        return

    # Consolida alertas em uma única mensagem
    linhas = ["🐄 *Alerta de Lotação de Pastos*", ""]
    for a in alertas_relevantes:
        linhas.append(f"⚠️ *{a['nome_pasto']}:* {a['motivo']}")
        linhas.append(f"   {a['recomendacao']}")
        linhas.append("")

    msg = "\n".join(linhas)

    # Enfileira para envio
    guardar_aviso_pendente(msg, tipo="eventos")

    # Tenta enviar imediatamente
    enviar_avisos_pendentes()

if __name__ == "__main__":
    executar_alertas_diarios()
