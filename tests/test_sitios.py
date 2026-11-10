# -*- coding: utf-8 -*-
"""
Fase 2 dos vários sítios — pasta por sítio, acesso por login e seletor.
Sem sitios.json: um sítio só (o de hoje) e todo mundo entra.
"""
import json
import os
import shutil

import pytest

import config
import db
import sitios


@pytest.fixture
def dois_sitios(dados_restaurados):
    """Raiz = Santo Antonio (dados de teste) + sítio do João (2 donos, pasta nova)."""
    raiz = db.RAIZ
    cfg = {"sitios": {"santo-antonio": {"nome": "Sítio Santo Antonio", "pasta": ""},
                      "joao": {"nome": "Sítio do João", "pasta": "sitios/joao"}},
           "acesso": {"deyvid": ["santo-antonio", "joao"], "joao": ["joao"],
                      "nilson": ["santo-antonio"]}}
    with open(os.path.join(raiz, "sitios.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    pasta_joao = os.path.join(raiz, "sitios", "joao")
    os.makedirs(pasta_joao, exist_ok=True)
    with open(os.path.join(pasta_joao, "sitio_config.json"), "w", encoding="utf-8") as f:
        json.dump({"nome": "Sítio do João", "membros": [
            {"chave": "Joao", "nome": "João", "emoji": "👨", "cor": "Verde", "logins": ["joao"]},
            {"chave": "Ana", "nome": "Ana", "emoji": "👩", "cor": "Rosa", "logins": ["ana"]}]}, f)
    yield pasta_joao
    os.remove(os.path.join(raiz, "sitios.json"))
    shutil.rmtree(os.path.join(raiz, "sitios"), ignore_errors=True)
    sitios.ativar(sitios.PADRAO)


# ── Task 1 ────────────────────────────────────────────────────────────────────

def test_sem_sitios_json_um_sitio_so():
    assert not os.path.exists(os.path.join(db.RAIZ, "sitios.json"))
    assert sitios.sitios_do_usuario("qualquer") == [sitios.PADRAO]
    assert os.path.abspath(sitios.pasta(sitios.PADRAO)) == os.path.abspath(db.RAIZ)


def test_slug_invalido(dois_sitios):
    for slug in ("../fora", "Joao", "", "x" * 41, "nao-existe"):
        with pytest.raises(ValueError):
            sitios.pasta(slug)


def test_acesso_por_login(dois_sitios):
    assert sitios.sitios_do_usuario("Deyvid") == ["santo-antonio", "joao"]
    assert sitios.sitios_do_usuario("joao") == ["joao"]
    assert sitios.sitios_do_usuario("fulano") == []
    assert sitios.tem_acesso("nilson", "santo-antonio") and not sitios.tem_acesso("nilson", "joao")
    assert sitios.nome("joao") == "Sítio do João"


def test_ativar_troca_pasta_e_donos(dois_sitios):
    sitios.ativar("joao")
    assert os.path.abspath(db.DATA_DIR) == os.path.abspath(dois_sitios)
    assert config.MEMBROS == ["Joao", "Ana"]
    assert os.path.exists(db.ARQUIVO_PATH)          # sítio novo nasce com o arquivo
    assert sitios.atual() == "joao"
    sitios.ativar("santo-antonio")
    assert config.MEMBROS == ["Mae", "Deyvid", "Nilson"]
    assert os.path.abspath(db.DATA_DIR) == os.path.abspath(db.RAIZ)


# ── Task 2: pedido dentro do sítio + seletor ──────────────────────────────────

def _logar(cliente, login, sitio=None):
    with cliente.session_transaction() as s:
        s.clear()
        s["logado"] = True
        s["usuario"] = login
        s["csrf_token"] = "tok"
        if sitio:
            s["sitio"] = sitio


def test_trocar_sitio_mostra_outros_dados(cliente, dois_sitios):
    _logar(cliente, "deyvid")
    antes = len(db.carregar_aba("Compras"))
    pagina = cliente.get("/compras/nova").get_data(as_text=True)
    assert "Geane" in pagina and "Sítio do João" in pagina   # seletor com os 2 sítios
    r = cliente.post("/sitio/trocar", data={"csrf_token": "tok", "sitio": "joao"})
    assert r.status_code == 302
    pagina = cliente.get("/compras/nova").get_data(as_text=True)
    assert "Ana" in pagina and "Geane" not in pagina
    cliente.post("/compras/nova", data={"csrf_token": "tok", "data": "2025-01-10", "cabecas": "2",
                                        "valor": "4000", "qtd_joao": "1", "qtd_ana": "1", "membro": "Joao"})
    assert "Sítio do João" in cliente.get("/").get_data(as_text=True)
    cliente.post("/sitio/trocar", data={"csrf_token": "tok", "sitio": "santo-antonio"})
    cliente.get("/")
    assert len(db.carregar_aba("Compras")) == antes          # Santo Antonio intacto
    sitios.ativar("joao")
    assert len(db.carregar_aba("Compras")) == 1


def test_sem_acesso_nao_troca(cliente, dois_sitios):
    _logar(cliente, "nilson")
    cliente.post("/sitio/trocar", data={"csrf_token": "tok", "sitio": "joao"})
    assert "Geane" in cliente.get("/compras/nova").get_data(as_text=True)


def test_sessao_forjada_nao_abre_sitio_alheio(cliente, dois_sitios):
    _logar(cliente, "joao", sitio="santo-antonio")
    pagina = cliente.get("/compras/nova").get_data(as_text=True)
    assert "Ana" in pagina and "Geane" not in pagina


def test_usuario_sem_sitio_403(cliente, dois_sitios):
    _logar(cliente, "fulano")
    assert cliente.get("/").status_code == 403
    assert cliente.get("/login").status_code != 403   # login/logout continuam abrindo


def test_erro_no_pedido_solta_a_trava(cliente, dois_sitios, monkeypatch):
    import extensions
    _logar(cliente, "deyvid")
    monkeypatch.setattr("routes_dashboard._gerar_alertas", lambda *a, **k: 1 / 0)
    cliente.application.config["PROPAGATE_EXCEPTIONS"] = False
    try:
        assert cliente.get("/").status_code == 500
    finally:
        cliente.application.config["PROPAGATE_EXCEPTIONS"] = None
    assert not extensions._trava_sitio.locked()
    assert cliente.get("/compras").status_code == 200


# ── Task 3: WhatsApp por sítio ────────────────────────────────────────────────

def test_aviso_so_para_quem_tem_acesso(cliente, dois_sitios, monkeypatch, fila_avisos_vazia):
    import alertas_whatsapp as aw
    wpp = lambda tel: {"whatsapp": {"telefone": tel, "apikey": "k", "alertas_ativos": True}}
    monkeypatch.setattr(aw, "carregar_usuarios",
                        lambda: {"deyvid": wpp("1"), "nilson": wpp("2"), "joao": wpp("3")})
    enviados = []
    monkeypatch.setattr(aw, "enviar_whatsapp", lambda tel, key, msg: enviados.append((tel, msg)) or True)
    _logar(cliente, "deyvid", sitio="joao")
    r = cliente.post("/manejo/novo", data={"csrf_token": "tok", "data": "2026-10-01", "tipo": "Nascimento",
                                           "cabecas": "1", "nascimento_de": "Ana", "responsavel": "Joao"})
    assert r.status_code == 302
    sitios.ativar("santo-antonio")          # outro pedido trocou de sítio antes do envio
    r.close()
    assert [t for t, _ in enviados] == ["3"]        # só o João: Deyvid registrou, Nilson não é do sítio
    assert "Ana" in enviados[0][1]


# ── Fase 3 / Task 1: administradores e privacidade ────────────────────────────

def test_admin_padrao(dois_sitios):
    # sem "admins": quem tem acesso ao 1º sítio (Santo Antonio)
    assert sitios.e_admin("deyvid") and sitios.e_admin("nilson")
    assert not sitios.e_admin("joao") and not sitios.e_admin("fulano")
    cfg = json.load(open(os.path.join(db.RAIZ, "sitios.json"), encoding="utf-8"))
    cfg["admins"] = ["deyvid"]
    json.dump(cfg, open(os.path.join(db.RAIZ, "sitios.json"), "w", encoding="utf-8"))
    assert sitios.e_admin("Deyvid") and not sitios.e_admin("nilson")


def test_sem_sitios_json_todo_mundo_admin():
    assert sitios.e_admin("qualquer")


def test_nao_admin_nao_gerencia_usuarios(cliente, dois_sitios):
    from routes_usuarios import _carregar_usuarios_local
    antes = json.dumps(_carregar_usuarios_local(), sort_keys=True)
    _logar(cliente, "joao")
    for url, dados in (("/configuracoes/resetar-senha", {"usuario": "deyvid", "senha_nova": "1234"}),
                       ("/configuracoes/adicionar-usuario", {"usuario": "intruso", "senha": "1234"}),
                       ("/configuracoes/excluir-usuario", {"usuario": "nilson"})):
        assert cliente.post(url, data={"csrf_token": "tok", **dados}).status_code == 403, url
    assert json.dumps(_carregar_usuarios_local(), sort_keys=True) == antes


def test_lista_so_do_sitio(cliente, dois_sitios, monkeypatch):
    import routes_api_extras
    todos = {"deyvid": {}, "nilson": {}, "joao": {}, "ana": {}}
    monkeypatch.setattr(routes_api_extras, "_carregar_usuarios", lambda: todos)
    _logar(cliente, "joao")
    nomes = [u["usuario"] for u in cliente.get("/api/config-whatsapp-todos").get_json()["usuarios"]]
    assert sorted(nomes) == ["deyvid", "joao"]   # Deyvid também é do sítio; Nilson e Ana não
    _logar(cliente, "deyvid", sitio="santo-antonio")
    nomes = [u["usuario"] for u in cliente.get("/api/config-whatsapp-todos").get_json()["usuarios"]]
    assert sorted(nomes) == ["ana", "deyvid", "joao", "nilson"]   # admin vê todos


def test_tela_sem_gestao_para_nao_admin(cliente, dois_sitios):
    _logar(cliente, "joao")
    p = cliente.get("/configuracoes").get_data(as_text=True)
    assert "Criar Usuário" not in p and "Só o administrador" in p
    _logar(cliente, "deyvid")
    assert "Criar Usuário" in cliente.get("/configuracoes").get_data(as_text=True)


# ── Fase 3 / Task 2: Tasks por sítio ──────────────────────────────────────────

def _capturar_envios(monkeypatch, modulo):
    chamadas = []
    monkeypatch.setattr(modulo, "enviar_para_familia",
                        lambda msg, **kw: chamadas.append((msg, kw)) or 1)
    return chamadas


def test_task_whatsapp_por_sitio(dois_sitios, monkeypatch):
    import alertas_whatsapp as aw
    chamadas = _capturar_envios(monkeypatch, aw)
    assert aw.main(["--semanal"]) == 0
    assert [kw["sitio"] for _, kw in chamadas] == ["santo-antonio", "joao"]
    assert chamadas[0][0].startswith("🐄 *Sítio Santo Antonio*")
    assert chamadas[1][0].startswith("🐄 *Sítio do João*")
    assert sitios.atual() == "santo-antonio"          # volta ao 1º no fim


def test_task_erro_num_sitio_nao_para_os_outros(dois_sitios, monkeypatch):
    import alertas_whatsapp as aw
    chamadas = _capturar_envios(monkeypatch, aw)
    original = aw.montar_itens

    def quebra_no_santo_antonio(*a, **k):
        if sitios.atual() == "santo-antonio":
            raise RuntimeError("planilha com problema")
        return original(*a, **k)
    monkeypatch.setattr(aw, "montar_itens", quebra_no_santo_antonio)
    assert aw.main(["--semanal"]) == 1
    assert [kw["sitio"] for _, kw in chamadas] == ["joao"]


def test_envio_manual_whatsapp_captura_e_restaurar_sitio(cliente, dois_sitios, monkeypatch):
    import alertas_whatsapp as aw
    import threading
    tarefas = []
    chamadas = []

    class ThreadAdiada:
        def __init__(self, target, daemon):
            self.target = target

        def start(self):
            tarefas.append(self.target)

    monkeypatch.setattr(threading, "Thread", ThreadAdiada)
    monkeypatch.setattr(aw, "montar_alertas", lambda: ["Alerta"])
    monkeypatch.setattr(aw, "montar_mensagem_alertas", lambda alertas: "Mensagem")
    monkeypatch.setattr(
        aw, "enviar_para_familia",
        lambda msg, **kw: chamadas.append((sitios.atual(), msg, kw)) or 1,
    )
    _logar(cliente, "joao", sitio="joao")

    resposta = cliente.post("/api/enviar-alertas-familia").get_json()
    sitios.ativar("santo-antonio")
    tarefas[0]()

    assert resposta["ok"] and resposta["enviados"] is None
    assert chamadas == [("joao", "Mensagem", {"sitio": "joao"})]
    assert sitios.atual() == "santo-antonio"


def test_resumo_mensal_por_sitio(dois_sitios, monkeypatch):
    from datetime import datetime
    import alertas_whatsapp
    import resumo_mensal as rm

    class Dia1(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 1)
    monkeypatch.setattr(rm, "datetime", Dia1)
    chamadas = _capturar_envios(monkeypatch, alertas_whatsapp)
    rm.main([])
    assert [kw["sitio"] for _, kw in chamadas] == ["santo-antonio", "joao"]
    assert "*Sítio do João*" in chamadas[1][0] and "Geane" not in chamadas[1][0]


def test_backup_por_sitio(tmp_path):
    import subprocess
    import sys
    from conftest import RAIZ
    shutil.copy2(db.ARQUIVO_PATH, tmp_path / "gado_familia.xlsx")
    (tmp_path / "usuarios.json").write_text("{}", encoding="utf-8")
    (tmp_path / "sitios.json").write_text(json.dumps({
        "sitios": {"santo-antonio": {"nome": "SA", "pasta": ""},
                   "joao": {"nome": "J", "pasta": "sitios/joao"}}, "acesso": {}}), encoding="utf-8")
    (tmp_path / "sitios" / "joao").mkdir(parents=True)
    shutil.copy2(db.ARQUIVO_PATH, tmp_path / "sitios" / "joao" / "gado_familia.xlsx")
    env = dict(os.environ, GADO_DATA_DIR=str(tmp_path), PYTHONIOENCODING="utf-8")
    proc = subprocess.run([sys.executable, os.path.join(RAIZ, "backup_automatico.py")],
                          env=env, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    raiz = os.listdir(tmp_path / "backups")
    joao = os.listdir(tmp_path / "sitios" / "joao" / "backups")
    assert any(n.startswith("backup_") for n in raiz) and any(n.startswith("backup_") for n in joao)
    assert any(n.startswith("usuarios_") for n in raiz) and any(n.startswith("sitios_") for n in raiz)
    assert not any(n.startswith("usuarios_") for n in joao)   # da família só na raiz


# ── Fase 3 / Task 3: tela de sítios ───────────────────────────────────────────

@pytest.fixture
def sem_sitios_json(dados_restaurados):
    """Começa sem sitios.json (como hoje) e limpa o que a tela criar."""
    raiz = db.RAIZ
    yield raiz
    for p in (os.path.join(raiz, "sitios.json"),):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(os.path.join(raiz, "sitios"), ignore_errors=True)
    sitios.ativar(sitios.PADRAO)


def _form_sitio(**extra):
    dados = {"csrf_token": "tok", "nome": "Sítio do Zé",
             "dono_nome_0": "Zé", "dono_login_0": "ze", "dono_cor_0": "Verde",
             "dono_nome_1": "Maria Clara", "dono_login_1": "maria", "dono_cor_1": "Rosa",
             "acesso": ["deyvid"]}
    dados.update(extra)
    return dados


def test_criar_primeiro_sitio_mantem_acessos(cliente, sem_sitios_json):
    from routes_usuarios import _carregar_usuarios_local
    _logar(cliente, "deyvid")
    r = cliente.post("/configuracoes/sitios/criar", data=_form_sitio())
    assert r.status_code == 302
    for login in _carregar_usuarios_local():
        assert sitios.tem_acesso(login, "santo-antonio"), login      # ninguém perdeu acesso
    assert sitios.tem_acesso("deyvid", "sitio-do-ze")
    assert not sitios.tem_acesso("nilson", "sitio-do-ze")
    cfg = json.load(open(os.path.join(sitios.pasta("sitio-do-ze"), "sitio_config.json"), encoding="utf-8"))
    assert cfg["nome"] == "Sítio do Zé"
    assert [m["chave"] for m in cfg["membros"]] == ["Ze", "MariaClara"]
    assert cfg["membros"][1]["logins"] == ["maria"]


def test_criar_sitio_pela_tela(cliente, dois_sitios):
    _logar(cliente, "deyvid")
    cliente.post("/configuracoes/sitios/criar", data=_form_sitio(slug="ze", acesso=["deyvid", "naoexiste"]))
    assert sitios.sitios_do_usuario("deyvid") == ["santo-antonio", "joao", "ze"]
    assert sitios.sitios_do_usuario("naoexiste") == []      # login que não existe não entra
    cliente.post("/sitio/trocar", data={"csrf_token": "tok", "sitio": "ze"})
    assert "Maria Clara" in cliente.get("/compras/nova").get_data(as_text=True)


def test_criar_sitio_invalido_nao_grava(cliente, sem_sitios_json):
    _logar(cliente, "deyvid")
    cliente.post("/configuracoes/sitios/criar", data=_form_sitio(dono_cor_1="Verde"))   # cor repetida
    assert not os.path.exists(os.path.join(sem_sitios_json, "sitios.json"))
    assert not os.path.exists(os.path.join(sem_sitios_json, "sitios"))
    cliente.post("/configuracoes/sitios/criar", data=_form_sitio(dono_nome_1="", dono_login_1=""))  # 1 dono só
    assert not os.path.exists(os.path.join(sem_sitios_json, "sitios.json"))


def test_criar_sitio_so_admin(cliente, dois_sitios):
    _logar(cliente, "joao")
    assert cliente.post("/configuracoes/sitios/criar", data=_form_sitio()).status_code == 403


def test_mudar_acesso(cliente, dois_sitios):
    _logar(cliente, "deyvid")
    r = cliente.post("/configuracoes/sitios/acesso", data={
        "csrf_token": "tok", "acesso": ["deyvid|santo-antonio", "deyvid|joao", "nilson|santo-antonio",
                                         "nilson|joao", "joao|joao"]})
    assert r.status_code == 302
    assert sitios.tem_acesso("nilson", "joao")


def test_nao_remove_ultimo_admin(cliente, dois_sitios):
    _logar(cliente, "deyvid")
    cliente.post("/configuracoes/sitios/acesso", data={"csrf_token": "tok", "acesso": ["deyvid|joao", "joao|joao"]})
    assert sitios.tem_acesso("deyvid", "santo-antonio")     # recusado: deyvid deixaria de ser admin
    assert sitios.e_admin("deyvid")


def test_tela_lista_sitios_para_admin(cliente, dois_sitios):
    _logar(cliente, "deyvid")
    p = cliente.get("/configuracoes").get_data(as_text=True)
    assert "🏡 Sítios" in p and "Sítio do João" in p


# ── Painel da Família (v5.0 fase 4): privado / redireciona ────────────────────

def test_familia_redireciona(cliente):
    _logar(cliente, "deyvid")
    r = cliente.get("/familia")
    assert r.status_code in (302, 303)
    assert "/dashboard" in r.headers["Location"] or r.headers["Location"].endswith("/")


def test_familia_sem_link_no_menu(cliente):
    _logar(cliente, "deyvid")
    assert 'href="/familia"' not in cliente.get("/").get_data(as_text=True)
