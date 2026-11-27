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


def test_growth_feature_extraction_handles_missing_history():
    from ia_features import extrair_features_crescimento
    animais = pd.DataFrame({'ID': ['A1']})
    result = extrair_features_crescimento('A1', animais, pd.DataFrame(), pd.DataFrame())
    assert result['dados_suficientes'] is False
