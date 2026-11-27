from agora import agora
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
partos_predicao.py — Previsão de partos, secagem e alertas (v5.10 Onda 3)
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
import db
import animais


DIAS_GESTACAO = 283  # Gestação bovina padrão
DIAS_ANTES_SECAGEM = 60  # Começar secagem 60 dias antes do parto
DIAS_ANTES_TOQUE = 35   # Começar toque (ordenha extra) 35 dias antes


def carregar_coberturas(dias: int = 365) -> pd.DataFrame:
    """Carrega histórico de coberturas dos últimos N dias."""
    try:
        df_manejo = db.carregar_aba("Manejo")
        if df_manejo.empty:
            return pd.DataFrame()

        df_manejo['Data'] = pd.to_datetime(df_manejo.get('Data', []),
                                           format='%d/%m/%Y', errors='coerce')

        # Filtra apenas registros de "Cobertura"
        df_coberturas = df_manejo[df_manejo['Tipo'].astype(str).str.lower() == 'cobertura']

        # Últimos N dias
        data_limite = agora() - timedelta(days=dias)
        df_recente = df_coberturas[df_coberturas['Data'] >= data_limite].copy()

        return df_recente.sort_values('Data', ascending=False)
    except Exception as e:
        print(f"Erro ao carregar coberturas: {e}")
        return pd.DataFrame()


def calcular_datas_parto(vaca_id: str) -> Dict:
    """
    Calcula data de parto baseado na última cobertura.
    Retorna: {vaca_id, data_cobertura, data_parto, dias_ate_parto, status}
    """
    try:
        df_coberturas = carregar_coberturas(dias=365)

        # Busca última cobertura (produto = touro)
        df_vaca = df_coberturas[
            (df_coberturas.get('Brincos', '').astype(str).str.contains(str(vaca_id), case=False, na=False)) |
            (df_coberturas.get('ID Animal', '').astype(str) == str(vaca_id))
        ].sort_values('Data', ascending=False)

        if df_vaca.empty:
            return {
                "vaca_id": vaca_id,
                "data_cobertura": None,
                "data_parto": None,
                "dias_ate_parto": None,
                "status": "sem_cobertura"
            }

        data_cobertura = df_vaca.iloc[0]['Data']
        data_parto = data_cobertura + timedelta(days=DIAS_GESTACAO)
        dias_ate_parto = (data_parto - agora()).days

        # Status
        if dias_ate_parto < 0:
            status = "atrasado"
        elif dias_ate_parto <= DIAS_ANTES_SECAGEM:
            status = "secagem"
        elif dias_ate_parto <= DIAS_ANTES_TOQUE:
            status = "toque"
        else:
            status = "gestacao"

        return {
            "vaca_id": vaca_id,
            "data_cobertura": data_cobertura,
            "data_parto": data_parto,
            "dias_ate_parto": dias_ate_parto,
            "status": status,
            "touro": df_vaca.iloc[0].get('Produto', '?')
        }

    except Exception as e:
        print(f"Erro ao calcular parto: {e}")
        return {"vaca_id": vaca_id, "status": "erro"}


def gerar_alertas_partos() -> List[Dict]:
    """
    Gera alertas de parto para todas as vacas em gestação.
    """
    alertas = []

    try:
        df_animais = animais.carregar()

        for _, animal in df_animais.iterrows():
            animal_id = str(animal.get('ID', ''))
            categoria = str(animal.get('Categoria', '')).lower()

            # Só processa vacas em lactação
            if animal_id and 'vaca' in categoria:
                parto_info = calcular_datas_parto(animal_id)

                if parto_info['status'] == 'sem_cobertura':
                    continue

                dias = parto_info.get('dias_ate_parto', 999)
                status = parto_info.get('status', '')

                tipo_alerta = None
                motivo = ""
                acao = ""

                if status == "atrasado":
                    tipo_alerta = "urgente"
                    motivo = f"Parto ATRASADO há {abs(dias)} dias!"
                    acao = "🚨 Verificar imediatamente — possível complicação"

                elif status == "secagem" and dias >= 0:
                    tipo_alerta = "urgente" if dias <= 7 else "aviso"
                    motivo = f"Secagem em {dias} dias (parto {parto_info['data_parto'].strftime('%d/%m')})"
                    acao = "Interromper ordenha, preparar maternidade"

                elif status == "toque":
                    tipo_alerta = "aviso"
                    motivo = f"Toque de pre-parto ({dias} dias antes)"
                    acao = "Ordenha 2-3x/dia, monitorar sinais de parto"

                elif status == "gestacao" and dias <= 60:
                    tipo_alerta = "aviso"
                    motivo = f"Gestação adiantada ({dias} dias para parto)"
                    acao = "Monitoramento regular"

                if tipo_alerta:
                    try:
                        brinco = f"{animal.get('Brinco Cor', '')} {int(animal.get('Brinco Nº', 0)) or '??'}"
                    except Exception:
                        brinco = f"ID {animal_id}"

                    alertas.append({
                        "tipo": tipo_alerta,
                        "animal_id": animal_id,
                        "animal_desc": brinco,
                        "motivo": motivo,
                        "data_parto": parto_info.get('data_parto'),
                        "dias_ate_parto": dias,
                        "status": status,
                        "acao": acao
                    })

    except Exception as e:
        print(f"Erro ao gerar alertas de partos: {e}")

    # Ordena: urgentes primeiro
    alertas.sort(key=lambda a: (a['tipo'] != 'urgente', a['dias_ate_parto']))
    return alertas


def resumo_reproducao() -> Dict:
    """Retorna resumo de reprodução para o painel."""
    alertas = gerar_alertas_partos()

    return {
        "total_alertas": len(alertas),
        "urgentes": len([a for a in alertas if a['tipo'] == 'urgente']),
        "avisos": len([a for a in alertas if a['tipo'] == 'aviso']),
        "alertas_detalhados": alertas[:10]
    }


if __name__ == '__main__':
    print("=== Resumo de Reprodução ===")
    resumo = resumo_reproducao()
    print(f"Alertas: {resumo['total_alertas']} (urgentes: {resumo['urgentes']}, avisos: {resumo['avisos']})")
    for a in resumo['alertas_detalhados'][:3]:
        print(f"  [{a['tipo'].upper()}] {a['animal_desc']}: {a['motivo']}")
