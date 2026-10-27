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
VERSAO = "5.6.0"
NOME_SITIO = "Sítio Santo Antonio"

# ── Donos (sócios) do sítio ─────────────────────────────────────────────────
# v5.0 fase 1: vêm de "membros" no sitio_config.json da pasta de dados; sem isso,
# os três de sempre. A chave vira nome de coluna ("Qtd Mae") e de campo ("qtd_mae"),
# por isso só letras. Trocar os donos só vale para sítio NOVO: um arquivo que já tem
# as colunas de outros donos é recusado no db.inicializar (senão grava desalinhado).
CORES_BRINCO = ["Amarelo", "Azul", "Vermelho", "Verde", "Laranja", "Branco",
                "Rosa", "Roxo", "Preto", "Cinza"]
MEMBROS_PADRAO = [
    {"chave": "Mae", "nome": "Geane", "emoji": "👩", "cor": "Vermelho", "logins": ["geane", "mae"]},
    {"chave": "Deyvid", "nome": "Deyvid", "emoji": "👦", "cor": "Amarelo", "logins": ["deyvid"]},
    {"chave": "Nilson", "nome": "Nilson", "emoji": "👦", "cor": "Azul", "logins": ["nilson"]},
]
MEMBROS_MIN, MEMBROS_MAX = 2, 8


def ler_membros(cfg) -> list:
    """Lista de donos do sitio_config (dict) — inválida ou ausente → MEMBROS_PADRAO."""
    import logging
    import re
    lista = (cfg or {}).get("membros") if isinstance(cfg, dict) else None
    if lista is None:
        return MEMBROS_PADRAO
    try:
        ok = (isinstance(lista, list) and MEMBROS_MIN <= len(lista) <= MEMBROS_MAX
              and all(re.fullmatch(r"[A-Za-zÀ-ÿ]+", str(m["chave"])) and m["cor"] in CORES_BRINCO
                      and str(m.get("nome") or "").strip() for m in lista)
              and len({m["chave"].lower() for m in lista}) == len(lista)
              and len({m["cor"] for m in lista}) == len(lista))
    except (TypeError, KeyError, AttributeError):
        ok = False
    if not ok:
        logging.error("sitio_config.json: 'membros' inválido — usando Geane/Deyvid/Nilson.")
        return MEMBROS_PADRAO
    return lista


def _ler_sitio_config() -> dict:
    import json
    from pasta_dados import _resolver_data_dir
    try:
        with open(os.path.join(_resolver_data_dir(), "sitio_config.json"), encoding="utf-8") as f:
            return json.load(f) or {}
    except (OSError, ValueError):
        return {}


def colunas_compras(chaves) -> list:
    return ["Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)",
            *[f"Qtd {m}" for m in chaves], "Descrição", "Registrado Por"]


def colunas_vendas(chaves) -> list:
    return ["Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)", "Valor Arroba (R$)",
            *[f"Qtd {m}" for m in chaves], *[f"Valor {m} (R$)" for m in chaves],
            *[f"Custo {m} (R$)" for m in chaves], *[f"Resultado {m} (R$)" for m in chaves],
            "CMP no momento (R$)", "Descrição",
            # NOVO v4.3: brincos dos animais vendidos (ex.: "Amarelo 21 #A0003; Azul 12 #A0007").
            "Brincos"]


MEMBROS: list = []
NOMES_MEMBROS: dict = {}
EMOJIS_MEMBROS: dict = {}
CORES_BRINCO_PADRAO: dict = {}   # cor de brinco de cada dono (ajustável em Animais → Cores)
LOGIN_MEMBRO: dict = {}          # login (minúsculo) → chave do dono
COLUNAS_COMPRAS: list = []
COLUNAS_VENDAS: list = []


def aplicar_membros(lista: list) -> None:
    """Troca os donos NO LUGAR: os módulos que fizeram `from config import MEMBROS`
    guardam o mesmo objeto e passam a ver os novos."""
    chaves = [m["chave"] for m in lista]
    MEMBROS[:] = chaves
    for d, campo in ((NOMES_MEMBROS, "nome"), (EMOJIS_MEMBROS, "emoji"), (CORES_BRINCO_PADRAO, "cor")):
        d.clear()
        d.update({m["chave"]: m.get(campo) or ("🙂" if campo == "emoji" else m["chave"]) for m in lista})
    LOGIN_MEMBRO.clear()
    for m in lista:
        for login in m.get("logins") or [m["chave"]]:
            LOGIN_MEMBRO[str(login).strip().lower()] = m["chave"]
    COLUNAS_COMPRAS[:] = colunas_compras(chaves)
    COLUNAS_VENDAS[:] = colunas_vendas(chaves)


aplicar_membros(ler_membros(_ler_sitio_config()))

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
    "Cobertura",                 # monta ou inseminação (reproducao.py)
    "Diagnóstico de Gestação",   # resultado do toque: Prenha/Vazia
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

COLUNAS_GASTOS = [
    "Data", "Tipo", "Descrição", "Valor Total (R$)",
    "Qtd Cabeças", "Valor/Cabeça (R$)", "Registrado Por",
    # NOVO v4.2: compra de insumo (Sal/Proteinado/Ração) e quantos sacos — alimenta
    # a previsão de estoque (insumos.py).
    "Produto", "Qtd Sacos",
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
    # NOVO v5.2: para qual pasto (ID P01…) foi a "Movimentação de Pasto" — pastos.py.
    "Pasto",
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
    # NOVO v5.4: módulo leiteiro (leite.py) — "leite"/"ambos"/"corte", "lactação"/"seca", dd/mm/aaaa.
    "Uso Produtivo", "Situação Leite", "Último Parto",
]

# v4.4 — Fotos dos animais (arquivos no Google Drive; aqui só os dados de cada foto).
COLUNAS_FOTOS = [
    "ID Foto", "Animal", "Data", "Tipo", "Legenda", "Principal",
    "Drive ID", "Enviado Por", "Enviado Em", "ID Envio",
]
# v5.2 — Pastos desenhados no mapa (pastos.py). Contorno = GeoJSON do polígono.
COLUNAS_PASTOS = ["ID", "Nome", "Área (ha)", "Contorno", "Cor", "Ativo", "Observações", "Criado Por"]
# v5.3 — Agenda de tarefas (tarefas.py). "Feito Em" vazio = ainda pendente.
COLUNAS_TAREFAS = ["ID", "Data", "Título", "Responsável", "Repetir", "Feito Em",
                   "Observações", "Criado Por"]

# v5.4 — módulo leiteiro. Abas novas; as colunas entram somente no fim do
# esquema existente e a migração não altera dados das abas anteriores.
COLUNAS_LEITE_PRODUCAO = [
    "Data", "Vaca ID", "Brinco", "Modo Registro", "Ordenha", "Litros",
    "CCS (células/mL)", "CPP (UFC/mL)", "Qualidade", "Temperatura",
    "Observação", "Responsável", "ID Envio", "Criado Em",
]
COLUNAS_LEITE_CONFIG = [
    "Preço por Litro", "Meta Litros por Vaca", "Queda de Alerta (%)",
    "Dias sem Registro", "Número de Ordenhas", "Dias até Secagem", "Observações",
]
COLUNAS_LEITE_ALIMENTACAO = [
    "Produto", "Fabricante", "Categoria", "Peso Saco (kg)",
    "Proteína Bruta (%)", "NDT/Energia (%)", "Fibra (%)", "Cálcio (%)",
    "Fósforo (%)", "Consumo Recomendado (g/cab/dia)", "Preço por Saco (R$)",
    "Lote", "Validade", "Observação", "Ativo",
]
COLUNAS_LEITE_NECESSIDADES = [
    "Categoria Produtiva", "Nutriente ou Item", "Valor Diário", "Unidade",
    "Fonte", "Data Revisão", "Observação", "Ativo",
]
COLUNAS_LEITE_TRATAMENTOS = [
    "Data", "Vaca ID", "Brinco", "Tipo", "Descrição", "Produto/Serviço",
    "Quantidade", "Unidade", "Custo (R$)", "Responsável", "Período de Carência",
    "Observação", "ID Envio", "Criado Em",
]
COLUNAS_LEITE_CONFORTO = [
    "Data", "Local", "Sombra", "Água Disponível", "Ventilação",
    "Área de Descanso", "Lotação", "Estresse Térmico", "Descanso Observado",
    "Estado do Cocho", "Observação", "Responsável", "ID Envio", "Criado Em",
]
COLUNAS_LEITE_COLCHAO = [
    "Data", "Local", "Material", "Quantidade", "Unidade", "Custo (R$)",
    "Fornecedor", "Condição", "Próxima Troca", "Observação", "Foto Antes",
    "Foto Depois", "Responsável", "ID Envio", "Criado Em",
]

# Repetição → de quantos em quantos dias a próxima é criada ao concluir.
REPETICOES_TAREFA = {"Não": 0, "Semanal": 7, "Quinzenal": 14, "Mensal": 30,
                     "Trimestral": 90, "Semestral": 182, "Anual": 365}
TIPOS_FOTO = ["Perfil", "Evolução", "Ocorrência"]
# Pasta "Sítio Santo Antonio" no Drive do Nilson (pode ser trocada no drive_token.json).
DRIVE_PASTA_PADRAO = "1hVTxC--URXg1j3rylOYyRt1nSuC_vbUt"

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

# v5.9 — Opções do módulo leiteiro (conforto, etc)
OPCOES_LEITE = {
    "estado_cocho": ["Vazio", "Normal", "Cheio"],
}

# v5.4 — Módulo leiteiro (gestão de leite, ordenha, calculador de ração)
COLUNAS_LEITE_PRODUCAO = [
    "Data", "Vaca ID", "Brinco", "Modo Registro", "Ordenha", "Litros",
    "CCS (células/mL)", "CPP (UFC/mL)", "Qualidade", "Temperatura",
    "Observação", "Responsável", "ID Envio", "Criado Em",
]
COLUNAS_LEITE_CONFIG = [
    "Preço por Litro", "Meta Litros por Vaca", "Queda de Alerta (%)",
    "Dias sem Registro", "Número de Ordenhas", "Dias até Secagem", "Observações",
]
COLUNAS_LEITE_ALIMENTACAO = [
    "Produto", "Fabricante", "Categoria", "Peso Saco (kg)",
    "Proteína Bruta (%)", "NDT/Energia (%)", "Fibra (%)", "Cálcio (%)",
    "Fósforo (%)", "Consumo Recomendado (g/cab/dia)", "Preço por Saco (R$)",
    "Lote", "Validade", "Observação", "Ativo",
]
COLUNAS_LEITE_NECESSIDADES = [
    "Categoria Produtiva", "Nutriente ou Item", "Valor Diário", "Unidade",
    "Fonte", "Data Revisão", "Observação", "Ativo",
]
COLUNAS_LEITE_TRATAMENTOS = [
    "Data", "Vaca ID", "Brinco", "Tipo", "Descrição", "Produto/Serviço",
    "Quantidade", "Unidade", "Custo (R$)", "Responsável", "Período de Carência",
    "Observação", "ID Envio", "Criado Em",
]
COLUNAS_LEITE_CONFORTO = [
    "Data", "Local", "Sombra", "Água Disponível", "Ventilação",
    "Área de Descanso", "Lotação", "Estresse Térmico", "Descanso Observado",
    "Estado do Cocho", "Observação", "Responsável", "ID Envio", "Criado Em",
]
COLUNAS_LEITE_COLCHAO = [
    "Data", "Local", "Material", "Quantidade", "Unidade", "Custo (R$)",
    "Fornecedor", "Condição", "Próxima Troca", "Observação", "Foto Antes",
    "Foto Depois", "Responsável", "ID Envio", "Criado Em",
]

# v5.5 — Volumosos (feno, silo, etc) — entrada e consumo, para corte e leite
COLUNAS_VOLUMOSOS = [
    "Data", "Tipo", "Quantidade (kg)", "Qualidade", "Origem", "Custo (R$)",
    "Observação", "ID Envio", "Criado Em",
]
COLUNAS_CONSUMO_VOLUMOSOS = [
    "Data", "Tipo", "Quantidade consumida (kg)", "Local", "Observação",
    "ID Envio", "Criado Em",
]

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
