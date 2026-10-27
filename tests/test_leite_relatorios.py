# -*- coding: utf-8 -*-
from io import BytesIO

from openpyxl import load_workbook

from leite import serie_diaria
import pandas as pd


def _df():
    return pd.DataFrame([
        {"Data": "01/10/2026", "Vaca ID": "", "Modo Registro": "total", "Ordenha": "manhã", "Litros": 40},
        {"Data": "01/10/2026", "Vaca ID": "A1", "Modo Registro": "individual", "Ordenha": "manhã", "Litros": 18},
        {"Data": "02/10/2026", "Vaca ID": "", "Modo Registro": "total", "Ordenha": "manhã", "Litros": 30},
        {"Data": "20/10/2026", "Vaca ID": "", "Modo Registro": "total", "Ordenha": "manhã", "Litros": 99},
    ])


def test_serie_diaria_filtra_periodo_e_nao_soma_total_com_individual():
    serie = serie_diaria(_df(), "01/10/2026", "10/10/2026")
    assert [(d.day, l) for d, l in serie] == [(1, 18.0), (2, 30.0)]


def test_serie_diaria_vazia():
    assert serie_diaria(pd.DataFrame(), "01/10/2026", "10/10/2026") == []


def test_relatorio_abre_sem_registros(cliente):
    r = cliente.get("/leite/relatorios?inicio=2000-01-01&fim=2000-01-31")
    assert r.status_code == 200
    assert "Nenhuma ordenha registrada" in r.get_data(as_text=True)


def test_exportar_gera_excel_sem_tocar_na_planilha(cliente):
    r = cliente.get("/leite/relatorios/exportar?inicio=2000-01-01&fim=2000-01-31")
    assert r.status_code == 200
    ws = load_workbook(BytesIO(r.data)).active
    assert [c.value for c in ws[1]] == ["Data", "Litros"]
