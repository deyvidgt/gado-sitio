# -*- coding: utf-8 -*-
import json

import db
import tempo


def test_cache_do_tempo_usa_a_pasta_do_sitio_ativo(tmp_path, monkeypatch):
    pasta_a = tmp_path / "a"
    pasta_b = tmp_path / "b"
    pasta_a.mkdir()
    pasta_b.mkdir()
    monkeypatch.setattr(tempo, "DATA_DIR", None)
    monkeypatch.setattr(db, "DATA_DIR", str(pasta_a))
    monkeypatch.setattr(tempo, "_configuracao", lambda: {"latitude": 1, "longitude": 2})
    dados = {"current": {}, "daily": {"time": []}}
    tempo._salvar_cache(dados, __import__("datetime").datetime(2026, 10, 26))
    monkeypatch.setattr(db, "DATA_DIR", str(pasta_b))
    assert not (pasta_b / tempo.NOME_CACHE).exists()
    assert (pasta_a / tempo.NOME_CACHE).exists()
