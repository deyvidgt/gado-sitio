# -*- coding: utf-8 -*-

from openpyxl import load_workbook

import config
import db


ABAS_LEITE = {
    "Leite Produção": config.COLUNAS_LEITE_PRODUCAO,
    "Leite Configuração": config.COLUNAS_LEITE_CONFIG,
    "Leite Alimentação": config.COLUNAS_LEITE_ALIMENTACAO,
    "Leite Necessidades": config.COLUNAS_LEITE_NECESSIDADES,
    "Leite Tratamentos": config.COLUNAS_LEITE_TRATAMENTOS,
    "Leite Conforto": config.COLUNAS_LEITE_CONFORTO,
    "Leite Colchão": config.COLUNAS_LEITE_COLCHAO,
}


def test_migra_abas_leiteiras_com_colunas_exatas():
    db.inicializar()
    wb = load_workbook(db.ARQUIVO_PATH, read_only=True, data_only=True)
    try:
        for aba, colunas in ABAS_LEITE.items():
            assert aba in wb.sheetnames
            cabecalho = [celula.value for celula in next(wb[aba].iter_rows(max_row=1))]
            # Migração acrescenta colunas, mas nunca reordena um cabeçalho legado.
            assert set(cabecalho) == set(colunas)
            assert len(cabecalho) == len(colunas)
    finally:
        wb.close()


def test_aba_animais_ganha_colunas_do_leite_no_fim():
    db.inicializar()
    wb = load_workbook(db.ARQUIVO_PATH, read_only=True, data_only=True)
    try:
        cabecalho = [celula.value for celula in next(wb["Animais"].iter_rows(max_row=1))]
    finally:
        wb.close()
    # No fim: a migração nunca reordena as colunas que já existiam.
    assert cabecalho == config.COLUNAS_ANIMAIS
    assert cabecalho[-5:] == ["Uso Produtivo", "Situação Leite", "Último Parto", "Pai", "Genótipo"]


def test_migracao_leiteira_e_idempotente():
    db.inicializar()
    wb = load_workbook(db.ARQUIVO_PATH, read_only=True, data_only=True)
    try:
        antes = {
            aba: [celula.value for celula in next(wb[aba].iter_rows(max_row=1))]
            for aba in ABAS_LEITE
        }
    finally:
        wb.close()

    db.inicializar()
    wb = load_workbook(db.ARQUIVO_PATH, read_only=True, data_only=True)
    try:
        depois = {
            aba: [celula.value for celula in next(wb[aba].iter_rows(max_row=1))]
            for aba in ABAS_LEITE
        }
    finally:
        wb.close()

    assert depois == antes
