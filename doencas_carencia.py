from agora import agora
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doencas_carencia.py — Histórico de doenças, tratamentos e períodos de carência.

Fonte ÚNICA da carência (v5.16): lê as três abas que registram medicação
(`Tratamentos`, `Medicações` e `Leite Tratamentos`) e responde a mesma coisa
para a venda, o painel de alertas, a ficha do animal e o dashboard. Antes cada
tela lia uma aba diferente — o mesmo animal podia estar em carência numa e
liberado em outra.
"""
import re
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

import pandas as pd

from db import carregar_aba


# Períodos de carência padrão em DIAS por medicamento.
# Os valores de leite eram HORAS gravadas na coluna de dias (Penicilina "48"
# virava 48 dias de descarte). Convertidos para dias: 48 h = 2, 72 h = 3.
PERIODOS_CARENCIA_PADRAO = {
    # Antibióticos
    "Penicilina": {"leite": 2, "carne": 8},
    "Amoxicilina": {"leite": 2, "carne": 15},
    "Tetraciclina": {"leite": 3, "carne": 28},
    "Gentamicina": {"leite": 3, "carne": 28},
    "Cefalosporina": {"leite": 2, "carne": 14},
    "Ceftiofur": {"leite": 3, "carne": 4},
    "Enrofloxacina": {"leite": 0, "carne": 28},
    "Sulfadiazina": {"leite": 3, "carne": 14},   # 60 h

    # Anti-inflamatórios
    "Meloxicam": {"leite": 0, "carne": 15},
    "Fenilbutazona": {"leite": 0, "carne": 28},
    "Dexametasona": {"leite": 0, "carne": 7},

    # Antiparasitários
    "Ivermectina": {"leite": 0, "carne": 35},
    "Albendazol": {"leite": 0, "carne": 28},
    "Doramectina": {"leite": 0, "carne": 49},
}

# Remédio fora da tabela: prazo conservador e AVISADO na tela (não finge que
# sabe a bula). Antes era 48 dias em silêncio — prejuízo por engano.
CARENCIA_DESCONHECIDA = {"leite": 7, "carne": 28}

_RE_ID = re.compile(r"#(A\d+)")

_SEM_CARENCIA = {
    "em_carencia": False, "dias_restantes": 0, "medicamento": None,
    "data_liberacao": None, "data_tratamento": None, "carencia_dias": 0,
    "carencia_conhecida": True, "brinco": "", "descricao": "",
}


def _hoje() -> date:
    """Hoje no fuso de Brasília (o servidor de produção roda em UTC)."""
    try:
        from extensions import _agora
        return _agora().date()
    except Exception:
        return agora().date()


def _data_linha(valor) -> date | None:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    ts = pd.to_datetime(valor, dayfirst=True, errors="coerce")
    return None if pd.isna(ts) else ts.date()


def _dias_informados(valor) -> int | None:
    """Dias digitados na própria linha (Medicações / Leite Tratamentos)."""
    try:
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            return None
        n = float(str(valor).replace(",", ".").strip())
        return int(n) if n >= 0 else None
    except (TypeError, ValueError):
        return None


def _obter_carencia(medicamento: str, tipo_produto: str = "leite") -> int | None:
    """Dias de carência da tabela; None quando o remédio não está cadastrado."""
    nome = _texto(medicamento).title()
    if not nome:
        return None
    if nome in PERIODOS_CARENCIA_PADRAO:
        return PERIODOS_CARENCIA_PADRAO[nome][tipo_produto]
    for cadastrado, periodos in PERIODOS_CARENCIA_PADRAO.items():
        if cadastrado.lower() in nome.lower() or nome.lower() in cadastrado.lower():
            return periodos[tipo_produto]
    return None


def _texto(valor) -> str:
    """Célula do Excel → texto limpo (NaN vira "")."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    return str(valor).strip()


def _primeiro(*valores) -> str:
    """Primeiro valor com texto — `a or b` falha quando `a` é NaN (truthy)."""
    for v in valores:
        texto = _texto(v)
        if texto:
            return texto
    return ""


def _linhas_tratamento() -> List[Dict]:
    """Normaliza as três abas de medicação em linhas por animal."""
    linhas = []

    def adicionar(animal_id, brinco, data, medicamento, descricao, dias_informados=None):
        data = _data_linha(data)
        animal_id = _texto(animal_id)
        if data is None or not animal_id:
            return
        tabela_leite = _obter_carencia(medicamento, "leite")
        tabela_carne = _obter_carencia(medicamento, "carne")
        informado = _dias_informados(dias_informados)
        # O prazo digitado na linha nunca encurta o da tabela.
        dias_leite = tabela_leite
        if informado is not None:
            dias_leite = informado if tabela_leite is None else max(informado, tabela_leite)
        linhas.append({
            "animal_id": animal_id,
            "brinco": _texto(brinco) or animal_id,
            "data": data,
            "medicamento": _texto(medicamento),
            "descricao": _texto(descricao),
            "dias_leite": dias_leite,
            "dias_carne": tabela_carne,
            "conhecida_leite": tabela_leite is not None or informado is not None,
            "conhecida_carne": tabela_carne is not None,
        })

    df = carregar_aba("Tratamentos")
    if not df.empty:
        for _, r in df.iterrows():
            adicionar(_primeiro(r.get("ID Animal"), r.get("Brinco")), r.get("Brinco"),
                      r.get("Data"), r.get("Medicamento"),
                      _primeiro(r.get("Tipo Doença"), r.get("Tratamento")))

    df = carregar_aba("Medicações")
    if not df.empty:
        for _, r in df.iterrows():
            texto = _texto(r.get("Brincos"))
            # Uma linha de medicação pode cobrir vários animais ("#A0001; #A0003").
            for animal_id in (_RE_ID.findall(texto) or [texto]):
                adicionar(animal_id, texto, r.get("Data"),
                          _primeiro(r.get("Princípio Ativo"), r.get("Tipo Medicação")),
                          r.get("Motivo"), r.get("Quarentena Leite (dias)"))

    df = carregar_aba("Leite Tratamentos")
    if not df.empty:
        for _, r in df.iterrows():
            adicionar(_primeiro(r.get("Vaca ID"), r.get("Brinco")),
                      _primeiro(r.get("Brinco"), r.get("Vaca ID")), r.get("Data"),
                      _primeiro(r.get("Produto/Serviço"), r.get("Descrição")),
                      r.get("Descrição"), r.get("Período de Carência"))

    return linhas


def _status_de(linhas: List[Dict], tipo_produto: str, referencia: date) -> Dict:
    """Status pela linha de liberação mais distante entre os tratamentos."""
    def liberacao(linha):
        dias = linha["dias_leite"] if tipo_produto == "leite" else linha["dias_carne"]
        conhecida = (linha["conhecida_leite"] if tipo_produto == "leite"
                     else linha["conhecida_carne"])
        if dias is None:
            dias = CARENCIA_DESCONHECIDA[tipo_produto]
        return linha["data"] + timedelta(days=dias), dias, conhecida

    melhor = max(linhas, key=lambda l: liberacao(l)[0])
    fim, dias, conhecida = liberacao(melhor)
    restantes = (fim - referencia).days
    return {
        "em_carencia": restantes > 0,
        "dias_restantes": max(restantes, 0),
        "medicamento": melhor["medicamento"],
        "data_liberacao": fim,
        "data_tratamento": melhor["data"],
        "carencia_dias": dias,
        "carencia_conhecida": conhecida,
        "brinco": melhor["brinco"],
        "descricao": melhor["descricao"],
    }


def status_por_animal(tipo_produto: str = "leite", referencia=None) -> Dict[str, Dict]:
    """Status de carência de cada animal com tratamento registrado nas 3 abas."""
    ref = referencia or _hoje()
    if isinstance(ref, datetime):
        ref = ref.date()
    por_animal: Dict[str, List[Dict]] = {}
    for linha in _linhas_tratamento():
        por_animal.setdefault(linha["animal_id"], []).append(linha)
    return {aid: _status_de(ls, tipo_produto, ref) for aid, ls in por_animal.items()}


def carencias_ativas(tipo_produto: str = "leite", referencia=None,
                     vaca_id: str = None) -> List[Dict]:
    """Animais ainda em carência — fonte única do painel, ficha e dashboard."""
    status = status_por_animal(tipo_produto, referencia)
    if vaca_id is not None:
        status = {k: v for k, v in status.items() if str(k) == str(vaca_id)}
    ativos = [dict(s, animal_id=aid) for aid, s in status.items() if s["em_carencia"]]
    return sorted(ativos, key=lambda s: s["data_liberacao"])


def carregar_tratamentos(vaca_id: str = None) -> pd.DataFrame:
    """Histórico de tratamentos da aba 'Tratamentos' (a oficial da venda)."""
    try:
        df = carregar_aba("Tratamentos")
        if df.empty:
            return pd.DataFrame()
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        if vaca_id:
            df = df[
                (df.get("ID Animal", "").astype(str) == str(vaca_id)) |
                (df.get("Brinco", "").astype(str) == str(vaca_id))
            ]
        return df.sort_values("Data", ascending=False)
    except Exception as e:
        print(f"Erro ao carregar tratamentos: {e}")
        return pd.DataFrame()


def obter_status_carencia(vaca_id: str, tipo_produto: str = "leite",
                          referencia=None) -> Dict:
    """Status do animal: {'em_carencia', 'dias_restantes', 'medicamento', 'data_liberacao'}."""
    status = status_por_animal(tipo_produto, referencia)
    return status.get(str(vaca_id)) or dict(_SEM_CARENCIA)


def validar_venda(vaca_id: str, tipo_produto: str = "leite",
                  status: Dict = None) -> Tuple[bool, str]:
    """Valida se o animal pode ser vendido (leite ou carne).
    `status` evita reler as abas ao validar vários animais da mesma venda."""
    status = status or obter_status_carencia(vaca_id, tipo_produto)

    if status["em_carencia"]:
        dias = status["dias_restantes"]
        med = status["medicamento"]
        data = status["data_liberacao"].strftime("%d/%m/%Y")
        aviso = "" if status["carencia_conhecida"] else " (período não cadastrado — confira a bula)"
        return False, f"⚠️ {med} — em carência por {dias} dias (libera em {data}){aviso}"

    return True, "✅ Liberado para venda"


def gerar_alerta_carencia(vaca_id: str) -> Dict | None:
    """Gera alerta se animal está em carência."""
    status = obter_status_carencia(vaca_id, "leite")

    if not status["em_carencia"]:
        return None

    dias = status["dias_restantes"]
    return {
        "tipo": "urgente" if dias <= 3 else "aviso",
        "animal_id": vaca_id,
        "medicamento": status["medicamento"],
        "dias_restantes": dias,
        "data_liberacao": status["data_liberacao"],
        "mensagem": f"{status['medicamento']} — libera em {dias} dias",
    }


def historico_animal(vaca_id: str, dias: int = 365) -> List[Dict]:
    """Retorna histórico de doenças e tratamentos do animal."""
    df = carregar_tratamentos(vaca_id)

    if df.empty:
        return []

    data_limite = pd.Timestamp(agora()) - timedelta(days=dias)
    df_recente = df[df["Data"] >= data_limite]

    historico = []
    for _, row in df_recente.iterrows():
        historico.append({
            "data": row.get("Data"),
            "doenca": row.get("Tipo Doença", "Tratamento"),
            "tratamento": row.get("Tratamento", ""),
            "medicamento": row.get("Medicamento", ""),
            "observacoes": row.get("Observações", ""),
            "resolvido": "✓" if row.get("Resolvido") == "Sim" else "⏳",
            "carencia": _obter_carencia(row.get("Medicamento", ""), "leite"),
        })

    return historico


if __name__ == "__main__":
    print("=== Teste de Carência ===")
    print(f"Animal A0001: {obter_status_carencia('A0001', 'leite')}")
