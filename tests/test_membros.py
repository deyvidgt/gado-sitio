# -*- coding: utf-8 -*-
"""
Fase 1 dos vários sítios — donos (sócios) vindos do sitio_config.json.
Sem configuração, tudo igual a hoje (Geane/Deyvid/Nilson).
"""
import os

import pytest
from openpyxl import Workbook

import config
import db

def test_padrao_igual_ao_de_hoje():
    assert config.MEMBROS == ["Mae", "Deyvid", "Nilson"]
    assert config.NOMES_MEMBROS == {"Mae": "Geane", "Deyvid": "Deyvid", "Nilson": "Nilson"}
    assert config.CORES_BRINCO_PADRAO == {"Deyvid": "Amarelo", "Nilson": "Azul", "Mae": "Vermelho"}
    assert config.COLUNAS_COMPRAS == [
        "Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)",
        "Qtd Mae", "Qtd Deyvid", "Qtd Nilson", "Descrição", "Registrado Por"]
    assert config.COLUNAS_VENDAS == [
        "Data", "Qtd Cabeças", "Valor Total (R$)", "Valor/Cabeça (R$)", "Valor Arroba (R$)",
        "Qtd Mae", "Qtd Deyvid", "Qtd Nilson",
        "Valor Mae (R$)", "Valor Deyvid (R$)", "Valor Nilson (R$)",
        "Custo Mae (R$)", "Custo Deyvid (R$)", "Custo Nilson (R$)",
        "Resultado Mae (R$)", "Resultado Deyvid (R$)", "Resultado Nilson (R$)",
        "CMP no momento (R$)", "Descrição", "Brincos"]
    assert config.LOGIN_MEMBRO == {"geane": "Mae", "mae": "Mae", "deyvid": "Deyvid", "nilson": "Nilson"}


def test_quatro_donos_gera_colunas(membros_teste):
    membros_teste(4)
    assert config.MEMBROS == ["A", "B", "C", "D"]
    c = config.COLUNAS_COMPRAS
    assert c[c.index("Qtd C") + 1] == "Qtd D" and c[c.index("Qtd D") + 1] == "Descrição"
    v = config.COLUNAS_VENDAS
    assert v.index("Resultado D (R$)") + 1 == v.index("CMP no momento (R$)")
    # quem importou por nome vê a troca (mesmo objeto)
    from calculos import MEMBROS as M_calc
    assert M_calc == ["A", "B", "C", "D"]
    assert db._SCHEMA_ABAS["Vendas"] is config.COLUNAS_VENDAS


def _m(chave, cor, nome=None):
    return {"chave": chave, "nome": nome or chave, "emoji": "🙂", "cor": cor, "logins": [chave.lower()]}


@pytest.mark.parametrize("membros", [
    [_m("Jo ao", "Azul"), _m("Ana", "Verde")],          # chave com espaço
    [_m("Joao", "Azul"), _m("Ana", "Azul")],             # cor repetida
    [_m("Joao", "Azul"), _m("Joao", "Verde")],           # chave repetida
    [_m("Joao", "Azul")],                                # um dono só
    [_m(f"D{chr(65 + i)}", c) for i, c in enumerate(config.CORES_BRINCO[:9])],  # 9 donos
    [_m("Joao", "Lilás"), _m("Ana", "Verde")],           # cor que não existe
    "não é lista",
])
def test_config_invalida_usa_padrao(membros):
    assert [m["chave"] for m in config.ler_membros({"membros": membros})] == ["Mae", "Deyvid", "Nilson"]


def test_config_sem_membros_usa_padrao():
    assert config.ler_membros(None) == config.MEMBROS_PADRAO
    assert config.ler_membros({"preco_arroba": 300}) == config.MEMBROS_PADRAO


def test_config_valida():
    lista = [_m("Joao", "Azul", "João"), _m("Ana", "Verde")]
    assert config.ler_membros({"membros": lista}) == lista


def test_arquivo_com_outros_donos_recusa(membros_teste, tmp_path, monkeypatch):
    # Arquivo de 3 donos (o de hoje) e configuração com 4: não pode gravar desalinhado.
    arq = tmp_path / "gado_familia.xlsx"
    wb = Workbook()
    wb.active.title = "Compras"
    wb.active.append(list(config.COLUNAS_COMPRAS))
    wb.save(arq)
    membros_teste(4)
    monkeypatch.setattr(db, "ARQUIVO_PATH", str(arq))
    monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))
    with pytest.raises(RuntimeError, match="donos"):
        db.inicializar()


def test_arquivo_novo_nasce_com_os_donos(membros_teste, tmp_path, monkeypatch):
    membros_teste(2)
    arq = tmp_path / "gado_familia.xlsx"
    monkeypatch.setattr(db, "ARQUIVO_PATH", str(arq))
    monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))
    db.inicializar()
    db.inicializar()   # 2ª vez (arquivo existe, donos batem): não reclama
    from openpyxl import load_workbook
    cab = [c.value for c in load_workbook(arq)["Compras"][1]]
    assert cab[4:6] == ["Qtd A", "Qtd B"]
    assert os.path.exists(arq)
