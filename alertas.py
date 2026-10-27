# -*- coding: utf-8 -*-
"""Alertas operacionais do módulo leiteiro."""

from datetime import date, timedelta

import pandas as pd

from leite import _data, _numero, contagens_rebanho, _sem_duplicidade, historico_colchao


def _item(origem, titulo, detalhe, prioridade="aviso", acao="Abrir módulo"):
    return {"origem": origem, "titulo": titulo, "detalhe": detalhe,
            "prioridade": prioridade, "acao": acao}


def _carencia(tratamentos, referencia):
    itens = []
    if tratamentos is None or tratamentos.empty:
        return itens
    for _, linha in tratamentos.iterrows():
        inicio = _data(linha.get("Data"))
        dias = _numero(linha.get("Período de Carência"))
        if inicio is None or dias is None or dias <= 0:
            continue
        fim = inicio + timedelta(days=int(dias))
        if inicio <= referencia < fim:
            animal = str(linha.get("Vaca ID") or linha.get("Brinco") or "animal não informado").strip()
            itens.append(_item("tratamento", "Tratamento em carência",
                                f"{animal} está em carência até {fim.strftime('%d/%m/%Y')}.",
                                "urgente", "Abrir tratamentos"))
    return itens


def _colchao_alertas(colchao, referencia):
    """Detecta alertas de colchão: urgente (<= 7 dias), aviso (<= 14 dias) e sugestão (> 180 dias)."""
    if colchao is None or colchao.empty:
        return []

    itens = []
    ref = _data(referencia) or date.today()
    historicos = historico_colchao(colchao, referencia=ref)

    for local, hist in historicos.items():
        if hist is None or hist.get("status") == "ok":
            continue

        # Urgente: próxima troca <= 7 dias
        if hist["status"] == "urgente" and hist.get("dias_para_troca") is not None:
            dias = hist["dias_para_troca"]
            proxima = hist.get("proxima_troca")
            data_str = proxima.strftime("%d/%m/%Y") if proxima else "—"
            itens.append(_item(
                "colchão", "🛏️ Colchão urgente",
                f"Colchão da {local} vence em {dias} dia(s) — troca prevista para {data_str}.",
                "urgente", "Abrir colchão"
            ))

        # Aviso: próxima troca <= 14 dias
        elif hist["status"] == "aviso" and hist.get("dias_para_troca") is not None:
            dias = hist["dias_para_troca"]
            proxima = hist.get("proxima_troca")
            data_str = proxima.strftime("%d/%m/%Y") if proxima else "—"
            itens.append(_item(
                "colchão", "🛏️ Colchão próximo da troca",
                f"Colchão da {local} próximo da troca (em {dias} dia(s), {data_str}).",
                "aviso", "Abrir colchão"
            ))

    # Sugestão suave: última troca > 180 dias sem próxima troca registrada
    if colchao is not None and not colchao.empty:
        for _, linha in colchao.iterrows():
            local = str(linha.get("Local") or "").strip()
            if not local or local in historicos:
                continue
            data_troca = _data(linha.get("Data"))
            if data_troca and (ref - data_troca).days > 180:
                dias = (ref - data_troca).days
                itens.append(_item(
                    "colchão", "🛏️ Revisar colchão",
                    f"Colchão da {local} não foi trocado há {dias} dias — considere revisar.",
                    "aviso", "Abrir colchão"
                ))

    return itens


def _nutricao_alertas(alimentacao):
    if alimentacao is None or alimentacao.empty:
        return [_item("nutrição", "Nutrição e consumo",
                       "Cadastre ao menos um alimento leiteiro e suas necessidades diárias.",
                       "aviso", "Abrir alimentação")]
    incompletos = []
    campos = ["Proteína Bruta (%)", "NDT/Energia (%)", "Fibra (%)", "Cálcio (%)", "Fósforo (%)"]
    for _, linha in alimentacao.iterrows():
        if str(linha.get("Ativo", "Sim")).strip().lower() in {"não", "nao", "false", "0"}:
            continue
        if any(str(linha.get(campo) or "").strip() == "" for campo in campos):
            incompletos.append(str(linha.get("Produto") or "produto sem nome"))
    if incompletos:
        return [_item("nutrição", "Nutrição e consumo",
                       "Ficha nutricional incompleta: " + ", ".join(incompletos) + ".",
                       "aviso", "Abrir alimentação")]
    return []


def todos(*, producao=None, animais=None, tratamentos=None, colchao=None,
           alimentacao=None, referencia=None):
    referencia = _data(referencia) or date.today()
    itens = []
    contagens = contagens_rebanho(animais)
    if producao is not None and contagens["vacas_lactacao"]:
        linhas = _sem_duplicidade(producao)
        ultima = linhas["_data"].max() if not linhas.empty else None
        if ultima is None or (referencia - ultima).days >= 1:
            itens.append(_item("produção", "Produção sem registro",
                               f"Há {contagens['vacas_lactacao']} vaca(s) em lactação sem registro desde o último dia.",
                               "urgente", "Abrir ordenha"))
    itens.extend(_carencia(tratamentos, referencia))
    itens.extend(_colchao_alertas(colchao, referencia))
    itens.extend(_nutricao_alertas(alimentacao))
    if not any(item["origem"] == "conforto" for item in itens):
        itens.append(_item("conforto", "Conforto térmico",
                           "Registre sombra, água, ventilação e descanso observado.",
                           "aviso", "Abrir conforto"))
    return itens
