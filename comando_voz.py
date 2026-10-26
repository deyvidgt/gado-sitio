#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
comando_voz.py — entende frases faladas/digitadas e monta o registro (v4.3)

Funciona com regras (sem IA paga, sem internet no servidor): o vocabulário do
sítio é pequeno e fixo. O texto vem do reconhecimento de voz do celular (ou do
microfone do teclado) e NUNCA é gravado direto — a tela mostra o que foi
entendido e só grava depois do "Salvar".

Exemplos que ele entende:
  registrar bezerra brinco amarelo 21 deyvid nelore branca
  registrar novilha brinco vermelho 07 geane amarela com detalhe branco na testa
  nasceu bezerra amarelo 22 nelore, mãe amarelo 08
  vacina brucelose novilha 35            (sem cor: se só há um 35 vivo, é ele)
  vermifuguei o rebanho todo com ivermectina
  pesagem amarelo 21 320 quilos, azul 12 280 quilos
  morreu a vaca azul 12 picada de cobra
  comprei 5 cabeças por 15 mil, 2 do deyvid 2 do nilson 1 da mãe
  vendi amarelo 21 e azul 12 por 9 mil, arroba a 310
  gastei 350 reais de sal, 10 sacos
  visita contei 38 cabeças, choveu 20 milímetros, sal baixo, proteinado ok
  ficha amarelo 21

Dividido em duas partes:
  • analisar(texto)          → intenção pura (só texto; fácil de testar);
  • montar(intencao, ctx)    → confere nos dados (animais vivos, cores…),
                               aponta ambiguidades/erros e prepara o que gravar.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta
from urllib.parse import urlencode

from config import (
    CATEGORIAS_ANIMAL, CORES_BRINCO, LOGIN_MEMBRO, MEMBROS, NOMES_MEMBROS, TIPOS_COM_PRODUTO,
)


# ── Vocabulário ───────────────────────────────────────────────────────────────

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


_UNI = {"zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4,
        "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11,
        "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14, "quinze": 15,
        "dezesseis": 16, "dezasseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19}
_DEZ = {"vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60,
        "setenta": 70, "oitenta": 80, "noventa": 90}
_CEM = {"cem": 100, "cento": 100, "duzentos": 200, "duzentas": 200, "trezentos": 300,
        "trezentas": 300, "quatrocentos": 400, "quatrocentas": 400, "quinhentos": 500,
        "quinhentas": 500, "seiscentos": 600, "seiscentas": 600, "setecentos": 700,
        "setecentas": 700, "oitocentos": 800, "oitocentas": 800, "novecentos": 900,
        "novecentas": 900}
_PALAVRA_NUM = {**_UNI, **_DEZ, **_CEM}

# Unidades: número seguido delas NÃO é brinco.
_UNIDADES = {"kg", "quilo", "quilos", "kilo", "kilos", "kgs", "arroba", "arrobas", "real",
             "reais", "mil", "saco", "sacos", "cabeca", "cabecas", "mm", "milimetro",
             "milimetros", "mes", "meses", "ano", "anos", "dia", "dias", "litro", "litros",
             "animais", "animal", "reses", "rez", "res", "centavos",
             "vacas", "bois", "bezerros", "bezerras", "novilhas", "novilhos", "garrotes",
             "touros", "porcento", "%"}

# Cor do brinco: aceita masculino/feminino; devolve o nome canônico de CORES_BRINCO.
_CORES = {}
for _c in CORES_BRINCO:
    _n = norm(_c)
    _CORES[_n] = _c
    if _n.endswith("o"):
        _CORES[_n[:-1] + "a"] = _c
_CORES.update({"amarela": "Amarelo", "vermelha": "Vermelho", "branca": "Branco",
               "preta": "Preto", "roxa": "Roxo"})

# Donos: nomes e como o reconhecimento de voz costuma escrever (os de sempre);
# donos de outros sítios entram pelo nome, chave e logins (ver _donos()).
_APELIDOS = {"deyvid": "Deyvid", "deivid": "Deyvid", "deivide": "Deyvid", "dayvid": "Deyvid",
          "david": "Deyvid", "davi": "Deyvid", "deyvide": "Deyvid", "deyvi": "Deyvid",
          "nilson": "Nilson", "nelson": "Nilson", "nilsom": "Nilson", "nilso": "Nilson",
          "milson": "Nilson",
          "geane": "Mae", "jeane": "Mae", "giane": "Mae", "geani": "Mae", "jane": "Mae",
          "gean": "Mae", "mae": "Mae", "mamae": "Mae"}
_cache_donos: dict = {}


def _donos() -> dict:
    """{palavra falada: chave do dono} para os donos configurados agora."""
    chave_cache = tuple((m, NOMES_MEMBROS.get(m)) for m in MEMBROS)
    if chave_cache not in _cache_donos:
        d = {k: v for k, v in _APELIDOS.items() if v in MEMBROS}
        for m in MEMBROS:
            for palavra in [m, str(NOMES_MEMBROS.get(m) or "").split(" ")[0],
                            *[l for l, c in LOGIN_MEMBRO.items() if c == m]]:
                if palavra:
                    d.setdefault(norm(palavra), m)
        _cache_donos.clear()
        _cache_donos[chave_cache] = d
    return _cache_donos[chave_cache]

_CATEGORIAS = {}
for _c in CATEGORIAS_ANIMAL:
    _CATEGORIAS[norm(_c)] = _c
    _CATEGORIAS[norm(_c) + "s"] = _c

_RACAS = {"nelore": "Nelore", "anelorado": "Anelorado", "anelorada": "Anelorado",
          "angus": "Angus", "brangus": "Brangus", "girolando": "Girolando",
          "girolanda": "Girolando", "gir": "Gir", "guzera": "Guzerá", "tabapua": "Tabapuã",
          "brahman": "Brahman", "senepol": "Senepol", "holandes": "Holandesa",
          "holandesa": "Holandesa", "jersey": "Jersey", "jersei": "Jersey",
          "mestico": "Mestiço", "mestica": "Mestiço", "cruzado": "Cruzado",
          "cruzada": "Cruzado", "sindi": "Sindi", "caracu": "Caracu", "simental": "Simental",
          "canchim": "Canchim", "guzerate": "Guzerá", "girolanda": "Girolando"}
_RACAS_DUPLAS = {("red", "angus"): "Red Angus", ("meio", "sangue"): "Meio-sangue"}

_PELAGENS = {"malhado", "malhada", "pintado", "pintada", "rajado", "rajada", "chitado",
             "chitada", "baio", "baia", "castanho", "castanha", "fumaca", "mouro", "moura",
             "pampa", "zaino", "zaina", "tordilho", "tordilha", "vermelho", "vermelha",
             "branco", "branca", "preto", "preta", "amarelo", "amarela", "cinza", "rosilho",
             "rosilha", "barroso", "barrosa", "pardo", "parda", "jacto", "jacta", "chumbo"}

# Palavras que não carregam informação (não vão para "sinais"/descrição).
_FILLER = {"registrar", "registra", "registre", "cadastrar", "cadastra", "cadastre",
           "brinco", "brincos", "numero", "n", "no", "nº", "n°", "do", "da", "de", "dos",
           "das", "dono", "dona", "e", "ou", "a", "o", "as", "os", "um", "uma", "raca",
           "cor", "pelagem", "nasceu", "nasceram", "comprado", "comprada", "chegou",
           "novo", "nova", "animal", "que", "eh", "é", "pra", "para", "pro", "na", "no",
           "hoje", "ontem", "anteontem", "foi", "ta", "esta", "com", "ai", "brincado",
           "brincada", "coloquei", "colocar", "botei", "dela", "dele", "gravar", "grava",
           "grave", "anotar", "anota", "lancar", "lanca", "vaca", "filha", "filho"}


# ── Tokens ────────────────────────────────────────────────────────────────────

class Tok:
    __slots__ = ("n", "o", "v", "usado")

    def __init__(self, n, o, v=None):
        self.n, self.o, self.v, self.usado = n, o, v, False

    def __repr__(self):
        return f"Tok({self.n!r}, v={self.v})"


def _num_digitos(s: str):
    """'15.000' → 15000 · '1.500,50' → 1500.5 · '21' → 21 · '07' → 7."""
    s = s.replace("r$", "")
    if not re.fullmatch(r"\d+([.,]\d+)*", s):
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") >= 1:
        partes = s.split(".")
        if all(len(p) == 3 for p in partes[1:]):
            s = s.replace(".", "")
    try:
        f = float(s)
    except ValueError:
        return None
    return int(f) if f == int(f) else f


def tokenizar(texto: str) -> list[Tok]:
    """Quebra o texto e converte números falados em algarismos.

    'vinte e um' → 21 · 'zero sete' → 7 · 'quinze mil e quinhentos' → 15500 ·
    '15 mil' → 15000. 'um/uma' só vira número quando não parece artigo.
    """
    brutos = []
    for parte in re.findall(r"r\$\s*[\d.,]+|[\w$%º°.,'-]+", str(texto or ""), flags=re.I):
        o = parte.strip(".,;:!?'-")
        if not o:
            continue
        n = norm(o).replace("r$ ", "r$")
        if n.startswith("r$") and len(n) > 2:
            brutos.append(Tok("r$", "R$"))
            n = n[2:].strip()
            o = o[2:].strip()
        # "21kg", "320kg" → número + unidade
        m = re.fullmatch(r"(\d+(?:[.,]\d+)?)(kg|mm|l|litros?|milim\w*)", n)
        if m:
            brutos.append(Tok(m.group(1), m.group(1), _num_digitos(m.group(1))))
            brutos.append(Tok(m.group(2), m.group(2)))
            continue
        # "nº21", "n21"
        m = re.fullmatch(r"(?:n|no|nº|n°)(\d{1,2})", n)
        if m:
            n = o = m.group(1)
        brutos.append(Tok(n, o, _num_digitos(n)))

    _CONTEXTO_TAG = set(_CORES) | {"brinco", "numero", "n", "nº", "zero"}
    out: list[Tok] = []
    i = 0
    while i < len(brutos):
        t = brutos[i]
        w = t.n
        ant = out[-1].n if out else ""
        prox = brutos[i + 1].n if i + 1 < len(brutos) else ""
        if w == "meia" and ant in _CONTEXTO_TAG:          # "amarelo meia" = 06
            out.append(Tok("6", t.o, 6)); i += 1; continue
        e_num = w in _PALAVRA_NUM or w == "mil"
        if w in ("um", "uma") and not (ant in _CONTEXTO_TAG or prox in _UNIDADES):
            e_num = False                                  # artigo: "uma bezerra"
        if w == "mil" and out and out[-1].v is not None:
            e_num = False                                  # "15 mil": 2ª passada
        if not e_num:
            out.append(t); i += 1; continue
        if w == "zero" and prox in _UNI and _UNI[prox] < 10:   # "zero sete" → 07
            out.append(Tok(str(_UNI[prox]), f"{t.o} {brutos[i + 1].o}", _UNI[prox]))
            i += 2; continue
        # Compõe: "vinte E um", "cento E vinte E cinco", "dois mil E quinhentos".
        total, grupo = 0, 0
        if w == "mil":
            total, ult = 1000, 1000
        else:
            grupo = ult = _PALAVRA_NUM[w]
        origs, j = [t.o], i + 1
        while j < len(brutos):
            nw = brutos[j].n
            if nw == "mil" and ult != 1000:
                total += (grupo or 1) * 1000; grupo = 0; ult = 1000
                origs.append(brutos[j].o); j += 1
                continue
            if nw == "e" and j + 1 < len(brutos) and brutos[j + 1].n in _PALAVRA_NUM:
                v2 = _PALAVRA_NUM[brutos[j + 1].n]
                lugar = 1000 if ult == 1000 else 100 if ult >= 100 else 10 if ult >= 20 else 0
                if 0 < v2 < lugar:
                    grupo += v2; ult = v2
                    origs += ["e", brutos[j + 1].o]; j += 2
                    continue
            break
        v = total + grupo
        out.append(Tok(str(v), " ".join(origs), v))
        i = j

    # Segunda passada: "15 mil" → 15000; "15 mil e 500" → 15500.
    fim: list[Tok] = []
    i = 0
    while i < len(out):
        t = out[i]
        if t.v is not None and i + 1 < len(out) and out[i + 1].n == "mil":
            v = t.v * 1000
            orig = f"{t.o} mil"
            i += 2
            if i + 1 < len(out) and out[i].n == "e" and out[i + 1].v is not None and out[i + 1].v < 1000:
                v += out[i + 1].v
                orig += f" e {out[i + 1].o}"
                i += 2
            fim.append(Tok(str(v), orig, v))
            continue
        fim.append(t)
        i += 1
    return fim


# ── Extração de pedaços ───────────────────────────────────────────────────────

def _eh_inteiro(t: Tok) -> bool:
    return isinstance(t.v, int) and not isinstance(t.v, bool)


def _marcador_mae(toks, i) -> bool:
    """'mãe amarelo 08' / 'filha da vaca 8' — o brinco a seguir é da MÃE."""
    w = toks[i].n
    if w not in ("mae", "filha", "filho", "mamae"):
        return False
    for k in range(i + 1, min(i + 5, len(toks))):
        if _eh_inteiro(toks[k]) and 1 <= toks[k].v <= 99:
            return True
        if toks[k].n not in _CORES and toks[k].n not in ("e", "a", "o", "da", "de", "do",
                                                       "vaca", "brinco", "numero", "eh", "é"):
            return False
    return False


def _brincos(toks, exigir_contexto=False) -> list[dict]:
    """Acha brincos (cor? + nº 1..99) e marca os tokens como usados.

    exigir_contexto: em compra/venda/gasto um número solto é quantidade/valor —
    só vira brinco com cor ou com a palavra "brinco" antes.
    """
    achados = []
    cat_atual = None
    em_mae = False
    ultimo_fim = -10
    ultima_cor = None
    for i, t in enumerate(toks):
        if t.n in _CATEGORIAS and not t.usado:
            cat_atual = _CATEGORIAS[t.n]
        if _marcador_mae(toks, i):
            em_mae = True
            t.usado = True
            for x in toks[i + 1:i + 4]:
                if x.n in ("da", "de", "do", "vaca", "a", "o", "e", "eh", "é"):
                    x.usado = True
                else:
                    break
            continue
        if not (_eh_inteiro(t) and 1 <= t.v <= 99) or t.usado:
            continue
        prox = toks[i + 1].n if i + 1 < len(toks) else ""
        ant = toks[i - 1].n if i else ""
        if prox in _UNIDADES or ant in ("dia", "r$", "arroba", "por", "contei", "contamos") or \
                (prox == "a" and i + 2 < len(toks) and toks[i + 2].n in ("arroba", "cabeca")):
            continue
        # cor: logo antes (pulando brinco/número) ou logo depois de "brinco N"
        cor, k = None, i - 1
        while k >= 0 and toks[k].n in ("brinco", "numero", "n", "nº", "no", "de", "do"):
            k -= 1
        if k >= 0 and toks[k].n in _CORES and not toks[k].usado:
            cor = _CORES[toks[k].n]
            toks[k].usado = True
            k -= 1
        teve_brinco = any(toks[x].n in ("brinco", "brincos", "numero", "n", "nº")
                          for x in range(max(0, i - 3), i))
        if not cor and (ultimo_fim == i - 1 or (ant in ("e", ",") and ultimo_fim == i - 2)):
            cor = ultima_cor   # "amarelo 21 22 e 23" → todos amarelos
        elif not cor and prox in _CORES and ant in ("brinco", "numero"):
            cor = _CORES[prox]
            toks[i + 1].usado = True
        if exigir_contexto and not cor and not teve_brinco and ultimo_fim not in (i - 1, i - 2):
            continue
        for x in range(max(0, i - 3), i):
            if toks[x].n in ("brinco", "brincos", "numero", "nº"):
                toks[x].usado = True
        t.usado = True
        achados.append({"num": int(t.v), "cor": cor, "categoria": None if em_mae else cat_atual,
                        "mae": em_mae, "pos": i})
        ultimo_fim, ultima_cor = i, cor
    return achados


def extrair_brincos(texto: str) -> list[dict]:
    """'amarelo 21, azul 12 e 35' → [{num, cor, categoria}] — campo Brincos dos formulários."""
    return [{"num": b["num"], "cor": b["cor"], "categoria": b["categoria"]}
            for b in _brincos(tokenizar(texto))]


def _dono(toks, ignorar_marcador=True):
    for i, t in enumerate(toks):
        if t.n in _donos() and not t.usado:
            if ignorar_marcador and _marcador_mae(toks, i):
                continue
            dono = _donos()[t.n]
            # "mãe ou geane": os dois nomes do mesmo dono saem do texto livre
            for x in toks:
                if _donos().get(x.n) == dono:
                    x.usado = True
            return dono
    return None


def _cotas_por_dono(toks) -> dict:
    """'2 do deyvid 2 do nilson 1 da mãe' / 'deyvid 2' → {membro: qtd}."""
    cotas = {}
    for i, t in enumerate(toks):
        if t.n not in _donos() or t.usado:
            continue
        membro = _donos()[t.n]
        # número antes (até 3 tokens: "2 do deyvid", "2 cabeças do deyvid")
        for k in range(i - 1, max(-1, i - 4), -1):
            if _eh_inteiro(toks[k]) and not toks[k].usado and toks[k].v < 1000:
                cotas[membro] = toks[k].v
                toks[k].usado = True
                break
            if toks[k].n in _donos():
                break
        else:
            k = None
        if membro not in cotas and i + 1 < len(toks) and _eh_inteiro(toks[i + 1]) \
                and not toks[i + 1].usado and toks[i + 1].v < 1000:
            cotas[membro] = toks[i + 1].v
            toks[i + 1].usado = True
        if membro not in cotas:
            cotas[membro] = None    # citado sem número
        t.usado = True
    return cotas


def _categoria(toks):
    for t in toks:
        if t.n in _CATEGORIAS and not t.usado:
            t.usado = True
            return _CATEGORIAS[t.n]
    return None


def _raca(toks):
    for i in range(len(toks) - 1):
        par = (toks[i].n, toks[i + 1].n)
        if par in _RACAS_DUPLAS and not toks[i].usado:
            toks[i].usado = toks[i + 1].usado = True
            return _RACAS_DUPLAS[par]
    for t in toks:
        if t.n in _RACAS and not t.usado:
            t.usado = True
            return _RACAS[t.n]
    return None


def _pelagem(toks):
    for t in toks:
        if t.n in _PELAGENS and not t.usado:
            t.usado = True
            return t.o[:1].upper() + t.o[1:].lower()
    return None


def _idade_meses(toks):
    """'com 4 meses' / '2 anos' → meses (consome os tokens)."""
    for i, t in enumerate(toks):
        if t.v is not None and not t.usado and i + 1 < len(toks) and \
                toks[i + 1].n in ("mes", "meses", "ano", "anos", "dias", "dia"):
            u = toks[i + 1].n
            meses = t.v * 12 if u.startswith("ano") else (t.v / 30 if u.startswith("dia") else t.v)
            t.usado = toks[i + 1].usado = True
            if i and toks[i - 1].n in ("com", "de"):
                toks[i - 1].usado = True
            return meses
    return None


def _data(toks, hoje: datetime):
    """hoje / ontem / anteontem / dia 12 → date (consome tokens)."""
    for i, t in enumerate(toks):
        if t.n == "ontem":
            t.usado = True
            return (hoje - timedelta(days=1)).date()
        if t.n == "anteontem":
            t.usado = True
            return (hoje - timedelta(days=2)).date()
        if t.n == "dia" and i + 1 < len(toks) and _eh_inteiro(toks[i + 1]) and 1 <= toks[i + 1].v <= 31:
            d = toks[i + 1].v
            t.usado = toks[i + 1].usado = True
            ano, mes = hoje.year, hoje.month
            if d > hoje.day:      # "dia 28" falado no dia 3 = mês passado
                mes -= 1
                if mes == 0:
                    ano, mes = ano - 1, 12
            try:
                return datetime(ano, mes, d).date()
            except ValueError:
                return hoje.date()
        if t.n == "hoje":
            t.usado = True
    return hoje.date()


def _peso_kg(toks, pos_min=0, pos_max=None):
    """Primeiro 'N quilos/kg/arrobas' no intervalo → kg (arroba = 15 kg)."""
    pos_max = len(toks) if pos_max is None else pos_max
    for i in range(pos_min, min(pos_max, len(toks) - 1)):
        t, u = toks[i], toks[i + 1].n
        if t.v is not None and not t.usado and u in ("kg", "kgs", "quilo", "quilos", "kilo",
                                                     "kilos", "arroba", "arrobas"):
            t.usado = toks[i + 1].usado = True
            return float(t.v) * (15 if u.startswith("arroba") else 1)
    return None


def _quantidade(toks):
    """'5 cabeças', '3 vacas', 'uma vaca'."""
    contaveis = {"cabeca", "cabecas", "animais", "animal", "reses", "res", "rez"} | set(_CATEGORIAS)
    for i, t in enumerate(toks):
        if t.usado:
            continue
        if t.v is not None and i + 1 < len(toks) and toks[i + 1].n in contaveis:
            t.usado = True
            if toks[i + 1].n in ("cabeca", "cabecas", "animais", "animal", "reses", "res", "rez"):
                toks[i + 1].usado = True
            return int(t.v)
        if t.n in ("um", "uma") and i + 1 < len(toks) and toks[i + 1].n in contaveis:
            t.usado = True
            return 1
    return None


def _arroba(toks):
    """'arroba a 310' / '310 a arroba' / 'arroba 310' → valor da arroba."""
    for i, t in enumerate(toks):
        if t.n not in ("arroba", "@") or t.usado:
            continue
        for k in (i + 1, i + 2, i - 1, i - 2):
            if 0 <= k < len(toks) and toks[k].v is not None and not toks[k].usado and toks[k].v >= 50:
                if k in (i - 1, i - 2) and k + 1 < len(toks) and toks[k + 1].n in ("kg", "quilos"):
                    continue
                toks[k].usado = t.usado = True
                return float(toks[k].v)
    return None


def _dinheiro(toks):
    """Valor em reais: 'N reais', 'R$ N', 'por N', 'N mil'… → (valor, por_cabeca)."""
    candidatos = []
    for i, t in enumerate(toks):
        if t.v is None or t.usado:
            continue
        prox = toks[i + 1].n if i + 1 < len(toks) else ""
        ant = toks[i - 1].n if i else ""
        if prox in {"kg", "quilos", "quilo", "sacos", "saco", "cabecas", "cabeca", "mm",
                    "milimetros", "litros", "meses", "anos", "dias"} | set(_CATEGORIAS):
            continue
        peso = 0
        if prox in ("reais", "real", "conto", "contos") or ant == "r$":
            peso = 3
        elif ant in ("por", "custou", "paguei", "pagamos", "valor", "deu", "foi", "total", "a"):
            peso = 2
        elif t.v >= 100:
            peso = 1
        if peso:
            candidatos.append((peso, t.v, i))
    if not candidatos:
        return None, False
    candidatos.sort(key=lambda c: (-c[0], -c[1]))
    _, v, i = candidatos[0]
    toks[i].usado = True
    resto = " ".join(x.n for x in toks[i + 1:i + 5])
    por_cab = bool(re.search(r"\b(cada|por cabeca|a cabeca|cada uma|cada um|por animal)\b", resto))
    return float(v), por_cab


def _texto_livre(toks, a_partir=0, parar_em=None) -> str:
    """Junta as palavras originais que sobraram (sem enchimento)."""
    palavras = []
    for t in toks[a_partir:parar_em]:
        if t.usado or t.n in _FILLER:
            continue
        palavras.append(t.o)
    return " ".join(palavras).strip(" ,.")


def _apos(toks, gatilhos: set) -> str:
    """Texto original depois da 1ª palavra-gatilho ('com detalhe branco na testa')."""
    for i, t in enumerate(toks):
        if t.n in gatilhos and not t.usado:
            resto = [x for x in toks[i + 1:] if not x.usado]
            if resto:
                t.usado = True
                for x in resto:
                    x.usado = True
                return " ".join(x.o for x in resto).strip(" ,.")
    return ""


# ── Ação ──────────────────────────────────────────────────────────────────────

_VACINAS = [
    ("brucel", "Vacina Brucelose"), ("raiva", "Vacina Raiva"), ("clostri", "Vacina Clostridioses"),
    ("carbun", "Vacina Clostridioses"), ("botul", "Vacina Clostridioses"),
    ("polivalente", "Vacina Clostridioses"), ("manqueira", "Vacina Clostridioses"),
]

# Voz só LANÇA registro novo. Apagar/editar/transferir pela voz é arriscado (um erro
# de reconhecimento mexe em lançamento antigo) — essas frases são recusadas antes de
# qualquer outra ação, senão "apaga a última venda" viraria uma venda nova.
_RECUSA = re.compile(r"\b(apag\w*|exclu\w*|delet\w*|remov\w*|edit\w*|corrig\w*|corrij\w*|"
                     r"alter\w*|cancel\w*|desfaz\w*|desfiz\w*|estorn\w*|transfer\w*)\b")

# Palavras de gado: "comprei" sem nenhuma delas é compra de insumo (gasto), não de gado.
_GADO = re.compile(r"\b(gado|boi|bois|bezerr\w*|novilh\w*|vaca|vacas|garrote\w*|touro\w*|"
                   r"cabeca|cabecas|animal|animais|rez|res|reses|brinco\w*)\b")

_ACOES = [
    ("consulta",   r"\b(quanto|quantos|quantas|quantidade)\b"),
    ("ficha",      r"\b(ficha|quem e|mostrar?|mostra|abrir?|abre|ver|historico)\b"),
    ("visita",     r"\b(vi[sz]ita|vi[sz]itei|fui no sitio|fui ao sitio)\b"),
    ("morte",      r"\b(morreu|morreram|morte|morta|morto|faleceu|perdemos|perdi)\b"),
    ("venda",      r"\b(vendi|vendeu|vendemos|venda|vendido|vendida|vendidos|vendidas)\b"),
    ("gasto",      r"\b(gastei|gastamos|gasto|gastos|paguei|pagamos|despesa)\b"),
    ("manejo",     r"\b(vacin\w*|vermif\w*|pesagem|pesei|pesou|pesamos|pesar|peso|tratamento|"
                   r"tratei|medicad\w*|medicamento|remedio|pasto)\b"),
    ("nascimento", r"\b(nasceu|nasceram|nascimento|pariu|nascida|nascido)\b"),
    ("compra",     r"\b(comprei|compramos|comprou|compra)\b"),
    ("cadastro",   r"\b(registrar|registra|registre|cadastrar|cadastra|cadastre|gravar|grava|grave|"
                   r"anotar|anota|lancar|lanca|brinco|brincar|"
                   r"brinquei|chegou|chegaram|coloquei)\b"),
]


def _acao(n: str, toks) -> str | None:
    if _RECUSA.search(n):
        return "recusa"
    if re.search(r"\b(comprei|compramos|comprou)\b", n) and not _GADO.search(n) \
            and not any(t.n in _CORES or t.n in _CATEGORIAS for t in toks):
        return "gasto"
    for nome, rx in _ACOES:
        if re.search(rx, n):
            if nome == "compra":
                # "registrar novilha brinco… comprada" = cadastro; compra tem valor
                tem_valor = any(t.n in ("reais", "real", "mil", "r$", "por") for t in toks)
                if not tem_valor and any(t.n in _CATEGORIAS for t in toks) and \
                        any(t.n in ("brinco", "brincos") for t in toks):
                    return "cadastro"
            if nome == "ficha" and not any(_eh_inteiro(t) for t in toks):
                continue
            return nome
    # "bezerra amarelo 21 deyvid" sem verbo → cadastro
    if any(t.n in _CATEGORIAS for t in toks) and any(_eh_inteiro(t) for t in toks):
        return "cadastro"
    return None


def _tipo_manejo(n: str) -> str | None:
    if "vacin" in n:
        for chave, tipo in _VACINAS:
            if chave in n:
                return tipo
        return "Vacinação"
    if "vermif" in n:
        return "Vermifugação"
    if re.search(r"\b(pesagem|pesei|pesou|pesamos|pesar|peso)\b", n):
        return "Pesagem"
    if re.search(r"\bpasto\b", n):
        return "Movimentação de Pasto"
    if re.search(r"\b(tratamento|tratei|medicad\w*|medicamento|remedio)\b", n):
        return "Tratamento Veterinário"
    return None


_PALAVRAS_MANEJO = re.compile(r"^(vacin\w*|vermif\w*|remedio|medicamento|tratamento|tratei|"
                              r"medic\w*|apliquei|aplicar|aplicado|aplicada|injecao|dose)$")
_TIPO_VACINA = re.compile(r"^(brucel\w*|raiva|clostri\w*|carbun\w*|botul\w*|polivalente|manqueira|contra)$")
_PARA_PRODUTO = {"na", "no", "nas", "nos", "em", "ou", "e", "do", "da", "de", "brinco", "brincos",
                 "numero", "hoje", "ontem", "anteontem", "dia", "todo", "todos", "todas", "rebanho",
                 "gado", "o", "a", "os", "as"}


def _produto_apos_manejo(toks) -> str:
    """'vacina estepto penicilina bezerra…' → 'estepto penicilina': as palavras logo
    depois de vacina/vermífugo/remédio, até a categoria, o brinco ou um número."""
    for i, t in enumerate(toks):
        if not _PALAVRAS_MANEJO.match(t.n):
            continue
        palavras = []
        for x in toks[i + 1:]:
            if _TIPO_VACINA.match(x.n) and not palavras:
                continue
            if (x.usado or x.v is not None or x.n in _CATEGORIAS or x.n in _CORES
                    or x.n in _donos() or x.n in _PARA_PRODUTO or _PALAVRAS_MANEJO.match(x.n)):
                break
            palavras.append(x)
        if palavras:
            for x in palavras:
                x.usado = True
            return " ".join(x.o for x in palavras)
    return ""


_NAO_PRODUTO = {"todo", "todos", "todas", "tudo", "rebanho", "gado", "aplicar", "apliquei",
                "nelas", "neles", "nela", "nele", "as", "os", "agora", "hoje", "contra"}


def _produto_sobra(toks) -> str:
    """Palavras que sobraram depois de tirar brincos, tipo, categoria etc. —
    o produto falado no fim ('… amarelo 01 08 09 dectomax')."""
    resto = [t for t in toks if not t.usado and t.v is None and t.n not in _FILLER
             and t.n not in _NAO_PRODUTO and t.n not in _CATEGORIAS and t.n not in _CORES
             and t.n not in _donos() and not _PALAVRAS_MANEJO.match(t.n) and not _TIPO_VACINA.match(t.n)
             and not re.match(r"^(vacinei|vacinamos|vermifuguei|vermifugamos|registrar|registra|cadastrar|"
                              r"vacinar|vermifugar|vacina|vacinas)$", t.n)]
    if not resto or len(resto) > 4:
        return ""
    for t in resto:
        t.usado = True
    return " ".join(t.o for t in resto)


# ── Visita ────────────────────────────────────────────────────────────────────

_NIVEL_INSUMO = [  # palavra falada → opção do formulário
    (("ok", "bom", "boa", "cheio", "cheia", "normal", "tranquilo"), "OK"),
    (("meio", "metade", "meia"), "Meio Saco"),
    (("baixo", "pouco", "acabando", "fraco"), "Baixo"),
    (("vazio", "acabou", "zerado", "sem", "nada"), "Vazio"),
]


def _nivel(toks, chaves: set, opcoes, ate=4):
    for i, t in enumerate(toks):
        if t.n not in chaves:
            continue
        janela = [x.n for x in toks[i + 1:i + 1 + ate]]
        for palavras, valor in opcoes:
            if any(p in janela for p in palavras):
                return valor
    return None


_CONTEINER = re.compile(r"cont[ea]i?ner")


def _analisar_visita(toks, n):
    campos = {}
    for t in toks:
        if t.n in _donos():            # "visita, deyvid, …" → quem foi
            campos["responsavel"] = NOMES_MEMBROS[_donos()[t.n]]
            break
    if re.search(r"\b(gado|contagem|contei|contado)\b(\s+\w+){0,3}?\s+(correto|certo|conferido|bateu|completo)\b", n):
        campos["gado_contado"] = "esperado"   # montar() troca pelo estoque do sistema
    for i, t in enumerate(toks):
        if t.v is not None and (t.n.isdigit() or True):
            prox = toks[i + 1].n if i + 1 < len(toks) else ""
            ant = toks[i - 1].n if i else ""
            if prox in ("cabecas", "cabeca", "animais", "bois", "reses") or ant in ("contei", "contamos", "contado"):
                campos["gado_contado"] = int(t.v)
            elif prox == "mm" or prox.startswith("milim"):
                campos["chuva_mm"] = t.v
                campos["choveu"] = "sim"
            elif prox in ("saco", "sacos"):
                # "2 sacos de sal" (produto depois) ou "proteinado tem 1 saco" (produto antes)
                depois = " ".join(x.n for x in toks[i + 2:i + 4])
                antes = " ".join(x.n for x in toks[max(0, i - 3):i])
                alvo = depois if re.search(r"prot|racao|sal", depois) else antes
                if "prot" in alvo:
                    campos["sacos_prot"] = int(t.v)
                elif "racao" in alvo:
                    campos["sacos_racao"] = int(t.v)
                elif "sal" in alvo:
                    campos["sacos_sal"] = int(t.v)
            elif prox in ("litro", "litros"):
                alvo = " ".join(x.n for x in toks[max(0, i - 4):i])
                if _CONTEINER.search(alvo):
                    campos["conteiner_litros"] = t.v
                else:
                    campos.setdefault("caixa_agua_litros", t.v)
    if re.search(r"\b(nao choveu|sem chuva)\b", n):
        campos["choveu"] = "nao"
    elif re.search(r"\bchoveu\b|\bchuva\b", n):
        campos.setdefault("choveu", "sim")
    # "sal proteinado" é o proteinado, não o sal comum
    toks_ins = [t for i, t in enumerate(toks)
                if not (t.n == "sal" and i + 1 < len(toks) and toks[i + 1].n.startswith("protein"))]
    for campo, chaves in (("sal_racao", {"sal"}), ("racao", {"racao"}),
                          ("proteinado", {"proteinado", "proteina"})):
        v = _nivel(toks_ins, chaves, _NIVEL_INSUMO, ate=2)
        if v:
            campos[campo] = v
    v = _nivel(toks, {"mato", "vegetacao", "capim", "daninha", "daninhas"}, [
        (("limpo",), "Limpo"), (("muito", "alto"), "Muito Mato"),
        (("capinar", "precisa", "crescendo"), "Precisa Capinar"),
        (("pouco", "pouca", "poucos", "poucas", "algumas", "alguns"), "Algumas, Não Precisa Capinar")])
    if v:
        campos["mato"] = v
    v = _nivel(toks, {"grama", "pastagem", "pasto"}, [
        (("boa", "bom", "verde"), "Boa"), (("seca", "secando", "amarela", "amarelando"), "Amarelando/Secando"),
        (("regular", "media"), "Regular"), (("pouca", "escassa", "rapada", "acabando"), "Escassa")])
    if v:
        campos["grama"] = v
    v = _nivel(toks, {"corrego", "agua", "rio"}, [
        (("normal", "bom", "cheio"), "Normal"), (("baixo", "pouca"), "Baixo"), (("seco", "secou"), "Seco")])
    if v:
        campos["corrego"] = v
    v = _nivel(toks, {"cisterna"}, [
        (("ok", "cheia", "boa"), "OK"), (("baixa", "secando"), "Baixo/Secando"), (("vazia", "seca"), "Vazia")])
    if v:
        campos["cisterna"] = v
    v = _nivel(toks, {"quintal"}, [(("ok", "limpo", "bom"), "OK"), (("atencao", "sujo", "precisa"), "Precisa Atenção")])
    if v:
        campos["quintal"] = v
    v = _nivel(toks, {"caixa"}, [
        (("cheia",), "Cheia"), (("meia", "metade"), "Meia"), (("baixa",), "Baixa"), (("vazia",), "Vazia")], ate=4)
    if v:
        campos["caixa_agua"] = v
    v = _nivel(toks, {t.n for t in toks if _CONTEINER.fullmatch(t.n)}, [
        (("cheio",), "Cheio"), (("meio", "metade"), "Meio"), (("baixo",), "Baixo"), (("vazio",), "Vazio")])
    if v:
        campos["conteiner"] = v
    obs = _apos(toks, {"observacao", "observacoes", "obs", "anotar", "anota"})
    if obs:
        campos["observacoes"] = obs
    return campos


# ── Análise (só texto) ────────────────────────────────────────────────────────

def analisar(texto: str, hoje: datetime | None = None) -> dict:
    """Frase → intenção. Não consulta dados; ver montar()."""
    hoje = hoje or datetime.now()
    toks = tokenizar(texto)
    n = " ".join(t.n for t in toks)
    acao = _acao(n, toks)
    r = {"acao": acao, "texto": str(texto or "").strip(), "data": None}
    if acao is None:
        return r
    if acao == "recusa":
        m = _RECUSA.search(n).group(1)
        r["verbo"] = "transferir" if m.startswith("transfer") else "apagar/editar"
        return r
    r["data"] = _data(toks, hoje)

    if acao == "visita":
        r["visita"] = _analisar_visita(toks, n)
        return r

    if acao == "consulta":
        r["dono"] = _dono(toks)
        r["categoria"] = _categoria(toks)
        return r

    if acao == "ficha":
        b = _brincos(toks)
        r["alvos"] = b[:1]
        return r

    if acao in ("cadastro", "nascimento"):
        brincos = _brincos(toks)
        proprios = [b for b in brincos if not b["mae"]]
        maes = [b for b in brincos if b["mae"]]
        idade = _idade_meses(toks)
        animal = {
            "Categoria": _categoria(toks) or (proprios[0]["categoria"] if proprios else None),
            "Brinco Cor": proprios[0]["cor"] if proprios else None,
            "Brinco Nº": proprios[0]["num"] if proprios else None,
            "Dono": _dono(toks),
            "Raça": _raca(toks),
            "Pelagem": None, "Sinais": "",
        }
        sinais = _apos(toks, {"com", "tem", "sinal", "sinais"})
        animal["Pelagem"] = _pelagem(toks)
        resto = _texto_livre(toks)
        animal["Sinais"] = "; ".join(x for x in (sinais, resto) if x)
        if acao == "nascimento":
            animal["Origem"] = "Nascimento"
            animal["Nascimento"] = r["data"]
        else:
            animal["Origem"] = "Compra" if re.search(r"\b(comprad\w*|chegou|chegaram|compra)\b", n) else "Já no sítio"
            if idade is not None:
                animal["Nascimento"] = (datetime.combine(r["data"], datetime.min.time())
                                        - timedelta(days=round(idade * 30.4))).date()
                animal["idade_estimada"] = True
        r["animal"] = animal
        r["mae"] = maes[0] if maes else None
        r["qtd"] = _quantidade(toks)
        if not proprios:
            for i, t in enumerate(toks):
                if _eh_inteiro(t) and t.v > 99 and i and (toks[i - 1].n in _CORES or toks[i - 1].n in ("brinco", "numero")):
                    r["brinco_invalido"] = t.v
                    break
        r["extra_brincos"] = proprios[1:]
        return r

    if acao in ("manejo", "morte"):
        r["tipo"] = _tipo_manejo(n) if acao == "manejo" else "Morte/Perda"
        alvos = _brincos(toks)
        pesos = []
        if r["tipo"] == "Pesagem":
            # cada brinco com o peso que vem logo depois dele
            for k, a in enumerate(alvos):
                fim = alvos[k + 1]["pos"] if k + 1 < len(alvos) else len(toks)
                pesos.append(_peso_kg(toks, a["pos"], fim))
            if not alvos:
                pesos.append(_peso_kg(toks))
        r["alvos"] = alvos
        r["pesos"] = pesos
        r["dono"] = _dono(toks)
        r["qtd"] = _quantidade(toks)
        r["todos"] = bool(re.search(r"\b(todos|todas|tudo|rebanho|gado todo|rebanho todo|todo o gado)\b", n))
        produto = _apos(toks, {"com", "produto", "usando", "usei", "marca"})
        r["produto"] = produto or _produto_apos_manejo(toks)
        if not r["produto"] and r["tipo"] in TIPOS_COM_PRODUTO:
            r["produto"] = _produto_sobra(toks)
        r["descricao"] = r["texto"]
        return r

    if acao in ("compra", "venda"):
        brincos = _brincos(toks, exigir_contexto=True)
        r["alvos"] = brincos
        r["arroba"] = _arroba(toks) if acao == "venda" else None
        r["qtd"] = _quantidade(toks)
        r["cotas"] = _cotas_por_dono(toks)
        valor, por_cab = _dinheiro(toks)
        r["valor"], r["por_cabeca"] = valor, por_cab
        r["quer_brinco"] = acao == "compra" and bool(re.search(r"\bbrinc", n))
        r["descricao"] = r["texto"]
        return r

    if acao == "gasto":
        sacos = None
        for i, t in enumerate(toks):
            if t.v is not None and i + 1 < len(toks) and toks[i + 1].n in ("saco", "sacos"):
                sacos = int(t.v); t.usado = toks[i + 1].usado = True
                break
        valor, por_unidade = _dinheiro(toks)
        if por_unidade and sacos and valor:   # "3 sacos a 95 cada" → total da compra
            valor = round(valor * sacos, 2)
        tipo, produto = "Manutenção/Outros", ""
        if re.search(r"\bproteinad\w*|\bproteina\b", n):
            tipo, produto = "Sal/Proteínado", "Proteinado"
        elif re.search(r"\bracao\b", n):
            tipo, produto = "Sal/Proteínado", "Ração"
        elif re.search(r"\bsal\b|\bmineral\b", n):
            tipo, produto = "Sal/Proteínado", "Sal"
        elif re.search(r"vacin|vermif|remedio|ivermectina|medicamento|veterinari|seringa|antibiotico", n):
            tipo = "Remédio/Vacina"
        elif re.search(r"gasolina|combustivel|diesel|frete|transporte|caminhao|oleo", n):
            tipo = "Gasolina/Transporte"
        elif re.search(r"veneno|herbicida|defensivo|mata mato|roundup|tordon|formicida|carrapaticida", n):
            tipo = "Veneno/Defensivo"
        elif re.search(r"calcario|adubo|adubacao|ureia|semente", n):
            tipo = "Calcário/Adubação"
        r.update({"tipo": tipo, "produto": produto, "sacos": sacos, "valor": valor,
                  "descricao": r["texto"]})
        return r
    return r


# ── Montagem (confere nos dados) ──────────────────────────────────────────────

def _brinco_txt(cor, num):
    return f"{cor + ' ' if cor else ''}{int(num):02d}"


def _rotulo_animal(a) -> str:
    partes = [_brinco_txt(a["Brinco Cor"], a["Brinco Nº"]), a.get("Categoria") or "",
              NOMES_MEMBROS.get(a.get("Dono"), a.get("Dono") or "")]
    return " · ".join(p for p in partes if p)


def montar(intencao: dict, ctx: dict, escolhas: dict | None = None) -> dict:
    """Confere a intenção nos dados e monta a resposta para a tela.

    ctx: df_animais (animais.carregar()), estoque (int), estoque_membro (dict),
         produtos_usados ({tipo: [..]}), membro (quem está logado).
    escolhas: {"<índice do alvo>": "<ID>"} — resposta às perguntas de ambiguidade.
    Resposta: acao, titulo, campos [[rótulo, valor]], avisos, erros, perguntas,
              payload (o que executar() grava), url_form (abrir no formulário).
    """
    import animais as A
    escolhas = {str(k): v for k, v in (escolhas or {}).items()}
    acao = intencao.get("acao")
    out = {"acao": acao, "texto": intencao.get("texto", ""), "campos": [], "avisos": [],
           "erros": [], "perguntas": [], "payload": None, "url_form": None, "titulo": ""}
    if not acao:
        out["erros"].append("Não entendi o comando. Comece com: registrar, nasceu, vacina, "
                            "vermífugo, pesagem, morreu, comprei, vendi, gastei, visita ou ficha.")
        return out
    if acao == "recusa":
        out["titulo"] = "Não faço isso por voz"
        if intencao.get("verbo") == "transferir":
            out["erros"].append("Transferir animal de dono não é feito por voz. Abra a ficha do "
                                "animal em Animais e use Editar.")
        else:
            out["erros"].append("Por voz eu só lanço registros novos — não apago, edito nem "
                                "cancelo. Para mudar um lançamento, abra a lista (Compras, Vendas, "
                                "Gastos, Manejo ou Animais) e use Editar/Excluir.")
        return out
    df = ctx["df_animais"]
    data = intencao.get("data")
    data_br = data.strftime("%d/%m/%Y") if data else ""
    data_iso = data.isoformat() if data else ""
    membro = ctx.get("membro") or ""

    def resolver_alvos(alvos, dono=None):
        refs, ids = [], []
        for k, alvo in enumerate(alvos):
            m = A.resolver(df, alvo["num"], alvo.get("cor"), alvo.get("categoria"), dono)
            pedido = _brinco_txt(alvo.get("cor"), alvo["num"])
            if escolhas.get(str(k)):
                m = m[m["ID"] == escolhas[str(k)]] if not m.empty else m
            if m.empty:
                out["erros"].append(f"Nenhum animal vivo com brinco {pedido}.")
            elif len(m) > 1:
                out["perguntas"].append({
                    "indice": k, "pergunta": f"Qual brinco {pedido}?",
                    "opcoes": [{"id": r["ID"], "rotulo": _rotulo_animal(r)} for _, r in m.iterrows()]})
            else:
                a = m.iloc[0]
                refs.append(A.ref(a))
                ids.append(a["ID"])
        return refs, ids

    # ── Consulta (só responde; não grava nada)
    if acao == "consulta":
        out["titulo"] = "📊 Rebanho"
        out["so_info"] = True
        est_m = ctx.get("estoque_membro") or {}
        dono, cat = intencao.get("dono"), intencao.get("categoria")
        vivos = A.vivos(df)
        if cat:
            v = vivos[vivos["Categoria"] == cat]
            if dono:
                v = v[v["Dono"] == dono]
            quem = f" de {NOMES_MEMBROS[dono]}" if dono else ""
            out["campos"].append([f"{cat}s com brinco{quem}", len(v)])
        elif dono:
            out["campos"].append([f"Cabeças de {NOMES_MEMBROS[dono]}", est_m.get(dono, 0)])
            out["campos"].append(["Com brinco", int((vivos["Dono"] == dono).sum()) if not vivos.empty else 0])
        else:
            out["campos"].append(["Cabeças no total", ctx.get("estoque") or 0])
            for m in MEMBROS:
                out["campos"].append([NOMES_MEMBROS[m], est_m.get(m, 0)])
            out["campos"].append(["Com brinco", len(vivos)])
        return out

    # ── Ficha
    if acao == "ficha":
        out["titulo"] = "🔎 Abrir ficha do animal"
        refs, ids = resolver_alvos(intencao.get("alvos") or [])
        if not intencao.get("alvos"):
            out["erros"].append("Diga o brinco (ex.: ficha amarelo 21).")
        if ids:
            out["campos"].append(["Animal", refs[0]])
            out["payload"] = {"acao": "ficha", "id": ids[0]}
        return out

    # ── Visita (só preenche o formulário: lá ele já guarda offline e confere tudo)
    if acao == "visita":
        campos = dict(intencao.get("visita") or {})
        out["titulo"] = "🌾 Visita ao sítio"
        if campos.get("gado_contado") == "esperado":
            campos["gado_contado"] = int(ctx.get("estoque") or 0)
        rot = {"responsavel": "Quem foi", "gado_contado": "Gado contado", "choveu": "Choveu", "chuva_mm": "Chuva (mm)",
               "sal_racao": "Sal", "racao": "Ração", "proteinado": "Proteinado",
               "sacos_sal": "Sacos de sal (estoque)", "sacos_racao": "Sacos de ração",
               "sacos_prot": "Sacos de proteinado", "mato": "Mato", "grama": "Pastagem",
               "corrego": "Córrego", "cisterna": "Cisterna", "quintal": "Quintal",
               "caixa_agua": "Caixa d'água", "caixa_agua_litros": "Caixa d'água (L)",
               "conteiner": "Contêiner", "conteiner_litros": "Contêiner (L)",
               "observacoes": "Observações"}
        out["campos"].append(["Data", data_br])
        for k, v in campos.items():
            out["campos"].append([rot.get(k, k), {"sim": "Sim", "nao": "Não"}.get(v, v)])
        if not campos:
            out["avisos"].append("Não peguei nenhum item da visita — o formulário abre em branco.")
        campos["data"] = data_iso
        out["url_form"] = "/visitas/nova?" + urlencode({"prefill": 1, **campos})
        out["so_formulario"] = True
        return out

    # ── Cadastro / Nascimento com brinco
    if acao in ("cadastro", "nascimento"):
        animal = dict(intencao.get("animal") or {})
        tem_brinco = animal.get("Brinco Nº") is not None
        if acao == "nascimento" and not tem_brinco:
            # Nasceu e ainda não pôs brinco: só o Nascimento no Manejo.
            dono = animal.get("Dono")
            qtd_n = int(intencao.get("qtd") or 1)
            out["titulo"] = "🐮 Nascimento (sem brinco)"
            out["campos"] += [["Data", data_br], ["Bezerro(a)", animal.get("Categoria") or "—"],
                              ["Quantos", qtd_n],
                              ["De quem", NOMES_MEMBROS.get(dono, "Dividido entre todos") if dono else "Dividido entre todos"]]
            desc = " ".join(x for x in (animal.get("Categoria"), animal.get("Raça"),
                                        animal.get("Pelagem"), animal.get("Sinais")) if x)
            out["payload"] = {"acao": "manejo", "linha": {
                "Data": data_iso, "Tipo": "Nascimento", "Qtd Cabeças": qtd_n, "Descrição": desc,
                "Responsável": membro, "Nascimento De": dono or "", "Brincos": ""}}
            out["avisos"].append("Sem número de brinco: registra só o nascimento. "
                                 "Para cadastrar com brinco, diga a cor e o número.")
            out["url_form"] = "/manejo/novo?" + urlencode({"prefill": 1, "tipo": "Nascimento",
                                                           "cabecas": qtd_n, "nascimento_de": dono or "",
                                                           "descricao": desc, "data": data_iso})
            return out
        out["titulo"] = "🐮 Nascimento com brinco" if acao == "nascimento" else "🏷️ Cadastrar animal"
        if intencao.get("brinco_invalido"):
            animal["Pelagem"] = None
            animal["Sinais"] = ""
            out["erros"].append(f"O número do brinco vai de 01 a 99 (ouvi {intencao['brinco_invalido']}).")
        elif not tem_brinco:
            out["erros"].append("Diga o número do brinco (ex.: brinco amarelo 21).")
        if intencao.get("extra_brincos"):
            out["avisos"].append("Ouvi mais de um brinco — cadastro um animal por vez; usei o primeiro.")
        if not animal.get("Categoria"):
            out["avisos"].append("Categoria não dita (bezerra, novilha, vaca…).")
        mae = intencao.get("mae")
        if mae:
            m = A.resolver(df, mae["num"], mae.get("cor"))
            if escolhas.get("mae"):
                m = m[m["ID"] == escolhas["mae"]]
            if len(m) == 1:
                animal["Mãe"] = A.ref(m.iloc[0])
            elif len(m) > 1:
                out["perguntas"].append({"indice": "mae", "pergunta": f"Qual é a mãe ({_brinco_txt(mae.get('cor'), mae['num'])})?",
                                         "opcoes": [{"id": r["ID"], "rotulo": _rotulo_animal(r)} for _, r in m.iterrows()]})
            else:
                animal["Mãe"] = _brinco_txt(mae.get("cor"), mae["num"])
                out["avisos"].append(f"A mãe {animal['Mãe']} não está cadastrada — anotei só o brinco.")
        if tem_brinco:
            try:
                reg, avisos = A.normalizar({**animal, "Entrada": data_iso}, df)
                out["avisos"] += avisos
                animal = {**animal, "Brinco Cor": reg["Brinco Cor"], "Dono": reg["Dono"],
                          "Sexo": reg["Sexo"]}
            except ValueError as e:
                out["erros"].append(str(e))
        idade = " (estimado pela idade)" if animal.get("idade_estimada") else ""
        nasc = animal.get("Nascimento")
        out["campos"] += [
            ["Brinco", _brinco_txt(animal.get("Brinco Cor"), animal["Brinco Nº"]) if tem_brinco else "—"],
            ["Dono", NOMES_MEMBROS.get(animal.get("Dono"), animal.get("Dono") or "—")],
            ["Categoria", animal.get("Categoria") or "—"],
            ["Raça", animal.get("Raça") or "—"],
            ["Pelagem", animal.get("Pelagem") or "—"],
            ["Sinais", animal.get("Sinais") or "—"],
            ["Origem", animal.get("Origem")],
            ["Nascimento", (nasc.strftime("%d/%m/%Y") + idade) if nasc else "—"],
        ]
        if animal.get("Mãe"):
            out["campos"].append(["Mãe", animal["Mãe"].split(" #")[0]])
        if acao == "nascimento":
            out["avisos"].append("Também registra o Nascimento no Manejo (entra no estoque do dono).")
        payload_animal = {k: (v.isoformat() if hasattr(v, "isoformat") else v)
                          for k, v in animal.items() if k != "idade_estimada"}
        payload_animal["Entrada"] = data_iso
        out["payload"] = {"acao": "cadastro", "animal": payload_animal}
        out["url_form"] = "/animais/novo?" + urlencode({"prefill": 1, **{
            "categoria": animal.get("Categoria") or "", "dono": animal.get("Dono") or "",
            "cor": animal.get("Brinco Cor") or "", "numero": animal.get("Brinco Nº") or "",
            "raca": animal.get("Raça") or "", "pelagem": animal.get("Pelagem") or "",
            "sinais": animal.get("Sinais") or "", "origem": animal.get("Origem") or "",
            "nascimento": payload_animal.get("Nascimento") or "", "mae": animal.get("Mãe") or "",
            "entrada": data_iso}})
        return out

    # ── Manejo / Morte
    if acao in ("manejo", "morte"):
        tipo = intencao.get("tipo")
        if not tipo:
            out["erros"].append("Não entendi o tipo de manejo (vacina, vermífugo, pesagem, tratamento…).")
            return out
        out["titulo"] = {"Morte/Perda": "⚰️ Morte / perda"}.get(tipo, f"🩺 {tipo}")
        refs, ids = resolver_alvos(intencao.get("alvos") or [], intencao.get("dono"))
        produto = intencao.get("produto") or ""
        if tipo in TIPOS_COM_PRODUTO and not produto:
            usados = (ctx.get("produtos_usados") or {}).get(tipo) or []
            if usados:
                produto = usados[0]
                out["avisos"].append(f"Produto não dito — usei o último: {produto}.")
            else:
                out["avisos"].append("Produto não dito — dá para completar depois em Manejo.")
        if ids:
            qtd = len(ids)
        elif intencao.get("alvos"):
            qtd = len(intencao["alvos"])      # falta responder a pergunta / brinco errado
        elif intencao.get("qtd"):
            qtd = intencao["qtd"]
        elif tipo in ("Morte/Perda",):
            qtd = 1
        else:
            qtd = ctx.get("estoque") or 0
            if not intencao.get("todos"):
                out["avisos"].append(f"Nenhum brinco dito — registro para o rebanho todo ({qtd} cab.).")
        desc = intencao.get("descricao") or ""
        if tipo == "Pesagem":
            pesos = intencao.get("pesos") or []
            if refs:
                desc = "; ".join(f"{r.split(' #')[0]}: {p:g} kg" if p else f"{r.split(' #')[0]}: sem peso"
                                 for r, p in zip(refs, pesos + [None] * len(refs)))
            elif pesos and pesos[0]:
                desc = f"Peso: {pesos[0]:g} kg"
            if not any(pesos):
                out["avisos"].append("Não ouvi o peso (ex.: 320 quilos).")
        out["campos"] += [["Data", data_br], ["Tipo", tipo], ["Animais", ", ".join(r.split(" #")[0] for r in refs) or "—"],
                          ["Cabeças", qtd]]
        if tipo in TIPOS_COM_PRODUTO:
            out["campos"].append(["Produto", produto or "—"])
        out["campos"].append(["Descrição", desc])

        if tipo == "Morte/Perda" and ids:
            out["payload"] = {"acao": "morte", "ids": ids, "data": data_iso, "motivo": desc}
            out["avisos"].append("Dá baixa no(s) animal(is) e registra a Morte/Perda no Manejo (perda do dono).")
        else:
            perda_de = ""
            if tipo == "Morte/Perda":
                perda_de = intencao.get("dono") or ""
                out["campos"].append(["Perda de", NOMES_MEMBROS.get(perda_de, "Dividida entre todos")])
            out["payload"] = {"acao": "manejo", "linha": {
                "Data": data_iso, "Tipo": tipo, "Qtd Cabeças": qtd, "Descrição": desc,
                "Responsável": membro, "Perda De": perda_de, "Produto": produto,
                "Brincos": "; ".join(refs)}}
            if tipo == "Pesagem" and refs:
                from pesagem import fmt_pesos
                pares = [(r, p) for r, p in zip(refs, intencao.get("pesos") or []) if p]
                out["payload"]["linha"]["Pesos"] = fmt_pesos(pares)
        out["url_form"] = "/manejo/novo?" + urlencode({
            "prefill": 1, "tipo": tipo, "cabecas": qtd, "produto": produto, "descricao": desc,
            "brincos": ", ".join(r.split(" #")[0] for r in refs), "data": data_iso,
            "perda_de": intencao.get("dono") or ""})
        return out

    # ── Compra / Venda
    if acao in ("compra", "venda"):
        refs, ids = resolver_alvos(intencao.get("alvos") or []) if acao == "venda" else ([], [])
        qtd = intencao.get("qtd") or (len(ids) if ids else None)
        cotas = {m: q for m, q in (intencao.get("cotas") or {}).items()}
        if acao == "venda" and ids and not any(cotas.values()):
            # Sem divisão falada: cada animal vendido conta para o seu dono.
            cotas = {}
            for id_ in ids:
                dono = A.por_id(df, id_)["Dono"]
                cotas[dono] = cotas.get(dono, 0) + 1
        citados = [m for m, q in cotas.items() if q is None]
        if qtd and len(citados) == 1 and not any(q for q in cotas.values() if q):
            cotas[citados[0]] = qtd       # "comprei 3 cabeças pro nilson"
        cotas = {m: int(q) for m, q in cotas.items() if q}
        if not qtd and cotas:
            qtd = sum(cotas.values())
        valor = intencao.get("valor")
        if valor and intencao.get("por_cabeca") and qtd:
            valor = valor * qtd
        nome = "Compra" if acao == "compra" else "Venda"
        out["titulo"] = "🛒 Compra de gado" if acao == "compra" else "🤝 Venda de gado"
        if not qtd:
            out["erros"].append("Quantas cabeças? (ex.: 5 cabeças)")
        if not valor:
            out["erros"].append("Qual o valor? (ex.: por 15 mil)")
        if cotas and qtd and sum(cotas.values()) != qtd:
            out["avisos"].append(f"A divisão ({sum(cotas.values())}) não bate com {qtd} cabeças — "
                                 "o sistema ajusta a diferença.")
        if not cotas and qtd:
            out["avisos"].append("Divisão entre donos não dita — fica em partes iguais.")
        out["campos"] += [["Data", data_br], ["Cabeças", qtd or "—"],
                          ["Valor total", f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if valor else "—"]]
        if qtd and valor:
            out["campos"].append(["Por cabeça", f"R$ {valor / qtd:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")])
        if acao == "venda" and intencao.get("arroba"):
            out["campos"].append(["Arroba", f"R$ {intencao['arroba']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")])
        out["campos"].append(["Divisão", ", ".join(f"{NOMES_MEMBROS[m]}: {q}" for m, q in cotas.items()) or "Partes iguais"])
        if refs:
            out["campos"].append(["Brincos", ", ".join(r.split(" #")[0] for r in refs)])
            if qtd and len(refs) != qtd:
                out["avisos"].append(f"{len(refs)} brinco(s) para {qtd} cabeça(s) — as outras ficam sem brinco.")
            out["avisos"].append("Os animais com brinco saem como Vendidos (o brinco fica livre).")
        form = {"data": data_iso, "cabecas": qtd or "", "valor": f"{valor:.2f}".replace(".", ",") if valor else "",
                **{f"qtd_{m.lower()}": cotas.get(m, 0) for m in MEMBROS},
                "descricao": intencao.get("descricao") or ""}
        if acao == "venda":
            form["valor_arroba"] = f"{intencao['arroba']:.2f}".replace(".", ",") if intencao.get("arroba") else ""
            form["brincos"] = "; ".join(refs)
        else:
            form["membro"] = membro
            if intencao.get("quer_brinco"):
                form["brincar"] = "1"
                out["avisos"].append("Depois de salvar, abre a tela para pôr brinco nos animais desta compra.")
        out["payload"] = {"acao": acao, "form": form}
        url_form = {k: v for k, v in form.items() if k != "brincos"}
        if acao == "venda" and refs:
            url_form["brincos"] = ", ".join(r.split(" #")[0] for r in refs)
        out["url_form"] = ("/compras/nova?" if acao == "compra" else "/vendas/nova?") + \
            urlencode({"prefill": 1, **url_form})
        return out

    # ── Gasto
    if acao == "gasto":
        valor = intencao.get("valor")
        out["titulo"] = "💸 Gasto"
        if not valor:
            out["erros"].append("Qual o valor? (ex.: 350 reais)")
        out["campos"] += [["Data", data_br], ["Tipo", intencao["tipo"]],
                          ["Valor", f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if valor else "—"]]
        if intencao.get("produto"):
            out["campos"].append(["Produto", intencao["produto"]])
            out["campos"].append(["Sacos", intencao.get("sacos") or "—"])
        out["campos"].append(["Descrição", intencao.get("descricao")])
        form = {"data": data_iso, "tipo": intencao["tipo"], "valor": f"{valor:.2f}".replace(".", ",") if valor else "",
                "descricao": intencao.get("descricao") or "", "cabecas": ctx.get("estoque") or "",
                "membro": membro, "produto": intencao.get("produto") or "",
                "qtd_sacos": intencao.get("sacos") or ""}
        out["payload"] = {"acao": "gasto", "form": form}
        out["url_form"] = "/gastos/novo?" + urlencode({"prefill": 1, **form})
        return out

    out["erros"].append("Comando não suportado.")
    return out


def pode_salvar(resp: dict) -> bool:
    return bool(resp.get("payload")) and not resp["erros"] and not resp["perguntas"] \
        and not resp.get("so_formulario")
