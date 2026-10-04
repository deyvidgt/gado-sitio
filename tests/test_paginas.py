# -*- coding: utf-8 -*-
"""
Smoke test das páginas: abre todas as rotas GET (logado) e garante que
nenhuma devolve erro 500. Roda numa cópia temporária dos dados.
"""
import pytest

import db

# Rotas que dependem de internet (cotações/chuva) — ficam de fora do teste.
ROTAS_EXTERNAS = {"/api/chuvas", "/api/cotacao-imea", "/api/cotacao-scot"}


def _rotas_get_sem_parametro():
    import app
    rotas = []
    for r in app.app.url_map.iter_rules():
        if "GET" not in r.methods or r.arguments or r.endpoint == "static":
            continue
        if r.rule in ROTAS_EXTERNAS:
            continue
        rotas.append(r.rule)
    return sorted(rotas)


@pytest.mark.parametrize("rota", _rotas_get_sem_parametro())
def test_pagina_abre_sem_erro(cliente, rota):
    resp = cliente.get(rota)
    assert resp.status_code < 500, f"{rota} deu {resp.status_code}"


@pytest.mark.parametrize("aba,rota", [
    ("Compras", "/compras/editar/0"),
    ("Gastos", "/gastos/editar/0"),
    ("Vendas", "/vendas/editar/0"),
    ("Manejo", "/manejo/editar/0"),
])
def test_tela_de_edicao_abre(cliente, aba, rota):
    if db.carregar_aba(aba).empty:
        pytest.skip(f"aba {aba} vazia")
    assert cliente.get(rota).status_code == 200


def test_sem_login_redireciona(flask_app):
    resp = flask_app.test_client().get("/")
    assert resp.status_code in (301, 302)
    assert "/login" in resp.headers["Location"]


def test_post_sem_csrf_e_recusado(cliente):
    resp = cliente.post("/compras/nova", data={"cabecas": "1", "valor": "100"})
    assert resp.status_code in (400, 403)


def test_nova_compra_grava_na_ordem_certa(cliente, dados_restaurados):
    """Grava uma compra pelo formulário e confere coluna por coluna."""
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    antes = len(db.carregar_aba("Compras"))
    resp = cliente.post("/compras/nova", data={
        "csrf_token": "tok", "data": "15/01/2026", "cabecas": "3",
        "valor": "4.500,00", "qtd_mae": "1", "qtd_deyvid": "1", "qtd_nilson": "1",
        "descricao": "TESTE AUTOMATICO",
    })
    assert resp.status_code in (302, 303)

    df = db.carregar_aba("Compras")
    assert len(df) == antes + 1
    nova = df.iloc[-1]
    assert int(nova["Qtd Cabeças"]) == 3
    assert float(nova["Valor Total (R$)"]) == pytest.approx(4500.0)
    assert float(nova["Valor/Cabeça (R$)"]) == pytest.approx(1500.0)
    assert int(nova["Qtd Mae"]) == int(nova["Qtd Deyvid"]) == int(nova["Qtd Nilson"]) == 1
    assert nova["Descrição"] == "TESTE AUTOMATICO"


def test_api_rebanho(cliente):
    d = cliente.get("/api/rebanho").get_json()
    assert set(d) == {"labels", "entradas", "saidas", "cabecas", "custo_cab"}
    assert len({len(v) for v in d.values()}) == 1  # todas as séries do mesmo tamanho


def test_painel_tem_grafico_do_rebanho(cliente):
    assert 'id="chartRebanho"' in cliente.get("/").get_data(as_text=True)


def _post_manejo(cliente, **campos):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    dados = {"csrf_token": "tok", "data": "2026-05-10", "cabecas": "10",
             "responsavel": "Deyvid", "descricao": ""}
    dados.update(campos)
    return cliente.post("/manejo/novo", data=dados)


def test_vacina_exige_produto(cliente, dados_restaurados):
    antes = len(db.carregar_aba("Manejo"))
    resp = _post_manejo(cliente, tipo="Vacina Raiva", produto="")
    assert resp.status_code in (302, 303) and "/manejo/novo" in resp.headers["Location"]
    assert len(db.carregar_aba("Manejo")) == antes  # nada gravado


def test_vacina_grava_produto_na_ultima_coluna(cliente, dados_restaurados):
    _post_manejo(cliente, tipo="Vermifugação", produto="Ivermectina 1%")
    df = db.carregar_aba("Manejo")
    from config import COLUNAS_MANEJO
    assert list(df.columns) == COLUNAS_MANEJO  # colunas novas só no fim, na ordem
    assert df.iloc[-1]["Tipo"] == "Vermifugação"
    assert df.iloc[-1]["Produto"] == "Ivermectina 1%"
    assert int(df.iloc[-1]["Qtd Cabeças"]) == 10
    # o produto aparece como sugestão no próximo registro
    assert "Ivermectina 1%" in cliente.get("/manejo/novo").get_data(as_text=True)


def test_produto_ignorado_em_outros_tipos(cliente, dados_restaurados):
    _post_manejo(cliente, tipo="Pesagem", produto="não deveria salvar")
    p = db.carregar_aba("Manejo").iloc[-1].get("Produto")
    assert p is None or str(p) in ("", "nan")


def test_nascimento_grava_de_quem_e(cliente, dados_restaurados):
    _post_manejo(cliente, tipo="Nascimento", cabecas="2", nascimento_de="Nilson",
                 perda_de="Mae")  # perda_de deve ser ignorado
    ult = db.carregar_aba("Manejo").iloc[-1]
    assert ult["Tipo"] == "Nascimento" and ult["Nascimento De"] == "Nilson"
    assert str(ult.get("Perda De")) in ("", "nan", "None")


def test_exportacao_excel_manejo_tem_titulo_em_todas_as_colunas(cliente):
    import io
    from openpyxl import load_workbook
    resp = cliente.get("/exportar")
    assert resp.status_code == 200
    wb = load_workbook(io.BytesIO(resp.data), read_only=True)
    aba = next(n for n in wb.sheetnames if "Manejo" in n)
    linhas = list(wb[aba].iter_rows(values_only=True))
    cab = linhas[0]
    largura = max(len([v for v in l if v is not None]) and len(l) for l in linhas)
    assert all(cab[i] for i in range(largura)), cab


def test_form_manejo_sugere_produtos_do_mercado(cliente):
    html = cliente.get("/manejo/novo").get_data(as_text=True)
    for nome in ("Raivacel Multi", "Bovilis Poli-Star T", "Dectomax (doramectina)"):
        assert nome in html


def test_lista_de_visitas_nao_mostra_nan(cliente):
    html = cliente.get("/visitas").get_data(as_text=True)
    assert "📝 nan" not in html


# ── Regressões (revisão de bugs out/2026) ──────────────────────────────────────

def test_editar_nao_deixa_linhas_vazias_na_planilha(cliente, dados_restaurados):
    """reescrever_aba só limpava os valores: a aba dobrava a cada edição."""
    from openpyxl import load_workbook
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    n = len(db.carregar_aba("Gastos"))
    r = cliente.post("/gastos/editar/0", data={
        "csrf_token": "tok", "data": "2025-01-05", "tipo": "Sal/Proteínado",
        "descricao": "teste", "valor": "100", "cabecas": "10"})
    assert r.status_code == 302
    assert load_workbook(db.ARQUIVO_PATH)["Gastos"].max_row == n + 1
    assert len(db.carregar_aba("Gastos")) == n


def test_numero_invalido_no_form_nao_da_500(cliente, dados_restaurados):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    r = cliente.post("/compras/nova", data={"csrf_token": "tok", "data": "2026-01-10",
                                            "cabecas": "abc", "valor": "10"})
    assert r.status_code == 302


def test_login_nao_redireciona_para_site_externo(flask_app, login_teste):
    cli = flask_app.test_client()
    with cli.session_transaction() as s:
        s["csrf_token"] = "tok"
    r = cli.post("/login?next=https://evil.example",
                 data={"csrf_token": "tok", "usuario": "teste", "senha": "x"})
    assert r.status_code == 302
    assert "evil.example" not in r.headers["Location"]


@pytest.fixture
def login_teste(monkeypatch):
    """Usuário fictício 'teste' (senha 'x') e arquivo de bloqueios zerado."""
    import os
    import extensions
    import routes_auth
    monkeypatch.setattr(routes_auth, "_carregar_usuarios",
                        lambda: {"teste": {"hash": extensions._sha256("x")}})
    monkeypatch.setattr(routes_auth, "_bcrypt_disponivel", lambda: False)
    caminho = routes_auth._bloqueios_path()
    if os.path.exists(caminho):
        os.remove(caminho)
    yield routes_auth
    if os.path.exists(caminho):
        os.remove(caminho)


def _tentar_login(flask_app, senha):
    """Cada tentativa num navegador NOVO (= cookie apagado)."""
    cli = flask_app.test_client()
    with cli.session_transaction() as s:
        s["csrf_token"] = "tok"
    return cli.post("/login", data={"csrf_token": "tok", "usuario": "teste", "senha": senha})


def test_bloqueio_de_login_vale_mesmo_apagando_o_cookie(flask_app, login_teste):
    from config import MAX_TENTATIVAS_LOGIN
    for _ in range(MAX_TENTATIVAS_LOGIN):
        assert _tentar_login(flask_app, "errada").status_code == 200
    # Bloqueado: nem a senha CERTA entra, mesmo vindo de outro navegador.
    r = _tentar_login(flask_app, "x")
    assert r.status_code == 200
    assert "Aguarde" in r.get_data(as_text=True)


def test_bloqueio_expira_e_login_certo_zera_contador(flask_app, login_teste):
    from datetime import timedelta
    from config import MAX_TENTATIVAS_LOGIN
    for _ in range(MAX_TENTATIVAS_LOGIN):
        _tentar_login(flask_app, "errada")
    # Simula os 15 minutos passando: bloqueio vencido no arquivo.
    dados = login_teste._ler_bloqueios()
    dados["teste"]["bloqueio_ate"] = (login_teste._agora() - timedelta(minutes=1)).isoformat()
    login_teste._gravar_bloqueios(dados)
    assert _tentar_login(flask_app, "x").status_code == 302
    assert "teste" not in login_teste._ler_bloqueios()


def test_login_certo_antes_do_limite_zera_falhas(flask_app, login_teste):
    _tentar_login(flask_app, "errada")
    _tentar_login(flask_app, "errada")
    assert _tentar_login(flask_app, "x").status_code == 302
    assert login_teste._estado_login("teste")["falhas"] == 0


def test_alerta_diario_whatsapp_aguenta_visita_com_campo_vazio(monkeypatch):
    """Visita com 'Gado Contado' vazio derrubava o relatório diário inteiro."""
    import alertas_whatsapp as aw
    original = aw.carregar_todas

    def com_vazio():
        dados = original()
        vis = dados["Visitas"].copy()
        if not vis.empty:
            i = vis["Data"].idxmax()
            vis.loc[i, ["Gado Contado", "Gado Esperado", "Gado Faltando", "Chuva mm"]] = float("nan")
        dados["Visitas"] = vis
        return dados

    monkeypatch.setattr(aw, "carregar_todas", com_vazio)
    assert aw.montar_mensagem_alertas(aw.montar_alertas())
    assert aw.montar_msg_nova_visita({"Gado Contado": float("nan")}, 10)


def test_calendario_e_ultima_visita_aguentam_celula_vazia(cliente, monkeypatch):
    """int(NaN) derrubava o calendário inteiro ('Erro ao carregar calendário')."""
    import routes_api_extras
    import routes_api
    original = db.carregar_aba

    def com_vazio(aba):
        df = original(aba)
        if aba == "Visitas" and not df.empty:
            df.loc[df["Data"].idxmax(), ["Gado Contado", "Gado Esperado", "Gado Faltando"]] = float("nan")
        if aba == "Compras" and not df.empty:
            df.loc[df["Data"].idxmax(), "Qtd Cabeças"] = float("nan")
        return df

    monkeypatch.setattr(routes_api_extras, "carregar_aba", com_vazio)
    monkeypatch.setattr(routes_api, "carregar_aba", com_vazio)
    assert cliente.get("/api/calendario-manejo").status_code == 200
    assert cliente.get("/api/ultima-visita").status_code == 200


def test_listas_mostram_cabecas_como_inteiro(cliente):
    import re
    for rota in ("/compras", "/vendas", "/manejo"):
        html = cliente.get(rota).get_data(as_text=True)
        assert not re.search(r"<td>\s*\d+\.0\s*</td>", html), rota


def test_lista_tem_dados_para_total_filtrado(cliente):
    html = cliente.get("/gastos").get_data(as_text=True)
    assert 'id="total-valor"' in html and "data-valor=" in html


def test_redefinir_senha_tira_bloqueio(cliente, login_teste, monkeypatch):
    import routes_usuarios
    from config import MAX_TENTATIVAS_LOGIN
    usuarios = {"teste": {"hash": "x"}, "deyvid": {"hash": "y"}}
    monkeypatch.setattr(routes_usuarios, "_carregar_usuarios_local", lambda: usuarios)
    monkeypatch.setattr(routes_usuarios, "_salvar_usuarios_local", lambda d: None)
    for _ in range(MAX_TENTATIVAS_LOGIN):
        login_teste._registrar_falha("teste")
    assert login_teste._estado_login("teste")["bloqueio_ate"]
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    r = cliente.post("/configuracoes/resetar-senha",
                     data={"csrf_token": "tok", "usuario": "teste", "senha_nova": "nova123"})
    assert r.status_code == 302
    assert not login_teste._estado_login("teste")["bloqueio_ate"]
