#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doencas_carencia.py — Histórico de doenças, tratamentos e períodos de carência (v5.10 Onda 2)

Registra doenças, medicamentos, datas e períodos de carência.
Valida se animal está em carência antes de venda de leite/carne.
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import db


# Períodos de carência padrão (dias) por medicamento
PERIODOS_CARENCIA_PADRAO = {
    # Antibióticos
    "Penicilina": {"leite": 48, "carne": 8},
    "Amoxicilina": {"leite": 48, "carne": 15},
    "Tetraciclina": {"leite": 72, "carne": 28},
    "Gentamicina": {"leite": 72, "carne": 28},
    "Cefalosporina": {"leite": 48, "carne": 14},

    # Anti-inflamatórios
    "Meloxicam": {"leite": 0, "carne": 15},
    "Fenilbutazona": {"leite": 0, "carne": 28},
    "Dexametasona": {"leite": 0, "carne": 7},

    # Antiparasitários
    "Ivermectina": {"leite": 0, "carne": 35},
    "Albendazol": {"leite": 0, "carne": 28},
    "Doramectina": {"leite": 0, "carne": 49},

    # Outros
    "Sulfadiazina": {"leite": 60, "carne": 14},
    "Enrofloxacina": {"leite": 0, "carne": 28},
}


def carregar_tratamentos(vaca_id: str = None) -> pd.DataFrame:
    """Carrega histórico de tratamentos da aba 'Tratamentos'."""
    try:
        df_tratamentos = db.carregar_aba("Tratamentos")
        if df_tratamentos.empty:
            return pd.DataFrame()

        # Converte Data para datetime
        df_tratamentos['Data'] = pd.to_datetime(
            df_tratamentos.get('Data', []),
            format='%d/%m/%Y',
            errors='coerce'
        )

        if vaca_id:
            df_tratamentos = df_tratamentos[
                (df_tratamentos.get('ID Animal', '').astype(str) == str(vaca_id)) |
                (df_tratamentos.get('Brinco', '').astype(str) == str(vaca_id))
            ]

        return df_tratamentos.sort_values('Data', ascending=False)
    except Exception as e:
        print(f"Erro ao carregar tratamentos: {e}")
        return pd.DataFrame()


def obter_status_carencia(vaca_id: str, tipo_produto: str = "leite") -> Dict:
    """
    Verifica se animal está em período de carência.
    tipo_produto: 'leite' ou 'carne'
    Retorna: {"em_carencia": bool, "dias_restantes": int, "medicamento": str, "data_liberacao": date}
    """
    df_tratamentos = carregar_tratamentos(vaca_id)

    if df_tratamentos.empty:
        return {
            "em_carencia": False,
            "dias_restantes": 0,
            "medicamento": None,
            "data_liberacao": None
        }

    hoje = datetime.now()
    tratamento_ativo = None

    for _, row in df_tratamentos.iterrows():
        data_tratamento = row.get('Data')
        medicamento = row.get('Medicamento', '').strip()

        if pd.isna(data_tratamento):
            continue

        # Obtém período de carência
        carencia_dias = _obter_carencia(medicamento, tipo_produto)
        data_liberacao = data_tratamento + timedelta(days=carencia_dias)

        if data_liberacao > hoje:
            dias_restantes = (data_liberacao - hoje).days
            tratamento_ativo = {
                "em_carencia": True,
                "dias_restantes": dias_restantes,
                "medicamento": medicamento,
                "data_liberacao": data_liberacao,
                "data_tratamento": data_tratamento,
                "carencia_dias": carencia_dias
            }
            break  # Pega primeiro tratamento ativo

    if not tratamento_ativo:
        return {
            "em_carencia": False,
            "dias_restantes": 0,
            "medicamento": None,
            "data_liberacao": None
        }

    return tratamento_ativo


def validar_venda(vaca_id: str, tipo_produto: str = "leite") -> Tuple[bool, str]:
    """
    Valida se animal pode ser vendido (leite ou carne).
    Retorna: (pode_vender: bool, motivo: str)
    """
    status = obter_status_carencia(vaca_id, tipo_produto)

    if status['em_carencia']:
        dias = status['dias_restantes']
        med = status['medicamento']
        data = status['data_liberacao'].strftime('%d/%m/%Y')
        motivo = f"⚠️ {med} — em carência por {dias} dias (libera em {data})"
        return False, motivo

    return True, "✅ Liberado para venda"


def _obter_carencia(medicamento: str, tipo_produto: str = "leite") -> int:
    """Obtém dias de carência para um medicamento."""
    medicamento = medicamento.strip().title()

    # Tenta match exato
    if medicamento in PERIODOS_CARENCIA_PADRAO:
        return PERIODOS_CARENCIA_PADRAO[medicamento][tipo_produto]

    # Tenta match parcial (contém)
    for med_config, periodos in PERIODOS_CARENCIA_PADRAO.items():
        if med_config.lower() in medicamento.lower() or medicamento.lower() in med_config.lower():
            return periodos[tipo_produto]

    # Padrão: 48h leite, 28 dias carne
    return 48 if tipo_produto == "leite" else 28


def gerar_alerta_carencia(vaca_id: str) -> Dict | None:
    """Gera alerta se animal está em carência."""
    status = obter_status_carencia(vaca_id, "leite")

    if not status['em_carencia']:
        return None

    dias = status['dias_restantes']
    tipo_alerta = "urgente" if dias <= 3 else "aviso"

    return {
        "tipo": tipo_alerta,
        "animal_id": vaca_id,
        "medicamento": status['medicamento'],
        "dias_restantes": dias,
        "data_liberacao": status['data_liberacao'],
        "mensagem": f"{status['medicamento']} — libera em {dias} dias"
    }


def registro_doenca(vaca_id: str, doenca: str, data: str, tratamento: str,
                   medicamento: str, observacoes: str = "") -> bool:
    """
    Registra uma doença no histórico do animal.
    vaca_id: ID do animal
    doenca: tipo de doença (Mastite, Cólica, Infecção, etc)
    data: data do tratamento (dd/mm/aaaa)
    tratamento: descrição do tratamento
    medicamento: nome do medicamento (para calcular carência)
    observacoes: notas adicionais
    """
    try:
        # Salva na aba Tratamentos
        from extensions import salvar_linha

        salvar_linha("Tratamentos", [
            vaca_id,
            data,
            doenca,
            tratamento,
            medicamento,
            observacoes,
            "Não",  # Resolvido: Sim/Não
            None    # Data de Resolução
        ])
        return True
    except Exception as e:
        print(f"Erro ao registrar doença: {e}")
        return False


def historico_animal(vaca_id: str, dias: int = 365) -> List[Dict]:
    """Retorna histórico de doenças e tratamentos do animal."""
    df = carregar_tratamentos(vaca_id)

    if df.empty:
        return []

    # Filtra últimos N dias
    data_limite = datetime.now() - timedelta(days=dias)
    df_recente = df[df['Data'] >= data_limite]

    historico = []
    for _, row in df_recente.iterrows():
        status_resolucao = "✓" if row.get('Resolvido') == 'Sim' else "⏳"
        historico.append({
            "data": row.get('Data'),
            "doenca": row.get('Tipo Doença', 'Tratamento'),
            "tratamento": row.get('Tratamento', ''),
            "medicamento": row.get('Medicamento', ''),
            "observacoes": row.get('Observações', ''),
            "resolvido": status_resolucao,
            "carencia": _obter_carencia(row.get('Medicamento', ''), 'leite')
        })

    return historico


if __name__ == '__main__':
    # Teste
    print("=== Teste de Carência ===")
    status = obter_status_carencia("A0001", "leite")
    print(f"Animal A0001: {status}")
