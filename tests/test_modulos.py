import json
from pathlib import Path

import pytest

import db
import modulos
from extensions import _cache_invalidar


@pytest.fixture
def config_modulos():
    caminho = Path(db.DATA_DIR) / "sitio_config.json"
    original = caminho.read_bytes() if caminho.exists() else None
    yield caminho
    if original is None:
        caminho.unlink(missing_ok=True)
    else:
        caminho.write_bytes(original)
    _cache_invalidar()


def _gravar_config(caminho, config):
    caminho.write_text(json.dumps(config), encoding="utf-8")
    _cache_invalidar()


def test_preferencias_ausentes_e_parciais_mantem_modulos_ativos():
    assert all(modulos.preferencias(None).values())

    estado = modulos.estado_efetivo({"modulos": {"leite": False}})
    assert estado["leite"] is False
    assert estado["conforto"] is False
    assert estado["reproducao"] is True
    assert estado["genetica_confinamento"] is True


def test_conforto_depende_de_leite():
    estado = modulos.estado_efetivo({
        "modulos": {"leite": False, "conforto": True},
    })
    assert not modulos.esta_ativo("conforto", estado)

    estado = modulos.estado_efetivo({
        "modulos": {"leite": True, "conforto": False},
    })
    assert not modulos.esta_ativo("conforto", estado)


def test_salvar_preferencias_preserva_outras_configuracoes(tmp_path):
    caminho = tmp_path / "sitio_config.json"
    caminho.write_text(json.dumps({"nome": "Sítio teste", "logo": "logo.png"}), encoding="utf-8")
    valores = {chave: False for chave in modulos.MODULOS}

    modulos.salvar_preferencias(str(caminho), valores)

    salvo = json.loads(caminho.read_text(encoding="utf-8"))
    assert salvo["nome"] == "Sítio teste"
    assert salvo["logo"] == "logo.png"
    assert salvo["modulos"] == valores
    with pytest.raises(ValueError):
        modulos.salvar_preferencias(str(caminho), {"desconhecido": True})


def test_salvar_pela_tela_atualiza_configuracao_compartilhada(
    cliente, config_modulos
):
    _gravar_config(config_modulos, {"nome": "Sítio teste", "logo": "logo.png"})
    with cliente.session_transaction() as sessao:
        sessao["csrf_token"] = "token-teste"
    dados = {"csrf_token": "token-teste", "leite": "1", "conforto": "1"}

    resposta = cliente.post("/configuracoes/modulos", data=dados)

    assert resposta.status_code == 302
    config = json.loads(config_modulos.read_text(encoding="utf-8"))
    assert config["nome"] == "Sítio teste"
    assert config["logo"] == "logo.png"
    assert config["modulos"] == {
        "leite": True,
        "conforto": True,
        "reproducao": False,
        "genetica_confinamento": False,
    }


def test_salvar_pela_tela_rejeita_campos_desconhecidos(cliente, config_modulos):
    existente = {"nome": "Sítio teste", "modulos": {"leite": False}}
    _gravar_config(config_modulos, existente)
    with cliente.session_transaction() as sessao:
        sessao["csrf_token"] = "token-teste"

    resposta = cliente.post("/configuracoes/modulos", data={
        "csrf_token": "token-teste",
        "leite": "1",
        "modulo_oculto": "1",
    })

    assert resposta.status_code == 302
    assert json.loads(config_modulos.read_text(encoding="utf-8")) == existente


def test_menu_e_busca_ocultam_modulos_desativados(cliente, config_modulos):
    _gravar_config(config_modulos, {
        "modulos": {
            "leite": False,
            "conforto": True,
            "reproducao": False,
            "genetica_confinamento": False,
        },
    })

    pagina = cliente.get("/").get_data(as_text=True)
    assert 'href="/leite/ordenha"' not in pagina
    assert 'href="/leite/conforto"' not in pagina
    assert 'href="/leite/colchao"' not in pagina
    assert 'href="/reproducao"' not in pagina
    assert 'href="/genetica"' not in pagina
    assert 'href="/confinamento"' not in pagina
    assert 'href="/leite/nutricao"' in pagina
    assert 'href="/leite/saude"' in pagina

    for caminho in ("/leite/nutricao", "/leite/saude"):
        html = cliente.get(caminho).get_data(as_text=True)
        assert 'href="/leite"' not in html
        assert 'href="/leite/ordenha"' not in html

    for termo in ("ordenha", "reproducao", "genetica", "conforto"):
        dados = cliente.get(f"/api/busca?q={termo}&tipo=aba").get_json()
        for resultado in dados["resultados"]:
            chave = modulos.modulo_da_rota(resultado["link"])
            assert chave is None or modulos.esta_ativo(chave, {
                "leite": False,
                "conforto": False,
                "reproducao": False,
                "genetica_confinamento": False,
            })


def test_rotas_desativadas_sao_bloqueadas_por_metodo(cliente, config_modulos):
    _gravar_config(config_modulos, {
        "modulos": {chave: False for chave in modulos.MODULOS},
    })

    for resposta in (
        cliente.get("/leite/ordenha"),
        cliente.post("/leite/ordenha", data={"data": "2026-01-01"}),
    ):
        assert resposta.status_code == 302
        assert resposta.headers["Location"].endswith("/configuracoes/modulos")

    resposta_api = cliente.get("/api/leite/comparativo")
    assert resposta_api.status_code == 403
    assert resposta_api.is_json
    assert resposta_api.get_json()["erro"] == "modulo_desativado"
