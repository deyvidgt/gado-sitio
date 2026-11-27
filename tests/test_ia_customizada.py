import numpy as np
import pandas as pd

from ia_modelos import ModeloGanhoPeso, ModeloPastagem, ModeloRiscoSanitario


def test_custom_models_return_bounded_horizons():
    X = np.random.RandomState(4).randn(30, 3)
    modelos = [ModeloGanhoPeso(), ModeloPastagem(), ModeloRiscoSanitario()]
    for modelo in modelos:
        modelo.treinar(X, np.linspace(0.1, 0.9, 30))
        resultado = modelo.prever({'f0': .4, 'f1': .5, 'f2': .6})
        assert resultado['dados_suficientes'] is True
        assert 0 <= resultado['confianca'] <= 1
        assert resultado['horizonte_dias'] in (30, 14, 7)
        assert resultado['motivos']


def test_custom_models_mark_short_history_insufficient():
    X = np.array([[.1, .2, .3]])
    for cls in (ModeloGanhoPeso, ModeloPastagem, ModeloRiscoSanitario):
        modelo = cls()
        resultado = modelo.prever({'f0': .4, 'f1': .5, 'f2': .6})
        assert resultado['dados_suficientes'] is False
        assert resultado['confianca'] == 0


def test_growth_features_use_weight_slope_and_recent_treatments():
    from ia_features import extrair_features_crescimento
    animais = pd.DataFrame({'ID': ['A1']})
    manejo = pd.DataFrame({
        'Tipo': ['Pesagem', 'Pesagem', 'Tratamento Veterinário', 'Tratamento Veterinário'],
        'Data': ['01/01/2026', '31/01/2026', '15/01/2026', '01/01/2025'],
        'Brincos': ['A1', 'A1', 'A1', 'A1'],
        'Descricao': ['400', '430', 'febre', 'antigo'],
    })
    result = extrair_features_crescimento('A1', animais, manejo, pd.DataFrame(), hoje='01/02/2026')
    assert result['dados_suficientes'] is True
    assert result['peso_tendencia'] > 0
    assert result['tratamentos_recentes'] == 1


def test_growth_feature_extraction_handles_missing_history():
    from ia_features import extrair_features_crescimento
    animais = pd.DataFrame({'ID': ['A1']})
    result = extrair_features_crescimento('A1', animais, pd.DataFrame(), pd.DataFrame())
    assert result['dados_suficientes'] is False
