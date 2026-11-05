# -*- coding: utf-8 -*-
"""Classificação consolidada dos gastos para análise financeira."""
import unicodedata

from config import CATEGORIAS_GASTO


def _normalizar(valor) -> str:
    texto = str(valor or "").strip().casefold()
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def categoria_legada(tipo, descricao="") -> str:
    """Classifica registros antigos de forma conservadora; casos sem pista vão a Outros."""
    texto = f"{_normalizar(tipo)} {_normalizar(descricao)}"
    if any(p in texto for p in ("imposto", "tributo", "icms", "iss", "ipva", "inss", "irpf")):
        return "Impostos"
    if any(p in texto for p in ("salario", "mao de obra", "diaria", "funcionario", "empreita")):
        return "Mão de obra"
    if any(p in texto for p in ("remedio", "vacina", "medicamento", "vermifugo",
                                "veneno", "defensivo", "sanitario", "veterin")):
        return "Sanidade"
    if any(p in texto for p in ("sal/", "sal ", "protein", "racao", "calcario", "adub")):
        return "Nutrição"
    if any(p in texto for p in ("gasolina", "transporte", "manutencao", "conserto",
                                "cerca", "maquina", "peca", "frete")):
        return "Manutenção"
    if tipo == "Remédio/Vacina" or tipo == "Veneno/Defensivo":
        return "Sanidade"
    if tipo == "Sal/Proteínado" or tipo == "Calcário/Adubação":
        return "Nutrição"
    if tipo in ("Gasolina/Transporte", "Manutenção/Outros"):
        return "Manutenção"
    return "Outros" if "Outros" in CATEGORIAS_GASTO else CATEGORIAS_GASTO[-1]
