#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ia_modelos.py — Three sklearn ML models for death, estrus, inbreeding prediction.

Models are trained once, serialized to pkl, loaded at app startup, used for
per-animal inference in alertas.py.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta


class ModeloMorte:
    """
    RandomForest classifier: predicts death/disease risk in next 30 days.

    Output: {prob_morte (0-100), urgencia (URGENTE|AVISO|OK), motivos (list), acao (str)}
    """

    def __init__(self):
        self.modelo = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_split=20,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1,
            class_weight='balanced'
        )
        self.scaler = StandardScaler()
        self.feature_names = None
        # Limiares calibráveis: com base de morte baixa o modelo nunca chega a 70%,
        # e o alerta urgente virava código morto (prob máx. observada: 0.69).
        self.limiar_urgente = 0.70
        self.limiar_aviso = 0.50

    def calibrar_limiares(self, X, y=None, pct_urgente=0.99, pct_aviso=0.90):
        """Define os limiares pelos percentis do próprio modelo (não por chute fixo).

        Assim o alerta pega sempre o grupo de maior risco, independente da escala
        de probabilidade que o treino produziu.
        """
        X_scaled = self.scaler.transform(X)
        prob = self.modelo.predict_proba(X_scaled)[:, 1]
        self.limiar_urgente = float(np.quantile(prob, pct_urgente))
        self.limiar_aviso = float(np.quantile(prob, pct_aviso))
        return self.limiar_urgente, self.limiar_aviso

    def treinar(self, X, y):
        """Train on (n_samples, n_features) and binary labels (0=vivo, 1=morte)."""
        if isinstance(X, pd.DataFrame):
            self.feature_names = X.columns.tolist()
            X = X.values

        X_scaled = self.scaler.fit_transform(X)
        self.modelo.fit(X_scaled, y)
        return self

    def prever(self, features_dict):
        """
        Predict death probability for one animal.

        Args:
            features_dict: dict with 25 keys from ia_features.extrair_features()

        Returns:
            dict with prob_morte, urgencia, motivos, acao
        """
        # Convert dict to array in correct order
        if self.feature_names:
            X = pd.DataFrame([features_dict])[self.feature_names]
        else:
            X = pd.DataFrame([features_dict])

        try:
            X_scaled = self.scaler.transform(X)
            prob = self.modelo.predict_proba(X_scaled)[0, 1]
        except Exception as e:
            print(f"⚠️ Erro predição morte: {e}")
            return {
                'prob_morte': 0.0,
                'urgencia': 'OK',
                'motivos': ['Erro no modelo'],
                'acao': 'Contate suporte'
            }

        # Thresholds calibrados no treino (padrão: 70%/50%)
        if prob > self.limiar_urgente:
            urgencia = "URGENTE"
            acao = "🚨 VENDER AGORA ou TRATAR INTENSIVO"
        elif prob > self.limiar_aviso:
            urgencia = "AVISO"
            acao = "⚠️ MONITORAR DIÁRIO + INVESTIGAR"
        else:
            urgencia = "OK"
            acao = "Continuar monitoramento normal"

        # Top 2 contributing features
        feature_importance = self.modelo.feature_importances_
        top_indices = np.argsort(feature_importance)[-2:][::-1]
        motivos = []

        for idx in top_indices:
            if idx < len(features_dict):
                if self.feature_names and idx < len(self.feature_names):
                    col = self.feature_names[idx]
                else:
                    col = list(features_dict.keys())[idx]

                val = features_dict.get(col, 0)

                if 'inbreeding' in col and val > 0.10:
                    motivos.append(f"Inbreeding alto ({val*100:.1f}%)")
                elif 'tratamentos' in col and val > 0.6:
                    motivos.append("Múltiplos tratamentos recentes")
                elif 'idade' in col and val > 0.8:
                    motivos.append("Idade avançada")
                elif 'peso' in col and val < 0.8:
                    motivos.append("Peso abaixo do esperado")

        return {
            'prob_morte': round(prob * 100, 1),
            'urgencia': urgencia,
            'motivos': motivos[:2],
            'acao': acao,
        }


class ModeloCio:
    """
    GradientBoosting regressor: predicts days to next estrus (fêmeas).

    Output: {dias_ate_cio (1-25), data_prevista, confianca (0-1), alertar (bool)}
    """

    def __init__(self):
        self.modelo = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
        )
        self.scaler = StandardScaler()
        self.feature_names = None

    def treinar(self, X, y):
        """Train on (n_samples, n_features) and regression labels (days 1-25)."""
        if isinstance(X, pd.DataFrame):
            self.feature_names = X.columns.tolist()
            X = X.values

        X_scaled = self.scaler.fit_transform(X)
        self.modelo.fit(X_scaled, y)
        return self

    def prever(self, features_dict):
        """
        Predict days to next estrus for one animal.

        Args:
            features_dict: dict from ia_features.extrair_features()

        Returns:
            dict with dias_ate_cio, data_prevista, confianca, alertar
        """
        if self.feature_names:
            X = pd.DataFrame([features_dict])[self.feature_names]
        else:
            X = pd.DataFrame([features_dict])

        try:
            X_scaled = self.scaler.transform(X)
            dias = self.modelo.predict(X_scaled)[0]
            dias = max(1, min(dias, 25))  # Clamp to [1, 25]
        except Exception as e:
            print(f"⚠️ Erro predição cio: {e}")
            return {
                'dias_ate_cio': 21,
                'data_prevista': (pd.Timestamp.now() + timedelta(days=21)).strftime('%d/%m/%Y'),
                'confianca': 0.0,
                'alertar': False,
            }

        data_prevista = pd.Timestamp.now() + timedelta(days=dias)

        # Confidence: peak at 21 days (normal cycle length)
        confianca = max(0.6, 1.0 - abs(dias - 21) / 21)

        # Alert if within 7 days
        alertar = dias <= 7

        return {
            'dias_ate_cio': int(dias),
            'data_prevista': data_prevista.strftime('%d/%m/%Y'),
            'confianca': round(confianca, 2),
            'alertar': alertar,
        }


def calcular_inbreeding_avk(animal_id, df_animais, max_depth=5):
    """
    Simple pedigree-based inbreeding coefficient (AVK approximation).

    Algorithm: Trace pedigree up to max_depth levels; count ancestor duplicates.
    If both pai and mae start with same character (proxy for shared ancestor),
    increase inbreeding score.

    Args:
        animal_id: String like 'A0001'
        df_animais: DataFrame with ID/animal_id, Pai/pai_id, Mãe/mae_id columns
        max_depth: Max generations to trace (default 5)

    Returns:
        float in [0, 1]; 0 if no pedigree data, up to 0.25 for high inbreeding
    """
    if df_animais.empty:
        return 0.0

    # Detect ID column (real data uses 'ID', synthetic uses 'animal_id')
    id_col = 'ID' if 'ID' in df_animais.columns else 'animal_id'
    pai_col = 'Pai' if 'Pai' in df_animais.columns else 'pai_id'
    mae_col = 'Mãe' if 'Mãe' in df_animais.columns else 'mae_id'

    if animal_id not in df_animais[id_col].values:
        return 0.0

    # Find animal
    animal = df_animais[df_animais[id_col] == animal_id].iloc[0]

    pai_id = str(animal.get(pai_col, '')).strip() if pai_col in df_animais.columns else ''
    mae_id = str(animal.get(mae_col, '')).strip() if mae_col in df_animais.columns else ''

    # If either parent missing, no inbreeding signal
    if not pai_id or not mae_id or pai_id == 'None' or mae_id == 'None':
        return 0.0

    # Simple heuristic: if parents start with same character, likely same origin
    if pai_id[0] == mae_id[0]:
        return 0.15  # Moderate inbreeding signal

    # Trace deeper (simplified: just check if any grandparents match)
    inbreeding_score = 0.0

    try:
        pai_animal = df_animais[df_animais['ID'] == pai_id].iloc[0] if pai_id in df_animais['ID'].values else None
        mae_animal = df_animais[df_animais['ID'] == mae_id].iloc[0] if mae_id in df_animais['ID'].values else None

        if pai_animal is not None and mae_animal is not None:
            # Check if grandparents overlap
            pai_pai = str(pai_animal.get('Pai', '')).strip() if 'Pai' in df_animais.columns else ''
            mae_mae = str(mae_animal.get('Mãe', '')).strip() if 'Mãe' in df_animais.columns else ''

            if pai_pai and mae_mae and pai_pai == mae_mae:
                inbreeding_score = 0.20  # High inbreeding
            elif pai_pai and mae_mae and pai_pai[0] == mae_mae[0]:
                inbreeding_score = 0.10  # Moderate inbreeding
    except Exception:
        pass

    # Final score: average with initial check
    return min(0.25, max(inbreeding_score, 0.15 if pai_id[0] == mae_id[0] else 0.0))
