# -*- coding: utf-8 -*-
"""
Configuração dos testes.

SEGURANÇA DOS DADOS: antes de importar qualquer módulo do sistema, apontamos
GADO_DATA_DIR para uma pasta temporária com uma CÓPIA do gado_familia.xlsx.
Assim nenhum teste lê ou grava o arquivo real (nem o de ~/gado-dados/).
"""
import os
import sys
import shutil
import tempfile

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

# Origem da cópia: GADO_DADOS_TESTE (opcional) → ~/gado-dados/ → pasta do projeto
_ORIGEM = os.environ.get("GADO_DADOS_TESTE") or (
    os.path.expanduser("~/gado-dados")
    if os.path.isfile(os.path.expanduser("~/gado-dados/gado_familia.xlsx"))
    else RAIZ
)

DATA_DIR_TESTE = tempfile.mkdtemp(prefix="gado_testes_")
TEM_DADOS_REAIS = False
for _nome in ("gado_familia.xlsx", "usuarios.json", "sitio_config.json"):
    _src = os.path.join(_ORIGEM, _nome)
    if os.path.isfile(_src):
        shutil.copy2(_src, os.path.join(DATA_DIR_TESTE, _nome))
        TEM_DADOS_REAIS = TEM_DADOS_REAIS or _nome == "gado_familia.xlsx"

os.environ["GADO_DATA_DIR"] = DATA_DIR_TESTE

import app as _app_mod  # noqa: E402  (precisa vir depois do GADO_DATA_DIR)
import db  # noqa: E402

assert os.path.abspath(db.DATA_DIR) == os.path.abspath(DATA_DIR_TESTE), \
    "Os testes NÃO podem rodar fora da pasta temporária!"


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(DATA_DIR_TESTE, ignore_errors=True)


@pytest.fixture(scope="session")
def flask_app():
    _app_mod.app.config.update(TESTING=True)
    return _app_mod.app


@pytest.fixture
def cliente(flask_app):
    """Cliente HTTP já logado (sessão de teste, sem precisar de senha)."""
    cli = flask_app.test_client()
    with cli.session_transaction() as s:
        s["logado"] = True
        s["usuario"] = "deyvid"
    return cli


@pytest.fixture
def dados_restaurados():
    """Para testes que gravam: guarda o .xlsx de teste e o restaura no fim."""
    from extensions import _cache_invalidar
    arq = db.ARQUIVO_PATH
    copia = arq + ".antes_do_teste"
    shutil.copy2(arq, copia)
    _cache_invalidar()
    yield
    shutil.move(copia, arq)
    _cache_invalidar()


@pytest.fixture
def fila_avisos_vazia():
    import alertas_whatsapp
    caminho = alertas_whatsapp._pendentes_path()
    if caminho.exists():
        caminho.unlink()
    yield caminho
    if caminho.exists():
        caminho.unlink()


@pytest.fixture(autouse=True)
def _whatsapp_nunca_envia(monkeypatch):
    """O usuarios.json copiado tem os telefones reais: nenhum teste pode mandar
    mensagem de verdade (morte/nascimento agora avisam na hora). Quem quer conferir
    o envio sobrescreve com o próprio monkeypatch."""
    import alertas_whatsapp
    monkeypatch.setattr(alertas_whatsapp, "enviar_whatsapp", lambda *a, **k: True)
