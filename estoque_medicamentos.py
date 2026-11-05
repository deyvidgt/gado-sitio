# -*- coding: utf-8 -*-
"""Estoque manual de medicamentos controlado por lote e validade."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import math
import uuid

import pandas as pd

import db

ABA = "Estoque Medicamentos"
TIPOS_MOVIMENTO = {"Entrada", "Saída", "Descarte"}
DIAS_ALERTA_VALIDADE = 30


def _texto(valor) -> str:
    if valor is None or pd.isna(valor):
        return ""
    return str(valor).strip()


def _data(valor) -> date | None:
    if valor is None or _texto(valor) == "":
        return None
    if isinstance(valor, (date, datetime)):
        return valor.date() if isinstance(valor, datetime) else valor
    texto = _texto(valor)
    try:
        if len(texto) >= 10 and texto[4:5] == "-" and texto[7:8] == "-":
            return datetime.strptime(texto[:10], "%Y-%m-%d").date()
        if len(texto) >= 10 and texto[2:3] == "/" and texto[5:6] == "/":
            return datetime.strptime(texto[:10], "%d/%m/%Y").date()
        return pd.to_datetime(valor, dayfirst=True, errors="raise").date()
    except (TypeError, ValueError):
        return None


def _numero(valor) -> float:
    try:
        n = float(str(valor).replace(",", ".").strip())
        return n if math.isfinite(n) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _lotes_da_aba(df: pd.DataFrame, hoje: date) -> list[dict]:
    lotes = {}
    if df is None or df.empty:
        return []

    for _, row in df.iterrows():
        data_movimento = _data(row.get("Data"))
        if data_movimento is None or data_movimento > hoje:
            continue
        tipo = _texto(row.get("Movimento"))
        lote_id = _texto(row.get("ID Lote"))
        quantidade = _numero(row.get("Quantidade"))
        if not lote_id or quantidade <= 0 or tipo not in TIPOS_MOVIMENTO:
            continue

        if tipo == "Entrada":
            lotes.setdefault(lote_id, {
                "id": lote_id,
                "produto": _texto(row.get("Produto")),
                "principio": _texto(row.get("Princípio Ativo")),
                "lote": _texto(row.get("Lote")),
                "validade": _data(row.get("Validade")),
                "unidade": _texto(row.get("Unidade")),
                "entrada_em": _data(row.get("Data")),
                "fornecedor": _texto(row.get("Fornecedor/Referência")),
                "saldo": 0.0,
            })
        if lote_id not in lotes:
            continue
        lotes[lote_id]["saldo"] += quantidade if tipo == "Entrada" else -quantidade

    resultado = []
    limite = hoje + timedelta(days=DIAS_ALERTA_VALIDADE)
    for lote in lotes.values():
        if lote["saldo"] <= 1e-9:
            continue
        validade = lote["validade"]
        lote["saldo"] = round(lote["saldo"], 3)
        lote["vencido"] = validade is not None and validade < hoje
        lote["vence_em_breve"] = validade is not None and hoje <= validade <= limite
        lote["dias_validade"] = (validade - hoje).days if validade else None
        lote["status"] = ("vencido" if lote["vencido"] else
                          "vence_em_breve" if lote["vence_em_breve"] else "ok")
        resultado.append(lote)
    resultado.sort(key=lambda l: (l["validade"] or date.max, l["produto"].casefold(), l["lote"]))
    return resultado


def lotes_ativos(hoje=None) -> list[dict]:
    """Lotes com saldo positivo, incluindo situação e prazo de validade."""
    referencia = hoje or datetime.now().date()
    if isinstance(referencia, datetime):
        referencia = referencia.date()
    return _lotes_da_aba(db.carregar_aba(ABA), referencia)


def registrar_movimento(movimento: str, data, produto: str = "", principio: str = "",
                        lote: str = "", validade=None, quantidade=0, unidade: str = "",
                        lote_id: str = "", fornecedor: str = "", observacoes: str = "",
                        responsavel: str = "Sistema") -> str:
    """Registra entrada, saída/uso ou descarte; saída é validada e gravada sob trava."""
    movimento = str(movimento or "").strip()
    data_movimento = _data(data)
    qtd = _numero(quantidade)
    if movimento not in TIPOS_MOVIMENTO:
        raise ValueError("Tipo de movimentação inválido.")
    if data_movimento is None:
        raise ValueError("Informe uma data válida.")
    if qtd <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")

    if movimento == "Entrada":
        produto, principio, lote, unidade = (
            str(v or "").strip() for v in (produto, principio, lote, unidade)
        )
        if not unidade:
            raise ValueError("Informe a unidade da quantidade.")
        data_validade = _data(validade)
        if not produto or not principio or not lote:
            raise ValueError("Informe produto, princípio ativo e lote.")
        if data_validade is None:
            raise ValueError("Informe uma validade válida.")
        if data_validade < data_movimento:
            raise ValueError("A validade não pode ser anterior à data de entrada.")
        novo_lote_id = uuid.uuid4().hex[:12].upper()
    else:
        novo_lote_id = str(lote_id or "").strip()
        if not novo_lote_id:
            raise ValueError("Selecione o lote do medicamento.")

    movimento_id = uuid.uuid4().hex[:12].upper()
    erro = []

    def atualizar(df):
        referencia = data_movimento
        atuais = {l["id"]: l for l in _lotes_da_aba(df, referencia)}
        if movimento != "Entrada":
            lote_atual = atuais.get(novo_lote_id)
            if lote_atual is None:
                erro.append("Lote sem saldo disponível.")
                return df
            data_entrada = lote_atual["entrada_em"]
            if data_entrada and data_movimento < data_entrada:
                erro.append("A data do movimento não pode anteceder a entrada do lote.")
                return df
            if movimento == "Saída" and lote_atual["vencido"]:
                erro.append("Lote vencido não pode ser lançado como uso; registre como descarte.")
                return df
            if movimento == "Saída" and data_movimento > lote_atual["validade"]:
                erro.append("Lote vencido na data do movimento; registre como descarte.")
                return df
            if qtd > lote_atual["saldo"] + 1e-9:
                erro.append(f"Saldo insuficiente: há {lote_atual['saldo']:g} {lote_atual['unidade']}.")
                return df
            produto_mov = lote_atual["produto"]
            principio_mov = lote_atual["principio"]
            lote_mov = lote_atual["lote"]
            validade_mov = lote_atual["validade"]
            unidade_mov = lote_atual["unidade"]
            lote_fornecedor = ""
        else:
            produto_mov, principio_mov, lote_mov = produto, principio, lote
            validade_mov = data_validade
            unidade_mov = unidade
            lote_fornecedor = str(fornecedor or "").strip()

        linha = {
            "ID Movimento": movimento_id,
            "Data": data_movimento.strftime("%d/%m/%Y"),
            "Movimento": movimento,
            "Produto": produto_mov,
            "Princípio Ativo": principio_mov,
            "Lote": lote_mov,
            "Validade": validade_mov.strftime("%d/%m/%Y") if validade_mov else "",
            "Quantidade": qtd,
            "Unidade": unidade_mov,
            "ID Lote": novo_lote_id,
            "Fornecedor/Referência": lote_fornecedor,
            "Observações": str(observacoes or "").strip(),
            "Responsável": str(responsavel or "Sistema").strip(),
        }
        return pd.concat([df, pd.DataFrame([linha])], ignore_index=True)

    db.alterar_aba(ABA, atualizar)
    if erro:
        raise ValueError(erro[0])
    return movimento_id
