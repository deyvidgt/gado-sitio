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
    {"termo": "alertas avisos notificacoes notificações", "titulo": "Avisos e Alertas", "link": "/alertas", "icone": "🔔"},
    {"termo": "familia família sitios sítios", "titulo": "Painel da Família", "link": "/familia", "icone": "👨‍👩‍👧"},
    {"termo": "animais", "titulo": "Animais", "link": "/animais", "icone": "🐄"},
    {"termo": "pesagem peso", "titulo": "Pesagem", "link": "/animais/pesagem", "icone": "⚖️"},
    {"termo": "animais leite vacas leiteiras", "titulo": "Animais Leite", "link": "/leite/animais", "icone": "🐮"},
    {"termo": "reproducao reprodução", "titulo": "Reprodução", "link": "/reproducao", "icone": "🐮"},
    {"termo": "pastos pastagem", "titulo": "Pastos", "link": "/pastos", "icone": "🗺️"},
    {"termo": "ocupacao ocupação rotacao rotação pastos", "titulo": "Ocupação e Rotação de Pastos", "link": "/pastos/ocupação", "icone": "🌾"},
    {"termo": "aplicacao aplicacoes aplicação aplicações insumos pasto custo hectare", "titulo": "Aplicações em Pastagens", "link": "/pastos/aplicacoes", "icone": "🌱"},
    {"termo": "manejo", "titulo": "Manejo", "link": "/manejo", "icone": "🌿"},
    {"termo": "cocho cochos", "titulo": "Cochos", "link": "/cochos", "icone": "🥣"},
    {"termo": "insumos sal racao ração", "titulo": "Insumos e estoque", "link": "/insumos/comparar", "icone": "🧂"},
    {"termo": "estoque geral", "titulo": "Estoque", "link": "/estoque", "icone": "📦"},
    {"termo": "parto partos previsao previsão nascimento bezerro", "titulo": "Previsão de Partos", "link": "/partos", "icone": "🍼"},
    {"termo": "mastite qualidade leite ccs cpp ordenha saude saúde", "titulo": "Mastite e Qualidade do Leite", "link": "/leite/saude", "icone": "💊"},
    {"termo": "nutricao nutrição alimentacao alimentação leite", "titulo": "Nutrição do Leite", "link": "/leite/nutricao", "icone": "🍽️"},
    {"termo": "consumo leite", "titulo": "Consumo do Rebanho Leiteiro", "link": "/leite/consumo", "icone": "📊"},
    {"termo": "volumoso volumosos silagem feno", "titulo": "Volumosos", "link": "/volumosos", "icone": "🌾"},
    {"termo": "consumo volumoso volumosos silagem", "titulo": "Consumo de Volumosos", "link": "/volumosos/consumo", "icone": "📉"},
    {"termo": "calculador calculadora racao ração dieta ingredientes", "titulo": "Calculador de Ração", "link": "/leite/calculador", "icone": "🧮"},
    {"termo": "conforto termico térmico calor", "titulo": "Conforto Térmico", "link": "/leite/conforto", "icone": "🏠"},
    {"termo": "colchao colchão cama troca", "titulo": "Colchão", "link": "/leite/colchao", "icone": "🛏️"},
    {"termo": "ordenha registrar producao produção leite", "titulo": "Registrar Ordenha", "link": "/leite/ordenha", "icone": "🥛"},
    {"termo": "relatorio relatorios relatórios leite", "titulo": "Relatórios do Leite", "link": "/leite/relatorios", "icone": "📈"},
    {"termo": "visita visitas", "titulo": "Visitas", "link": "/visitas", "icone": "🗓️"},
    {"termo": "tarefa tarefas", "titulo": "Tarefas", "link": "/tarefas", "icone": "📋"},
    {"termo": "calendario calendário agenda", "titulo": "Calendário", "link": "/calendario", "icone": "📅"},
    {"termo": "agenda unificada", "titulo": "Agenda Unificada", "link": "/agenda", "icone": "📅"},
    {"termo": "compra compras venda vendas comercializacao comercialização transacao transação", "titulo": "Comercialização", "link": "/transacoes", "icone": "📦🤝"},
    {"termo": "gasto gastos despesa despesas", "titulo": "Gastos", "link": "/gastos", "icone": "💸"},
    {"termo": "lote lotes", "titulo": "Lotes", "link": "/lotes", "icone": "📦"},
    {"termo": "relatorio relatórios relatorios gerais", "titulo": "Relatórios", "link": "/relatorios", "icone": "📈"},
    {"termo": "financeiro", "titulo": "Financeiro", "link": "/financeiro", "icone": "💰"},
    {"termo": "planejamento orcamento orçamento contas futuras", "titulo": "Orçamento e Contas", "link": "/planejamento", "icone": "📅"},
    {"termo": "resultado membro", "titulo": "Resultado por Membro", "link": "/resultado", "icone": "📊"},
    {"termo": "comparativo anual financeiro", "titulo": "Comparativo Anual", "link": "/comparativo-anual", "icone": "📈"},
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
    {"termo": "iatf", "titulo": "IATF", "link": "/reproducao/iatf", "icone": "💉"},
    {"termo": "observacao observação cio", "titulo": "Observação de Cio", "link": "/reproducao/observacao-cio", "icone": "🔥"},
    {"termo": "descarte culling", "titulo": "Sugestões de Descarte", "link": "/reproducao/culling", "icone": "✂️"},
    {"termo": "ia preditiva", "titulo": "IA Preditiva", "link": "/reproducao/ia-predicoes", "icone": "🤖"},
    {"termo": "ponto corte arroba vender", "titulo": "Ponto de Corte", "link": "/ponto-corte", "icone": "🎯"},
    {"termo": "tempo clima previsao previsão", "titulo": "Tempo", "link": "/tempo", "icone": "🌤️"},
    {"termo": "configuracao configurações usuarios usuários sitio sítio", "titulo": "Configurações", "link": "/configuracoes", "icone": "⚙️"},
    {"termo": "modulos módulos personalizar ativar desativar", "titulo": "Módulos do Sítio", "link": "/configuracoes/modulos", "icone": "🧩"},
    {"termo": "alimentacao alimentação catalogo catálogo produtos leite", "titulo": "Alimentação do Leite", "link": "/leite/alimentacao", "icone": "🥛"},
    {"termo": "lancar volumoso entrada feno silagem", "titulo": "Lançar Volumoso", "link": "/volumosos/lançar", "icone": "➕"},
    {"termo": "indicadores crescimento gmd", "titulo": "Indicadores de Crescimento", "link": "/indicadores/gmd", "icone": "📈"},
    {"termo": "engorda pastagem gmd", "titulo": "Engorda em Pastagem", "link": "/indicadores/engorda-pastagem", "icone": "🌱"},
    {"termo": "gmd lotacao lotação capacidade", "titulo": "GMD e Lotação", "link": "/indicadores/gmd-lotacao", "icone": "📊"},
    {"termo": "consumo racao ração desperdicio desperdício", "titulo": "Consumo de Ração", "link": "/indicadores/racao-consumo", "icone": "🥣"},
    {"termo": "mortalidade bezerros", "titulo": "Mortalidade de Bezerros", "link": "/indicadores/mortalidade-bezerros", "icone": "🐮"},
    {"termo": "historico doenças tratamentos", "titulo": "Histórico de Doenças", "link": "/doencas", "icone": "🩺"},
    {"termo": "historico medicacoes medicações", "titulo": "Histórico de Medicações", "link": "/medicacoes", "icone": "💉"},
    {"termo": "relatorios avancados avançados", "titulo": "Relatórios Avançados", "link": "/relatorios/avancados", "icone": "📈"},
    {"termo": "backup backups restaurar baixar", "titulo": "Backups", "link": "/backups", "icone": "💾"},
    {"termo": "importar dados planilha", "titulo": "Importar Dados", "link": "/importar", "icone": "📥"},
    {"termo": "exportar dados planilha", "titulo": "Exportar Dados", "link": "/exportar", "icone": "📤"},
]

ABAS_REGISTROS_EXTRAS = [
    ("Cochos", "Cocho", "🥣", "/cochos", ("Nome", "Tipo", "Local", "Observações")),
    ("Pastos", "Pasto", "🗺️", "/pastos", ("Nome", "ID", "Observações")),
    ("Pastos Aplicações", "Aplicação em pasto", "🌱", "/pastos/aplicacoes",
     ("Produto", "Tipo Insumo", "Pasto ID", "Responsável")),
    ("Leite Produção", "Produção de leite", "🥛", "/leite/relatorios",
     ("Vaca ID", "Brinco", "Ordenha", "Qualidade", "Observação")),
    ("Leite Configuração", "Configuração do leite", "🥛", "/leite", ("Observações",)),
    ("Leite Alimentação", "Alimento leiteiro", "🍽️", "/leite/alimentacao",
     ("Produto", "Fabricante", "Categoria", "Lote")),
    ("Leite Necessidades", "Necessidade nutricional", "🍽️", "/leite/nutricao",
     ("Categoria Produtiva", "Nutriente ou Item", "Fonte")),
    ("Leite Tratamentos", "Tratamento leiteiro", "💊", "/leite/saude",
     ("Vaca ID", "Brinco", "Tipo", "Descrição", "Produto/Serviço")),
    ("Leite Conforto", "Conforto térmico", "🏠", "/leite/conforto",
     ("Local", "Observação", "Responsável")),
    ("Leite Colchão", "Colchão", "🛏️", "/leite/colchao",
     ("Local", "Material", "Condição", "Observação")),
    ("Tratamentos", "Tratamento", "🩺", "/doencas",
     ("ID Animal", "Brinco", "Tipo Doença", "Tratamento", "Medicamento", "Observações")),
    ("Medicações", "Medicação", "💉", "/medicacoes",
     ("Brincos", "Tipo Medicação", "Princípio Ativo", "Motivo", "Observações")),
    ("Volumosos", "Volumoso", "🌾", "/volumosos",
     ("Tipo", "Qualidade", "Origem", "Observação")),
    ("Consumo Volumosos", "Consumo de volumoso", "🌾", "/volumosos/consumo",
     ("Tipo", "Local", "Observação")),
    ("Engorda Pastagem", "Engorda em pastagem", "🌱", "/indicadores/engorda-pastagem",
     ("Pasto ID", "Brincos", "Condição Pasto", "Observação")),
    ("GMD Lotação", "GMD e lotação", "📊", "/indicadores/gmd-lotacao",
     ("Animais", "Pasto ID", "Qualidade Pasto", "Clima", "Observação")),
    ("Ração Consumo", "Consumo de ração", "🥣", "/indicadores/racao-consumo",
     ("Tipo Ração", "Observação")),
    ("Mortalidade Bezerros", "Mortalidade de bezerros", "🐮", "/indicadores/mortalidade-bezerros",
     ("Causa 1", "Causa 2", "Causa 3", "Observação")),
    ("Confinamento Lotes", "Lote de confinamento", "🏚️", "/confinamento",
     ("Lote ID", "Brincos", "Status", "Observação")),
    ("Genética", "Registro genético", "🧬", "/genetica",
     ("Animal ID", "Pai ID", "Mãe ID", "Genótipo", "Observação")),
    ("Insumos", "Insumo", "🧂", "/insumos/comparar",
     ("Tipo", "Marca", "Observações")),
    ("Orçamento Previsto", "Orçamento previsto", "📅", "/planejamento",
     ("Tipo", "Categoria", "Descrição", "Membro")),
    ("Contas Futuras", "Conta futura", "📅", "/planejamento",
     ("Tipo", "Categoria", "Descrição", "Status", "Membro")),
    ("Fotos", "Foto de animal", "📷", "/animais",
     ("Animal ID", "Brinco", "Descrição", "Legenda")),
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
    modulos: dict[str, bool] | None = None,
) -> list[dict]:
    """Busca até 10 resultados por texto, sem diferenciar acentos ou caixa."""
    consulta = _normalizar(termo)
    if len(consulta) < 2:
        return []
    termos = [parte for parte in consulta.split() if parte not in PALAVRAS_IGNORADAS]
    if not termos:
        return []
    resultados = []
    if modulos is not None:
        from modulos import esta_ativo, modulo_da_rota

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

    for nome_aba, rotulo, icone, link, campos_titulo in ABAS_REGISTROS_EXTRAS:
        if modulos is not None:
            chave_modulo = modulo_da_rota(link)
            if chave_modulo and not esta_ativo(chave_modulo, modulos):
                continue
        df = dados.get(nome_aba)
        if df is None:
            df = db.carregar_aba(nome_aba)
        for _, row in df.iterrows():
            corresponde, alvo = _contem_termos(termos, row.to_dict().values())
            if not corresponde:
                continue
            titulo_detalhe = next(
                (_texto(row.get(campo)) for campo in campos_titulo if _texto(row.get(campo))),
                "",
            )
            data = next(
                (_texto(row.get(campo)) for campo in ("Data", "Data Registro", "Data Entrada")
                 if _texto(row.get(campo))),
                "",
            )
            registro_id = _texto(row.get("ID"))
            titulo = f"{rotulo}: {titulo_detalhe}" if titulo_detalhe else rotulo
            if registro_id:
                titulo += f" ({registro_id})"
            subtitulo = " — ".join(v for v in (data, titulo_detalhe) if v)
            _adicionar(resultados, "registro", titulo, subtitulo, link, icone, alvo, consulta)

    for aba in ABAS_DISPONIVEIS:
        if modulos is not None:
            chave_modulo = modulo_da_rota(aba["link"])
            if chave_modulo and not esta_ativo(chave_modulo, modulos):
                continue
        campos = [aba["termo"], aba["titulo"]]
        corresponde, alvo = _contem_termos(termos, campos)
        if corresponde:
            _adicionar(
                resultados, "aba", aba["titulo"], "Abrir tela",
                aba["link"], aba["icone"], alvo, consulta,
            )
            titulo = _normalizar(aba["titulo"]).split()
            palavras_aba = set(titulo)
            if consulta == " ".join(titulo):
                resultados[-1]["_relevancia"] += 250
            elif consulta in titulo:
                resultados[-1]["_relevancia"] += 200
            elif all(termo in palavras_aba for termo in termos):
                resultados[-1]["_relevancia"] += 150

    if tipo_filtro:
        resultados = [r for r in resultados if r["tipo"] == tipo_filtro]

    ordem = {"animal": 0, "tarefa": 1, "evento": 2, "registro": 3, "aba": 4}
    resultados.sort(key=lambda r: (-r["_relevancia"], ordem.get(r["tipo"], 99), r["titulo"]))
    for resultado in resultados:
        resultado.pop("_relevancia")
    return resultados[:10]
