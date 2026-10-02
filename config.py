#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurações e constantes do Sistema de Gestão de Gado
Sítio Santo Antonio — Família: Geane, Deyvid, Nilson
v3.3
"""

import os
import sys

# ── Encoding do console ─────────────────────────────────────────────────────────
# No Windows o console usa cp1252 e quebra (UnicodeEncodeError) ao imprimir emojis
# usados nos logs de boot (📂 📊 ✅ 🐄 …). Força UTF-8 na saída padrão.
# BUG CORRIGIDO v3.6: o app podia crashar no boot em terminal Windows.
for _stream in ("stdout", "stderr"):
    try:
        getattr(sys, _stream).reconfigure(encoding="utf-8")
    except Exception:
        pass

ARQUIVO_DADOS = "gado_familia.xlsx"
VERSAO = "4.0"
NOME_SITIO = "Sítio Santo Antonio"
FAMILIA = "Geane, Deyvid e Nilson"

MEMBROS = ["Mae", "Deyvid", "Nilson"]
NOMES_MEMBROS = {"Mae": "Geane", "Deyvid": "Deyvid", "Nilson": "Nilson"}
EMOJIS_MEMBROS = {"Mae": "👩", "Deyvid": "👦", "Nilson": "👦"}

# ── Segurança ─────────────────────────────────────────────────────────────────
# Em produção, defina a variável de ambiente GADO_SECRET_KEY com um valor aleatório:
#   python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = os.environ.get(
    "GADO_SECRET_KEY",
    "gado_sitio_dev_only_nao_usar_em_producao_xK9mP3r7"
)

# ── Login ──────────────────────────────────────────────────────────────────────
# Hashes SHA-256 legados — migrados para bcrypt no primeiro login bem-sucedido.
# Senha padrão de todos: sitio2025
USUARIOS = {
    "geane":  "490235b01db7dfb8844ff53d572f905ad3cdfeed4c2e866d335c4ee48aeeaecf",
    "deyvid": "490235b01db7dfb8844ff53d572f905ad3cdfeed4c2e866d335c4ee48aeeaecf",
    "nilson": "490235b01db7dfb8844ff53d572f905ad3cdfeed4c2e866d335c4ee48aeeaecf",
}

SESSAO_MINUTOS = 480        # 8 horas
MAX_TENTATIVAS_LOGIN = 5

# ── Cache do resumo financeiro ────────────────────────────────────────────────
# Evita recalcular tudo a cada request. Invalida automaticamente após salvar.
CACHE_RESUMO_TTL = 30       # segundos

TIPOS_GASTO = [
    "Remédio/Vacina",
    "Sal/Proteínado",
    "Gasolina/Transporte",
    "Veneno/Defensivo",
    "Calcário/Adubação",
    "Manutenção/Outros",
]

TIPOS_MANEJO = [
    "Vacinação",
    "Vermifugação",
    "Pesagem",
    "Morte/Perda",
    "Nascimento",
    "Tratamento Veterinário",
    "Movimentação de Pasto",
    "Outro",
]

ALERTAS_SAUDE = {
    "Vacinação":              180,   # dias entre vacinações
    "Vermifugação":           120,   # dias entre vermifugações
    "Pesagem":                90,    # dias entre pesagens
    "Tratamento Veterinário": 365,   # revisão anual
}

# ── WhatsApp (CallMeBot) ──────────────────────────────────────────────────────
# Deixe vazio; cada usuário configura o próprio número nas Configurações do sistema.
# Documentação: https://www.callmebot.com/blog/free-api-whatsapp-messages/
WHATSAPP_LEMBRETES_HORA = 7   # hora do dia para envio automático (se implementado via cron)

COLUNAS_COMPRAS = [
    "Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)",
    "Qtd Mae", "Qtd Deyvid", "Qtd Nilson",
    "Descrição", "Registrado Por",
]
COLUNAS_GASTOS = [
    "Data", "Tipo", "Descrição", "Valor Total (R$)",
    "Qtd Cabeças", "Valor/Cabeça (R$)", "Registrado Por",
]
COLUNAS_VENDAS = [
    "Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)",
    "Valor Arroba (R$)",
    "Qtd Mae", "Qtd Deyvid", "Qtd Nilson",
    "Valor Mae (R$)", "Valor Deyvid (R$)", "Valor Nilson (R$)",
    "Custo Mae (R$)", "Custo Deyvid (R$)", "Custo Nilson (R$)",
    "Resultado Mae (R$)", "Resultado Deyvid (R$)", "Resultado Nilson (R$)",
    "CMP no momento (R$)", "Descrição",
]
COLUNAS_MANEJO = [
    "Data", "Tipo", "Qtd Cabeças", "Descrição", "Responsável",
    # NOVO v3.6: em caso de Morte/Perda, de qual membro foi a perda.
    "Perda De",
]
COLUNAS_VISITAS = [
    "Data", "Responsável",
    "Gado Contado", "Gado Esperado", "Gado Faltando",
    "Sal/Ração", "Proteinado",
    "Mato/Vegetação", "Grama/Pastagem", "Córrego/Água",
    "Quintal", "Cisterna",
    "Choveu", "Chuva mm",
    "Observações", "Sugestões",
    "Sacos Sal/Ração", "Sacos Proteinado",
    # NOVO v3.6: reservatórios de água (status + litros restantes).
    "Caixa d'Água", "Caixa d'Água Litros",
    "Conteiner", "Conteiner Litros",
    # NOVO v4.0: Ração separada do Sal (a coluna "Sal/Ração" guarda o Sal).
    "Ração", "Sacos Ração",
]

OPCOES_VISITA = {
    "sal_racao":  ["OK", "Meio Saco", "Baixo", "Vazio"],
    "proteinado": ["OK", "Meio Saco", "Baixo", "Vazio"],
    "mato":       ["Limpo", "Precisa Capinar", "Muito Mato"],
    "grama":      ["Boa", "Amarelando/Secando", "Regular", "Escassa"],
    "corrego":    ["Normal", "Baixo", "Seco"],
    "quintal":    ["OK", "Precisa Atenção"],
    "cisterna":   ["OK", "Baixo/Secando", "Vazia"],
    "caixa_agua": ["Cheia", "Meia", "Baixa", "Vazia"],
    "conteiner":  ["Cheio", "Meio", "Baixo", "Vazio"],
}

CORES = {
    "verde_escuro":  "1B5E20",
    "verde_medio":   "388E3C",
    "verde_claro":   "C8E6C9",
    "amarelo":       "FFF9C4",
    "laranja":       "FFE0B2",
    "azul_claro":    "E3F2FD",
    "vermelho":      "FFCDD2",
    "vermelho_esc":  "BF360C",
    "azul_escuro":   "1A237E",
    "roxo":          "4A148C",
}
