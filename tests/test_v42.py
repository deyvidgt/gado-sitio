# -*- coding: utf-8 -*-
"""v4.2: estoque de insumos, visita offline (/api/visitas) e WhatsApp urgente/semanal."""
from datetime import datetime

import pandas as pd
import pytest

import db
from insumos import previsao_insumo

T = pd.Timestamp


# ── Estoque de insumos ─────────────────────────────────────────────────────────

def _vis(*linhas):
    return pd.DataFrame([{"Data": T(d), "Sacos Sal/Ração": q} for d, q in linhas])


def _compras(*linhas):
    return pd.DataFrame([{"Data": T(d), "Produto": "Sal", "Qtd Sacos": q} for d, q in linhas])


def test_previsao_usa_contagens_e_compras():
    vis = _vis(("2026-09-01", 10), ("2026-09-11", 8), ("2026-09-21", 9))
    p = previsao_insumo("Sal", vis, _compras(("2026-09-15", 3)), datetime(2026, 10, 1))
    # (10−8) + (8+3−9) = 4 sacos em 20 dias → 0,2/dia; hoje: 9 − 0,2×10 = 7
    assert p["consumo_dia"] == pytest.approx(0.2)
    assert p["estoque"] == pytest.approx(7)
    assert p["dias_restantes"] == 35 and p["status"] == "ok"


def test_compra_nao_lancada_nao_vira_consumo_negativo():
    vis = _vis(("2026-09-01", 10), ("2026-09-11", 8), ("2026-09-21", 9))
    p = previsao_insumo("Sal", vis, pd.DataFrame(), datetime(2026, 10, 1))
    assert p["consumo_dia"] == pytest.approx(0.2)   # só o 1º intervalo conta


def test_uma_contagem_so_pede_nova_contagem():
    p = previsao_insumo("Sal", _vis(("2026-09-01", 4)), pd.DataFrame(), datetime(2026, 10, 1))
    assert p["status"] == "sem_consumo" and p["estoque"] == 4


def test_estoque_acabando_e_urgente():
    vis = _vis(("2026-09-01", 10), ("2026-09-21", 2))
    p = previsao_insumo("Sal", vis, pd.DataFrame(), datetime(2026, 9, 25))
    assert p["status"] in ("urgente", "acabou")


# ── Visita pelo celular / offline ──────────────────────────────────────────────

def _post_visita(cliente, **extra):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    dados = {"csrf_token": "tok", "data": "2026-10-03", "responsavel": "Deyvid",
             "gado_contado": "28", "sacos_sal": "5", "id_envio": "a1b2c3d4e5f6a7b8"}
    dados.update(extra)
    return cliente.post("/api/visitas", data=dados)


def test_api_visita_grava_e_nao_duplica_reenvio(cliente, dados_restaurados, monkeypatch):
    import alertas_whatsapp
    monkeypatch.setattr(alertas_whatsapp, "enviar_para_familia", lambda msg, **kw: 0)
    n = len(db.carregar_aba("Visitas"))
    r1 = _post_visita(cliente)
    assert r1.status_code == 200 and r1.get_json()["ok"] and not r1.get_json()["duplicada"]
    r2 = _post_visita(cliente)   # celular reenviou (não recebeu a confirmação)
    assert r2.get_json()["duplicada"]
    df = db.carregar_aba("Visitas")
    assert len(df) == n + 1
    ult = df.iloc[-1]
    assert ult["ID Envio"] == "id:a1b2c3d4e5f6a7b8" and int(ult["Sacos Sal/Ração"]) == 5


def test_api_visita_sem_login_responde_json_401(flask_app):
    r = flask_app.test_client().post("/api/visitas", data={"data": "2026-10-03"})
    assert r.status_code == 401 and r.get_json()["erro"] == "login"


def test_api_visita_token_errado_responde_json_403(cliente):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "certo"
    r = cliente.post("/api/visitas", data={"csrf_token": "errado"})
    assert r.status_code == 403 and r.get_json()["erro"] == "csrf"


def test_api_csrf_entrega_token_da_sessao(cliente):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "abc"
    assert cliente.get("/api/csrf").get_json()["csrf_token"] == "abc"


@pytest.fixture
def fila_avisos_vazia():
    import alertas_whatsapp
    caminho = alertas_whatsapp._pendentes_path()
    if caminho.exists():
        caminho.unlink()
    yield caminho
    if caminho.exists():
        caminho.unlink()


def test_aviso_de_visita_roda_depois_da_resposta(cliente, dados_restaurados, monkeypatch,
                                                  fila_avisos_vazia):
    """Sem thread: o envio roda ao fechar a resposta (call_on_close)."""
    import alertas_whatsapp
    chamadas = []
    monkeypatch.setattr(alertas_whatsapp, "enviar_para_familia", lambda msg, **kw: chamadas.append(msg) or 1)
    r = _post_visita(cliente, id_envio="ffffeeeeddddcccc")
    assert r.status_code == 200 and chamadas == []   # ainda não: só depois da resposta
    r.close()
    assert len(chamadas) == 1 and "Deyvid" in chamadas[0]
    assert not fila_avisos_vazia.exists()


def test_aviso_nao_se_perde_se_a_conexao_cair(cliente, dados_restaurados, monkeypatch,
                                             fila_avisos_vazia):
    """1ª aba grava e some antes da resposta (close nunca roda); o reenvio da
    outra aba volta 'duplicada' e é ele que entrega o aviso guardado."""
    import alertas_whatsapp
    chamadas = []
    monkeypatch.setattr(alertas_whatsapp, "enviar_para_familia", lambda msg, **kw: chamadas.append(msg) or 1)
    _post_visita(cliente, id_envio="9999888877776666")          # resposta nunca fechada
    assert fila_avisos_vazia.exists() and chamadas == []
    r2 = _post_visita(cliente, id_envio="9999888877776666")
    assert r2.get_json()["duplicada"]
    r2.close()
    assert len(chamadas) == 1


# ── Gasto com produto/sacos ────────────────────────────────────────────────────

def test_gasto_de_sal_grava_produto_e_sacos(cliente, dados_restaurados):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    cliente.post("/gastos/novo", data={"csrf_token": "tok", "data": "2026-10-03",
                                       "tipo": "Sal/Proteínado", "descricao": "sal mineral",
                                       "valor": "450,00", "cabecas": "28", "membro": "Deyvid",
                                       "produto": "Sal", "qtd_sacos": "6"})
    ult = db.carregar_aba("Gastos").iloc[-1]
    assert ult["Produto"] == "Sal" and int(ult["Qtd Sacos"]) == 6
    assert ult["Valor Total (R$)"] == pytest.approx(450.0)


def test_gasto_de_outro_tipo_ignora_produto(cliente, dados_restaurados):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    cliente.post("/gastos/novo", data={"csrf_token": "tok", "data": "2026-10-03",
                                       "tipo": "Gasolina/Transporte", "valor": "100", "cabecas": "28",
                                       "membro": "Deyvid", "produto": "Sal", "qtd_sacos": "6"})
    ult = db.carregar_aba("Gastos").iloc[-1]
    assert pd.isna(ult["Produto"]) or ult["Produto"] in ("", None)


# ── WhatsApp: urgente nos dias comuns, sem repetir; resumo na segunda ─────────

def test_urgente_nao_repete_antes_do_prazo():
    import alertas_whatsapp as aw
    itens = [{"chave": "x", "texto": "t", "urgente": True, "repetir": 3},
             {"chave": "y", "texto": "info", "urgente": False, "repetir": 3}]
    hoje = datetime(2026, 10, 6)
    assert [i["chave"] for i in aw.urgentes_a_enviar(itens, hoje, {})] == ["x"]
    estado = aw._marcar_enviados(itens, hoje, {})
    assert aw.urgentes_a_enviar(itens, datetime(2026, 10, 8), estado) == []
    assert len(aw.urgentes_a_enviar(itens, datetime(2026, 10, 9), estado)) == 1


def test_dia_comum_sem_urgencia_nao_envia(monkeypatch):
    import alertas_whatsapp as aw
    enviados = []
    monkeypatch.setattr(aw, "montar_itens", lambda hoje=None: [
        {"chave": "y", "texto": "info", "urgente": False, "repetir": 3}])
    monkeypatch.setattr(aw, "enviar_para_familia", lambda msg, **kw: enviados.append(msg) or 1)
    monkeypatch.setattr(aw, "_agora_br", lambda: datetime(2026, 10, 7))   # quarta
    aw.main([])
    assert enviados == []
    monkeypatch.setattr(aw, "_agora_br", lambda: datetime(2026, 10, 5))   # segunda
    monkeypatch.setattr(aw, "_gravar_estado", lambda e: None)
    aw.main([])
    assert len(enviados) == 1 and "Resumo semanal" in enviados[0]


def test_mesma_visita_enviada_ao_mesmo_tempo_grava_uma_vez(flask_app, dados_restaurados, monkeypatch):
    """Duas abas reenviando a mesma visita juntas: a trava faz só uma gravar."""
    import threading
    import alertas_whatsapp
    monkeypatch.setattr(alertas_whatsapp, "enviar_para_familia", lambda msg, **kw: 0)
    n = len(db.carregar_aba("Visitas"))
    resultados = []

    def enviar():
        cli = flask_app.test_client()
        with cli.session_transaction() as s:
            s["logado"], s["usuario"], s["csrf_token"] = True, "deyvid", "tok"
        r = cli.post("/api/visitas", data={"csrf_token": "tok", "data": "2026-10-03",
                                           "responsavel": "Deyvid", "id_envio": "abcabcabcabc0001"})
        resultados.append(r.get_json())

    threads = [threading.Thread(target=enviar) for _ in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert all(r["ok"] for r in resultados)
    assert sum(not r["duplicada"] for r in resultados) == 1
    assert len(db.carregar_aba("Visitas")) == n + 1


@pytest.mark.parametrize("rota,marca", [
    ("/visitas/nova", 'form.addEventListener("submit"'),
    ("/manejo/novo", 'const grpPerda = document.getElementById("grupo-perda")'),
])
def test_scripts_do_formulario_aparecem_uma_vez(cliente, rota, marca):
    """Bloco scripts dentro do content fazia o Jinja desenhar os scripts 2x
    (cada 'Salvar' da visita enviava duas visitas)."""
    assert cliente.get(rota).get_data(as_text=True).count(marca) == 1
