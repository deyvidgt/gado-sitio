#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurações e constantes do Sistema de Gestão de Gado
Sítio Santo Antonio — Família: Geane, Deyvid, Nilson
"""

ARQUIVO_DADOS = "gado_familia.xlsx"
VERSAO = "3.2"
NOME_SITIO = "Sítio Santo Antonio"
FAMILIA = "Geane, Deyvid e Nilson"

MEMBROS = ["Mae", "Deyvid", "Nilson"]
NOMES_MEMBROS = {"Mae": "Geane", "Deyvid": "Deyvid", "Nilson": "Nilson"}
EMOJIS_MEMBROS = {"Mae": "👩", "Deyvid": "👦", "Nilson": "👦"}

# ── Login ──────────────────────────────────────────────────────────────────────
# Senhas armazenadas como SHA-256. Para trocar a senha de um usuário:
#   python -c "import hashlib; print(hashlib.sha256('NOVA_SENHA'.encode()).hexdigest())"
# Cole o hash resultante no campo abaixo.
#
# Senha padrão de todos: sitio2025
USUARIOS = {
    "geane":  "490235b01db7dfb8844ff53d572f905ad3cdfeed4c2e866d335c4ee48aeeaecf",
    "deyvid": "490235b01db7dfb8844ff53d572f905ad3cdfeed4c2e866d335c4ee48aeeaecf",
    "nilson": "490235b01db7dfb8844ff53d572f905ad3cdfeed4c2e866d335c4ee48aeeaecf",
}

# Tempo de sessão em minutos (0 = até fechar o navegador)
SESSAO_MINUTOS = 480   # 8 horas


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

# Limites de alerta para saúde do rebanho (em dias)
ALERTAS_SAUDE = {
    "Vacinação": 180,       # 6 meses
    "Vermifugação": 120,    # 4 meses
}

# Colunas de cada aba
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
]

# ── VISITAS AO SÍTIO ──────────────────────────────────────────────────────────
COLUNAS_VISITAS = [
    "Data", "Responsável",
    "Gado Contado", "Gado Esperado", "Gado Faltando",
    "Sal/Ração", "Proteinado",
    "Mato/Vegetação", "Grama/Pastagem", "Córrego/Água",
    "Quintal", "Cisterna",
    "Choveu", "Chuva mm",
    "Observações", "Sugestões",
]

# Opções para campos de status da visita
OPCOES_VISITA = {
    "sal_racao":  ["OK", "Baixo", "Vazio"],
    "proteinado": ["OK", "Baixo", "Vazio"],
    "mato":       ["Limpo", "Precisa Capinar", "Muito Mato"],
    "grama":      ["Boa", "Regular", "Escassa"],
    "corrego":    ["Normal", "Baixo", "Seco"],
    "quintal":    ["OK", "Precisa Atenção"],
    "cisterna":   ["OK", "Baixo", "Vazia"],
}

# Pesos de cores para exportação Excel
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
