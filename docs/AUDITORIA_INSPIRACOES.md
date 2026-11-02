# Auditoria das inspirações (pasta `exemplos`) — o que falta no sistema

Data: 2026-11-01 · Cruzamento do catálogo de 62 telas (`exemplos/CATALOGO.md`, `dados_analise.json`
e a descrição funcional das telas) com o código em produção na `feat/v5.14-onda14-ponto-corte-relatorios`.

**Resposta curta: ~90% das inspirações já estão implementadas.** Faltam 9 itens, sendo 5 baratos.
A sugestão de migrar para PostgreSQL que veio junto com as referências **não se aplica** — ver fim.

---

## 1. Matriz de cobertura (referência → o que existe aqui)

### Nutrição e comparativo de insumos (BOI GORDO, Ponta BI)

| Item da referência | Status | Onde |
|---|---|---|
| Comparativo de insumos lado a lado | ✅ | `insumos.comparar()` — R$/kg, R$/cab/dia, `/insumos/comparar` |
| Preço do saco, kg/saco | ✅ | idem + aba `Insumos` (marca, PB%, energia) |
| GMD previsto por produto | ❌ | não existe em lugar nenhum |
| Consumo por % do peso vivo | ⚠️ | hoje é `consumo_g` fixo (g/cab/dia), não %PV |
| Custo diário alimentar (diária) | ✅ | `comparar()` |
| Custo por @ produzida / lucro projetado / rentabilidade % | ❌ | `ponto_corte.py` faz o análogo por animal (vender hoje vs. esperar), mas não simula "bote" por dieta |
| Balanço nutricional MS/PB/Energia | ✅ | `racao.py` (fórmulas Embrapa, balanceia 1-3 ingredientes) |
| Minerais (Ca/P) e NDF | ❌ | `racao.py` só MS/PB/EM |
| Vender hoje vs. esperar (ponto de corte) | ✅ | `/ponto-corte` (v5.14) |

### Zootecnia, pasto e rebanho

| Item | Status | Onde |
|---|---|---|
| UA/ha vs. capacidade, % ocupação, semáforo | ✅ | `pastos.py` (`nivel()`, `total_lotacao()`) + `pastos_ocupacao.py` (rotação, ciclos) |
| @/ha produzida (produtividade por área) | ❌ | `indicadores_v58.gmd_lotacao_analise()` cruza GMD × lotação, mas não converte em @/ha |
| Peso total do rebanho, valor em @ | ✅ | dashboard (`animais`, arrobas) |
| GMD médio, curva de peso por animal | ✅ | `pesagem.py`, ficha do animal |
| Cotação da @ (CEPEA/Esalq/IMEA) | ✅ | `routes_api.py` (IMEA com cache + Scot de reserva) |
| Composição por categoria/sexo | ✅ | `animais.composicao()` |
| Peso estimado por foto | ✅ | `peso_foto.py` (com fator de calibração por balança) |
| Escore morfofisiológico EPMURAS (E,P,M,U,R,A,S) | ❌ | nada no código (guia visual da imagem 6) |

### Custos e BI

| Item | Status | Onde |
|---|---|---|
| Custo médio por cabeça (média móvel) | ✅ | `calculos.py` + `lotes.py` (FIFO) |
| Confinamento: GMD do lote, custo/cab, receita em @ | ✅ | `confinamento.py` |
| Break-even (preço mínimo da @ p/ cobrir custo) | ❌ | deriva do custo acumulado ÷ @ existentes |
| Fixo vs. variável | ❌ | `Gastos` tem `Tipo`, sem essa separação |
| Margem bruta/operacional/líquida | ⚠️ | tem resultado por membro + margem gauge; não as 3 margens por lote |
| Previsto vs. realizado (caixa) | ❌ | só realizado (comparativo anual) — **não fazer** (contabilidade, não é dor do sítio) |

### Sanidade

| Item | Status | Onde |
|---|---|---|
| Medicações individuais/lote com carência | ✅ | `medicacoes.py` + `doencas_carencia.py` |
| Quarentena do leite por antibiótico (descarte) | ✅ | `medicacoes.py` calcula liberação automática |
| Calendário sanitário + vacinas por prazo | ✅ | `saude.py` + calendário unificado (cores por urgência) |
| Mortalidade de bezerros | ✅ | `indicadores_v58.py` (aba própria, causas) |
| Morbidade por doença/mês (epidemiologia) | ❌ | não cruza `Doenças` × animais |
| Custo sanitário por doença/marca | ❌ | `Gastos` tem `Produto`, mas sem cruzamento |
| Ranking de causas (barras horizontais) | ⚠️ | tem a função de gráfico; sem tela de ranking |
| Treemap de tratamentos por curral | ❌ | nem existe entidade "curral" (pasto é o recorte) |

### Leite e reprodução

| Item | Status | Onde |
|---|---|---|
| Ativos, em lactação, DEL, IEP, litros/mês, acumulados | ✅ | `leite.py` painel |
| Curva de lactação + persistência | ✅ | `/leite/animal/<id>` |
| Taxa de prenhez | ✅ | `reproducao.indicadores()` |
| Taxa de serviço e de concepção | ❌ | só prenhez/IEP — dados p/ calcular já existem |
| Situação por vaca (prenha/vazia/pariu/atrasada) | ✅ | `reproducao.situacao()` |
| Parto previsto (283-285d), toque 35d, secagem 60d | ✅ | `reproducao.py` + `partos_predicao.py` |
| Alerta de cio (momento ideal +12h, intensidade) | ✅ | `reproducao_avancada.py` + IA preditiva ≤7d |
| Culling score | ✅ | `reproducao_avancada.py` |
| CCS/CPP com alertas | ✅ | `alertas.py` (limiares 200k/400k e 100k/500k) |
| Média geométrica mensal/trimestral de CCS/CPP | ❌ | hoje só a última leitura |
| Gordura/proteína do leite | ❌ | colunas não existem |
| Mastite, conforto térmico, colchão | ✅ | `leite.py` / `alertas.py` |
| Alerta de parto próximo | ✅ | `partos_predicao.py` |

### IoT / precisão

| Item | Status | Onde |
|---|---|---|
| Sensores (balança/colar/comedouro) + emuladores + fila offline | ✅ | Onda 16 |
| Ruminação (min/12h), THI, horas ofegantes | ❌ | sem hardware; conforto térmico do leite é subjetivo (score) |
| Alertas consolidados (IA + leite + IoT) | ✅ | `alertas.todos()` |

### Mobile / campo

| Item | Status | Onde |
|---|---|---|
| PWA offline-first (fila IndexedDB, anti-duplicata) | ✅ | `fila_visitas.js`, `fila_fotos.js` |
| Manejo rápido por voz + prefill de formulário | ✅ | `comando_voz.py`, `voz_campos.js` |
| Ficha rápida com GMD/@/gráficos | ✅ | ficha do animal |
| Calendário acionável com urgência por cores | ✅ | v5.10 |
| RFID/brinco eletrônico (NFC) | ⚠️ | brinco visual (cor/nº); leitura NFC não — voz cobre o caso |
| Checklists de campo (fezes/lama/bebedouro/comportamento) | ❌ | ver `ANALISE_CONCORRENTES.md` §3: só se sentir falta |

### Visualização

Biblioteca: **Chart.js já usada — mantida** (radar é nativo, zero dependência nova).
Recharts/PowerBI Embedded não se aplicam (não é React, não é BI corporativo).

| Componente | Status | Onde |
|---|---|---|
| KPI cards, gauge, donut, barras (vert./horiz.), linhas, área empilhada, duplo eixo | ✅ | `graficos-sistema.js` + `charts-gauge.js` |
| Radar | ❌ | ~20 linhas (Chart.js nativo) |
| Treemap | ❌ | sem fonte de dados que peça |

---

## 2. Regra de especificidade por fase (o que muda entre Corte e Leite)

- **Comum:** sanidade, pastos/lotação, financeiro (média móvel), tarefas, multi-sítio, WhatsApp.
- **Corte (cria→recria→engorda):** GMD e @ como unidade de resultado (`pesagem`, `lotes` FIFO, `confinamento`, `ponto_corte`), desmama (**lacuna**: não existe como evento), EPMURAS na seleção.
- **Leite:** litros e CCS/CPP como unidade (`leite.py`), carência de antibiótico bloqueia o leite (não a venda de gado), curva de lactação, IEP por vaca.
- **Cocho compartilhado:** o mesmo animal pode passar pelas duas contas — o sistema já separa ("Separado das contas do rebanho de corte", CLAUDE.md) e está certo.

---

## 3. Lacunas em ordem de retorno

| # | O quê | Esforço | Por quê |
|---|---|---|---|
| 1 | Taxa de serviço + concepção | ~1 h | `reproducao.indicadores()` já tem os insumos (coberturas, diagnósticos). Só a conta e mais duas gauges. |
| 2 | Média geométrica CCS/CPP (mês/trimestre) | ~2 h | Exigência normativa de leite (IN 62); hoje só a última leitura dispara alerta. |
| 3 | Radar (5 eixos: sanidade, ganho, custo, reprodução, margem) | ~3 h | `graficos_pizza`-style em `graficos-sistema.js`; a inspiração veio 3× no catálogo. |
| 4 | Simulador de dieta com GMD previsto → custo/@, lucro projetado | ~meio dia | Estende `insumos.comparar()`: entra GMD previsto e consumo %PV → sai dias de trato, custo/@ produzida, lucro/animal, rentabilidade %. É o BOI GORDO. |
| 5 | @/ha produzida | ~meio dia | `gmd_lotacao_analise()` já cruza GMD × lotação; falta `@ = cab × GMD × dias ÷ área` e um card. |
| 6 | EPMURAS no cadastro | ~meio dia | 7 colunas no fim da aba `Animais` (nota 1-6) + bloco na ficha. Peso por foto já dá o "quanto"; isso dá o "quão bom". |
| 7 | Break-even da @ | ~2 h | custo acumulado ÷ @ do rebanho = preço mínimo; um card no painel. |
| 8 | Gordura/proteína do leite | ~meio dia | 2 colunas novas (fim da aba) + linha no gráfico de qualidade. |
| 9 | Morbidade/custo por doença | ~1 dia | Cruza `Doenças` × `Gastos`; barras horizontais já existem. |

**Não fazer** (inspiração que não serve): THI/ruminação (exige hardware que não se paga para o rebanho deles), previsto vs. realizado de caixa, treemap por curral (não há curral), "fazenda vs. mercado" (comparar com a capacidade do próprio pasto é mais honesto que uma média de mercado inventada), checklists de escore de campo (`ANALISE_CONCORRENTES.md` §3 já avaliou).

---

## 4. Arquitetura de dados: por que NÃO migrar para PostgreSQL

As referências pedem "modelagem PostgreSQL", mas o requisito real delas é *suportar cálculo em tempo real + sincronização offline* — e o sistema já resolve os dois:

- **Cálculo:** abas do `.xlsx` carregadas em DataFrame com cache por versão de arquivo (`extensions._cache_dados`) — leitura é em memória, não no disco.
- **Offline:** PWA com fila IndexedDB e `ID Envio` anti-duplicata (`/api/visitas`, `/api/fotos`).
- **Migração de colunas:** `db.inicializar()` adiciona coluna no fim sem tocar nos dados — o mesmo papel de uma migration, para um schema que a família edita no Excel.
- Backups diários + rotação já cobrem o "dump".

Trocar xlsx por PostgreSQL é trocar o banco que a família consegue abrir e entender por um servidor para manter — custo alto, ganho zero no cálculo. Se um dia o rebanho passar de ~1.000 cabeças com registro diário, aí sim se repensa.

---

## 5. O que as imagens ainda ensinam e não virou item

- **PESO RURAL** (peso por foto): já coberto — inclusive melhor (fator de calibração por balança).
- **Ponta BI** (dashboards dark): estilo visual; o sistema é mobile-first claro — tema escuro não está no radar e não é pedido.
- **Guia EPMURAS**: virou lacuna #6.
