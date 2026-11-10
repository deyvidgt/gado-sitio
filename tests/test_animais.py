# -*- coding: utf-8 -*-
"""
v4.3 — Animais com brinco e Comando de Voz.

Regras do brinco: cor por dono, 01..99 por cor recomeçando do 01, único só entre
os VIVOS; o cadastro não mexe nas contas (só "Nascimento" e a baixa por morte
gravam no Manejo). Tudo roda na cópia temporária dos dados (conftest).
"""
import os
from datetime import datetime

import pandas as pd
import pytest

import animais as A
import comando_voz as V
import db
from config import COLUNAS_MANEJO, COLUNAS_VENDAS
from calculos import calcular_estoque, calcular_estoque_por_membro
from test_calculos import checar_invariantes

HOJE = datetime(2026, 10, 15)


@pytest.mark.parametrize(
    "cor,esperada",
    [("Amarelo", "#17211b"), ("Azul", "#ffffff"), ("Vermelho", "#ffffff")],
)
def test_cor_do_texto_dos_brincos_tem_contraste(cor, esperada):
    assert A.cor_texto_brinco(cor) == esperada


def test_cor_do_brinco_nao_depende_de_maiusculas():
    assert A.hex_cor_brinco("amarelo") == A.COR_HEX["Amarelo"]
    assert A.cor_texto_brinco("azul") == "#ffffff"


@pytest.fixture(autouse=True)
def _sem_sobra_de_backup():
    """Baixa/edição fazem backup de verdade; apaga os criados aqui para não
    atrapalhar o teste de limpeza de backups (que conta os arquivos da pasta)."""
    pasta = os.path.join(db.DATA_DIR, "backups")
    antes = set(os.listdir(pasta)) if os.path.isdir(pasta) else set()
    yield
    if os.path.isdir(pasta):
        for n in set(os.listdir(pasta)) - antes:
            os.remove(os.path.join(pasta, n))


@pytest.fixture
def sem_animais(dados_restaurados):
    """Testes que gravam começam com a aba Animais vazia (na cópia), para os
    brincos usados aqui não baterem com animais já cadastrados nos dados reais."""
    df = A.carregar()
    A._gravar(df.iloc[0:0])
    yield


# ── Interpretação das frases (só texto) ──────────────────────────────────────

@pytest.mark.parametrize("frase,esperado", [
    ("registrar bezerra, brinco amarelo 21 deyvid nelore branca",
     {"Categoria": "Bezerra", "Brinco Cor": "Amarelo", "Brinco Nº": 21, "Dono": "Deyvid",
      "Raça": "Nelore", "Pelagem": "Branca"}),
    ("registrar bezerra brinco azul 12 nilson nelore preta",
     {"Categoria": "Bezerra", "Brinco Cor": "Azul", "Brinco Nº": 12, "Dono": "Nilson",
      "Raça": "Nelore", "Pelagem": "Preta"}),
    ("registrar novilha brinco vermelho 07 mae ou geane amarela com detalhe branco na testa",
     {"Categoria": "Novilha", "Brinco Cor": "Vermelho", "Brinco Nº": 7, "Dono": "Mae",
      "Pelagem": "Amarela", "Sinais": "detalhe branco na testa"}),
    ("registrar garrote brinco amarelo trinta comprado",
     {"Categoria": "Garrote", "Brinco Nº": 30, "Origem": "Compra"}),
])
def test_frases_de_cadastro(frase, esperado):
    r = V.analisar(frase, HOJE)
    assert r["acao"] == "cadastro"
    for k, v in esperado.items():
        assert r["animal"][k] == v, k


def test_numeros_falados():
    assert [t.v for t in V.tokenizar("vinte e um")] == [21]
    assert [t.v for t in V.tokenizar("zero sete")] == [7]
    assert [t.v for t in V.tokenizar("quinze mil e quinhentos")] == [15500]
    assert [t.v for t in V.tokenizar("15 mil")] == [15000]
    # "uma" artigo não vira número
    assert V.tokenizar("uma bezerra")[0].v is None


def test_vacina_sem_cor_e_com_varios():
    r = V.analisar("registrar vacina brucelose novilha 35", HOJE)
    assert r["acao"] == "manejo" and r["tipo"] == "Vacina Brucelose"
    assert r["alvos"][0]["num"] == 35 and r["alvos"][0]["cor"] is None
    r = V.analisar("vacina raiva amarelo 21 e 22 ontem", HOJE)
    assert [(a["cor"], a["num"]) for a in r["alvos"]] == [("Amarelo", 21), ("Amarelo", 22)]
    assert r["data"] == datetime(2026, 10, 14).date()


def test_nascimento_com_mae():
    r = V.analisar("nasceu bezerra amarelo vinte e dois nelore, mãe amarelo 08", HOJE)
    assert r["acao"] == "nascimento"
    assert r["animal"]["Brinco Nº"] == 22 and r["animal"]["Dono"] is None
    assert (r["mae"]["cor"], r["mae"]["num"]) == ("Amarelo", 8)


def test_compra_venda_gasto_visita():
    r = V.analisar("comprei 5 cabeças por 15 mil, 2 do deyvid 2 do nilson 1 da mãe", HOJE)
    assert (r["acao"], r["qtd"], r["valor"]) == ("compra", 5, 15000)
    assert r["cotas"] == {"Deyvid": 2, "Nilson": 2, "Mae": 1}
    r = V.analisar("vendi amarelo 21 e azul 12 por 9 mil, arroba a 310", HOJE)
    assert r["acao"] == "venda" and len(r["alvos"]) == 2
    assert (r["valor"], r["arroba"]) == (9000, 310)
    r = V.analisar("comprei 3 bezerros a 2500 cada pro nilson", HOJE)
    assert r["qtd"] == 3 and r["valor"] == 2500 and r["por_cabeca"]
    r = V.analisar("gastei 350 reais de sal, 10 sacos", HOJE)
    assert (r["tipo"], r["produto"], r["sacos"], r["valor"]) == ("Sal/Proteínado", "Sal", 10, 350)
    r = V.analisar("visita contei 38 cabeças, choveu 20 milímetros, sal baixo, proteinado ok", HOJE)
    assert r["visita"]["gado_contado"] == 38 and r["visita"]["chuva_mm"] == 20
    assert r["visita"]["sal_racao"] == "Baixo" and r["visita"]["proteinado"] == "OK"


def test_pesagem_pareia_peso_com_brinco():
    r = V.analisar("pesagem amarelo 21 320 quilos, azul 12 280 quilos", HOJE)
    assert r["tipo"] == "Pesagem" and r["pesos"] == [320, 280]


def test_extrair_brincos_do_campo():
    assert V.extrair_brincos("amarelo 21, azul 12") == [
        {"num": 21, "cor": "Amarelo", "categoria": None},
        {"num": 12, "cor": "Azul", "categoria": None}]


# ── Regras do brinco (sem gravar) ────────────────────────────────────────────

def _df(linhas):
    df = pd.DataFrame([{**{c: "" for c in A.COLUNAS_ANIMAIS}, **l} for l in linhas])
    df["Brinco Nº"] = pd.to_numeric(df["Brinco Nº"]).astype("Int64")
    for c in ("Nascimento", "Entrada", "Data Saída"):
        df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def test_conferencia_conta_o_recorte_que_a_tela_mostra():
    """B3: o card do dono contava o rebanho vivo inteiro mesmo com ?status=Vendido."""
    df = _df([{"ID": "A0001", "Dono": "Deyvid", "Status": "Vivo"},
              {"ID": "A0002", "Dono": "Deyvid", "Status": "Vendido"},
              {"ID": "A0003", "Dono": "Nilson", "Status": "Vendido"}])
    estoque = {"Deyvid": 1, "Nilson": 1}

    vivos = {c["membro"]: c["com_brinco"] for c in A.conferencia(A.vivos(df), estoque)}
    vendidos = {c["membro"]: c["com_brinco"]
                for c in A.conferencia(df[df["Status"] == "Vendido"], estoque)}

    assert vivos == {"Mae": 0, "Deyvid": 1, "Nilson": 0}
    assert vendidos == {"Mae": 0, "Deyvid": 1, "Nilson": 1}


def test_proximo_numero_continua_e_recomeca_depois_do_99():
    df = _df([{"ID": "A0001", "Brinco Cor": "Amarelo", "Brinco Nº": 98, "Status": "Vivo"},
              {"ID": "A0002", "Brinco Cor": "Amarelo", "Brinco Nº": 99, "Status": "Vivo"}])
    assert A.proximo_numero(df, "Amarelo") == 1
    df = _df([{"ID": "A0001", "Brinco Cor": "Amarelo", "Brinco Nº": 1, "Status": "Vivo"},
              {"ID": "A0002", "Brinco Cor": "Amarelo", "Brinco Nº": 99, "Status": "Vivo"}])
    assert A.proximo_numero(df, "Amarelo") == 2       # pula o 01 ainda vivo
    assert A.proximo_numero(df, "Azul") == 1


def test_brinco_so_e_unico_entre_os_vivos():
    df = _df([{"ID": "A0001", "Brinco Cor": "Amarelo", "Brinco Nº": 21, "Status": "Vendido"},
              {"ID": "A0002", "Brinco Cor": "Azul", "Brinco Nº": 21, "Status": "Vivo"}])
    assert A.brinco_ocupado(df, "Amarelo", 21) is None
    assert A.brinco_ocupado(df, "Azul", 21)["ID"] == "A0002"
    with pytest.raises(ValueError):
        A.normalizar({"Dono": "Nilson", "Brinco Nº": 21}, df)       # Azul 21 vivo
    reg, _ = A.normalizar({"Dono": "Deyvid", "Brinco Nº": 21}, df)  # Amarelo 21 reaproveitado
    assert (reg["Brinco Cor"], reg["Brinco Nº"]) == ("Amarelo", 21)


def test_resolver_sem_cor_ambiguo():
    df = _df([{"ID": "A0001", "Brinco Cor": "Amarelo", "Brinco Nº": 35, "Status": "Vivo", "Categoria": "Novilha"},
              {"ID": "A0002", "Brinco Cor": "Azul", "Brinco Nº": 35, "Status": "Vivo", "Categoria": "Vaca"}])
    assert len(A.resolver(df, 35)) == 2
    assert A.resolver(df, 35, categoria="Novilha").iloc[0]["ID"] == "A0001"
    assert A.resolver(df, 35, dono="Nilson").iloc[0]["ID"] == "A0002"


# ── Fluxos gravando (na cópia) ───────────────────────────────────────────────

def _csrf(cliente):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    return {"X-CSRF-Token": "tok"}


def _voz(cliente, texto, escolhas=None, salvar=True):
    h = _csrf(cliente)
    corpo = {"texto": texto, "escolhas": escolhas or {}}
    r = cliente.post("/api/voz/interpretar", json=corpo, headers=h).get_json()
    if salvar:
        return r, cliente.post("/api/voz/executar", json=corpo, headers=h)
    return r, None


def test_api_voz_exige_csrf(cliente):
    r = cliente.post("/api/voz/interpretar", json={"texto": "ficha amarelo 1"})
    assert r.status_code == 403


def test_cadastro_por_voz_nao_mexe_no_estoque(cliente, sem_animais):
    d = db.carregar_todas()
    est_antes = calcular_estoque(d["Compras"], d["Vendas"], d["Manejo"])
    r, resp = _voz(cliente, "registrar bezerra brinco amarelo 91 deyvid nelore branca")
    assert r["pode_salvar"], r
    assert resp.status_code == 200 and resp.get_json()["ok"]
    a = A.carregar().iloc[-1]
    assert (a["Brinco Cor"], int(a["Brinco Nº"]), a["Dono"], a["Sexo"]) == ("Amarelo", 91, "Deyvid", "F")
    d = db.carregar_todas()
    assert calcular_estoque(d["Compras"], d["Vendas"], d["Manejo"]) == est_antes
    # o mesmo brinco de novo é recusado (já está num animal vivo)
    r, resp = _voz(cliente, "registrar bezerra brinco amarelo 91 deyvid")
    assert not r["pode_salvar"] and resp.status_code == 400


def test_nascimento_por_voz_grava_manejo_e_estoque(cliente, sem_animais):
    d = db.carregar_todas()
    est = calcular_estoque_por_membro(d["Compras"], d["Vendas"], d["Manejo"])
    _, resp = _voz(cliente, "nasceu bezerro azul 77 nelore")
    assert resp.get_json()["ok"], resp.get_json()
    man = db.carregar_aba("Manejo")
    ult = man.iloc[-1]
    assert ult["Tipo"] == "Nascimento" and ult["Nascimento De"] == "Nilson"
    assert "Azul 77 #A" in ult["Brincos"]
    d = db.carregar_todas()
    est2 = calcular_estoque_por_membro(d["Compras"], d["Vendas"], d["Manejo"])
    assert est2["Nilson"] == est["Nilson"] + 1
    checar_invariantes(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"])


def test_vacina_morte_e_historico(cliente, sem_animais):
    _voz(cliente, "registrar novilha brinco vermelho 88 geane")
    id_ = A.carregar().iloc[-1]["ID"]
    _, resp = _voz(cliente, "vacina brucelose novilha vermelho 88 com B19")
    assert resp.get_json()["ok"], resp.get_json()
    man = db.carregar_aba("Manejo")
    assert list(man.columns[:len(COLUNAS_MANEJO)]) == COLUNAS_MANEJO
    ult = man.iloc[-1]
    assert (ult["Tipo"], int(ult["Qtd Cabeças"]), ult["Produto"]) == ("Vacina Brucelose", 1, "B19")
    hist = A.historico(id_, man, db.carregar_aba("Vendas"))
    assert hist and hist[0]["tipo"] == "Vacina Brucelose"
    # morte: baixa + Morte/Perda com Perda De = dono; o brinco fica livre
    _, resp = _voz(cliente, "morreu a novilha vermelho 88 picada de cobra")
    assert resp.get_json()["ok"], resp.get_json()
    a = A.por_id(A.carregar(), id_)
    assert a["Status"] == "Morto"
    ult = db.carregar_aba("Manejo").iloc[-1]
    assert (ult["Tipo"], ult["Perda De"]) == ("Morte/Perda", "Mae")
    assert A.brinco_ocupado(A.carregar(), "Vermelho", 88) is None
    d = db.carregar_todas()
    checar_invariantes(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"])


def test_compra_e_venda_por_voz(cliente, sem_animais):
    _, resp = _voz(cliente, "comprei 2 cabeças por 6 mil, 1 do deyvid 1 do nilson")
    assert resp.get_json()["ok"], resp.get_json()
    c = db.carregar_aba("Compras").iloc[-1]
    assert (int(c["Qtd Cabeças"]), float(c["Valor Total (R$)"]), int(c["Qtd Deyvid"]), int(c["Qtd Nilson"])) == (2, 6000, 1, 1)
    _voz(cliente, "registrar boi brinco amarelo 95 deyvid")
    _voz(cliente, "registrar boi brinco azul 95 nilson")
    _, resp = _voz(cliente, "vendi amarelo 95 e azul 95 por 9 mil, arroba a 310")
    assert resp.get_json()["ok"], resp.get_json()
    v = db.carregar_aba("Vendas")
    assert list(v.columns[:len(COLUNAS_VENDAS)]) == COLUNAS_VENDAS
    ult = v.iloc[-1]
    assert int(ult["Qtd Cabeças"]) == 2 and int(ult["Qtd Deyvid"]) == 1 and int(ult["Qtd Nilson"]) == 1
    assert float(ult["Valor Arroba (R$)"]) == pytest.approx(310)
    assert "Amarelo 95 #A" in ult["Brincos"] and "Azul 95 #A" in ult["Brincos"]
    vivos = A.vivos(A.carregar())
    assert vivos[(vivos["Brinco Nº"] == 95)].empty
    d = db.carregar_todas()
    checar_invariantes(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"])


def test_gasto_por_voz(cliente, sem_animais):
    _, resp = _voz(cliente, "gastei 350 reais de sal, 10 sacos")
    assert resp.get_json()["ok"], resp.get_json()
    g = db.carregar_aba("Gastos").iloc[-1]
    assert (g["Tipo"], float(g["Valor Total (R$)"]), g["Produto"], int(g["Qtd Sacos"])) == \
        ("Sal/Proteínado", 350, "Sal", 10)


def test_ambiguidade_pergunta_e_escolha_resolve(cliente, sem_animais):
    _voz(cliente, "registrar vaca brinco amarelo 93 deyvid")
    _voz(cliente, "registrar vaca brinco azul 93 nilson")
    r, _ = _voz(cliente, "vermifugar vaca 93 com ivermectina", salvar=False)
    assert r["perguntas"] and not r["pode_salvar"]
    escolha = r["perguntas"][0]["opcoes"][1]["id"]
    r, resp = _voz(cliente, "vermifugar vaca 93 com ivermectina", escolhas={"0": escolha})
    assert r["pode_salvar"] and resp.get_json()["ok"]
    assert f"#{escolha}" in db.carregar_aba("Manejo").iloc[-1]["Brincos"]


def test_visita_por_voz_so_preenche_formulario(cliente, sem_animais):
    r, resp = _voz(cliente, "visita contei 38 cabeças, sal baixo")
    assert r["so_formulario"] and not r["pode_salvar"]
    assert r["url_form"].startswith("/visitas/nova?") and "gado_contado=38" in r["url_form"]
    assert resp.status_code == 400


def test_formulario_de_manejo_com_brincos(cliente, sem_animais):
    _voz(cliente, "registrar vaca brinco amarelo 94 deyvid")
    h = _csrf(cliente)
    resp = cliente.post("/manejo/novo", data={
        "csrf_token": "tok", "data": "2026-10-15", "tipo": "Pesagem", "cabecas": "1",
        "responsavel": "Deyvid", "descricao": "300 kg", "brincos": "amarelo 94"})
    assert resp.status_code in (302, 303)
    ult = db.carregar_aba("Manejo").iloc[-1]
    assert ult["Tipo"] == "Pesagem" and "Amarelo 94 #A" in ult["Brincos"]
    # brinco que não existe → não grava
    antes = len(db.carregar_aba("Manejo"))
    cliente.post("/manejo/novo", data={"csrf_token": "tok", "tipo": "Pesagem", "cabecas": "1",
                                       "responsavel": "Deyvid", "brincos": "roxo 50"})
    assert len(db.carregar_aba("Manejo")) == antes


def test_brincar_compra(cliente, sem_animais):
    _csrf(cliente)
    resp = cliente.post("/compras/nova", data={
        "csrf_token": "tok", "data": "15/10/2026", "cabecas": "2", "valor": "5.000,00",
        "qtd_mae": "0", "qtd_deyvid": "2", "qtd_nilson": "0", "membro": "Deyvid", "brincar": "1"})
    assert "/animais/compra/" in resp.headers["Location"]
    pagina = cliente.get(resp.headers["Location"]).get_data(as_text=True)
    assert 'name="numero_1"' in pagina
    idx = int(resp.headers["Location"].rstrip("/").split("/")[-1])
    resp = cliente.post(f"/animais/compra/{idx}", data={
        "csrf_token": "tok", "qtd": "2",
        "incluir_0": "1", "dono_0": "Deyvid", "cor_0": "Amarelo", "numero_0": "96", "categoria_0": "Garrote",
        "incluir_1": "1", "dono_1": "Deyvid", "cor_1": "Amarelo", "numero_1": "97", "categoria_1": "Garrote"})
    assert resp.status_code in (302, 303)
    df = A.carregar()
    novos = df[df["Brinco Nº"].isin([96, 97]) & (df["Brinco Cor"] == "Amarelo")]
    assert len(novos) == 2 and set(novos["Origem"]) == {"Compra"}


def test_paginas_de_animais_abrem(cliente, sem_animais):
    _voz(cliente, "registrar bezerra brinco amarelo 92 deyvid")
    id_ = A.carregar().iloc[-1]["ID"]
    for rota in ("/animais", "/animais?status=todos", f"/animais/{id_}", f"/animais/{id_}/editar",
                 "/voz", "/animais/novo?prefill=1&cor=Azul&numero=3"):
        assert cliente.get(rota).status_code == 200, rota
    html_lista = cliente.get("/animais").get_data(as_text=True)
    assert 'class="chip-brinco animal-identificacao"' in html_lista
    assert "--cor-brinco:#f4c430;--texto-brinco:#17211b" in html_lista
    html_ficha = cliente.get(f"/animais/{id_}").get_data(as_text=True)
    assert "brinco-identidade" in html_ficha and "Amarelo 92" in html_ficha
    assert "background:#f4c430;color:#17211b" in html_ficha
    html_mobile = cliente.get(f"/animais/{id_}?modo=mobile").get_data(as_text=True)
    assert "cond-brinco-identidade" in html_mobile and "Amarelo 92" in html_mobile


def test_ficha_mobile_mostra_acoes_e_um_microfone(cliente, sem_animais, monkeypatch):
    import routes_animais
    monkeypatch.setattr(routes_animais.drive, "configurado", lambda: True)
    _voz(cliente, "registrar bezerra brinco amarelo 92 deyvid")
    id_ = A.carregar().iloc[-1]["ID"]
    # Histórico não-vazio: o template mobile deve listar itens (não lotes do |slice).
    _voz(cliente, "gravar vacina estepto penicilina bezerra, brinco amarelo 92")

    html = cliente.get(f"/animais/{id_}?modo=mobile").get_data(as_text=True)

    assert "Erro ao carregar a ficha" not in html
    assert "cond-acao" in html
    assert "Vacina" in html or "Vacinação" in html
    assert 'id="search-mic"' in html
    assert 'id="btn-voz-top"' not in html
    assert 'id="cond-foto-arquivo"' in html
    assert 'aria-label="Tirar foto"' in html
    assert 'data-cond-abrir="mov-pasto"' in html
    assert 'id="mov-pasto"' in html
    assert 'data-cond-abrir="baixa-animal"' in html
    assert 'id="baixa-animal"' in html
    assert 'action="/animais/' + id_ + '/baixa"' in html


def test_frases_do_usuario_gravam_de_verdade(cliente, sem_animais):
    """As duas frases perguntadas: vacina com produto dito logo após 'vacina' e
    venda de 10 novilhas com brincos de três cores, em sequência sem 'e'."""
    for cor, dono, nums in (("vermelho", "geane", ["12", "13", "17"]),
                            ("amarelo", "deyvid", ["01", "08", "09", "12"]),
                            ("azul", "nilson", ["11", "25", "33", "07"])):
        for n in nums:
            _, resp = _voz(cliente, f"registrar novilha brinco {cor} {n} {dono}")
            assert resp.get_json()["ok"], resp.get_json()

    _, resp = _voz(cliente, "gravar vacina estepto penicilina bezerra ou novilha, brinco amarelo 12")
    assert resp.get_json()["ok"], resp.get_json()
    ult = db.carregar_aba("Manejo").iloc[-1]
    assert (ult["Tipo"], ult["Produto"], int(ult["Qtd Cabeças"])) == ("Vacinação", "estepto penicilina", 1)
    assert "Amarelo 12 #A" in ult["Brincos"]

    frase = "venda 10 novilhas, brincos vermelho 12 13 17, amarelo 01 08 09, azul 11 25 33 07"
    r, resp = _voz(cliente, frase)
    assert resp.status_code == 400 and "valor" in resp.get_json()["erro"].lower()   # falta o preço

    _, resp = _voz(cliente, frase.replace("venda 10 novilhas,", "venda 10 novilhas por 38 mil,"))
    assert resp.get_json()["ok"], resp.get_json()
    v = db.carregar_aba("Vendas").iloc[-1]
    assert (int(v["Qtd Cabeças"]), float(v["Valor Total (R$)"])) == (10, 38000)
    assert (int(v["Qtd Mae"]), int(v["Qtd Deyvid"]), int(v["Qtd Nilson"])) == (3, 3, 4)
    assert v["Brincos"].count("#A") == 10
    vivos = A.vivos(A.carregar())
    assert len(vivos) == 1 and int(vivos.iloc[0]["Brinco Nº"]) == 12   # só o amarelo 12 ficou
    d = db.carregar_todas()
    checar_invariantes(d["Compras"], d["Gastos"], d["Vendas"], d["Manejo"])


# ── Evolução de categoria e sexo ─────────────────────────────────────────────

def _animal(id_, cat, nasc=None, mae="", status="Vivo"):
    from config import COLUNAS_ANIMAIS
    return {**{c: "" for c in COLUNAS_ANIMAIS}, "ID": id_, "Categoria": cat, "Status": status,
            "Nascimento": pd.Timestamp(nasc) if nasc else pd.NaT, "Mãe": mae}


@pytest.mark.parametrize("cat,nasc,esperado", [
    ("Bezerra", "2025-10-16", "Bezerra"),    # 1 dia antes dos 12 meses
    ("Bezerra", "2025-10-15", "Novilha"),    # 12 meses certinho
    ("Bezerro", "2025-06-01", "Garrote"),
    ("Garrote", "2024-10-15", "Boi"),        # 24 meses
    ("Bezerro", "2023-01-01", "Boi"),        # pula dois degraus de uma vez
    ("Bezerra", None, "Bezerra"),            # sem nascimento não dá para saber
    ("Touro", "2020-01-01", "Touro"),        # manual, não muda
    ("Novilho", "2020-01-01", "Novilho"),
    ("Vaca", "2026-01-01", "Vaca"),          # nunca desce
    ("Novilha", "2020-01-01", "Novilha"),    # vira vaca só com cria, não por idade
])
def test_evolucao_por_idade(cat, nasc, esperado):
    df = pd.DataFrame([_animal("A0001", cat, nasc)])
    assert A.evoluir_categorias(df, HOJE).at[0, "Categoria"] == esperado


def test_novilha_com_cria_vira_vaca_e_morto_nao_evolui():
    df = pd.DataFrame([_animal("A0001", "Novilha", "2024-01-01"),
                       _animal("A0002", "Bezerra", "2026-09-01", mae="Amarelo 01 #A0001"),
                       _animal("A0003", "Bezerra", "2020-01-01", status="Morto")])
    cats = list(A.evoluir_categorias(df, HOJE)["Categoria"])
    assert cats == ["Vaca", "Bezerra", "Bezerra"]


def test_sexo_vem_da_categoria():
    reg, _ = A.normalizar({"Dono": "Deyvid", "Brinco Nº": 77, "Categoria": "Novilha", "Sexo": "M"},
                          A.carregar().iloc[0:0])
    assert reg["Sexo"] == "F"     # categoria manda, mesmo com sexo errado vindo
    reg, _ = A.normalizar({"Dono": "Deyvid", "Brinco Nº": 78, "Sexo": "M"}, A.carregar().iloc[0:0])
    assert reg["Sexo"] == "M"     # sem categoria, vale o informado
