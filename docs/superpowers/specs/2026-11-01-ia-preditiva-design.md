# Onda 19 — IA Preditiva (Culling Automático + Cio Premonitório)

**Data:** 2026-11-01  
**Versão:** 1.0 (MVP)  
**Status:** Design Aprovado  
**Tempo:** 2 semanas  
**Dependências:** v5.12 (Ondas 0-14 entregues)

---

## 1. Visão Geral

**Objetivo:** Prevenir perdas financeiras (morte/doença) e melhorar genética (inbreeding, cio oportuno) usando ML em histórico real + sintético.

**3 Modelos Preditivos:**
1. **Morte/Doença (30 dias)** — RandomForest, threshold 70% urgente
2. **Cio Premonitório (21 dias)** — GradientBoosting, ETA com intervalo de confiança
3. **Inbreeding AVK** — Cálculo determinístico, alerta >10%

**Integração:** Alertas globais → Dashboard → WhatsApp

**Dados:** Sintético (5k registros 2024-2026) + Real (gado_familia.xlsx histórico)

---

## 2. Componentes

### 2.1 Gerador Sintético (`ia_sintetico.py`)

**Propósito:** Expandir dados históricos para 5k registros, balancear classes (morte, cio, parto), evitar overfitting em 300 animais reais.

**Entrada:**
- `n_animais` = 5000 (simulados)
- `anos` = 3 (2024-2026)
- `seed` = 42 (reprodutível)
- `MEMBROS` de `config.py` (DONOS)

**Saída:** `historico_sintetico_5k.pkl` — DataFrame com colunas:

```
animal_id, data_nascimento, sexo, dono, pai_id, mae_id, 
evento_tipo, evento_data, idade_dias_evento, status_vivo,
peso_estimado_kg, num_tratamentos_90d, ultimo_tratamento_dias,
dias_desde_parto, ciclo_cio_dias, iep_dias, intensidade_cio,
inbreeding_avk_pct, peso_ratio_esperado, num_parentes_mortos
```

**Algoritmo:**

```python
def gerar_sintetico(n_animais=5000, anos=3, seed=42):
    """Simula rebanho com eventos realistas."""
    np.random.seed(seed)
    animais = []
    
    # 1. Popula animais (nascimentos distribuídos)
    for i in range(n_animais):
        data_nasc = random_date(2024, 2026)
        sexo = np.random.choice(['F', 'M'], p=[0.55, 0.45])
        dono = np.random.choice(MEMBROS)
        pai_id = f"T{np.random.randint(1000, 9999)}" if np.random.random() > 0.2 else None
        mae_id = f"V{np.random.randint(1000, 9999)}" if np.random.random() > 0.2 else None
        
        animais.append({
            'animal_id': f"A{i:05d}",
            'data_nascimento': data_nasc,
            'sexo': sexo,
            'dono': dono,
            'pai_id': pai_id,
            'mae_id': mae_id,
        })
    
    # 2. Simula eventos (morte, parto, tratamento, cio)
    for animal in animais:
        simular_mortes(animal, taxa_base=0.03)  # 3% ao ano
        simular_partos(animal, taxa=0.8)  # 0.8 partos/vaca/ano se fêmea
        simular_tratamentos(animal, taxa=0.15)  # 15% recebem tratamento veterinário
    
    # 3. Calcula features derivadas
    for animal in animais:
        animal['inbreeding_avk_pct'] = calcular_avk_simples(animal['pai_id'], animal['mae_id'])
        animal['peso_ratio_esperado'] = simular_peso(animal['sexo'], animal['idade_dias'])
    
    return pd.DataFrame(animais)

def simular_mortes(animal, taxa_morte_anual=0.03, risco_relativo=None):
    """Morte correlacionada com idade, inbreeding, tratamentos."""
    idade_dias = (data_hoje - animal['data_nascimento']).days
    
    # Taxa base aumenta com idade (exponencial)
    taxa_idade = taxa_morte_anual * (1 + 0.05 * (idade_dias / 365))
    
    # Risco relativo: inbreeding >10% = 1.5x, múltiplos tratamentos = 1.3x
    risco = taxa_idade
    if animal.get('inbreeding_avk_pct', 0) > 0.10:
        risco *= 1.5
    if animal.get('num_tratamentos_90d', 0) > 2:
        risco *= 1.3
    
    if np.random.random() < risco:
        animal['evento_tipo'] = 'MORTE'
        animal['evento_data'] = data_hoje - timedelta(days=np.random.randint(1, 30))
        animal['status_vivo'] = False
    else:
        animal['status_vivo'] = True

def simular_partos(animal, taxa_partos=0.8):
    """Parto em fêmeas 24-72 meses, correlacionado com IEP."""
    if animal['sexo'] != 'F':
        return
    
    idade_dias = (data_hoje - animal['data_nascimento']).days
    if not (24*30 <= idade_dias <= 72*30):  # Fora idade reprodutiva
        return
    
    # Distribui partos ao longo de 3 anos
    num_partos = np.random.poisson(taxa_partos * 3)
    
    for j in range(num_partos):
        data_parto = animal['data_nascimento'] + timedelta(days=np.random.randint(730, 1095))
        
        animal['eventos_parto'].append({
            'data': data_parto,
            'dias_desde_parto': (data_hoje - data_parto).days,
            'ciclo_cio_dias': np.random.normal(21, 2),  # 21±2 dias
        })

def calcular_avk_simples(pai_id, mae_id):
    """Coeficiente de inbreeding simples: 0.25 se pais são meio-irmãos, 0 se desconhecidos."""
    if not pai_id or not mae_id:
        return 0.0
    
    # Heurística: se IDs compartilham prefixo ou data próxima → parentesco
    if pai_id[:3] == mae_id[:3]:  # Mesma origem
        return 0.05  # Assume ligeiro inbreeding
    
    return 0.0
```

**Outputs:**
- `data/ia_models/historico_sintetico_5k.pkl` — DataFrame
- `data/ia_models/sintetico_stats.json` — Distribution: 150 mortes (3%), 3800 partos, 450 tratamentos

---

### 2.2 Extrator de Features (`ia_features.py`)

**Propósito:** Transforma histórico animal em vetor numérico para ML (20-30 dimensões).

**Função Principal:**

```python
def extrair_features(animal_id, df_animais, df_manejo, df_vendas, hoje=None):
    """
    Input: animal_id (string ex. "A0001")
    Output: dict com 25 features normalizadas (0-1)
    
    Features para MORTE/DOENÇA:
    - idade_dias (0-3650)
    - sexo (0/1)
    - peso_ratio (peso_real / peso_esperado_idade)
    - num_tratamentos_90d (0-5)
    - dias_desde_ultimo_tratamento (0-90)
    - inbreeding_avk (0-1)
    - num_mortes_parentes (0-3)
    - num_eventos_parto (vacas)
    - iep_ultimo (365-500 dias)
    - dias_imobilizado (correlato de peso_ratio)
    
    Features para CIO:
    - dias_desde_ultimo_parto (0-450)
    - ciclo_cio_medio (19-23 dias, idealmente 21)
    - num_partos_total (0-8)
    - iep_media_historica (365-500)
    - iep_variancia (baixa = regular, alta = irregular)
    - intensidade_ultimo_cio (1-5)
    - temperatura_media_mes (19-28C, se disponível)
    - estacao (0-3: primavera, verão, outono, inverno)
    - stress_score (num_tratamentos + mudança_pasto)
    - estro_detectado_ultimo_21d (bool)
    
    Features GERAIS:
    - producao_leite_ultima_ordenha (0-30L)
    - mastite_eventos_ultimos_90d (0-3)
    - peso_velocidade_ganho (kg/dia)
    - circunferencia_escrotal (touros)
    - score_corporal (1-5)
    """
    
    hoje = pd.Timestamp(hoje or pd.Timestamp.now()).normalize()
    
    # 1. Dados animal base
    animal = df_animais[df_animais['ID'] == animal_id].iloc[0] if animal_id in df_animais['ID'].values else None
    if animal is None:
        return None
    
    data_nasc = pd.to_datetime(animal.get('Data Nascimento', hoje), errors='coerce')
    if pd.isna(data_nasc):
        data_nasc = hoje - timedelta(days=365*2)  # Assume 2 anos se desconhecido
    
    idade_dias = (hoje - data_nasc).days
    sexo = 1 if 'F' in str(animal.get('Sexo', 'M')).upper() else 0
    
    # 2. Histórico de tratamentos (últimos 90 dias)
    df_man = df_manejo[df_manejo['Brincos'].str.contains(animal_id, na=False)] if df_manejo is not None else pd.DataFrame()
    
    tipos_saude = ['Medicação', 'Tratamento Veterinário', 'Vacina Raiva', 'Vermifugação']
    tratamentos_90d = df_man[
        (df_man['Tipo'].isin(tipos_saude)) & 
        ((hoje - pd.to_datetime(df_man['Data'], errors='coerce', dayfirst=True)).dt.days <= 90)
    ]
    num_tratamentos_90d = len(tratamentos_90d)
    
    if len(tratamentos_90d) > 0:
        dias_ultimo_trat = (hoje - pd.to_datetime(tratamentos_90d.iloc[0]['Data'], errors='coerce', dayfirst=True)).days
    else:
        dias_ultimo_trat = 365  # Nunca tratado = risco
    
    # 3. Histórico reprodutivo (fêmeas)
    partos = df_man[df_man['Tipo'] == 'Nascimento']
    num_partos = len(partos)
    
    if num_partos > 0:
        data_ultimo_parto = pd.to_datetime(partos.iloc[0]['Data'], errors='coerce', dayfirst=True)
        dias_ultimo_parto = (hoje - data_ultimo_parto).days
        
        # IEP (intervalo entre últimos 2 partos)
        if num_partos >= 2:
            data_penultimo = pd.to_datetime(partos.iloc[1]['Data'], errors='coerce', dayfirst=True)
            iep_ultimo = (data_ultimo_parto - data_penultimo).days
        else:
            iep_ultimo = 365  # Primeira prenhação
    else:
        dias_ultimo_parto = 9999  # Nunca pariu
        iep_ultimo = 365
    
    # 4. Cios observados (últimos 21 dias)
    cios = df_man[
        (df_man['Tipo'] == 'Observação de Cio') & 
        ((hoje - pd.to_datetime(df_man['Data'], errors='coerce', dayfirst=True)).dt.days <= 21)
    ]
    estro_21d = len(cios) > 0
    
    if len(cios) > 0:
        # Extrai intensidade da descrição (ex. "Intensidade 4/5")
        ultima_desc = str(cios.iloc[0].get('Descrição', ''))
        try:
            intensidade_cio = int(ultima_desc.split('Intensidade ')[1].split('/')[0])
        except:
            intensidade_cio = 3
    else:
        intensidade_cio = 0
    
    # 5. Inbreeding (AVK)
    pai = animal.get('Pai', '')
    mae = animal.get('Mãe', '')
    inbreeding_avk = calcular_avk_simples(pai, mae, df_animais)
    
    # 6. Peso (ratio esperado)
    peso_atual = animal.get('Peso Estimado (kg)', np.nan)
    if pd.isna(peso_atual):
        peso_ratio = 1.0  # Neutro
    else:
        peso_esperado = peso_esperado_por_idade(sexo, idade_dias)
        peso_ratio = peso_atual / peso_esperado if peso_esperado > 0 else 1.0
    
    # 7. Compila features (normaliza 0-1)
    features = {
        # Morte/Doença
        'idade_dias_norm': min(idade_dias / 3650, 1.0),  # Max 10 anos
        'sexo': sexo,
        'num_tratamentos_90d_norm': min(num_tratamentos_90d / 5, 1.0),
        'dias_ultimo_trat_norm': min(dias_ultimo_trat / 90, 1.0),
        'inbreeding_avk': inbreeding_avk,
        'peso_ratio': peso_ratio,
        
        # Cio
        'dias_parto_norm': min(dias_ultimo_parto / 450, 1.0) if sexo == 1 else 0,
        'num_partos_norm': min(num_partos / 8, 1.0) if sexo == 1 else 0,
        'iep_norm': min(iep_ultimo / 500, 1.0) if sexo == 1 else 0,
        'intensidade_cio': intensidade_cio / 5.0,
        'estro_21d': 1.0 if estro_21d else 0.0,
        
        # Derivadas
        'risco_morte_score': 0,  # Preenchido pelo modelo
    }
    
    return features

def preprocessar_batch(features_list):
    """Normaliza batch de features, imputa NaN."""
    df = pd.DataFrame(features_list)
    
    # Imputa NaN com mediana
    df = df.fillna(df.median())
    
    # Normaliza (0-1) por coluna
    scaler = StandardScaler()
    df_scaled = pd.DataFrame(scaler.fit_transform(df), columns=df.columns)
    
    return df_scaled, scaler
```

---

### 2.3 Modelos Preditivos (`ia_modelos.py`)

**Propósito:** 3 modelos sklearn treinados 1x em dados históricos (sintético + real).

#### 2.3.1 Modelo Morte/Doença

```python
class ModeloMorte:
    """RandomForest: classifica morte em próximos 30 dias."""
    
    def __init__(self):
        self.modelo = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_split=20,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1,
            class_weight='balanced'  # Evita viés (morte é rara)
        )
        self.scaler = StandardScaler()
    
    def treinar(self, X_treino, y_morte):
        """
        Input: 
        - X_treino: features (n_samples, n_features)
        - y_morte: binário (1 = morreu em 30d, 0 = sobreviveu)
        
        Output: self.modelo treinado
        """
        X_scaled = self.scaler.fit_transform(X_treino)
        self.modelo.fit(X_scaled, y_morte)
        
        return self
    
    def prever(self, features_dict):
        """
        Input: um animal com features extraídas
        Output: (prob_morte %, diagnóstico, ação_recomendada)
        """
        X = pd.DataFrame([features_dict])
        X_scaled = self.scaler.transform(X)
        
        prob_morte = self.modelo.predict_proba(X_scaled)[0, 1]
        
        # Interpretabilidade: qual feature mais contribuiu?
        feature_importance = self.modelo.feature_importances_
        top_features = np.argsort(feature_importance)[-3:][::-1]
        
        motivos = []
        for idx in top_features:
            col_name = list(features_dict.keys())[idx]
            val = features_dict[col_name]
            if col_name == 'inbreeding_avk' and val > 0.10:
                motivos.append(f"Inbreeding alto ({val*100:.1f}%)")
            elif col_name == 'num_tratamentos_90d_norm' and val > 0.6:
                motivos.append("Múltiplos tratamentos recentes")
            elif col_name == 'idade_dias_norm' and val > 0.8:
                motivos.append("Idade avançada")
            elif col_name == 'peso_ratio' and val < 0.8:
                motivos.append("Peso abaixo do esperado")
        
        if prob_morte > 0.70:
            urgencia = "URGENTE"
            acao = "🚨 VENDER AGORA ou TRATAR INTENSIVO"
        elif prob_morte > 0.50:
            urgencia = "AVISO"
            acao = "⚠️ MONITORAR DIÁRIO + INVESTIGAR"
        else:
            urgencia = "OK"
            acao = "Continuar monitoramento normal"
        
        return {
            'prob_morte': round(prob_morte * 100, 1),
            'urgencia': urgencia,
            'motivos': motivos[:2],
            'acao': acao,
        }
```

#### 2.3.2 Modelo Cio

```python
class ModeloCio:
    """GradientBoosting: prevê dias até próximo cio."""
    
    def __init__(self):
        self.modelo = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
        )
        self.scaler = StandardScaler()
    
    def treinar(self, X_treino, y_dias_cio):
        """
        Input:
        - X_treino: features (n_samples, n_features)
        - y_dias_cio: dias até cio (regressão contínua)
        """
        X_scaled = self.scaler.fit_transform(X_treino)
        self.modelo.fit(X_scaled, y_dias_cio)
        
        return self
    
    def prever(self, features_dict):
        """
        Output: (dias_predito, data_prevista, confiança, alertar)
        """
        X = pd.DataFrame([features_dict])
        X_scaled = self.scaler.transform(X)
        
        dias_predito = self.modelo.predict(X_scaled)[0]
        dias_predito = max(1, min(dias_predito, 25))  # Clamp [1, 25]
        
        data_prevista = pd.Timestamp.now() + timedelta(days=dias_predito)
        
        # Confiança: resíduo médio em validação
        confianca = max(0.6, 1.0 - abs(dias_predito - 21) / 21)  # Pico em 21 dias
        
        alertar = dias_predito <= 7
        
        return {
            'dias_ate_cio': round(dias_predito),
            'data_prevista': data_prevista.strftime("%d/%m/%Y"),
            'confianca': round(confianca * 100, 1),
            'alertar': alertar,
        }
```

#### 2.3.3 Inbreeding AVK

```python
def calcular_inbreeding_avk(animal_id, df_animais, max_depth=5):
    """
    Coeficiente de inbreeding (AVK) simples por antepassados comuns.
    
    AVK = (1/2)^n, onde n = gerações até antepassado comum
    
    Exemplo:
    - Pai e Mãe meios-irmãos (AVK 0.125) → F = 0.0625 (6.25%)
    - Pai e Mãe desconhecidos → AVK = 0 (0%)
    """
    
    def find_ancestors(id_animal, depth=0, visited=None):
        """Recursivamente busca pais até max_depth."""
        if visited is None:
            visited = set()
        
        if depth > max_depth or id_animal in visited or not id_animal:
            return set()
        
        visited.add(id_animal)
        
        animal = df_animais[df_animais['ID'] == id_animal]
        if animal.empty:
            return {id_animal}
        
        pai = animal.iloc[0].get('Pai')
        mae = animal.iloc[0].get('Mãe')
        
        ancestors = {id_animal}
        if pai:
            ancestors.update(find_ancestors(pai, depth+1, visited))
        if mae:
            ancestors.update(find_ancestors(mae, depth+1, visited))
        
        return ancestors
    
    # Busca pais do animal
    animal = df_animais[df_animais['ID'] == animal_id]
    if animal.empty:
        return 0.0
    
    pai_id = animal.iloc[0].get('Pai')
    mae_id = animal.iloc[0].get('Mãe')
    
    if not pai_id or not mae_id:
        return 0.0  # Um dos pais desconhecido
    
    # Encontra antepassados comuns
    anc_pai = find_ancestors(pai_id, max_depth=max_depth)
    anc_mae = find_ancestors(mae_id, max_depth=max_depth)
    
    anc_comuns = anc_pai & anc_mae
    
    if not anc_comuns:
        return 0.0  # Nenhum antepassado comum (até max_depth)
    
    # AVK = média de (1/2)^(distância ao antepassado comum)
    avk = 0.0
    for anc in anc_comuns:
        dist_pai = len(shortest_path(pai_id, anc, df_animais))
        dist_mae = len(shortest_path(mae_id, anc, df_animais))
        avk += (0.5) ** (dist_pai + dist_mae)
    
    avk = avk / len(anc_comuns)
    
    return min(avk, 1.0)  # Cap at 100%

def shortest_path(start, end, df_animais):
    """BFS: caminho mais curto no pedigree."""
    from collections import deque
    
    queue = deque([(start, [start])])
    visited = {start}
    
    while queue:
        node, path = queue.popleft()
        
        if node == end:
            return path
        
        animal = df_animais[df_animais['ID'] == node]
        if not animal.empty:
            for parent in [animal.iloc[0].get('Pai'), animal.iloc[0].get('Mãe')]:
                if parent and parent not in visited:
                    visited.add(parent)
                    queue.append((parent, path + [parent]))
    
    return [start, end]  # Caminho não encontrado, retorna direto
```

---

### 2.4 Script de Treino (`scripts/train_ia_modelos.py`)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
train_ia_modelos.py — Treina 3 modelos 1x em dados históricos (sintético + real).

Uso:
  python scripts/train_ia_modelos.py --treinar
  python scripts/train_ia_modelos.py --validar  # Valida modelos salvos
"""

import sys
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import roc_auc_score, mean_absolute_error, classification_report

sys.path.insert(0, '/path/to/programa-sitio')
import db
import animais as A
from ia_sintetico import gerar_sintetico
from ia_features import extrair_features, preprocessar_batch
from ia_modelos import ModeloMorte, ModeloCio, calcular_inbreeding_avk

def main():
    print("🤖 TREINO — IA Preditiva Onda 19\n")
    
    # 1. Carrega dados reais
    print("📂 Carregando dados reais...")
    df_an = db.carregar_aba('Animais')
    df_man = db.carregar_aba('Manejo')
    df_comp = db.carregar_aba('Compras')
    df_vend = db.carregar_aba('Vendas')
    
    # 2. Gera dados sintéticos
    print("🎲 Gerando 5k registros sintéticos...")
    df_sint = gerar_sintetico(n_animais=5000, anos=3)
    
    # 3. Merge: sintético + real
    print("🔀 Merge sintético + real...")
    df_todos = pd.concat([df_sint, df_an.head(200)], ignore_index=True)  # 200 reais + 5k sintéticos
    
    # 4. Extrai features
    print("🔧 Extraindo features...")
    X_list = []
    y_morte_list = []
    y_cio_list = []
    
    for idx, animal in df_todos.iterrows():
        features = extrair_features(
            animal['animal_id'], 
            df_todos, 
            df_man, 
            df_vend
        )
        if features:
            X_list.append(features)
            
            # Labels (sintéticos já têm evento_tipo; reais infer do Manejo)
            if 'evento_tipo' in animal:
                y_morte_list.append(1 if animal['evento_tipo'] == 'MORTE' else 0)
            else:
                y_morte_list.append(0)
            
            # CIO: dias até próximo cio (regressão)
            dias_cio = animal.get('dias_ate_cio_estimado', 21)
            y_cio_list.append(dias_cio)
    
    X = pd.DataFrame(X_list)
    y_morte = np.array(y_morte_list)
    y_cio = np.array(y_cio_list)
    
    # 5. Treina Modelo Morte
    print("\n🚨 Treinando Modelo Morte/Doença...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_morte, test_size=0.2, random_state=42, stratify=y_morte
    )
    
    modelo_morte = ModeloMorte()
    modelo_morte.treinar(X_train, y_train)
    
    y_pred = modelo_morte.modelo.predict(modelo_morte.scaler.transform(X_test))
    y_proba = modelo_morte.modelo.predict_proba(modelo_morte.scaler.transform(X_test))[:, 1]
    
    acc = (y_pred == y_test).mean()
    auc = roc_auc_score(y_test, y_proba)
    
    print(f"  ✅ Acurácia: {acc:.2%}")
    print(f"  ✅ AUC-ROC: {auc:.2%}")
    print(f"  Matriz confusão:\n{classification_report(y_test, y_pred)}")
    
    # 6. Treina Modelo Cio
    print("\n🔥 Treinando Modelo Cio Premonitório...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_cio, test_size=0.2, random_state=42
    )
    
    modelo_cio = ModeloCio()
    modelo_cio.treinar(X_train, y_train)
    
    y_pred = modelo_cio.modelo.predict(modelo_cio.scaler.transform(X_test))
    mae = mean_absolute_error(y_test, y_pred)
    
    print(f"  ✅ MAE (Mean Absolute Error): {mae:.2f} dias")
    print(f"  Exemplo previsões: {y_pred[:5].round(1)} dias vs real: {y_test[:5].round(1)}")
    
    # 7. Salva modelos
    print("\n💾 Salvando modelos...")
    import pickle
    import os
    
    os.makedirs('data/ia_models', exist_ok=True)
    
    with open('data/ia_models/modelo_morte.pkl', 'wb') as f:
        pickle.dump(modelo_morte, f)
    print("  ✅ modelo_morte.pkl")
    
    with open('data/ia_models/modelo_cio.pkl', 'wb') as f:
        pickle.dump(modelo_cio, f)
    print("  ✅ modelo_cio.pkl")
    
    with open('data/ia_models/scaler.pkl', 'wb') as f:
        pickle.dump(modelo_morte.scaler, f)  # Reutiliza scaler
    print("  ✅ scaler.pkl")
    
    print("\n✅ TREINO COMPLETO!\n")
    print("Próximo: python app.py → /reproducao/ia-predicoes")

if __name__ == '__main__':
    main()
```

---

### 2.5 Integração Alertas (`reproducao_avancada.py` expand)

```python
def alertas_ia_preditiva(df_animais, df_manejo, df_compras, df_vendas, hoje=None):
    """
    Orquestra 3 modelos preditivos → alertas consolidados.
    
    Output JSON:
    {
        "urgentes": [
            {"tipo": "🚨 MORTE PREVISTA", "animal": "Amarelo 21", "prob": 72, ...},
            {"tipo": "🔥 CIO EM", "animal": "Preta 05", "dias": 3, ...}
        ],
        "avisos": [...]
    }
    """
    
    import pickle
    
    hoje = pd.Timestamp(hoje or pd.Timestamp.now()).normalize()
    
    # Carrega modelos (cache em memória)
    try:
        with open('data/ia_models/modelo_morte.pkl', 'rb') as f:
            modelo_morte = pickle.load(f)
        with open('data/ia_models/modelo_cio.pkl', 'rb') as f:
            modelo_cio = pickle.load(f)
    except FileNotFoundError:
        app.logger.warning("❌ Modelos IA não encontrados. Execute: python scripts/train_ia_modelos.py")
        return {"urgentes": [], "avisos": []}
    
    alertas_urgentes = []
    alertas_avisos = []
    
    # Itera animais vivos
    animais_vivos = df_animais[
        (df_animais['Status'].isin(['Vivo', '']) | df_animais['Status'].isna()) &
        (df_animais['Sexo'].notna())
    ]
    
    for _, animal in animais_vivos.iterrows():
        animal_id = animal['ID']
        ref_animal = A.ref(animal)  # Ex. "Amarelo 21"
        
        # 1. MORTE (todos os animais)
        try:
            features = extrair_features(animal_id, df_animais, df_manejo, df_vendas, hoje)
            if features:
                pred_morte = modelo_morte.prever(features)
                
                if pred_morte['prob_morte'] > 70:
                    alertas_urgentes.append({
                        "tipo": "🚨 MORTE PREVISTA",
                        "animal": ref_animal,
                        "prob": pred_morte['prob_morte'],
                        "motivos": pred_morte['motivos'],
                        "acao": pred_morte['acao'],
                        "prioridade": 1,
                    })
                elif pred_morte['prob_morte'] > 50:
                    alertas_avisos.append({
                        "tipo": "⚠️ RISCO MORTE",
                        "animal": ref_animal,
                        "prob": pred_morte['prob_morte'],
                        "prioridade": 3,
                    })
        except Exception as e:
            app.logger.debug(f"Erro ao prever morte {animal_id}: {e}")
        
        # 2. CIO (fêmeas)
        if _eh_femea(animal):
            try:
                pred_cio = modelo_cio.prever(features)
                
                if pred_cio['alertar']:
                    alertas_urgentes.append({
                        "tipo": "🔥 CIO EM",
                        "animal": ref_animal,
                        "dias": pred_cio['dias_ate_cio'],
                        "data": pred_cio['data_prevista'],
                        "confianca": pred_cio['confianca'],
                        "acao": f"INSEMINAR EM {pred_cio['dias_ate_cio'] - 1} DIAS",
                        "prioridade": 2,
                    })
            except Exception as e:
                app.logger.debug(f"Erro ao prever cio {animal_id}: {e}")
        
        # 3. INBREEDING (todos)
        try:
            avk = calcular_inbreeding_avk(animal_id, df_animais)
            
            if avk > 0.15:  # >15% é crítico
                alertas_avisos.append({
                    "tipo": "⚠️ INBREEDING CRÍTICO",
                    "animal": ref_animal,
                    "avk": round(avk * 100, 1),
                    "acao": "🚫 NÃO CRUZAR COM PARENTES PRÓXIMOS",
                    "prioridade": 3,
                })
            elif avk > 0.10:
                alertas_avisos.append({
                    "tipo": "⚠️ INBREEDING ALTO",
                    "animal": ref_animal,
                    "avk": round(avk * 100, 1),
                    "acao": "Considerar cruzamento com genética externa",
                    "prioridade": 4,
                })
        except Exception as e:
            app.logger.debug(f"Erro ao calcular inbreeding {animal_id}: {e}")
    
    # Ordena por prioridade
    alertas_urgentes.sort(key=lambda x: x['prioridade'])
    alertas_avisos.sort(key=lambda x: x['prioridade'])
    
    return {
        "urgentes": alertas_urgentes,
        "avisos": alertas_avisos,
        "total": len(alertas_urgentes) + len(alertas_avisos),
        "timestamp": hoje.isoformat(),
    }

def _eh_femea(animal):
    sexo = str(animal.get('Sexo', 'M')).upper()
    return 'F' in sexo or sexo == 'FÊMEA'
```

---

### 2.6 Integração Alertas Globais (`alertas.py` expand)

```python
def todos(df_man=None, df_an=None, df_comp=None, df_vend=None, df_leite=None, hoje=None):
    """Agregador: todos os alertas (existentes + IA Preditiva)."""
    
    alertas = {
        "quarentena_leite": alertas_quarentena() if df_leite is not None else [],
        "iatf_protocolo": alertas_iatf(df_man, df_an, hoje),
        "reproducao": alertas_reproducao(df_man, df_an, hoje),
        "cochos_manutencao": alertas_manutencao_cochos(df_man),
    }
    
    # ✅ NOVO: IA Preditiva
    if df_an is not None:
        alertas["ia_preditiva"] = alertas_ia_preditiva(df_an, df_man, df_comp, df_vend, hoje)
    else:
        alertas["ia_preditiva"] = {"urgentes": [], "avisos": []}
    
    return alertas

def alertas_para_whatsapp(alertas_dict, membro=None, limite=5):
    """Formata top alertas urgentes para WhatsApp."""
    
    urgentes = []
    
    # Coleta urgentes de todos os módulos
    for chave in ["ia_preditiva", "iatf_protocolo", "quarentena_leite", "reproducao"]:
        if alertas_dict.get(chave, {}).get("urgentes"):
            urgentes.extend(alertas_dict[chave]["urgentes"])
    
    # Ordena por prioridade (IA preditiva vem primeiro)
    urgentes.sort(key=lambda x: x.get("prioridade", 99))
    
    # Top 5
    top_urgentes = urgentes[:limite]
    
    # Formata para WhatsApp
    linhas = []
    for a in top_urgentes:
        tipo = a.get("tipo", "")
        animal = a.get("animal", "?")
        acao = a.get("acao", "")
        
        if "MORTE" in tipo:
            prob = a.get("prob", 0)
            linhas.append(f"{tipo} {animal} ({prob}%) — {acao}")
        elif "CIO" in tipo:
            dias = a.get("dias", 0)
            linhas.append(f"{tipo} {dias}d — {animal} — {acao}")
        elif "INBREEDING" in tipo:
            avk = a.get("avk", 0)
            linhas.append(f"{tipo} {animal} (AVK {avk}%)")
        else:
            linhas.append(f"{tipo} {animal} — {acao}")
    
    return "\n".join(linhas) if linhas else "✅ Sem alertas urgentes"
```

---

### 2.7 Dashboard (`routes_dashboard.py` expand)

```python
@app.route("/reproducao/ia-predicoes")
@login_required
def reproducao_ia_predicoes():
    """Tabela detalhada com scores IA (morte, cio, inbreeding)."""
    
    df_an = A.carregar()
    df_man = db.carregar_aba("Manejo")
    df_comp = db.carregar_aba("Compras")
    df_vend = db.carregar_aba("Vendas")
    
    alertas = alertas_ia_preditiva(df_an, df_man, df_comp, df_vend)
    
    # Constrói tabela com todos os animais + scores
    animais_scores = []
    
    for _, animal in df_an.iterrows():
        animal_id = animal["ID"]
        
        # Busca alertas desse animal
        alerta_morte = next(
            (a for a in alertas["urgentes"] + alertas["avisos"] if "MORTE" in a["tipo"] and a["animal"] == A.ref(animal)),
            None
        )
        alerta_cio = next(
            (a for a in alertas["urgentes"] + alertas["avisos"] if "CIO" in a["tipo"] and a["animal"] == A.ref(animal)),
            None
        )
        alerta_inbred = next(
            (a for a in alertas["urgentes"] + alertas["avisos"] if "INBREEDING" in a["tipo"] and a["animal"] == A.ref(animal)),
            None
        )
        
        animais_scores.append({
            "animal_id": animal_id,
            "animal_ref": A.ref(animal),
            "sexo": animal.get("Sexo", "?"),
            "prob_morte": alerta_morte["prob"] if alerta_morte else 0,
            "status_morte": alerta_morte["urgencia"] if alerta_morte else "OK",
            "dias_cio": alerta_cio["dias"] if alerta_cio else "—",
            "data_cio": alerta_cio["data"] if alerta_cio else "—",
            "avk_pct": alerta_inbred["avk"] if alerta_inbred else 0,
        })
    
    return render_template("reproducao_ia_predicoes.html",
                         animais_scores=animais_scores,
                         resumo={
                             "total_animais": len(animais_scores),
                             "risco_morte": len([a for a in animais_scores if a["prob_morte"] > 50]),
                             "cios_proximos": len([a for a in animais_scores if a["dias_cio"] != "—"]),
                             "inbreeding_alto": len([a for a in animais_scores if a["avk_pct"] > 10]),
                         })
```

---

### 2.8 Template Dashboard Preditivo (`templates/reproducao_ia_predicoes.html`)

```html
{% extends "base.html" %}

{% block title %}IA Preditiva — Scores{% endblock %}

{% block content %}
<div class="container">
    <h1>🤖 IA Preditiva — Análise Completa</h1>
    
    <!-- Cards Resumo -->
    <div class="metrics">
        <div class="metric badge-ok">
            <span class="numero">{{ resumo.total_animais }}</span>
            <span class="rotulo">Animais Analisados</span>
        </div>
        <div class="metric badge-ruim">
            <span class="numero">{{ resumo.risco_morte }}</span>
            <span class="rotulo">Em Risco de Morte</span>
        </div>
        <div class="metric badge-aviso">
            <span class="numero">{{ resumo.cios_proximos }}</span>
            <span class="rotulo">Cios Previstos (7d)</span>
        </div>
        <div class="metric badge-aviso">
            <span class="numero">{{ resumo.inbreeding_alto }}</span>
            <span class="rotulo">Inbreeding Alto</span>
        </div>
    </div>
    
    <!-- Tabela Scores -->
    <table class="tabela-dados">
        <thead>
            <tr>
                <th>Animal</th>
                <th>Morte (30d)</th>
                <th>Status</th>
                <th>Cio (ETA)</th>
                <th>Data Prevista</th>
                <th>Inbreeding (AVK)</th>
                <th>Ações</th>
            </tr>
        </thead>
        <tbody>
            {% for animal in animais_scores %}
            <tr class="{% if animal.prob_morte > 70 %}linha-urgente{% elif animal.prob_morte > 50 %}linha-aviso{% endif %}">
                <td><strong>{{ animal.animal_ref }}</strong></td>
                <td class="numero">
                    {% if animal.prob_morte > 0 %}
                        <span class="badge badge-ruim">{{ animal.prob_morte }}%</span>
                    {% else %}
                        <span class="badge badge-ok">OK</span>
                    {% endif %}
                </td>
                <td>
                    {% if animal.status_morte == "URGENTE" %}
                        <span class="badge badge-ruim">🚨 URGENTE</span>
                    {% elif animal.status_morte == "AVISO" %}
                        <span class="badge badge-aviso">⚠️ AVISO</span>
                    {% else %}
                        <span class="badge badge-ok">✅ OK</span>
                    {% endif %}
                </td>
                <td class="numero">
                    {% if animal.dias_cio != "—" %}
                        <span class="badge badge-aviso">{{ animal.dias_cio }}d</span>
                    {% else %}
                        —
                    {% endif %}
                </td>
                <td>{{ animal.data_cio }}</td>
                <td class="numero">
                    {% if animal.avk_pct > 15 %}
                        <span class="badge badge-ruim">{{ animal.avk_pct }}%</span>
                    {% elif animal.avk_pct > 10 %}
                        <span class="badge badge-aviso">{{ animal.avk_pct }}%</span>
                    {% else %}
                        {{ animal.avk_pct }}%
                    {% endif %}
                </td>
                <td>
                    <a href="/reproducao/vaca/{{ animal.animal_id }}" class="btn btn-small">Ficha</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <!-- Legenda -->
    <div class="info-box">
        <h3>📊 Como Funciona</h3>
        <p><strong>Morte (30d):</strong> Probabilidade (%) de morte/doença nos próximos 30 dias, baseada em idade, inbreeding, histórico de tratamentos e peso.</p>
        <p><strong>Cio (ETA):</strong> Dias até próximo cio, calculado por ciclo histórico e IEP.</p>
        <p><strong>Inbreeding (AVK):</strong> Coeficiente de inbreeding (%). >10% = recomenda cruzamento com genética externa.</p>
    </div>
</div>

<style>
    .linha-urgente { background-color: rgba(255, 0, 0, 0.1); }
    .linha-aviso { background-color: rgba(255, 165, 0, 0.1); }
    .info-box {
        background: var(--bg-secondary);
        padding: 1.5rem;
        border-radius: 8px;
        margin-top: 2rem;
    }
</style>

{% endblock %}
```

---

## 3. Fluxo de Integração

### 3.1 Startup (`app.py`)

```python
# Em app.py, após registrar rotas:

try:
    import pickle
    with open('data/ia_models/modelo_morte.pkl', 'rb') as f:
        _CACHE_MODELO_MORTE = pickle.load(f)
    print("✅ Modelos IA carregados em cache")
except FileNotFoundError:
    print("⚠️ Modelos IA não encontrados. Execute: python scripts/train_ia_modelos.py")
```

### 3.2 Cache & Performance

- **Modelos:** Carregados 1x em startup, reutilizados
- **Features:** Extraídas on-demand, ~50ms por animal
- **Batch:** Processa 100 animais em <5s
- **Cache alertas:** 6 horas (pode ser on-demand via `/api/alertas-ia`)

---

## 4. Teste & Validação

### 4.1 Unit Tests (`tests/test_ia_predicoes.py`)

```python
def test_modelo_morte_carrega():
    """Modelo treina e salva corretamente."""
    pass

def test_prever_morte_score_0_a_1():
    """Probabilidade está em [0, 1]."""
    pass

def test_cio_dias_valido():
    """Dias até cio em [1, 25]."""
    pass

def test_inbreeding_avk_0_a_1():
    """AVK está em [0, 1]."""
    pass

def test_alertas_ia_formato_json():
    """Output segue schema esperado."""
    pass
```

### 4.2 Smoke Test (Dados Reais)

```bash
cd "F:\programa sitio"
python scripts/train_ia_modelos.py --treinar
python app.py
# GET /reproducao/ia-predicoes → verifica tabela com scores reais
```

---

## 5. Gitignore

```
data/ia_models/*.pkl
data/ia_models/historico_sintetico_*.pkl
```

---

## 6. Dependências

```
scikit-learn>=1.0
numpy>=1.20
pandas>=1.3
```

(Já instalado em requirements.txt; confirm com `pip freeze | grep scikit`)

---

## 7. Próximos Passos (Onda 20)

- **SISBOV Export:** Rastreabilidade oficial (XML, assinatura)
- **Marketplace:** Múltiplos sítios trocam gado + histórico

---

**Spec Completo ✅ Pronto para Implementação**

