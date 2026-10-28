# Coleta Automática de Dados para Indicadores (v5.8+)

## O que é

O sistema agora **coleta automaticamente dados** para três páginas de indicadores:

1. **Engorda vs Pastagem** (`/indicadores/engorda-pastagem`): GMD + lotação por pasto
2. **GMD vs Lotação** (`/indicadores/gmd-lotacao`): histórico correlação GMD vs UA/ha  
3. **Ração Consumo** (`/indicadores/racao-consumo`): eficiência alimentar (oferecido vs consumido)

Antes, essas abas eram vazias e exigiam **entrada manual**. Agora preenchem **automaticamente** conforme o usuário registra no manejo.

## Como funciona

### Aba: Engorda Pastagem

Alimentada quando o usuário registra em **Manejo** → **Movimentação de Pasto** + **Pesagem**.

**Fluxo:**
1. Usuário clica "Movimentação de Pasto" no manejo
2. Seleciona pasto, brincos e quantidade
3. Sistema registra entrada em "Engorda Pastagem" com dados parciais (pasto, brincos, lotação)
4. Usuário registra "Pesagem" do rebanho no pasto (peso inicial)
5. Sistema atualiza linha com peso inicial
6. Após 30 dias, usuário registra "Pesagem" novamente (peso final)
7. Sistema completa a linha com peso final, dias, GMD, consumo estimado

**Colunas** (config.py):
```
Data, Pasto ID, Brincos, Peso Inicial (kg), Peso Final (kg),
Dias no Pasto, GMD (kg/dia), Lotação (UA/ha), Condição Pasto,
Consumo Estimado (kg MS/dia), Observação, Responsável, ID Envio, Criado Em
```

**Função:** `indicadores_coleta.registrar_engorda_pastagem()`

---

### Aba: GMD Lotação

Alimentada quando o usuário **edita pesagem e informa pasto + período**.

**Fluxo:**
1. Usuário registra "Pesagem" com identificação do pasto onde estava
2. Informa duração do período (ex.: 30 dias)
3. Sistema calcula GMD = (peso_final - peso_inicial) / dias
4. Sistema registra em "GMD Lotação" com lotação (cabeças / área do pasto em UA/ha)

**Colunas:**
```
Data, Período (dias), Animais, Peso Inicial (kg), Peso Final (kg),
GMD (kg/dia), Pasto ID, Lotação (UA/ha), Capacidade (UA/ha),
% Ocupação, Qualidade Pasto, Clima, Observação, ID Envio, Criado Em
```

**Função:** `indicadores_coleta.registrar_gmd_lotacao()`

---

### Aba: Ração Consumo

Alimentada quando o usuário registra **Alimentação** no módulo leiteiro.

**Fluxo:**
1. Usuário vai a **Leite** → **Alimentação**
2. Registra tipo de ração (ex.: "Ração de Produção")
3. Informa quantidade oferecida (kg) e consumida (kg)
4. Sistema registra em "Ração Consumo" e calcula:
   - Taxa Consumo (%) = consumida / oferecida × 100
   - Desperdício (kg) = oferecida - consumida
   - % Desperdício = desperdício / oferecida × 100

**Colunas:**
```
Data, Tipo Ração, Quantidade Oferecida (kg), Quantidade Consumida (kg),
Taxa Consumo (%), Custo/kg, Custo Total Oferecido (R$), Desperdício (kg),
% Desperdício, Observação, Responsável, ID Envio, Criado Em
```

**Função:** `indicadores_coleta.registrar_racao_consumo()`

---

## Fluxo manual alternativo

Se o usuário preferir **entrar dados manualmente** (sem manejo), pode ir direto a:

- **Engorda Pastagem**: `/registros?aba=Engorda%20Pastagem`  
- **GMD Lotação**: `/registros?aba=GMD%20Lotação`  
- **Ração Consumo**: `/registros?aba=Ração%20Consumo`

Ou usar a API de coleta em `indicadores_coleta.py`:

```python
from indicadores_coleta import registrar_engorda_pastagem, registrar_gmd_lotacao, registrar_racao_consumo

# Engorda
registrar_engorda_pastagem(
    pasto_id="P001",
    brincos="Amarelo 21 #A0001; Azul 15 #A0002",
    peso_inicial=280,
    peso_final=360,
    dias=30,
    gmd=2.67,
    lotacao_ua_ha=1.2,
    condicao_pasto="bom"
)

# GMD Lotação
registrar_gmd_lotacao(
    periodo_dias=30,
    animais=15,
    peso_inicial=280,
    peso_final=360,
    gmd=2.67,
    pasto_id="P001",
    lotacao_ua_ha=1.2,
    capacidade_ua_ha=1.5,
    qualidade_pasto="bom"
)

# Ração Consumo
registrar_racao_consumo(
    tipo_racao="Ração de Produção",
    qty_oferecida=100,
    qty_consumida=92,
    custo_kg=2.50,
    observacao="Teste"
)
```

---

## Integração com rotas

Em `routes_registros.py`, após cada `salvar_linha("Manejo", ...)` (novo_manejo e editar_manejo):

```python
from indicadores_coleta import processar_manejo_automatico

processar_manejo_automatico(
    tipo_manejo=f.get("tipo", ""),
    brincos_str=form["brincos_refs"],
    descricao=f.get("descricao", "").strip(),
    pasto_id=f.get("pasto", ""),
    qtd_cabecas=_int_form(f.get("cabecas"))
)
```

A função `processar_manejo_automatico()` **dispatcha** para:
- `_processar_pesagem_automatica()` se tipo = "Pesagem"
- `_processar_movimentacao_automatica()` se tipo = "Movimentação de Pasto"
- `_processar_alimentacao_automatica()` se tipo = "Alimentação"

---

## Próximos passos (v5.9+)

1. **API de integração com pesagem automática** (balança):
   - Pesagem via `pesagem.py` dispara automaticamente registros em GMD Lotação
   - Calcula GMD de forma mais precisa (com histórico)

2. **Integração com sensores IoT** (temperatura, umidade):
   - "Clima" é preenchido automaticamente em GMD Lotação

3. **Dashboard dos indicadores** com gráficos em tempo real:
   - Correlação GMD vs UA/ha
   - Eficiência de conversão alimentar (kg de ração / kg de ganho)

---

## Garantias

- ✅ As abas `Engorda Pastagem`, `GMD Lotação`, `Ração Consumo` são criadas automaticamente no arquivo (v5.0+)
- ✅ Colunas são adicionadas sem perder dados (migração automática em `db.inicializar()`)
- ✅ Dados chegam preenchidos com a **data atual** e hora ISO (`Criado Em`)
- ✅ Campos vazios (pesagem parcial, dados faltando) são salvos com zeros/strings vazias
- ✅ Sem duplicatas: cada operação gera **uma linha** por operação (não agrupa)

---

## Arquivo de configuração

Todas as abas são definidas em `config.py`:

```python
COLUNAS_ENGORDA_PASTAGEM = [...]  # v5.8
COLUNAS_GMD_LOTACAO = [...]       # v5.8
COLUNAS_RACAO_CONSUMO = [...]     # v5.8
COLUNAS_MORTALIDADE_BEZERROS = [...]  # v5.8
```

E mapeadas em `db.py` → `_SCHEMA_ABAS`:

```python
_SCHEMA_ABAS = {
    ...
    "Engorda Pastagem": COLUNAS_ENGORDA_PASTAGEM,
    "GMD Lotação": COLUNAS_GMD_LOTACAO,
    "Ração Consumo": COLUNAS_RACAO_CONSUMO,
    ...
}
```

Portanto, **nenhuma mudança manual é necessária** — basta atualizar o código e as abas aparecem.
