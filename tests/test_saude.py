# -*- coding: utf-8 -*-
"""Testes do calendário sanitário (saude.py) — regras do Triângulo Mineiro."""
from datetime import datetime

import pandas as pd

import saude
from test_calculos import manejo, VAZIO_MAN


def _msgs(lst):
    return " | ".join(x["msg"] for x in lst)


def test_vacinacao_antiga_conta_para_raiva_e_clostridioses():
    df = manejo(("2026-03-10", "Vacinação", 30, None))
    assert saude.ultima_data(df, "Vacina Raiva") == pd.Timestamp("2026-03-10")
    assert saude.ultima_data(df, "Vacina Clostridioses") == pd.Timestamp("2026-03-10")
    assert saude.ultima_data(df, "Vacina Brucelose") is None


def test_vacina_especifica_mais_recente_vence():
    df = manejo(("2025-01-10", "Vacinação", 30, None),
                ("2026-02-01", "Vacina Raiva", 30, None))
    assert saude.ultima_data(df, "Vacina Raiva") == pd.Timestamp("2026-02-01")
    assert saude.ultima_data(df, "Vacina Clostridioses") == pd.Timestamp("2025-01-10")


def test_brucelose_avisa_no_fim_da_etapa_sem_vacina():
    msg = _msgs(saude.lembretes_sazonais(VAZIO_MAN, datetime(2026, 6, 5)))
    assert "Brucelose (1ª etapa)" in msg and "até 30/06" in msg and "10/07" in msg


def test_brucelose_vacinada_so_lembra_declaracao():
    df = manejo(("2026-11-20", "Vacina Brucelose", 4, None))
    lst = saude.lembretes_sazonais(df, datetime(2026, 12, 2))
    bru = [x for x in lst if "Brucelose" in x["msg"]]
    assert bru and bru[0]["nivel"] == "info" and "10/01" in bru[0]["msg"]


def test_brucelose_janela_de_declaracao_em_janeiro():
    df = manejo(("2026-12-10", "Vacina Brucelose", 4, None))
    assert "declare" in _msgs(saude.lembretes_sazonais(df, datetime(2027, 1, 5)))
    # sem vacina no semestre anterior, não há o que declarar
    assert "Brucelose" not in _msgs(saude.lembretes_sazonais(VAZIO_MAN, datetime(2027, 1, 5)))


def test_sem_lembrete_fora_de_epoca():
    assert saude.lembretes_sazonais(VAZIO_MAN, datetime(2026, 3, 15)) == []


def test_vermifugacao_5_7_9():
    assert "5-7-9" in _msgs(saude.lembretes_sazonais(VAZIO_MAN, datetime(2026, 7, 3)))
    feita = manejo(("2026-07-01", "Vermifugação", 20, None))
    assert "5-7-9" not in _msgs(saude.lembretes_sazonais(feita, datetime(2026, 7, 3)))
    assert "5-7-9" not in _msgs(saude.lembretes_sazonais(VAZIO_MAN, datetime(2026, 8, 3)))


def test_brucelose_no_calendario():
    p = saude.brucelose_proxima(VAZIO_MAN, datetime(2026, 6, 20))
    assert p["data_prevista"] == "2026-06-30" and p["status"] == "urgente"
    df = manejo(("2026-03-01", "Vacina Brucelose", 3, None))
    p = saude.brucelose_proxima(df, datetime(2026, 6, 20))
    assert p["status"] == "ok" and p["data_prevista"] == "2026-12-31"
    assert p["ultima_data"] == "01/03/2026"


def test_api_calendario_tem_vacinas_separadas(cliente):
    d = cliente.get("/api/calendario-manejo").get_json()
    tipos = [p["tipo"] for p in d["proximas"]]
    for t in ("Vacina Raiva", "Vacina Clostridioses", "Vacina Brucelose", "Vermifugação"):
        assert t in tipos


def test_form_de_manejo_oferece_as_vacinas(cliente):
    html = cliente.get("/manejo/novo").get_data(as_text=True)
    for t in ("Vacina Raiva", "Vacina Clostridioses", "Vacina Brucelose"):
        assert t in html


def test_prazo_salvo_com_padrao_antigo_vira_o_novo(tmp_path, monkeypatch):
    import json
    import db
    cfg = tmp_path / "sitio_config.json"
    cfg.write_text(json.dumps({"alertas_saude": {"Vermifugação": 120, "Pesagem": 60,
                                                 "Vacinação": 180}}), encoding="utf-8")
    monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))
    prazos = db.get_alertas_saude()
    assert prazos["Vermifugação"] == 240   # 120 era o padrão antigo → padrão novo
    assert prazos["Pesagem"] == 60         # ajuste de verdade é respeitado
    assert "Vacinação" not in prazos       # chave antiga ignorada


def test_vencimento_no_proprio_dia_nao_aparece_atrasado(monkeypatch):
    """Data prevista é meia-noite; com a hora atual o dia do vencimento dava −1."""
    from datetime import datetime
    import pandas as pd
    import routes_api_extras as rae
    from saude import brucelose_proxima
    agora = datetime(2026, 10, 4, 15, 30)
    man = pd.DataFrame({"Data": [pd.Timestamp("2025-10-04")], "Tipo": ["Vacina Raiva"],
                        "Qtd Cabeças": [10]})
    monkeypatch.setattr(rae, "_agora", lambda: agora)
    monkeypatch.setattr(rae, "carregar_aba",
                        lambda aba: man if aba == "Manejo" else pd.DataFrame())
    monkeypatch.setattr(rae, "get_alertas_saude", lambda: {"Vacina Raiva": 365})
    with rae.app.test_request_context():
        from flask import session
        session["logado"] = True
        dados = rae.api_calendario_manejo.__wrapped__().get_json()
    raiva = next(p for p in dados["proximas"] if p["tipo"] == "Vacina Raiva")
    assert raiva["dias_restantes"] == 0 and raiva["status"] != "atrasado"
    assert brucelose_proxima(man, datetime(2026, 12, 31, 18, 0))["dias_restantes"] == 0
