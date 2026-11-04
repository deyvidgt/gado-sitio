#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Busca rápida global por animais, tarefas, registros e páginas."""
import re
import unicodedata
from datetime import date, datetime
from urllib.parse import quote

import animais
import db
import tarefas


PALAVRAS_IGNORADAS = {"a", "as", "o", "os", "de", "da", "do", "das", "dos", "e", "em", "por", "para", "com"}

ABAS_DISPONIVEIS = [
    {"termo": "dashboard", "titulo": "Painel", "link": "/", "icone": "🏠"},
    {"termo": "animais", "titulo": "Animais", "link": "/animais", "icone": "🐄"},
    {"termo": "pesagem peso", "titulo": "Pesagem", "link": "/animais/pesagem", "icone": "⚖️"},
    {"termo": "reproducao reprodução", "titulo": "Reprodução", "link": "/reproducao", "icone": "🐮"},
    {"termo": "pastos pastagem", "titulo": "Pastos", "link": "/pastos", "icone": "🗺️"},
    {"termo": "manejo", "titulo": "Manejo", "link": "/manejo", "icone": "🌿"},
    {"termo": "cocho cochos", "titulo": "Cochos", "link": "/cochos", "icone": "🥣"},
    {"termo": "insumos sal racao ração", "titulo": "Insumos e estoque", "link": "/insumos/comparar", "icone": "🧂"},
    {"termo": "visita visitas", "titulo": "Visitas", "link": "/visitas", "icone": "🗓️"},
    {"termo": "tarefa tarefas", "titulo": "Tarefas", "link": "/tarefas", "icone": "📋"},
    {"termo": "calendario calendário agenda", "titulo": "Calendário", "link": "/calendario", "icone": "📅"},
    {"termo": "agenda unificada", "titulo": "Agenda Unificada", "link": "/agenda", "icone": "📅"},
    {"termo": "compra compras venda vendas comercializacao comercialização transacao transação", "titulo": "Comercialização", "link": "/transacoes", "icone": "📦🤝"},
    {"termo": "gasto gastos despesa despesas", "titulo": "Gastos", "link": "/gastos", "icone": "💸"},
    {"termo": "lote lotes", "titulo": "Lotes", "link": "/lotes", "icone": "📦"},
    {"termo": "relatorio relatórios relatorios", "titulo": "Relatórios", "link": "/relatorios", "icone": "📈"},
    {"termo": "financeiro", "titulo": "Financeiro", "link": "/financeiro", "icone": "💰"},
    {"termo": "resultado membro", "titulo": "Resultado por Membro", "link": "/resultado", "icone": "📊"},
    {"termo": "fluxo caixa", "titulo": "Fluxo de Caixa", "link": "/fluxo-caixa", "icone": "📈"},
    {"termo": "fluxo animais rebanho", "titulo": "Fluxo de Animais", "link": "/fluxo-animais", "icone": "🐄"},
    {"termo": "leite ordenha", "titulo": "Painel do Leite", "link": "/leite", "icone": "🥛"},
    {"termo": "conversao conversão alimentar nutricao nutrição", "titulo": "Conversão Alimentar", "link": "/nutrição/conversão", "icone": "🥣"},
    {"termo": "doenca doença doencas doenças carencia carência tratamento vacina vacinação saude saúde", "titulo": "Doenças e Carência", "link": "/doencas", "icone": "🩺"},
    {"termo": "medicacao medicação medicamentos", "titulo": "Medicações", "link": "/medicacoes", "icone": "💉"},
    {"termo": "bulas embalagem remedio remédio", "titulo": "Bulas e Embalagens", "link": "/bulas", "icone": "📖"},
    {"termo": "genetica genética", "titulo": "Genética", "link": "/genetica", "icone": "🧬"},
    {"termo": "confinamento", "titulo": "Confinamento", "link": "/confinamento", "icone": "🏚️"},
    {"termo": "voz microfone", "titulo": "Comando de Voz", "link": "/voz", "icone": "🎤"},
    {"termo": "ajuda manual", "titulo": "Ajuda", "link": "/ajuda", "icone": "❓"},
    {"termo": "ocupacao ocupação rotacao rotação pastos", "titulo": "Ocupação de Pastos", "link": "/pastos/ocupação", "icone": "🌾"},
    {"termo": "iatf", "titulo": "IATF", "link": "/reproducao/iatf", "icone": "💉"},
    {"termo": "observacao observação cio", "titulo": "Observação de Cio", "link": "/reproducao/observacao-cio", "icone": "🔥"},
    {"termo": "descarte culling", "titulo": "Sugestões de Descarte", "link": "/reproducao/culling", "icone": "✂️"},
    {"termo": "ia preditiva", "titulo": "IA Preditiva", "link": "/reproducao/ia-predicoes", "icone": "🤖"},
]


def _normalizar(valor) -> str:
    texto = unicodedata.normalize("NFKD", _texto(valor))
    sem_acentos = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", sem_acentos.casefold()))


def _texto(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%d/%m/%Y %Y-%m-%d")
    texto = str(valor).strip()
    return "" if texto.lower() in {"nan", "none", "nat", "<na>"} else texto


def _contem_termos(termos: list[str], campos) -> tuple[bool, str]:
    alvo = _normalizar(" ".join(_texto(campo) for campo in campos))
    return all(termo in alvo for termo in termos), alvo


def _adicionar(resultados, tipo, titulo, subtitulo, link, icone, alvo, consulta):
    resultados.append({
        "tipo": tipo,
        "id": link,
        "titulo": titulo,
        "subtitulo": subtitulo,
        "link": link,
        "icone": icone,
        "_relevancia": (100 if consulta in alvo else 0)
        + sum(5 for termo in consulta.split() if alvo.startswith(termo))
        + sum(1 for termo in consulta.split() if termo in alvo),
    })


def buscar_global(
    termo: str,
    tipo_filtro: str | None = None,
    dados: dict | None = None,
) -> list[dict]:
    """Busca até 10 resultados por texto, sem diferenciar acentos ou caixa."""
    consulta = _normalizar(termo)
    if len(consulta) < 2:
        return []
    termos = [parte for parte in consulta.split() if parte not in PALAVRAS_IGNORADAS]
    if not termos:
        return []
    resultados = []

    df_animais = animais.carregar()
    for _, row in df_animais.iterrows():
        campos = [
            row.get("Brinco Cor"), row.get("Brinco Nº"), row.get("ID"),
            row.get("Nome"), row.get("Categoria"), row.get("Sexo"),
            row.get("Raça"), row.get("Pelagem"), row.get("Dono"),
            row.get("Status"), row.get("Observações"), row.get("Nascimento"),
            row.get("Entrada"), row.get("Data Saída"), row.get("Uso Produtivo"),
            row.get("Situação Leite"),
        ]
        corresponde, alvo = _contem_termos(termos, campos)
        if not corresponde:
            continue
        numero = _texto(row.get("Brinco Nº"))
        try:
            numero = str(int(float(numero)))
        except (ValueError, TypeError):
            numero = numero or "??"
        categoria = _texto(row.get("Categoria")) or "Animal"
        peso = _texto(row.get("Peso Estimado")) or _texto(row.get("Peso"))
        subtitulo = categoria.title() + (f", {peso} kg" if peso else "")
        animal_id = _texto(row.get("ID"))
        link = f"/animais/{quote(animal_id, safe='')}" if animal_id else "/animais"
        _adicionar(
            resultados, "animal",
            f"{_texto(row.get('Brinco Cor'))} {numero} ({categoria})".strip(),
            subtitulo, link, "🐄", alvo, consulta,
        )

    df_tarefas = tarefas.carregar()
    for _, row in df_tarefas.iterrows():
        campos = [
            row.get("Título"), row.get("ID"), row.get("Responsável"),
            row.get("Observações"), row.get("Data"), row.get("Repetir"),
        ]
        corresponde, alvo = _contem_termos(termos, campos)
        if not corresponde:
            continue
        tarefa_id = _texto(row.get("ID"))
        feito = "✓ " if _texto(row.get("Feito Em")) else ""
        link = f"/tarefas?id={quote(tarefa_id, safe='')}"
        _adicionar(
            resultados, "tarefa", f"{feito}{_texto(row.get('Título'))}",
            f"Data: {_texto(row.get('Data'))}", link, "📋", alvo, consulta,
        )

    dados = dados or {}
    df_manejo = dados.get("Manejo")
    if df_manejo is None:
        df_manejo = db.carregar_aba("Manejo")
    for _, row in df_manejo.iterrows():
        campos = [
            row.get("Tipo"), row.get("Descrição"), row.get("Brincos"),
            row.get("Produto"), row.get("Responsável"), row.get("Data"),
        ]
        corresponde, alvo = _contem_termos(termos, campos)
        if corresponde:
            titulo = f"{_texto(row.get('Tipo')) or 'Evento'} — {_texto(row.get('Brincos')) or 'Rebanho'}"
            subtitulo = " — ".join(v for v in (_texto(row.get("Data")), _texto(row.get("Descrição"))) if v)
            _adicionar(resultados, "evento", titulo, subtitulo, "/manejo", "📅", alvo, consulta)

    tabelas = (
        ("Compras", "Compra", "📦", "compra"),
        ("Vendas", "Venda", "🤝", "venda"),
        ("Gastos", "Gasto", "💸", "gasto"),
        ("Visitas", "Visita", "🗓️", "visita"),
    )
    for aba, nome, icone, rota in tabelas:
        df = dados.get(aba)
        if df is None:
            df = db.carregar_aba(aba)
        for _, row in df.iterrows():
            campos = [_texto(valor) for valor in row.to_dict().values()]
            corresponde, alvo = _contem_termos(termos, campos)
            if not corresponde:
                continue
            data = _texto(row.get("Data"))
            descricao = _texto(row.get("Descrição")) or _texto(row.get("Tipo"))
            cabecas = _texto(row.get("Qtd Cabeças"))
            if rota in {"compra", "venda"}:
                titulo = f"{nome}: {cabecas} cabeças" if cabecas else nome
                link = f"/transacoes?busca={quote(descricao)}" if descricao else "/transacoes"
            elif rota == "gasto":
                titulo = " — ".join(v for v in (nome, descricao) if v)
                link = "/gastos"
            else:
                titulo = f"{nome}: {data}" if data else nome
                link = "/visitas"
            _adicionar(
                resultados, "registro", titulo or nome,
                " — ".join(v for v in (data, descricao) if v),
                link, icone, alvo, consulta,
            )

    for aba in ABAS_DISPONIVEIS:
        campos = [aba["termo"], aba["titulo"]]
        corresponde, alvo = _contem_termos(termos, campos)
        if corresponde:
            _adicionar(
                resultados, "aba", aba["titulo"], "Abrir página",
                aba["link"], aba["icone"], alvo, consulta,
            )

    if tipo_filtro:
        resultados = [r for r in resultados if r["tipo"] == tipo_filtro]

    ordem = {"animal": 0, "tarefa": 1, "evento": 2, "registro": 3, "aba": 4}
    resultados.sort(key=lambda r: (-r["_relevancia"], ordem.get(r["tipo"], 99), r["titulo"]))
    for resultado in resultados:
        resultado.pop("_relevancia")
    return resultados[:10]
