# Auditoria das inspirações (pasta `exemplos`) — o que falta no sistema

Data: 2026-11-01 · Revisada em 2026-11-02 contra o código na `main` (v5.15).
Cruzamento do catálogo de 62 telas (`exemplos/CATALOGO.md`, `dados_analise.json`
e a descrição funcional das telas) com o que está em produção.

**Resposta curta: ~90% das inspirações já estão implementadas.** Faltam 10 itens, sendo 5 baratos —
os 5 defeitos que estavam em código no ar (§3) foram corrigidos na v5.16, um deles de segurança alimentar.
A sugestão de migrar para PostgreSQL que veio junto com as referências **não se aplica** (§5).

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
| Break-even (custo por cabeça do rebanho vivo) | ✅ | `calculos.py` (`break_even = capital_imobilizado / estoque`), em `/`, `/financeiro`, `/relatorios` e no form de venda. **Não** é "preço mínimo da @" — é R$/cabeça; a versão em @ é `arrobas_min_cab` (também já existe) |
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
| Carência bloqueia a ordenha (não só avisa) | ⚠️ | **B4** corrigido: todas as telas leem a mesma fonte. O bloqueio em si continua sendo aviso na venda — bloquear de verdade é decisão de produto |
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

## 3. Defeitos encontrados na revisão de 2026-11-02 (corrigidos na v5.16)

Nenhum era "falta de módulo": eram contas erradas ou código morto que já estava no ar.

| # | O quê | Onde | Efeito | Status |
|---|---|---|---|---|
| **B1** | `confinamento.custo_por_lote()` dividia a arroba por **30 kg** em vez de 15 | `confinamento.py` | Metade das arrobas → **metade da receita** e "margem" negativa falsa. 450 kg × 58 % = 17,4 @, o código calculava 8,7 @. A função só era chamada por teste, então o bug estava **latente** | ✅ `/15` + teste fixando R$ 5.220/cab |
| **B2** | `dashboard-exemplo-graficos` era uma rota **sem `login_required`** e mostra números fixos (425 animais, 220 em lactação, IEP 12,4) | `routes_dashboard.py` | Vazava a estrutura interna do sistema para quem não fez login, e é a única página com números inventados | ✅ `@login_required` + teste |
| **B3** | O filtro por dono contava sobre o rebanho **vivo inteiro**, mesmo com `?status=Vendido/Morto` ou filtro de categoria/sexo ativo | `animais.conferencia()` + `templates/animais.html` | Card dizia "12 de 15" e a tabela mostrava 3 linhas. Números que não fecham minam a confiança na tela | ✅ conta o recorte que a tela mostra |
| **B4** | A carência que alimenta o painel de alertas lia `Leite Tratamentos`; a que valida venda/leite lia `Tratamentos` (outra aba) e a quarentena de `medicacoes.py` lia `Medicações` (uma terceira) | `routes_alertas.py` × `doencas_carencia.py` × `medicacoes.py` × `routes_leite.py` | Três fontes para a mesma regra: um animal podia estar em carência numa tela e liberado em outra. Item de **segurança alimentar** | ✅ `doencas_carencia.status_por_animal()` lê as 3 abas; prazo mais longo vence; todas as telas leem dele |
| **B5** | `_obter_carencia()` devolvia **48 dias** quando o remédio não estava na tabela, e a tabela guardava "48" como se fosse horas (Penicilina real: ~2-3 dias) | `doencas_carencia.py` | Conservador (nunca libera cedo demais), mas 48 dias de descarte por engano é prejuízo; e `Ceftiofur` caía no default | ✅ tabela em dias, Ceftiofur incluído, desconhecido usa 7/28 **e avisa na tela** |

B4 foi resolvido com `status_por_animal()` como fonte única (o teste `tests/test_carencia_unica.py` prova que as três abas do mesmo animal dão o mesmo status em todas as telas).

---

## 4. Lacunas em ordem de retorno
| # | O quê | Esforço | Por quê |
|---|---|---|---|
| 1 | Taxa de serviço + concepção | ~1 h | `reproducao.indicadores()` já tem os insumos (coberturas, diagnósticos). Só a conta e mais duas gauges. |
| 2 | Média geométrica CCS/CPP (mês/trimestre) | ~2 h | Exigência normativa de leite (IN 62); hoje só a última leitura dispara alerta. |
| 3 | Radar (5 eixos: sanidade, ganho, custo, reprodução, margem) | ~3 h | `graficos_pizza`-style em `graficos-sistema.js`; a inspiração veio 3× no catálogo. |
| 4 | Simulador de dieta com GMD previsto → custo/@, lucro projetado | ~meio dia | Estende `insumos.comparar()`: entra GMD previsto e consumo %PV → sai dias de trato, custo/@ produzida, lucro/animal, rentabilidade %. É o BOI GORDO. |
| 5 | @/ha produzida | ~meio dia | `gmd_lotacao_analise()` já cruza GMD × lotação; falta `@ = cab × GMD × dias ÷ área` e um card. |
| 6 | EPMURAS no cadastro | ~meio dia | 7 colunas no fim da aba `Animais` (nota 1-6) + bloco na ficha. Peso por foto já dá o "quanto"; isso dá o "quão bom". |
| 7 | Preço mínimo da @ (o "break-even" já existe em R$/cab) | ~1 h | `arrobas_min_cab` já está na tela; falta multiplicar pelo preço para dizer "não venda abaixo de R$X/@". |
| 8 | Gordura/proteína do leite | ~meio dia | 2 colunas novas (fim da aba) + linha no gráfico de qualidade. |
| 9 | Morbidade/custo por doença | ~1 dia | Cruza `Tratamentos` × `Gastos`; barras horizontais já existem. |
| 10 | Checklist de cocho no manejo (não só na visita) | ~2 h | v5.15 pôs o checklist em `Visitas`; o curral individual (`form_manejo.html`) ainda não tem fila offline nem cocho — é o caso de uso do celular na manga |

**Não fazer** (inspiração que não serve): THI/ruminação (exige hardware que não se paga para o rebanho deles), previsto vs. realizado de caixa, treemap por curral (não há curral), "fazenda vs. mercado" (comparar com a capacidade do próprio pasto é mais honesto que uma média de mercado inventada), checklists de escore de campo (`ANALISE_CONCORRENTES.md` §3 já avaliou), gauge/radar como *componente* novo (o `charts-gauge.js` existe e só é usado na página de exemplo — antes de criar gráfico novo, ligar o que já existe).

---

## 5. Arquitetura de dados: por que NÃO migrar para PostgreSQL

As referências pedem "modelagem PostgreSQL", mas o requisito real delas é *suportar cálculo em tempo real + sincronização offline* — e o sistema já resolve os dois:

- **Cálculo:** abas do `.xlsx` carregadas em DataFrame com cache por versão de arquivo (`extensions._cache_dados`) — leitura é em memória, não no disco.
- **Offline:** PWA com fila IndexedDB e `ID Envio` anti-duplicata (`/api/visitas`, `/api/fotos`).
- **Migração de colunas:** `db.inicializar()` adiciona coluna no fim sem tocar nos dados — o mesmo papel de uma migration, para um schema que a família edita no Excel.
- Backups diários + rotação já cobrem o "dump".

Trocar xlsx por PostgreSQL é trocar o banco que a família consegue abrir e entender por um servidor para manter — custo alto, ganho zero no cálculo. Se um dia o rebanho passar de ~1.000 cabeças com registro diário, aí sim se repensa.

### 5.1 "É possível converter para PostgreSQL?" — sim, e é a pior opção hoje

Medido neste repo (2026-11-02, dados reais de 315 linhas em 28 abas):

| Caminho | O que muda | Esforço | Ganho |
|---|---|---|---|
| **A. Trocar a implementação de `db.py`** (xlsx → SQLite/PostgreSQL, mantendo `carregar_aba`/`salvar_linha`/`reescrever_aba`) | 1 arquivo. Os 61 módulos e 212 chamadas continuam iguais, porque todos falam a API do `db`, não o Excel | ~2 dias para SQLite; +1 para Postgres | Escrita deixa de reescrever o arquivo inteiro |
| **B. Normalizar em tabelas relacionais de verdade** (Animais, Eventos, Lotes…) | Motor de cálculo (`calculos.py`, `lotes.py`, `pesagem.py`) e 63 módulos com pandas, 102 operações de `merge/groupby/apply` | meses | Nenhum para 315 linhas |
| **C. Manter Excel** | nada | 0 | é o que a família abre e entende |

Números que decidem: `carregar_todas()` = **66 ms**, `salvar_linha()` = **186 ms** num arquivo de 28 KB. Nada aqui é lento; o gargalo é o `save` do arquivo inteiro, que já é atômico e travado (`_trava_escrita` + `_salvar_atomico`).

**Recomendação:** se a dor for "dois celulares gravando ao mesmo tempo e um apaga o outro", o caminho **A com SQLite** resolve com 1 arquivo trocado e sem servidor para manter (o PythonAnywhere já tem `sqlite3` na stdlib). Postgres só se passar de ~1.000 cabeças **e** vários usuários gravando ao mesmo tempo — o que é o mesmo gatilho já registrado acima.

Atenção: hoje `db.DATA_DIR` é **trocado por requisição** entre sítios (`sitios.ativar`). Qualquer banco novo tem de seguir o mesmo desenho (um arquivo por pasta de sítio, caminho lido na hora, nunca `from db import DATA_DIR`).

---

## 6. O que as imagens ainda ensinam e não virou item

- **PESO RURAL** (peso por foto): já coberto — inclusive melhor (fator de calibração por balança).
- **Ponta BI** (dashboards dark): estilo visual; o sistema é mobile-first claro — tema escuro não está no radar e não é pedido.
- **Guia EPMURAS**: virou lacuna #6.
