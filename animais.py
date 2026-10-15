#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
animais.py — cadastro individual do rebanho por brinco (v4.3)

Regras do brinco (decididas pela família):
  • cada dono tem a sua cor (config.CORES_BRINCO_PADRAO, ajustável em sitio_config);
  • numeração 01..99 por cor; depois do 99 recomeça do 01 — o animal antigo com
    aquele número já saiu faz tempo;
  • o brinco vai nos nascimentos e nos animais comprados quando chegam ao sítio.

Como o brinco se repete (entre cores e ao reaproveitar), "cor + nº" só identifica
um animal entre os VIVOS. O histórico liga ao ID interno (A0001…), gravado junto
na coluna "Brincos" de Manejo/Vendas no formato "Amarelo 21 #A0003; Azul 12 #A0007"
— legível na planilha e sem ambiguidade para o sistema.

O cadastro em si NÃO mexe nas finanças: a cabeça já entrou pela compra ou pelo
nascimento. Só o atalho "Nascimento" grava também a linha de Manejo (que é o que
faz a cabeça entrar no estoque), e a baixa por morte grava a Morte/Perda.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta

import pandas as pd

import db
from config import (
    COLUNAS_ANIMAIS, COLUNAS_MANEJO, CORES_BRINCO_PADRAO, CORES_BRINCO,
    BRINCO_MAX, CATEGORIAS_ANIMAL, MEMBROS,
)

ABA = "Animais"
_RE_ID = re.compile(r"#(A\d+)")

# Cor do chip na tela (o nome da cor é o que vale; isto é só visual).
COR_HEX = {
    "Amarelo": "#f4c430", "Azul": "#2f6fd6", "Vermelho": "#d33a2c", "Verde": "#2e9e48",
    "Laranja": "#f08a24", "Branco": "#f4f4f4", "Rosa": "#e86aa6", "Roxo": "#7d4bc2",
    "Preto": "#222222", "Cinza": "#8a8a8a",
}


# ── Cores por dono ────────────────────────────────────────────────────────────

def _sitio_config_path() -> str:
    return os.path.join(db.DATA_DIR, "sitio_config.json")


def cores_brinco() -> dict:
    """{membro: cor} efetivo — padrão do config com o ajuste salvo por cima."""
    cores = dict(CORES_BRINCO_PADRAO)
    try:
        with open(_sitio_config_path(), encoding="utf-8") as f:
            salvas = (json.load(f) or {}).get("cores_brinco") or {}
        for m in MEMBROS:
            if salvas.get(m) in CORES_BRINCO:
                cores[m] = salvas[m]
    except (OSError, ValueError):
        pass
    return cores


def salvar_cores_brinco(cores: dict):
    caminho = _sitio_config_path()
    cfg = {}
    if os.path.exists(caminho):
        try:
            with open(caminho, encoding="utf-8") as f:
                cfg = json.load(f) or {}
        except (OSError, ValueError):
            cfg = {}
    cfg["cores_brinco"] = {m: c for m, c in cores.items() if m in MEMBROS and c in CORES_BRINCO}
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def dono_da_cor(cor: str | None) -> str | None:
    if not cor:
        return None
    for m, c in cores_brinco().items():
        if c == cor:
            return m
    return None


# ── Leitura / gravação ────────────────────────────────────────────────────────

def _data(v):
    """Data do formulário (aaaa-mm-dd), da planilha (dd/mm/aaaa) ou Timestamp."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return pd.NaT
    iso = isinstance(v, str) and re.match(r"\d{4}-\d{2}-\d{2}", v.strip())
    t = pd.to_datetime(v, dayfirst=not iso, errors="coerce")
    return t if pd.notna(t) else pd.NaT


def carregar() -> pd.DataFrame:
    """Aba Animais com tipos arrumados (nº inteiro, datas, textos sem NaN)."""
    df = db.carregar_aba(ABA)
    for c in COLUNAS_ANIMAIS:
        if c not in df.columns:
            df[c] = None
    df = df[COLUNAS_ANIMAIS + [c for c in df.columns if c not in COLUNAS_ANIMAIS]].copy()
    df["Brinco Nº"] = pd.to_numeric(df["Brinco Nº"], errors="coerce").astype("Int64")
    for c in ("Nascimento", "Entrada", "Data Saída"):
        df[c] = pd.to_datetime(df[c], dayfirst=True, format="mixed", errors="coerce")
    for c in ("ID", "Brinco Cor", "Dono", "Categoria", "Sexo", "Raça", "Pelagem", "Sinais",
              "Origem", "Ref Compra", "Mãe", "Status", "Observações", "Registrado Por"):
        df[c] = df[c].apply(lambda v: "" if v is None or (isinstance(v, float) and pd.isna(v))
                            else str(v).strip()).astype(object)
    df.loc[df["Status"] == "", "Status"] = "Vivo"
    return evoluir_categorias(df.reset_index(drop=True))


# Categoria → (idade em meses, próxima). Só sobe, nunca desce; Touro/Novilho são manuais.
EVOLUCAO_IDADE = {"Bezerra": (12, "Novilha"), "Bezerro": (12, "Garrote"), "Garrote": (24, "Boi")}


def evoluir_categorias(df: pd.DataFrame, hoje=None) -> pd.DataFrame:
    """Atualiza a categoria dos vivos: bezerra/bezerro → novilha/garrote aos 12 meses,
    garrote → boi aos 24 (precisa da data de nascimento); fêmea com cria cadastrada
    (alguém tem ela como "Mãe") → vaca. Calculado na leitura, então toda tela vê a
    categoria de hoje; a planilha recebe o valor novo na próxima gravação da aba."""
    if df.empty:
        return df
    hoje = pd.Timestamp(hoje or datetime.now()).normalize()
    maes = set()
    for ref in df["Mãe"]:
        maes |= set(ids_de(ref))
    for i in df.index[df["Status"] == "Vivo"]:
        cat, nasc = df.at[i, "Categoria"], df.at[i, "Nascimento"]
        if pd.notna(nasc):
            while cat in EVOLUCAO_IDADE and nasc + pd.DateOffset(months=EVOLUCAO_IDADE[cat][0]) <= hoje:
                cat = EVOLUCAO_IDADE[cat][1]
        if cat in ("Bezerra", "Novilha") and df.at[i, "ID"] in maes:
            cat = "Vaca"
        df.at[i, "Categoria"] = cat
    return df


def _gravar(df: pd.DataFrame):
    """Reescreve a aba. Int64/NA viram int/None (o openpyxl não aceita pd.NA)."""
    out = df.copy().astype(object)
    out = out.where(pd.notna(out), None)
    out["Brinco Nº"] = [int(v) if v is not None else None for v in out["Brinco Nº"]]
    db.reescrever_aba(ABA, out)


def vivos(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["Status"] == "Vivo"] if not df.empty else df


def por_id(df: pd.DataFrame, id_: str):
    m = df[df["ID"] == id_]
    return None if m.empty else m.iloc[0]


# ── Brinco ────────────────────────────────────────────────────────────────────

def fmt_brinco(cor, num) -> str:
    try:
        n = f"{int(num):02d}"
    except (TypeError, ValueError):
        n = "??"
    return f"{cor or '?'} {n}"


def ref(row) -> str:
    """'Amarelo 21 #A0003' — como o animal aparece nas colunas "Brincos"/"Mãe"."""
    return f"{fmt_brinco(row['Brinco Cor'], row['Brinco Nº'])} #{row['ID']}"


def ids_de(texto) -> list[str]:
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return []
    return _RE_ID.findall(str(texto))


def brinco_ocupado(df: pd.DataFrame, cor: str, num: int, exceto_id: str | None = None):
    """Animal VIVO que já usa essa cor+nº (ou None)."""
    if df.empty:
        return None
    v = vivos(df)
    m = v[(v["Brinco Cor"] == cor) & (v["Brinco Nº"] == int(num))]
    if exceto_id:
        m = m[m["ID"] != exceto_id]
    return None if m.empty else m.iloc[0]


def proximo_numero(df: pd.DataFrame, cor: str, reservados=()) -> int | None:
    """Próximo nº livre da cor, continuando de onde o último brinco dessa cor parou
    e voltando ao 01 depois do 99. Pula os que ainda estão em animais vivos."""
    usados = set(reservados)
    ultimo = 0
    if not df.empty:
        da_cor = df[(df["Brinco Cor"] == cor) & df["Brinco Nº"].notna()]
        usados |= set(int(n) for n in vivos(da_cor)["Brinco Nº"])
        if not da_cor.empty:
            # "Último colocado" = o cadastrado por último (ordem da planilha).
            ultimo = int(da_cor["Brinco Nº"].iloc[-1])
    for passo in range(1, BRINCO_MAX + 1):
        n = (ultimo + passo - 1) % BRINCO_MAX + 1
        if n not in usados:
            return n
    return None   # todos os 99 em uso


def novo_id(df: pd.DataFrame, reservados=()) -> str:
    nums = [int(m.group(1)) for v in list(df["ID"]) + list(reservados)
            if (m := re.fullmatch(r"A(\d+)", str(v)))]
    return f"A{(max(nums) + 1 if nums else 1):04d}"


# ── Cadastro ──────────────────────────────────────────────────────────────────

def _txt(v) -> str:
    return str(v or "").strip()


def normalizar(dados: dict, df: pd.DataFrame, reservados_num=None, exceto_id=None):
    """Completa e valida um cadastro. Devolve (registro, avisos); levanta ValueError
    com mensagem para a tela quando não dá para gravar.

    - sem cor → cor do dono; sem dono → dono dono da cor;
    - sem nº → próximo livre da cor;
    - sexo vem da categoria (o formulário não pergunta mais).
    """
    reservados_num = reservados_num or {}
    avisos = []
    cores = cores_brinco()
    dono = _txt(dados.get("Dono"))
    cor = _txt(dados.get("Brinco Cor"))
    if dono and dono not in MEMBROS:
        raise ValueError(f"Dono inválido: {dono}")
    if cor and cor not in CORES_BRINCO:
        raise ValueError(f"Cor de brinco inválida: {cor}")
    if not cor and dono:
        cor = cores.get(dono, "")
    if not dono and cor:
        dono = dono_da_cor(cor) or ""
    if not dono:
        raise ValueError("Informe o dono (ou a cor do brinco).")
    if not cor:
        raise ValueError("Informe a cor do brinco.")
    if cores.get(dono) and cores[dono] != cor:
        avisos.append(f"Brinco {cor} mas o dono é {dono} (a cor dele é {cores[dono]}).")

    num = dados.get("Brinco Nº")
    num = int(num) if str(num or "").strip().isdigit() else None
    if num is None:
        num = proximo_numero(df, cor, reservados_num.get(cor, ()))
        if num is None:
            raise ValueError(f"Todos os brincos {cor} de 01 a {BRINCO_MAX} estão em uso.")
    if not 1 <= num <= BRINCO_MAX:
        raise ValueError(f"O número do brinco vai de 01 a {BRINCO_MAX}.")
    if num in reservados_num.get(cor, ()):
        raise ValueError(f"Brinco {fmt_brinco(cor, num)} repetido nesta lista.")
    ocupado = brinco_ocupado(df, cor, num, exceto_id=exceto_id)
    if ocupado is not None:
        raise ValueError(f"O brinco {fmt_brinco(cor, num)} já está num animal vivo "
                         f"({ocupado['Categoria'] or 'animal'} #{ocupado['ID']}). "
                         "Dê baixa nele antes ou use outro número.")

    categoria = _txt(dados.get("Categoria"))
    if categoria and categoria not in CATEGORIAS_ANIMAL:
        raise ValueError(f"Categoria inválida: {categoria}")
    # A categoria manda no sexo (Novilha é sempre fêmea); o informado só vale sem categoria.
    sexo = CATEGORIAS_ANIMAL.get(categoria) or _txt(dados.get("Sexo"))

    reg = {c: dados.get(c, "") for c in COLUNAS_ANIMAIS}
    reg.update({"Brinco Cor": cor, "Brinco Nº": num, "Dono": dono,
                "Categoria": categoria, "Sexo": sexo})
    for c in ("Raça", "Pelagem", "Sinais", "Origem", "Ref Compra", "Mãe",
              "Observações", "Registrado Por"):
        reg[c] = _txt(reg.get(c))
    reg["Status"] = _txt(reg.get("Status")) or "Vivo"
    reg["Origem"] = reg["Origem"] or "Já no sítio"
    for c in ("Nascimento", "Entrada", "Data Saída"):
        reg[c] = _data(reg.get(c))
    if pd.isna(reg["Entrada"]) and reg["Status"] == "Vivo":
        reg["Entrada"] = pd.Timestamp(datetime.now().date())
    return reg, avisos


def _linha_manejo(data, tipo, qtd, desc, responsavel, perda_de="", produto="",
                  nasc_de="", brincos="") -> list:
    vals = {"Data": data, "Tipo": tipo, "Qtd Cabeças": qtd, "Descrição": desc,
            "Responsável": responsavel, "Perda De": perda_de, "Produto": produto,
            "Nascimento De": nasc_de, "Brincos": brincos}
    return [vals.get(c, "") for c in COLUNAS_MANEJO]


def _celula(v):
    """Valor de um registro pronto para salvar_linha (NaT → vazio)."""
    if isinstance(v, pd.Timestamp):
        return v if pd.notna(v) else None
    if v is pd.NaT:
        return None
    return v


def cadastrar(lista: list[dict], registrado_por: str = "", responsavel: str = "") -> list[dict]:
    """Grava 1+ animais (validando todos antes de gravar qualquer um).

    Origem "Nascimento" também grava a linha de Nascimento no Manejo (com
    "Nascimento De" = dono) — é ela que põe a cabeça no estoque. Compra e
    "Já no sítio" não mexem em mais nada: a cabeça já está contada.
    Devolve os registros gravados (com ID) e seus avisos.
    """
    df = carregar()
    reservados_num: dict[str, set] = {}
    reservados_id: list[str] = []
    prontos = []
    for dados in lista:
        reg, avisos = normalizar(dados, df, reservados_num)
        reg["ID"] = novo_id(df, reservados_id)
        reg["Registrado Por"] = reg["Registrado Por"] or registrado_por
        reservados_id.append(reg["ID"])
        reservados_num.setdefault(reg["Brinco Cor"], set()).add(reg["Brinco Nº"])
        prontos.append((reg, avisos))

    for reg, _ in prontos:
        db.salvar_linha(ABA, [_celula(reg[c]) for c in COLUNAS_ANIMAIS])
        if reg["Origem"] == "Nascimento":
            data = reg["Nascimento"] if pd.notna(reg["Nascimento"]) else reg["Entrada"]
            desc = " ".join(x for x in (reg["Categoria"], reg["Raça"], reg["Pelagem"]) if x)
            if reg["Mãe"]:
                desc += " — mãe " + _RE_ID.sub("", reg["Mãe"]).strip()
            db.salvar_linha("Manejo", _linha_manejo(
                data, "Nascimento", 1, desc.strip(), responsavel or registrado_por,
                nasc_de=reg["Dono"], brincos=ref(reg)))
    return [dict(reg, avisos=av) for reg, av in prontos]


def atualizar(id_: str, dados: dict):
    """Edita o cadastro (não mexe em Manejo/Vendas já gravados)."""
    df = carregar()
    idx = df.index[df["ID"] == id_]
    if len(idx) == 0:
        raise ValueError("Animal não encontrado.")
    i = idx[0]
    base = df.loc[i].to_dict()
    base.update(dados)
    if base.get("Status") != "Vivo":
        # Animal que já saiu não disputa brinco com os vivos.
        reg = {**base, "Brinco Nº": int(base["Brinco Nº"]) if pd.notna(base["Brinco Nº"]) else None}
        avisos = []
        for c in ("Nascimento", "Entrada", "Data Saída"):
            reg[c] = _data(reg.get(c))
    else:
        reg, avisos = normalizar(base, df, exceto_id=id_)
    reg["ID"] = id_
    for c in COLUNAS_ANIMAIS:
        if c in ("Brinco Nº",):
            df.at[i, c] = reg[c]
        else:
            df.at[i, c] = reg.get(c, "")
    _gravar(df)
    return avisos


# ── Baixa (venda / morte) ─────────────────────────────────────────────────────

def dar_baixa(ids: list[str], status: str, data=None, responsavel: str = "",
              registrar_morte: bool = True, motivo: str = "") -> list[str]:
    """Marca os animais como Vendido/Morto (libera o brinco para reaproveitar).

    Morte: grava também a Morte/Perda no Manejo — uma linha por dono, com
    "Perda De" = dono — para o estoque e as perdas financeiras baterem.
    Venda: só o status; o valor da venda é registrado em Nova Venda (aba Vendas),
    que é onde a cabeça sai do estoque.
    """
    if status not in ("Vendido", "Morto"):
        raise ValueError("Status de baixa inválido.")
    df = carregar()
    data_ts = _data(data) if data else pd.Timestamp(datetime.now().date())
    if pd.isna(data_ts):
        data_ts = pd.Timestamp(datetime.now().date())
    feitos, por_dono = [], {}
    for id_ in ids:
        idx = df.index[df["ID"] == id_]
        if len(idx) == 0:
            continue
        i = idx[0]
        if df.at[i, "Status"] != "Vivo":
            continue
        df.at[i, "Status"] = status
        df.at[i, "Data Saída"] = data_ts
        if motivo:
            obs = df.at[i, "Observações"]
            df.at[i, "Observações"] = f"{obs} | {motivo}".strip(" |") if obs else motivo
        feitos.append(id_)
        por_dono.setdefault(df.at[i, "Dono"], []).append(ref(df.loc[i]))
    if not feitos:
        return []
    _gravar(df)
    if status == "Morto" and registrar_morte:
        for dono, refs in por_dono.items():
            db.salvar_linha("Manejo", _linha_manejo(
                data_ts, "Morte/Perda", len(refs), motivo or "Baixa pelo cadastro de animais",
                responsavel, perda_de=dono, brincos="; ".join(refs)))
    return feitos


def baixa_por_refs(texto_brincos: str, status: str, data=None) -> list[str]:
    """Usado pela venda: marca como vendidos os IDs citados na coluna Brincos."""
    ids = ids_de(texto_brincos)
    return dar_baixa(ids, status, data) if ids else []


# ── Resolver brinco falado/digitado → animal ──────────────────────────────────

def resolver(df: pd.DataFrame, num: int, cor: str | None = None,
             categoria: str | None = None, dono: str | None = None) -> pd.DataFrame:
    """Animais VIVOS que batem com o brinco. Sem cor, usa a cor do dono (se dito);
    com mais de um, a categoria ajuda a desempatar."""
    v = vivos(df)
    if v.empty:
        return v
    if not cor and dono:
        cor = cores_brinco().get(dono)
    m = v[v["Brinco Nº"] == int(num)]
    if cor:
        m = m[m["Brinco Cor"] == cor]
    if len(m) > 1 and categoria:
        mc = m[m["Categoria"] == categoria]
        if not mc.empty:
            m = mc
    return m


def resolver_texto(texto: str, df: pd.DataFrame | None = None):
    """'amarelo 21, azul 12, 35' → (refs resolvidas, erros). Usado nos formulários
    (Manejo/Venda) para o campo "Brincos". Também aceita refs com #ID."""
    df = carregar() if df is None else df
    refs, erros = [], []
    if not str(texto or "").strip():
        return refs, erros
    from comando_voz import extrair_brincos
    vistos = set()
    for id_ in ids_de(texto):
        a = por_id(df, id_)
        if a is None:
            erros.append(f"#{id_} não existe.")
        elif id_ not in vistos:
            vistos.add(id_)
            refs.append(ref(a))
    sem_ids = _RE_ID.sub(" ", str(texto))
    for alvo in extrair_brincos(sem_ids):
        m = resolver(df, alvo["num"], alvo.get("cor"))
        pedido = fmt_brinco(alvo.get("cor") or "", alvo["num"]).strip()
        if m.empty:
            erros.append(f"Nenhum animal vivo com brinco {pedido}.")
        elif len(m) > 1:
            opcoes = ", ".join(fmt_brinco(r["Brinco Cor"], r["Brinco Nº"]) for _, r in m.iterrows())
            erros.append(f"Brinco {alvo['num']:02d} sem cor é ambíguo ({opcoes}) — diga a cor.")
        else:
            a = m.iloc[0]
            if a["ID"] not in vistos:
                vistos.add(a["ID"])
                refs.append(ref(a))
    return refs, erros


# ── Consultas para as telas ───────────────────────────────────────────────────

def idade_txt(nasc, hoje=None) -> str:
    if nasc is None or pd.isna(nasc):
        return ""
    hoje = hoje or datetime.now()
    dias = (pd.Timestamp(hoje) - pd.Timestamp(nasc)).days
    if dias < 0:
        return ""
    if dias < 60:
        return f"{dias} dias"
    meses = dias // 30
    if meses < 24:
        return f"{meses} meses"
    return f"{meses // 12} anos"


def historico(id_: str, df_man: pd.DataFrame, df_vend: pd.DataFrame) -> list[dict]:
    """Manejos e vendas que citam o animal (pelo #ID), do mais recente ao mais antigo."""
    itens = []
    marca = f"#{id_}"
    for aba, df in (("Manejo", df_man), ("Vendas", df_vend)):
        if df is None or df.empty or "Brincos" not in df.columns:
            continue
        m = df[df["Brincos"].astype(str).str.contains(marca, regex=False, na=False)]
        for _, r in m.iterrows():
            if aba == "Manejo":
                det = " · ".join(str(x) for x in (r.get("Produto"), r.get("Descrição"))
                                 if x is not None and not (isinstance(x, float) and pd.isna(x)) and str(x).strip())
                itens.append({"data": r.get("Data"), "tipo": r.get("Tipo") or "Manejo", "detalhe": det})
            else:
                itens.append({"data": r.get("Data"), "tipo": "Venda",
                              "detalhe": f"{int(r.get('Qtd Cabeças') or 0)} cab. no lote"})
    itens.sort(key=lambda x: x["data"] if pd.notna(x["data"]) else pd.Timestamp.min, reverse=True)
    return itens


def janela_brucelose(df: pd.DataFrame, df_man: pd.DataFrame, hoje=None) -> list[dict]:
    """Fêmeas vivas com nascimento conhecido, sem Vacina Brucelose registrada nelas,
    na janela de 3 a 8 meses (ou entrando nela nos próximos 30 dias)."""
    hoje = pd.Timestamp(hoje or datetime.now())
    if df.empty:
        return []
    vacinadas = set()
    if df_man is not None and not df_man.empty and "Brincos" in df_man.columns:
        for _, r in df_man[df_man["Tipo"] == "Vacina Brucelose"].iterrows():
            vacinadas |= set(ids_de(r.get("Brincos")))
    out = []
    for _, a in vivos(df).iterrows():
        if a["Sexo"] != "F" or pd.isna(a["Nascimento"]) or a["ID"] in vacinadas:
            continue
        dias = (hoje - a["Nascimento"]).days
        if 90 <= dias <= 240:
            out.append({"animal": a, "situacao": "na janela",
                        "msg": f"está com {dias // 30} meses — vacinar até "
                               f"{(a['Nascimento'] + timedelta(days=240)).strftime('%d/%m/%Y')}"})
        elif 60 <= dias < 90:
            out.append({"animal": a, "situacao": "chegando",
                        "msg": f"entra na janela em {90 - dias} dias"})
    return out


def conferencia(df: pd.DataFrame, estoque_por_membro: dict) -> list[dict]:
    """Vivos com brinco × estoque do sistema, por dono — mostra quantos faltam
    brincar (ou se há mais animais cadastrados do que o estoque diz)."""
    v = vivos(df)
    out = []
    for m in MEMBROS:
        com_brinco = int((v["Dono"] == m).sum()) if not v.empty else 0
        estoque = int(estoque_por_membro.get(m, 0) or 0)
        out.append({"membro": m, "com_brinco": com_brinco, "estoque": estoque,
                    "sem_brinco": max(estoque - com_brinco, 0),
                    "sobrando": max(com_brinco - estoque, 0)})
    return out
