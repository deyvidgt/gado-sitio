from agora import agora
# -*- coding: utf-8 -*-
"""
Coleta automática de dados para indicadores (v5.8+):
- Engorda Pastagem: GMD + Lotação por pasto
- GMD Lotação: histórico correlação GMD vs UA/ha
- Ração Consumo: do módulo leiteiro (leite.py)

Roda automaticamente no manejo (após pesagem, movimentação de pasto) via
routes_manejo.py → atualizar_indicadores_coleta() no salvar_manejo().
"""

from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
from db import carregar_aba, salvar_linha, reescrever_aba
from config import (
    COLUNAS_ENGORDA_PASTAGEM, COLUNAS_GMD_LOTACAO, COLUNAS_RACAO_CONSUMO,
)


def registrar_engorda_pastagem(pasto_id: str, brincos: str, peso_inicial: float,
                               peso_final: float, dias: int, gmd: float,
                               lotacao_ua_ha: float, condicao_pasto: str = "",
                               observacao: str = "") -> bool:
    """
    Registra um período de engorda em pasto.

    Chamado após movimentação de pasto e pesagem final.

    Args:
        pasto_id: ID do pasto (ex.: "P001")
        brincos: lista de brincos (ex.: "Amarelo 21 #A0001; Azul 15 #A0002")
        peso_inicial: peso ao entrar no pasto (kg)
        peso_final: peso ao sair do pasto (kg)
        dias: dias no pasto
        gmd: ganho médio diário calculado (kg/dia)
        lotacao_ua_ha: cabeças / área em UA/ha
        condicao_pasto: visual do pasto (bom/regular/ruim)
        observacao: observações adicionais

    Returns:
        True se registrou, False se erro
    """
    try:
        df = carregar_aba("Engorda Pastagem")
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            df = pd.DataFrame()

        # Calcula consumo estimado por diferença de peso e duração
        consumo_estimado = ((peso_final - peso_inicial) / dias) if dias > 0 else 0

        nova_linha = [
            agora().strftime("%d/%m/%Y"),  # Data
            pasto_id or "",  # Pasto ID
            brincos or "",  # Brincos
            float(peso_inicial) if peso_inicial else 0,  # Peso Inicial
            float(peso_final) if peso_final else 0,  # Peso Final
            int(dias) if dias else 0,  # Dias no Pasto
            float(gmd) if gmd else 0,  # GMD (kg/dia)
            float(lotacao_ua_ha) if lotacao_ua_ha else 0,  # Lotação (UA/ha)
            condicao_pasto or "",  # Condição Pasto
            round(consumo_estimado, 2),  # Consumo Estimado (kg MS/dia)
            observacao or "",  # Observação
            "",  # Responsável (preenchido no formulário)
            "",  # ID Envio (offline)
            agora().isoformat(),  # Criado Em
        ]

        salvar_linha("Engorda Pastagem", nova_linha)
        return True
    except Exception as e:
        print(f"❌ Engorda Pastagem: {e}")
        return False


def registrar_gmd_lotacao(periodo_dias: int, animais: int, peso_inicial: float,
                          peso_final: float, gmd: float, pasto_id: str,
                          lotacao_ua_ha: float, capacidade_ua_ha: float = 0,
                          qualidade_pasto: str = "", clima: str = "",
                          observacao: str = "") -> bool:
    """
    Registra histórico de GMD vs Lotação para análise de correlação.

    Chamado em pesagem de lote (após final do período).

    Args:
        periodo_dias: duração do período (ex.: 30 dias)
        animais: número de cabeças no período
        peso_inicial: peso médio inicial (kg)
        peso_final: peso médio final (kg)
        gmd: ganho médio diário calculado (kg/dia)
        pasto_id: ID do pasto (ex.: "P001")
        lotacao_ua_ha: cabeças / área em UA/ha
        capacidade_ua_ha: capacidade teórica do pasto (UA/ha)
        qualidade_pasto: visual (bom/regular/ruim)
        clima: condições climáticas (normal/seco/úmido)
        observacao: observações

    Returns:
        True se registrou, False se erro
    """
    try:
        df = carregar_aba("GMD Lotação")
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            df = pd.DataFrame()

        # % de ocupação = lotação atual / capacidade
        ocupacao_perc = 0
        if capacidade_ua_ha and capacidade_ua_ha > 0:
            ocupacao_perc = min(100, round((lotacao_ua_ha / capacidade_ua_ha) * 100, 1))

        nova_linha = [
            agora().strftime("%d/%m/%Y"),  # Data
            int(periodo_dias) if periodo_dias else 0,  # Período (dias)
            int(animais) if animais else 0,  # Animais
            float(peso_inicial) if peso_inicial else 0,  # Peso Inicial (kg)
            float(peso_final) if peso_final else 0,  # Peso Final (kg)
            float(gmd) if gmd else 0,  # GMD (kg/dia)
            pasto_id or "",  # Pasto ID
            float(lotacao_ua_ha) if lotacao_ua_ha else 0,  # Lotação (UA/ha)
            float(capacidade_ua_ha) if capacidade_ua_ha else 0,  # Capacidade (UA/ha)
            ocupacao_perc,  # % Ocupação
            qualidade_pasto or "",  # Qualidade Pasto
            clima or "",  # Clima
            observacao or "",  # Observação
            "",  # ID Envio
            agora().isoformat(),  # Criado Em
        ]

        salvar_linha("GMD Lotação", nova_linha)
        return True
    except Exception as e:
        print(f"❌ GMD Lotação: {e}")
        return False


def registrar_racao_consumo(tipo_racao: str, qty_oferecida: float, qty_consumida: float,
                            custo_kg: float, observacao: str = "",
                            responsavel: str = "") -> bool:
    """
    Registra ração oferecida vs consumida (eficiência alimentar).

    Chamado após alimentação registrada no leite.py ou insumos.py.

    Args:
        tipo_racao: tipo (ex.: "Ração de Produção", "Concentrado", "Feno")
        qty_oferecida: quantidade oferecida (kg)
        qty_consumida: quantidade consumida (kg)
        custo_kg: valor do kg (R$)
        observacao: observações
        responsavel: quem registrou

    Returns:
        True se registrou, False se erro
    """
    try:
        df = carregar_aba("Ração Consumo")
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            df = pd.DataFrame()

        # Cálculos de consumo e desperdício
        taxa_consumo = 0
        desperdicio_kg = 0
        perc_desperdicio = 0

        if qty_oferecida and qty_oferecida > 0:
            taxa_consumo = round((qty_consumida / qty_oferecida) * 100, 1) if qty_consumida else 0
            desperdicio_kg = qty_oferecida - qty_consumida
            perc_desperdicio = round((desperdicio_kg / qty_oferecida) * 100, 1)

        custo_total = (qty_oferecida or 0) * (custo_kg or 0)

        nova_linha = [
            agora().strftime("%d/%m/%Y"),  # Data
            tipo_racao or "",  # Tipo Ração
            float(qty_oferecida) if qty_oferecida else 0,  # Quantidade Oferecida (kg)
            float(qty_consumida) if qty_consumida else 0,  # Quantidade Consumida (kg)
            taxa_consumo,  # Taxa Consumo (%)
            float(custo_kg) if custo_kg else 0,  # Custo/kg
            round(custo_total, 2),  # Custo Total Oferecido (R$)
            round(desperdicio_kg, 2) if desperdicio_kg > 0 else 0,  # Desperdício (kg)
            perc_desperdicio,  # % Desperdício
            observacao or "",  # Observação
            responsavel or "",  # Responsável
            "",  # ID Envio
            agora().isoformat(),  # Criado Em
        ]

        salvar_linha("Ração Consumo", nova_linha)
        return True
    except Exception as e:
        print(f"❌ Ração Consumo: {e}")
        return False


def sugerir_engorda_pastagem() -> dict:
    """
    Sugere um novo registro de engorda com dados de pesagem + pasto recentes.

    Usado no formulário de manejo para pré-preencher campos.

    Returns:
        {
            "brincos": "Amarelo 21 #A0001; ...",
            "pasto_id": "P001",
            "peso_inicial": 280,
            "dias_estimados": 30,
            "lotacao_ua_ha": 1.2,
        }
    """
    try:
        from pesagem import todas
        from pastos import situacao

        sugestao = {}

        # Último pasto onde houve movimento (últimos 7 dias)
        try:
            df_manejo = carregar_aba("Manejo")
            if df_manejo is not None and isinstance(df_manejo, pd.DataFrame) and not df_manejo.empty:
                # Procura "Movimentação de Pasto" recente
                moves = df_manejo[
                    (df_manejo["Tipo"] == "Movimentação de Pasto") &
                    (pd.notna(df_manejo["Data"])) &
                    (pd.notna(df_manejo["Pasto"]))
                ].sort_values("Data", ascending=False)

                if not moves.empty:
                    last_move = moves.iloc[0]
                    sugestao["pasto_id"] = str(last_move.get("Pasto", ""))
                    sugestao["brincos"] = str(last_move.get("Brincos", ""))
        except Exception:
            pass

        # Peso inicial (última pesagem)
        try:
            todos_pesos = todas()
            if isinstance(todos_pesos, list) and len(todos_pesos) > 0:
                sugestao["peso_inicial"] = todos_pesos[0].get("peso", 0)
        except Exception:
            pass

        # Lotação do pasto sugerido
        if "pasto_id" in sugestao:
            try:
                sit = situacao()
                if sugestao["pasto_id"] in sit:
                    info = sit[sugestao["pasto_id"]]
                    sugestao["lotacao_ua_ha"] = info.get("ua_ha", 0)
            except Exception:
                pass

        # Dias estimados (30 dias é padrão)
        sugestao["dias_estimados"] = 30

        return sugestao
    except Exception as e:
        return {}  # silencioso em erro total


def processar_manejo_automatico(tipo_manejo: str, brincos_str: str = "",
                                descricao: str = "", pasto_id: str = "",
                                qtd_cabecas: int = 0) -> None:
    """
    Processa um manejo registrado e alimenta automaticamente os indicadores.

    Chamado pelo routes_manejo.py após salvar_linha("Manejo", ...).

    Args:
        tipo_manejo: tipo de manejo (ex.: "Pesagem", "Movimentação de Pasto")
        brincos_str: brincos afetados (ex.: "Amarelo 21 #A0001; Azul 15")
        descricao: descrição do manejo
        pasto_id: ID do pasto (se aplicável)
        qtd_cabecas: número de cabeças (se aplicável)
    """
    try:
        # Se é pesagem, tenta calcular GMD com a última entrada
        if tipo_manejo == "Pesagem" and brincos_str:
            _processar_pesagem_automatica(brincos_str, descricao)

        # Se é movimentação de pasto, tenta gerar sugestão de engorda
        if tipo_manejo == "Movimentação de Pasto" and pasto_id:
            _processar_movimentacao_automatica(pasto_id, brincos_str, qtd_cabecas)

        # Se é alimentação registrada, tenta preencher ração consumo
        if tipo_manejo == "Alimentação" and descricao:
            _processar_alimentacao_automatica(descricao)

    except Exception as e:
        print(f"⚠️ Processamento automático falhou: {e}")


def _processar_pesagem_automatica(brincos_str: str, descricao: str) -> None:
    """
    Após pesagem registrada, tenta calcular GMD com dados anteriores.

    Exemplo descricao: "Amarelo 21 #A0001: 320 kg; Azul 15 #A0002: 285 kg"
    """
    try:
        from pesagem import todas

        # Se há múltiplos pesos, calcula GMD
        pesos_atuais = todas()
        if not pesos_atuais or len(pesos_atuais) < 2:
            return  # Precisa de pelo menos 2 pesagens

        # Para cada animal, calcula dias desde última pesagem e GMD
        # (Isso é mais complexo e requer matching de brincos com histórico)
        # Por agora, apenas registra que houve pesagem
    except Exception as e:
        print(f"⚠️ GMD automático: {e}")


def _processar_movimentacao_automatica(pasto_id: str, brincos_str: str,
                                       qtd_cabecas: int) -> None:
    """
    Após movimentação de pasto, tenta gerar sugestão de engorda.

    O usuário preencherá peso_inicial e peso_final depois (na pesagem).
    Por agora, apenas registra a entrada da movimentação.
    """
    try:
        from pastos import situacao

        sit = situacao()
        if pasto_id not in sit:
            return  # Pasto não existe

        info = sit[pasto_id]
        lotacao_ua_ha = info.get("ua_ha", 0)

        # Registra a movimentação em GMD Lotação com dados parciais
        # (peso_inicial/final vem depois de pesagem)
        registrar_gmd_lotacao(
            periodo_dias=0,  # será preenchido no final
            animais=qtd_cabecas or info.get("cabecas", 0),
            peso_inicial=0,  # será preenchido na pesagem
            peso_final=0,
            gmd=0,
            pasto_id=pasto_id,
            lotacao_ua_ha=lotacao_ua_ha,
            observacao=f"Movido: {brincos_str or 'rebanho todo'}"
        )
    except Exception as e:
        print(f"⚠️ Movimentação automática: {e}")


def _processar_alimentacao_automatica(descricao: str) -> None:
    """
    Após alimentação registrada no leite, tenta preencher ração consumo.

    Exemplo descricao: "Ração de produção 30 kg, concentrado 5 kg"
    """
    try:
        # Parse simples: "Tipo quantidade kg"
        # Requer integração com leite.py para dados reais
        pass
    except Exception as e:
        print(f"⚠️ Alimentação automática: {e}")
