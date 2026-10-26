# -*- coding: utf-8 -*-
"""
Pastos com mapa (v5.2): área pelo contorno, onde cada cabeça está, dias e UA/ha.
"""
import io
import json
import zipfile

import pandas as pd
import pytest

import pastos as PA
from config import COLUNAS_MANEJO, COLUNAS_PASTOS

# Quadrado de ~1 km de lado no equador (1 km ≈ 0,0089832°).
LADO = 0.0089832


def _quadrado(lon=0.0, lat=0.0, lado=LADO):
    return {"type": "Polygon", "coordinates": [[[lon, lat], [lon + lado, lat],
                                                [lon + lado, lat + lado], [lon, lat + lado],
                                                [lon, lat]]]}


def test_area_quadrado_de_1km():
    assert PA.area_ha(_quadrado()) == pytest.approx(100, rel=0.01)


@pytest.mark.parametrize("contorno", [
    "não é json", json.dumps({"type": "Point", "coordinates": [0, 0]}),
    json.dumps({"type": "Polygon", "coordinates": [[[0, 0], [0, 1]]]}),          # 2 pontos
    json.dumps({"type": "Polygon", "coordinates": [[[0, 200], [1, 0], [1, 1]]]}),  # lat 200
    json.dumps({"type": "Polygon", "coordinates": [[[0, 0], ["a", 0], [1, 1]]]}),
    json.dumps({"type": "Polygon", "coordinates": [[[0, 0], [1e-9, 0], [0, 1e-9]]]}),  # área ~0
])
def test_contorno_invalido(contorno):
    with pytest.raises(ValueError):
        PA.validar_contorno(contorno)


def test_contorno_feature_do_leaflet():
    feat = {"type": "Feature", "properties": {}, "geometry": _quadrado()}
    geo, area = PA.validar_contorno(json.dumps(feat))
    assert geo["type"] == "Polygon" and area == pytest.approx(100, rel=0.01)


def test_criar_e_nome_repetido(dados_restaurados):
    id_ = PA.criar("Pasto da Mina", json.dumps(_quadrado()), "Deyvid")
    df = PA.carregar()
    p = df[df["ID"] == id_].iloc[0]
    assert p["Nome"] == "Pasto da Mina" and p["Ativo"] == "Sim"
    assert float(p["Área (ha)"]) == pytest.approx(100, rel=0.01)
    with pytest.raises(ValueError):
        PA.criar("pasto da mina", json.dumps(_quadrado(1, 1)))
    with pytest.raises(ValueError):
        PA.criar("", json.dumps(_quadrado(1, 1)))
    assert PA.criar("Outro", json.dumps(_quadrado(1, 1))) != id_


def _pastos(*ids):
    return pd.DataFrame([{**{c: "" for c in COLUNAS_PASTOS}, "ID": i, "Nome": i, "Área (ha)": 10,
                          "Ativo": "Sim"} for i in ids], columns=COLUNAS_PASTOS)


def _animais(*ids, vendidos=()):
    return pd.DataFrame([{"ID": i, "Status": "Vendido" if i in vendidos else "Vivo"} for i in ids])


def _mov(data, pasto, brincos="", qtd=1, tipo="Movimentação de Pasto", pesos=""):
    return {**{c: "" for c in COLUNAS_MANEJO}, "Data": pd.Timestamp(data), "Tipo": tipo,
            "Qtd Cabeças": qtd, "Brincos": brincos, "Pasto": pasto, "Pesos": pesos}


def _man(*linhas):
    return pd.DataFrame(list(linhas), columns=COLUNAS_MANEJO)


HOJE = pd.Timestamp("2026-10-26")


def test_mover_e_situacao():
    man = _man(_mov("2026-10-01", "P01", qtd=10),
               _mov("2026-10-16", "P02", "Amarelo 01 #A0001; Amarelo 02 #A0002", 2),
               _mov("2026-10-16", "P02", tipo="Pesagem", pesos="Amarelo 01 #A0001: 450 kg"))
    s = PA.situacao(_pastos("P01", "P02"), _animais("A0001", "A0002", "A0003"), man,
                    estoque=10, peso_medio=450, hoje=HOJE)
    assert s["P01"]["cab"] == 8 and s["P02"]["cab"] == 2
    assert s["P01"]["dias"] == 25 and s["P02"]["dias"] == 10
    assert s["P02"]["ua"] == pytest.approx(2) and s["P02"]["ua_ha"] == pytest.approx(0.2)
    assert s[None]["cab"] == 0


def test_rebanho_todo_mais_recente_vence():
    man = _man(_mov("2026-10-01", "P02", "Amarelo 01 #A0001"),
               _mov("2026-10-10", "P01", qtd=5))
    s = PA.situacao(_pastos("P01", "P02"), _animais("A0001"), man, estoque=5, peso_medio=450,
                    hoje=HOJE)
    assert s["P01"]["cab"] == 5 and s["P02"]["cab"] == 0


def test_vendido_sai_do_pasto():
    man = _man(_mov("2026-10-01", "P01", qtd=3),
               _mov("2026-10-02", "P02", "Amarelo 01 #A0001; Amarelo 02 #A0002", 2))
    s = PA.situacao(_pastos("P01", "P02"), _animais("A0001", "A0002", vendidos=("A0002",)), man,
                    estoque=2, peso_medio=450, hoje=HOJE)
    assert s["P02"]["cab"] == 1 and s["P01"]["cab"] == 1


def test_sem_movimentacao_fica_sem_pasto():
    s = PA.situacao(_pastos("P01"), _animais(), _man(_mov("2026-10-01", "", qtd=3)),
                    estoque=3, peso_medio=450, hoje=HOJE)
    assert s[None]["cab"] == 3 and s["P01"]["cab"] == 0


def test_excluir_pasto(dados_restaurados):
    id_ = PA.criar("Some", json.dumps(_quadrado()))
    PA.excluir(id_)
    df = PA.carregar()
    assert df[df["ID"] == id_].iloc[0]["Ativo"] == "Não"
    assert id_ not in PA.ativos(df)["ID"].tolist()
    s = PA.situacao(df, _animais(), _man(_mov("2026-10-01", id_, qtd=4)), estoque=4,
                    peso_medio=450, hoje=HOJE)
    assert id_ not in s and s[None]["cab"] == 4
    PA.criar("Some", json.dumps(_quadrado()))   # nome de excluído pode voltar


def test_ua_sem_peso():
    s = PA.situacao(_pastos("P01"), _animais("A0001"), _man(_mov("2026-10-01", "P01", qtd=2)),
                    estoque=2, peso_medio=0, hoje=HOJE)
    assert s["P01"]["ua"] == pytest.approx(2) and s["P01"]["estimado"]


def test_mover_grava_no_manejo(dados_restaurados):
    import db
    id_ = PA.criar("Destino", json.dumps(_quadrado()))
    PA.mover(id_, "2026-10-20", None, 7, "Deyvid")
    m = db.carregar_aba("Manejo").iloc[-1]
    assert m["Tipo"] == "Movimentação de Pasto" and m["Pasto"] == id_
    assert int(m["Qtd Cabeças"]) == 7 and m["Data"] == pd.Timestamp("2026-10-20")
    with pytest.raises(ValueError):
        PA.mover("P99", "2026-10-20", None, 7)


# ── Lotação e composição do rebanho ───────────────────────────────────────────

@pytest.mark.parametrize("ua_ha, capacidade, esperado", [
    (1.0, 1.5, "ok"),          # 67%
    (1.04, 1.5, "ok"),         # 69% — última do verde
    (1.05, 1.5, "atencao"),    # 70% — começa o amarelo
    (1.5, 1.5, "atencao"),     # 100% — no limite ainda é amarelo
    (1.6, 1.5, "excesso"),     # acima da capacidade
    (0.0, 1.5, "ok"),          # pasto vazio
    (None, 1.5, None),         # pasto sem área desenhada
    (1.0, 0, None),            # capacidade não configurada
    (1.0, None, None),
])
def test_nivel_de_lotacao(ua_ha, capacidade, esperado):
    assert PA.nivel(ua_ha, capacidade) == esperado


def test_composicao_do_rebanho():
    import animais as A
    df = pd.DataFrame([
        {"ID": "A0001", "Status": "Vivo",    "Categoria": "Boi",     "Sexo": "M"},
        {"ID": "A0002", "Status": "Vivo",    "Categoria": "Vaca",    "Sexo": "F"},
        {"ID": "A0003", "Status": "Vivo",    "Categoria": "Boi",     "Sexo": "M"},
        {"ID": "A0004", "Status": "Vendido", "Categoria": "Garrote", "Sexo": "M"},
    ])
    c = A.composicao(df, estoque=6)
    # Vendido não conta; 6 cabeças no estoque e 3 cadastradas = 3 sem cadastro.
    assert c["categorias"] == {"Boi": 2, "Vaca": 1}
    assert c["sexos"] == {"M": 2, "F": 1}
    assert c["sem_cadastro"] == 3 and c["total"] == 6


def test_composicao_sem_animais_cadastrados():
    import animais as A
    c = A.composicao(pd.DataFrame(), estoque=4)
    assert c["categorias"] == {} and c["sem_cadastro"] == 4 and c["total"] == 4


def test_composicao_estoque_menor_que_cadastro():
    """Estoque desatualizado nunca vira fatia negativa."""
    import animais as A
    df = pd.DataFrame([{"ID": "A0001", "Status": "Vivo", "Categoria": "Boi", "Sexo": "M"},
                       {"ID": "A0002", "Status": "Vivo", "Categoria": "Boi", "Sexo": "M"}])
    c = A.composicao(df, estoque=1)
    assert c["sem_cadastro"] == 0 and c["total"] == 2


# ── Telas ─────────────────────────────────────────────────────────────────────

def _post(cliente, rota, **dados):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    return cliente.post(rota, data={"csrf_token": "tok", **dados}, follow_redirects=True)


def test_pagina_pastos_abre(cliente):
    r = cliente.get("/pastos")
    assert r.status_code == 200 and "leaflet" in r.get_data(as_text=True)


def test_criar_pela_tela(cliente, dados_restaurados):
    r = _post(cliente, "/pastos/novo", nome="Pasto Tela", contorno=json.dumps(_quadrado()))
    html = r.get_data(as_text=True)
    assert r.status_code == 200 and "Pasto Tela" in html
    p = PA.carregar().iloc[-1]
    assert p["Nome"] == "Pasto Tela" and p["Criado Por"] == "Deyvid"
    r = _post(cliente, "/pastos/novo", nome="Forjado", contorno='{"type":"Polygon","coordinates":[[[0,200],[1,0],[1,1]]]}')
    assert "Forjado" not in PA.carregar()["Nome"].tolist()


def test_mover_pela_tela(cliente, dados_restaurados):
    import db
    id_ = PA.criar("Pasto Mover", json.dumps(_quadrado()))
    antes = len(db.carregar_aba("Manejo"))
    _post(cliente, "/pastos/mover", pasto=id_, data="2026-10-20", quem="todos")
    man = db.carregar_aba("Manejo")
    assert len(man) == antes + 1 and man.iloc[-1]["Pasto"] == id_


def test_pagina_pastos_mostra_lotacao_e_composicao(cliente):
    html = cliente.get("/pastos").get_data(as_text=True)
    assert "Lotação" in html and "Rebanho" in html


def test_dashboard_mostra_lotacao_e_composicao(cliente):
    html = cliente.get("/").get_data(as_text=True)
    assert "Lotação" in html and "UA/ha" in html


def test_salvar_capacidade_ua_ha(cliente, dados_restaurados):
    from routes_usuarios import _carregar_sitio_config
    _post(cliente, "/configuracoes/rebanho", peso_medio="480", rendimento="52",
          preco_arroba="320", capacidade_ua_ha="2,5")
    assert _carregar_sitio_config()["capacidade_ua_ha"] == 2.5
    # Fora da faixa é aparado, não aceito cru.
    _post(cliente, "/configuracoes/rebanho", peso_medio="480", rendimento="52",
          preco_arroba="320", capacidade_ua_ha="99")
    assert _carregar_sitio_config()["capacidade_ua_ha"] == 20.0


def test_mover_brinco_errado(cliente, dados_restaurados):
    import animais as A
    import db
    A._gravar(A.carregar().iloc[0:0])
    id_ = PA.criar("Pasto Brinco", json.dumps(_quadrado()))
    antes = len(db.carregar_aba("Manejo"))
    r = _post(cliente, "/pastos/mover", pasto=id_, quem="brincos", brincos="amarelo 77")
    assert len(db.carregar_aba("Manejo")) == antes
    assert r.status_code == 200


# ── Importação KMZ / KML e controles do mapa ─────────────────────────────────

KML_EXEMPLO = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Pasto da Represa</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -48.280,-18.920,0 -48.285,-18.920,0 -48.285,-18.925,0 -48.280,-18.925,0 -48.280,-18.920,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""


def _gerar_kmz(kml_texto=KML_EXEMPLO) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("doc.kml", kml_texto)
    return buf.getvalue()


def test_extrair_poligonos_kmz_e_kml():
    # KML direto em bytes
    pols = PA.extrair_poligonos_kmz(KML_EXEMPLO.encode("utf-8"))
    assert len(pols) == 1
    assert pols[0][0] == "Pasto da Represa"
    assert pols[0][1]["type"] == "Polygon"

    # KMZ zipado
    kmz_bytes = _gerar_kmz()
    pols_kmz = PA.extrair_poligonos_kmz(kmz_bytes)
    assert len(pols_kmz) == 1
    assert pols_kmz[0][0] == "Pasto da Represa"


def test_importar_kmz(dados_restaurados):
    kmz_bytes = _gerar_kmz()
    criados = PA.importar_kmz(kmz_bytes, "fazenda.kmz", "Deyvid")
    assert len(criados) == 1
    pasto_id = criados[0]["id"]
    assert criados[0]["nome"] == "Pasto da Represa"
    assert criados[0]["area"] > 0

    # Importar de novo: o nome não conflita, ganha sufixo (2)
    criados2 = PA.importar_kmz(kmz_bytes, "fazenda.kmz", "Deyvid")
    assert criados2[0]["nome"] == "Pasto da Represa (2)"
    assert criados2[0]["id"] != pasto_id


def test_importar_kmz_invalido():
    with pytest.raises(ValueError):
        PA.importar_kmz(b"conteudo nao xml nem zip")


def test_importar_kmz_pela_tela(cliente, dados_restaurados):
    with cliente.session_transaction() as s:
        s["csrf_token"] = "tok"
    kmz_bytes = _gerar_kmz()
    r = cliente.post("/pastos/importar-kmz", data={
        "csrf_token": "tok",
        "arquivo_kmz": (io.BytesIO(kmz_bytes), "meu_mapa.kmz")
    }, content_type="multipart/form-data", follow_redirects=True)
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "importado(s) com sucesso" in html
    assert "Pasto da Represa" in html


def test_pagina_pastos_tem_controles_mapa(cliente, dados_restaurados):
    PA.criar("Pasto Teste", json.dumps(_quadrado()))
    html = cliente.get("/pastos").get_data(as_text=True)
    assert "Mostrar selecionado" in html
    assert "Importar KMZ" in html
    assert "Ver no mapa" in html
