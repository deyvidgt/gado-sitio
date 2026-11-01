# -*- coding: utf-8 -*-
"""Cálculos e validações do módulo leiteiro."""

from datetime import date, datetime, timedelta

import pandas as pd


def _data(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if valor is None or str(valor).strip() == "":
        return None
    # Formato explícito: sem ele o pandas adivinha e avisa (dayfirst com ISO).
    # Planilha guarda dd/mm/aaaa; formulário manda aaaa-mm-dd.
    texto = str(valor).strip()[:10]
    formato = "%Y-%m-%d" if texto[4:5] == "-" else "%d/%m/%Y"
    try:
        return datetime.strptime(texto, formato).date()
    except ValueError:
        return None


def _hoje_br():
    """Hoje no fuso de Brasília — date.today() usa o fuso do servidor (UTC no
    PythonAnywhere) e adiantava/atrasava os cálculos de 'hoje' pela manhã."""
    try:
        from extensions import _agora
        return _agora().date()
    except Exception:
        return date.today()


def _numero(valor):
    if isinstance(valor, (int, float)):
        return float(valor)
    if valor is None or str(valor).strip() == "":
        return None
    from extensions import parse_valor
    return parse_valor(valor)


def validar_producao(dados):
    """Retorna a mensagem de erro ou ``None`` para um lançamento válido."""
    litros = _numero(dados.get("Litros"))
    if litros is None or litros < 0:
        return "Litros deve ser um número maior ou igual a zero."
    modo = str(dados.get("Modo Registro") or "").strip().lower()
    if modo not in {"individual", "total"}:
        return "Modo Registro inválido."
    if modo == "individual" and not str(dados.get("Vaca ID") or "").strip():
        return "Vaca ID é obrigatório no registro individual."
    if _data(dados.get("Data")) is None:
        return "Data inválida."
    return None


def _linhas_validas(df):
    colunas = ["Data", "Vaca ID", "Modo Registro", "Ordenha", "Litros"]
    if df is None or df.empty:
        return pd.DataFrame(columns=colunas + ["_data", "_litros", "_modo", "_ordenha"])
    linhas = df.copy()
    linhas["_data"] = linhas.get("Data", "").map(_data)
    linhas["_litros"] = linhas.get("Litros", 0).map(_numero)
    linhas["_modo"] = linhas.get("Modo Registro", pd.Series("", index=linhas.index)).astype(str).str.strip().str.lower()
    linhas["_ordenha"] = linhas.get("Ordenha", pd.Series("", index=linhas.index)).fillna("").astype(str).str.strip()
    return linhas[linhas["_data"].notna() & linhas["_litros"].notna() & (linhas["_litros"] >= 0)].copy()


def _sem_duplicidade(df):
    """Prefere individuais quando há individual e total na mesma data/ordenha."""
    linhas = _linhas_validas(df)
    if linhas.empty:
        return linhas
    chave = ["_data", "_ordenha"]
    tem_individual = linhas.groupby(chave)["_modo"].transform(lambda serie: (serie == "individual").any())
    return linhas[~((linhas["_modo"] == "total") & tem_individual)].copy()


def _recorte(df, inicio, fim):
    linhas = _sem_duplicidade(df)
    inicio, fim = _data(inicio), _data(fim)
    if inicio is not None:
        linhas = linhas[linhas["_data"] >= inicio]
    if fim is not None:
        linhas = linhas[linhas["_data"] <= fim]
    return linhas


def resumo_periodo(df, inicio, fim, animais_lactacao=0):
    linhas = _recorte(df, inicio, fim)
    individuais = linhas[linhas["_modo"] == "individual"]
    totais = linhas[linhas["_modo"] == "total"]
    litros_individuais = float(individuais["_litros"].sum())
    litros_totais = float(totais["_litros"].sum())
    animais = int(animais_lactacao or 0)
    return {
        "litros": litros_individuais + litros_totais,
        "litros_individuais": litros_individuais,
        "litros_totais": litros_totais,
        "media_por_animal": (litros_individuais / animais) if animais else None,
    }


def serie_diaria(df, inicio, fim):
    """Litros por dia no período, do mais antigo ao mais recente (dias sem registro ficam de fora)."""
    linhas = _recorte(df, inicio, fim)
    if linhas.empty:
        return []
    por_dia = linhas.groupby("_data")["_litros"].sum().sort_index()
    return [(dia, float(litros)) for dia, litros in por_dia.items()]


def acumulados(df, referencia):
    ref = _data(referencia)
    if ref is None:
        return {"dia": 0, "semana": 0, "mes": 0, "total": 0}
    inicio_semana = ref - timedelta(days=ref.weekday())
    linhas = _sem_duplicidade(df)

    def soma(inicio, fim=ref):
        recorte = linhas[(linhas["_data"] >= inicio) & (linhas["_data"] <= fim)]
        return float(recorte["_litros"].sum())

    return {
        "dia": soma(ref),
        "semana": soma(inicio_semana),
        "mes": soma(ref.replace(day=1)),
        "total": float(linhas[linhas["_data"] <= ref]["_litros"].sum()),
    }


def producao_por_animal(df, inicio, fim):
    linhas = _recorte(df, inicio, fim)
    linhas = linhas[linhas["_modo"] == "individual"]
    if linhas.empty:
        return {}
    linhas["_vaca"] = linhas.get("Vaca ID", "").fillna("").astype(str).str.strip()
    linhas = linhas[linhas["_vaca"] != ""]
    return {str(vaca): float(valor) for vaca, valor in linhas.groupby("_vaca")["_litros"].sum().items()}


def medias_periodo(df, inicio, fim, animais_lactacao=0):
    linhas = _recorte(df, inicio, fim)
    total = float(linhas["_litros"].sum())
    dias = linhas["_data"].nunique()
    meses = linhas["_data"].map(lambda valor: (valor.year, valor.month)).nunique()
    individuais = linhas[linhas["_modo"] == "individual"]
    animais = individuais["Vaca ID"].fillna("").astype(str).str.strip().replace("", pd.NA).nunique()
    lactacao = int(animais_lactacao or 0)
    return {
        "media_diaria": total / dias if dias else None,
        "media_mensal": total / meses if meses else None,
        "media_por_animal": individuais["_litros"].sum() / animais if animais else None,
        "media_por_animal_lactacao": individuais["_litros"].sum() / lactacao if lactacao else None,
    }


def _serie(df, nome, padrao=""):
    """Coluna como texto; aba sem a coluna vira o padrão (nunca um str solto)."""
    col = df[nome] if nome in df.columns else pd.Series(padrao, index=df.index)
    return col.astype(str).str.strip()


def contagens_rebanho(animais):
    if animais is None or animais.empty:
        return {"animais_ativos": 0, "vacas_leiteiras_ativas": 0, "vacas_lactacao": 0}
    # Sem a coluna Status a cabeça conta como viva (mesma convenção de animais.py).
    vivos = animais[_serie(animais, "Status", "vivo").str.lower().isin({"vivo", "ativo"})]
    uso = _serie(vivos, "Uso Produtivo").str.lower()
    sexo = _serie(vivos, "Sexo").str.upper()
    situacao = _serie(vivos, "Situação Leite").str.lower()
    leiteiras = (sexo == "F") & uso.isin({"leite", "ambos"})
    return {
        "animais_ativos": int(len(vivos)),
        "vacas_leiteiras_ativas": int(leiteiras.sum()),
        "vacas_lactacao": int((leiteiras & situacao.isin({"lactação", "lactacao"})).sum()),
    }


def dias_em_lactacao(data_parto, referencia=None):
    parto = _data(data_parto)
    referencia = _data(referencia) or _hoje_br()
    if parto is None or parto > referencia:
        return None
    return (referencia - parto).days


def historico_colchao(df_colchao, local=None, referencia=None):
    """
    Retorna histórico e status de um ou mais colchões.

    Args:
        df_colchao: DataFrame da aba Leite Colchão
        local: string para filtrar um local específico (opcional)
        referencia: data de referência (padrão: hoje)

    Returns: dict
        Se local fornecido:
            {
                "ultima_troca": {"data": date, "material": str, "condicao": str},
                "proxima_troca": date,
                "dias_desde_troca": int,
                "dias_para_troca": int,
                "status": "ok" | "aviso" | "urgente"
            }
        Se local não fornecido:
            dict de local → status (acima)
    """
    ref = _data(referencia) or _hoje_br()

    if df_colchao is None or df_colchao.empty:
        if local:
            return {
                "ultima_troca": None,
                "proxima_troca": None,
                "dias_desde_troca": None,
                "dias_para_troca": None,
                "status": "ok"
            }
        return {}

    locais = {}
    linhas_ordenadas = df_colchao.sort_values("Data", ascending=False, na_position="last") if "Data" in df_colchao.columns else df_colchao

    for _, linha in linhas_ordenadas.iterrows():
        loc = str(linha.get("Local") or "").strip()
        if not loc:
            continue
        if loc in locais:  # já tem a mais recente
            continue

        data_troca = _data(linha.get("Data"))
        proxima = _data(linha.get("Próxima Troca"))
        material = str(linha.get("Material") or "").strip()
        condicao = str(linha.get("Condição") or "").strip()

        # Se não tem próxima troca, calcula +180 dias (vida útil padrão)
        if not proxima and data_troca:
            proxima = data_troca + timedelta(days=180)

        dias_desde = (ref - data_troca).days if data_troca else None
        dias_para = (proxima - ref).days if proxima else None

        # Determina status: urgente (<=7 dias), aviso (<=14 dias), ok
        if proxima and dias_para <= 7:
            status = "urgente"
        elif proxima and dias_para <= 14:
            status = "aviso"
        else:
            status = "ok"

        locais[loc] = {
            "ultima_troca": {
                "data": data_troca,
                "material": material,
                "condicao": condicao
            },
            "proxima_troca": proxima,
            "dias_desde_troca": dias_desde,
            "dias_para_troca": dias_para,
            "status": status
        }

    if local:
        return locais.get(local, {
            "ultima_troca": None,
            "proxima_troca": None,
            "dias_desde_troca": None,
            "dias_para_troca": None,
            "status": "ok"
        })
    return locais
