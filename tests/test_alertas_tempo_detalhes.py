# -*- coding: utf-8 -*-
import tempo


def test_alertas_mostra_temperatura_e_previsao_diaria(cliente, monkeypatch):
    monkeypatch.setattr(tempo, "previsao", lambda: {
        "status": "atualizado", "mensagem": "Previsão atualizada.",
        "local": "Sítio Teste", "atual": {"temperatura": 28.4, "umidade": 61,
        "vento_kmh": 12.3, "condicao": "Predominantemente limpo"},
        "dias": [{"data": "2026-10-26", "maxima": 31, "minima": 20,
                  "chuva_probabilidade": 20, "chuva_mm": 0, "condicao": "Céu limpo"}],
    })
    html = cliente.get("/alertas").get_data(as_text=True)
    assert "28,4" in html
    assert "Predominantemente limpo" in html
    assert "31" in html
    assert "20%" in html
