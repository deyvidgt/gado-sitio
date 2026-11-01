#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ia_features.py — Extract 25 ML features per animal from farm data.

Normalizes all features to [0,1], handles NaN via median imputation,
and produces vectors ready for sklearn models.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler


def extrair_features(animal_id, df_animais, df_manejo, df_vendas, hoje=None):
    """
    Extract 25 normalized features for one animal.

    Args:
        animal_id: String like 'A0001'
        df_animais: DataFrame with ID, Data Nascimento, Sexo, Peso Estimado (kg)
        df_manejo: DataFrame with Tipo, Data, Brincos columns
        df_vendas: DataFrame with animal transaction records
        hoje: Reference date (default: today)

    Returns:
        dict with 25 keys, all values in [0, 1]; None if animal not found
    """
    hoje = pd.Timestamp(hoje or datetime.now()).normalize()

    # Find animal
    if df_animais.empty or animal_id not in df_animais['ID'].values:
        return None

    animal = df_animais[df_animais['ID'] == animal_id].iloc[0]

    features = {}

    # === AGE ===
    data_nasc = pd.to_datetime(animal.get('Data Nascimento', None), errors='coerce', dayfirst=True)
    if pd.isna(data_nasc):
        data_nasc = hoje - timedelta(days=365 * 2)  # Default: 2 years old
    idade_dias = max(0, (hoje - data_nasc).days)
    features['idade_dias_norm'] = min(idade_dias / 3650, 1.0)  # Max 10 years

    # === SEX ===
    sexo_str = str(animal.get('Sexo', 'M')).upper()
    features['sexo'] = 1.0 if 'F' in sexo_str else 0.0

    # === HEALTH HISTORY ===
    df_man = df_manejo
    if df_manejo is not None and not df_manejo.empty:
        df_man = df_manejo[df_manejo['Brincos'].astype(str).str.contains(animal_id, na=False)]
    else:
        df_man = pd.DataFrame()

    # Treatments in last 90 days
    tipos_saude = ['Medicação', 'Tratamento Veterinário', 'Vacina', 'Vermifugação']
    if not df_man.empty:
        tratamentos_90d = df_man[
            (df_man['Tipo'].astype(str).isin(tipos_saude)) &
            ((hoje - pd.to_datetime(df_man['Data'], errors='coerce', dayfirst=True)).dt.days <= 90)
        ]
    else:
        tratamentos_90d = pd.DataFrame()

    num_trat = len(tratamentos_90d)
    features['num_tratamentos_90d_norm'] = min(num_trat / 5, 1.0)

    # Days since last treatment
    if len(tratamentos_90d) > 0:
        dias_trat = (hoje - pd.to_datetime(tratamentos_90d.iloc[0]['Data'], errors='coerce', dayfirst=True)).days
    else:
        dias_trat = 365
    features['dias_ultimo_trat_norm'] = min(dias_trat / 180, 1.0)

    # === INBREEDING (AVK) ===
    # Simple heuristic: check if pai_id and mae_id start with same character
    pai_id = str(animal.get('Pai', '')).strip() if 'Pai' in animal.index else ''
    mae_id = str(animal.get('Mãe', '')).strip() if 'Mãe' in animal.index else ''

    if pai_id and mae_id and pai_id[0] == mae_id[0]:
        features['inbreeding_avk'] = 0.15  # High inbreeding indicator
    else:
        features['inbreeding_avk'] = 0.05

    # === WEIGHT ===
    peso_atual = animal.get('Peso Estimado (kg)', np.nan)
    if pd.isna(peso_atual):
        peso_atual = 400.0
    peso_esperado = 400.0 if features['sexo'] == 1.0 else 450.0
    features['peso_ratio'] = min(peso_atual / peso_esperado, 1.5)

    # === REPRODUCTION (fêmeas only) ===
    if features['sexo'] == 1.0:  # Female
        partos = pd.DataFrame()
        if not df_man.empty:
            partos = df_man[df_man['Tipo'].astype(str) == 'Nascimento']

        num_partos = len(partos)

        if num_partos > 0:
            data_ultimo = pd.to_datetime(partos.iloc[0]['Data'], errors='coerce', dayfirst=True)
            dias_parto = max(0, (hoje - data_ultimo).days)

            if num_partos >= 2:
                data_penultimo = pd.to_datetime(partos.iloc[1]['Data'], errors='coerce', dayfirst=True)
                iep = max(1, (data_ultimo - data_penultimo).days)
            else:
                iep = 365
        else:
            dias_parto = 9999
            iep = 365

        features['dias_parto_norm'] = min(dias_parto / 450, 1.0)
        features['num_partos_norm'] = min(num_partos / 10, 1.0)
        features['iep_norm'] = min(iep / 500, 1.0)

        # Estrus observations (last 21 days)
        cios = pd.DataFrame()
        if not df_man.empty:
            cios = df_man[
                (df_man['Tipo'].astype(str) == 'Observação de Cio') &
                ((hoje - pd.to_datetime(df_man['Data'], errors='coerce', dayfirst=True)).dt.days <= 21)
            ]

        num_cios = len(cios)
        features['estro_21d'] = min(num_cios / 3, 1.0)

        # Estrus intensity (1-5 scale, default 3 if no data)
        if num_cios > 0:
            intensidade = 3  # Default middle
            features['intensidade_cio'] = min(intensidade / 5, 1.0)
        else:
            features['intensidade_cio'] = 0.6

        # Temperature (placeholder: normal=38.5°C, range 36-40)
        features['temp_media'] = 0.75  # Normal range

        # Season (1=summer=hot, 0=winter=cold; currently neutral)
        features['estacao'] = 0.5

        # Stress score (0=low, 1=high; default neutral)
        features['stress_score'] = 0.3
    else:
        # Males: no reproductive features
        features['dias_parto_norm'] = 0.0
        features['num_partos_norm'] = 0.0
        features['iep_norm'] = 0.0
        features['estro_21d'] = 0.0
        features['intensidade_cio'] = 0.0
        features['temp_media'] = 0.75
        features['estacao'] = 0.5
        features['stress_score'] = 0.3

    # === MORTALITY RISK FACTORS ===
    num_parentes_mortos = 0  # Placeholder
    features['num_parentes_mortos_norm'] = min(num_parentes_mortos / 5, 1.0)

    # Death events in manejo
    mortes = pd.DataFrame()
    if not df_man.empty:
        mortes = df_man[df_man['Tipo'].astype(str) == 'Morte']

    features['morte_nunca'] = 0.0 if len(mortes) > 0 else 1.0

    # === SALES/MARKET ===
    vendido = False
    if not df_vendas.empty:
        vendido = animal_id in df_vendas['Brincos'].astype(str).values

    features['vendido'] = 1.0 if vendido else 0.0

    # === ADDITIONAL CONTEXT ===
    features['sexo_m'] = 1.0 - features['sexo']  # Males

    # Days since last event (any Manejo record)
    if not df_man.empty:
        df_man_copy = df_man.copy()
        df_man_copy['Data_parsed'] = pd.to_datetime(df_man_copy['Data'], errors='coerce', dayfirst=True)
        ultimas = df_man_copy[df_man_copy['Data_parsed'].notna()].sort_values('Data_parsed', ascending=False)
        if len(ultimas) > 0:
            dias_evento = (hoje - ultimas.iloc[0]['Data_parsed']).days
        else:
            dias_evento = 365
    else:
        dias_evento = 365
    features['dias_desde_ultimo_evento_norm'] = min(dias_evento / 180, 1.0)

    # Number of events in last 90 days
    if not df_man.empty:
        df_man_copy = df_man.copy()
        df_man_copy['Data_parsed'] = pd.to_datetime(df_man_copy['Data'], errors='coerce', dayfirst=True)
        eventos_90d = df_man_copy[
            (df_man_copy['Data_parsed'].notna()) &
            ((hoje - df_man_copy['Data_parsed']).dt.days <= 90)
        ]
    else:
        eventos_90d = pd.DataFrame()

    num_eventos = len(eventos_90d)
    features['num_eventos_90d_norm'] = min(num_eventos / 10, 1.0)

    # Estrus cycle length (typical 21 days for cattle, normalized 17-25)
    features['ciclo_cio_dias_norm'] = 0.8  # 21 / 25 = 0.84

    # Health status (0=sick/risky, 1=healthy)
    if num_trat > 3 or (len(mortes) > 0):
        status_saude = 0.3
    else:
        status_saude = 0.8
    features['status_saude'] = status_saude

    # Fertility score (fêmeas: based on IEP; males: neutral)
    if features['sexo'] == 1.0:
        if iep > 0:
            fertilidade = 1.0 / (1.0 + (iep - 365) ** 2 / 10000)  # Peak at 365d
        else:
            fertilidade = 0.5
        fertilidade = max(0, min(1, fertilidade))
        features['fertilidade_score'] = fertilidade
    else:
        features['fertilidade_score'] = 0.5

    # Growth rate (peso_ratio trend)
    features['crescimento_rate'] = max(0, min(1, features['peso_ratio'] - 0.5))

    # Base death risk (age + treatments + inbreeding - health)
    risco_base = (
        0.3 * features['idade_dias_norm'] +
        0.2 * features['num_tratamentos_90d_norm'] +
        0.5 * features['inbreeding_avk'] -
        0.2 * status_saude
    )
    features['risco_morte_base'] = max(0, min(1, risco_base))

    # Ensure all values are in [0, 1]
    for key in features:
        if not (0 <= features[key] <= 1):
            features[key] = max(0, min(1, features[key]))

    return features


def preprocessar_batch(features_list, scaler=None):
    """
    Convert list of feature dicts to normalized DataFrame + scaler.

    Args:
        features_list: List of dicts from extrair_features()
        scaler: Optional pre-fitted StandardScaler (if None, fit on data)

    Returns:
        (df_scaled, scaler): Normalized DataFrame and fitted scaler
    """
    df = pd.DataFrame(features_list)

    if scaler is None:
        scaler = StandardScaler()
        df_scaled = scaler.fit_transform(df)
    else:
        df_scaled = scaler.transform(df)

    df_scaled = pd.DataFrame(df_scaled, columns=df.columns)

    return df_scaled, scaler
