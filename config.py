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
VERSAO = "4.5.1"
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
# Evita recalcular tudo a cada request. Invalida automaticamente após salvar e
# sempre que o .xlsx muda no disco (extensions._cache_dados); o TTL é só uma rede
# de segurança.
CACHE_RESUMO_TTL = 600      # segundos

TIPOS_GASTO = [
    "Remédio/Vacina",
    "Sal/Proteínado",
    "Gasolina/Transporte",
    "Veneno/Defensivo",
    "Calcário/Adubação",
    "Manutenção/Outros",
]

TIPOS_MANEJO = [
    "Vacina Raiva",
    "Vacina Clostridioses",   # inclui botulismo quando a vacina é polivalente
    "Vacina Brucelose",       # fêmeas de 3 a 8 meses (campanha IMA)
    "Vacinação",              # outras vacinas (registros antigos também usam este)
    "Vermifugação",
    "Pesagem",
    "Morte/Perda",
    "Nascimento",
    "Tratamento Veterinário",
    "Movimentação de Pasto",
    "Outro",
]

# Intervalos (em dias) dos alertas de saúde — PADRÕES DE REFERÊNCIA p/ gado de
# corte no Triângulo Mineiro (cerrado/MG), conforme IMA-MG e Embrapa (ver saude.py).
# Podem ser ajustados em ⚙️ Configurações → Alertas de Saúde (db.get_alertas_saude()
# aplica os ajustes salvos por cima destes). Confirme com seu veterinário.
# Brucelose não entra aqui: segue as etapas da campanha (saude.lembretes_sazonais).
ALERTAS_SAUDE = {
    "Vacina Raiva":           365,   # obrigatória em MG; anual (1ª vez: 2 doses c/ 30 dias)
    "Vacina Clostridioses":   365,   # anual (1ª vez: 4 meses + reforço em 30 dias)
    "Vermifugação":           240,   # 5-7-9 (mai/jul/set); de set a mai são ~8 meses
    "Pesagem":                90,    # trimestral (acompanhar ganho de peso)
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
    # NOVO v4.2: compra de insumo (Sal/Proteinado/Ração) e quantos sacos — alimenta
    # a previsão de estoque (insumos.py).
    "Produto", "Qtd Sacos",
]
COLUNAS_VENDAS = [
    "Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)",
    "Valor Arroba (R$)",
    "Qtd Mae", "Qtd Deyvid", "Qtd Nilson",
    "Valor Mae (R$)", "Valor Deyvid (R$)", "Valor Nilson (R$)",
    "Custo Mae (R$)", "Custo Deyvid (R$)", "Custo Nilson (R$)",
    "Resultado Mae (R$)", "Resultado Deyvid (R$)", "Resultado Nilson (R$)",
    "CMP no momento (R$)", "Descrição",
    # NOVO v4.3: brincos dos animais vendidos (ex.: "Amarelo 21 #A0003; Azul 12 #A0007").
    "Brincos",
]
COLUNAS_MANEJO = [
    "Data", "Tipo", "Qtd Cabeças", "Descrição", "Responsável",
    # NOVO v3.6: em caso de Morte/Perda, de qual membro foi a perda.
    "Perda De",
    # NOVO v4.1: remédio/produto usado em vacinas e vermifugação.
    "Produto",
    # NOVO v4.1: em caso de Nascimento, de qual membro é o bezerro (o inverso de "Perda De").
    "Nascimento De",
    # NOVO v4.3: em quais animais (brincos) o manejo foi feito — mesmo formato de Vendas.
    "Brincos",
    # NOVO v4.6: peso de cada animal na Pesagem ("Amarelo 21 #A0003: 320 kg; …") — pesagem.py.
    "Pesos",
]

# Tipos de manejo em que o formulário pergunta qual remédio/produto foi usado.
TIPOS_COM_PRODUTO = [
    "Vacina Raiva", "Vacina Clostridioses", "Vacina Brucelose",
    "Vacinação", "Vermifugação",
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
    # NOVO v4.2: código único gerado no celular — evita gravar a mesma visita
    # duas vezes quando o envio offline é repetido.
    "ID Envio",
]

# ── Animais com brinco (v4.3) ────────────────────────────────────────────────
# Uma linha por animal. O "ID" (A0001…) nunca se repete; o brinco (cor + nº) se
# repete entre cores e é reaproveitado depois do 99 — só é único entre os VIVOS.
# Por isso o histórico (Manejo/Vendas → coluna "Brincos") guarda o ID junto.
# O cadastro NÃO mexe nas finanças: a cabeça já entrou pela compra ou pelo
# nascimento (aba Manejo). Datas sem a coluna "Data" de propósito: esta aba
# não entra nas somas por ano do dashboard.
COLUNAS_ANIMAIS = [
    "ID", "Brinco Cor", "Brinco Nº", "Dono", "Categoria", "Sexo",
    "Raça", "Pelagem", "Sinais", "Nascimento", "Entrada", "Origem",
    "Ref Compra", "Mãe", "Status", "Data Saída", "Observações", "Registrado Por",
]

# v4.4 — Fotos dos animais (arquivos no Google Drive; aqui só os dados de cada foto).
COLUNAS_FOTOS = [
    "ID Foto", "Animal", "Data", "Tipo", "Legenda", "Principal",
    "Drive ID", "Enviado Por", "Enviado Em", "ID Envio",
]
TIPOS_FOTO = ["Perfil", "Evolução", "Ocorrência"]
# Pasta "Sítio Santo Antonio" no Drive do Nilson (pode ser trocada no drive_token.json).
DRIVE_PASTA_PADRAO = "1hVTxC--URXg1j3rylOYyRt1nSuC_vbUt"

# Cada dono tem a sua cor de brinco (ajustável na página Animais → Cores).
CORES_BRINCO_PADRAO = {"Deyvid": "Amarelo", "Nilson": "Azul", "Mae": "Vermelho"}
CORES_BRINCO = ["Amarelo", "Azul", "Vermelho", "Verde", "Laranja", "Branco",
                "Rosa", "Roxo", "Preto", "Cinza"]
BRINCO_MAX = 99   # numeração 01..99 por cor; depois recomeça do 01

CATEGORIAS_ANIMAL = {   # categoria → sexo
    "Bezerra": "F", "Novilha": "F", "Vaca": "F",
    "Bezerro": "M", "Garrote": "M", "Novilho": "M", "Boi": "M", "Touro": "M",
}
ORIGENS_ANIMAL = ["Já no sítio", "Compra", "Nascimento"]
STATUS_ANIMAL  = ["Vivo", "Vendido", "Morto"]

# v4.2: na visita, "Sacos" = sacos EM ESTOQUE no sítio (contados naquela visita).
# Coluna da aba Visitas com o estoque contado de cada insumo.
INSUMOS = {
    "Sal":        "Sacos Sal/Ração",
    "Proteinado": "Sacos Proteinado",
    "Ração":      "Sacos Ração",
}

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
