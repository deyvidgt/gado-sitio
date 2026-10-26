# Reformulação de módulos e layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar o sistema em uma central de manejo clara no desktop e no celular, começando pelo dashboard e depois entregando calendário, ficha animal, pastos/insumos e financeiro sem quebrar os dados existentes.

**Architecture:** Reutilizar os motores de cálculo e as rotas atuais, concentrando a linguagem visual em `templates/base.html` e criando módulos somente quando a informação ainda não tiver uma tela própria. O calendário será somente leitura e normalizará eventos de módulos existentes; nenhuma nova aba da planilha será criada.

**Tech Stack:** Flask, Jinja2, CSS/JavaScript próprios, pandas, Chart.js já instalado no template, pytest, Excel via camada `db.py`.

**Spec:** `docs/superpowers/specs/2026-10-26-reformulacao-modulos-layout-design.md`

## Global Constraints

- A planilha continua sendo a fonte de dados; não reordenar colunas existentes.
- Colunas novas entram somente no fim das listas de `config.py` e passam pela migração existente.
- Não criar uma aba nova para dados que já existem em Manejo, Tarefas ou Visitas.
- Não adicionar dependência apenas para componentes de interface.
- A matemática financeira e suas invariantes permanecem inalteradas.
- A interface deve continuar funcionando para sítios com membros configuráveis e para dois a oito membros.
- Status sempre terá texto junto da cor.
- Peso de foto continua separado do peso de balança e nunca entra no GMD oficial.
- Nunca gravar no arquivo real durante testes; usar a fixture existente.
- Preservar o diff local não commitado em `pastos.py`, `pesagem.py`, `routes_animais.py`, templates e testes relacionados.

## Review Focus

- Planilha vazia ou com dados parciais: dashboard e calendário devem renderizar estados vazios, não 500. Teste em `tests/test_paginas.py` e `tests/test_calendario.py`.
- Dois ou oito membros configurados: cartões e navegação não podem assumir três donos. Teste em `tests/test_membros.py` e renderização do dashboard.
- Animal com peso somente estimado por foto: deve aparecer como aproximado e não alterar GMD. Teste em `tests/test_pesagem.py`.
- Evento com data inválida ou ausente: deve ser ignorado ou aparecer como sem data, sem derrubar a lista. Teste em `tests/test_calendario.py`.
- Tela móvel estreita: ações e cartões devem caber sem rolagem horizontal involuntária. Teste de presença de classes/markup e revisão visual em largura móvel.

---

### Task 1: Atualizar a especificação com a análise das referências

**Files:**
- Modify: `docs/superpowers/specs/2026-10-26-reformulacao-modulos-layout-design.md`

**Interfaces:**
- Produces: escopo aprovado para todas as fases, incluindo os elementos identificados nas 65 imagens e os itens explicitamente fora do escopo.

- [x] **Step 1: Consolidar no documento os achados das imagens**

Registrar dashboard com KPIs, ocorrências, filtros, módulos móveis, animais por categoria, pesagem por foto, mapa/descanso, calendário, sanidade, reprodução, insumos, lotes e avaliação visual; separar implementar, fase posterior e não implementar.

- [x] **Step 2: Revisar o documento**

Confirmar ausência de placeholders, contradições e promessas de dados que o sistema não possui.

---

### Task 2: Componentes visuais globais e navegação

**Files:**
- Modify: `templates/base.html`
- Test: `tests/test_paginas.py`

**Interfaces:**
- Produces: classes reutilizáveis `.estado-sitio`, `.acoes-rapidas`, `.ocorrencias`, `.modulo-grid`, `.status`, `.mobile-card` e agrupamento visual da navegação.

- [ ] **Step 1: Escrever testes de markup global**

Verificar que a resposta do dashboard contém os grupos “Rebanho”, “Campo”, “Financeiro” e “Ferramentas”, e que os componentes base possuem classes esperadas.

- [ ] **Step 2: Rodar os testes para registrar a falha**

Run: `python -m pytest tests/test_paginas.py -k "dashboard or menu" -v`
Expected: falha apenas nos novos marcadores.

- [ ] **Step 3: Implementar os tokens e componentes em `base.html`**

Adicionar estilos responsivos, foco visível e `prefers-reduced-motion`; reorganizar os links existentes sem alterar endpoints, permissões ou URLs.

- [ ] **Step 4: Rodar os testes**

Run: `python -m pytest tests/test_paginas.py -k "dashboard or menu" -v`
Expected: PASS.

- [ ] **Step 5: Verificar diferenças**

Run: `git diff --check`
Expected: nenhuma saída.

---

### Task 3: Agregadores do dashboard operacional

**Files:**
- Modify: `routes_dashboard.py`
- Modify: `templates/dashboard.html`
- Test: `tests/test_paginas.py`

**Interfaces:**
- Consumes: `_get_dados_cache()`, `_get_resumo_cache()`, `pesagem`, `pastos`, `insumos`, `reproducao`, `tarefas` e `saude` existentes.
- Produces: contexto `estado_sitio`, `acoes_rapidas`, `atencao_agora`, `ocorrencias` e `tendencia_peso`, todos tolerantes a dados ausentes.

- [ ] **Step 1: Escrever testes de contexto e estados vazios**

Adicionar cobertura para dashboard com dados normais, sem animais cadastrados, sem pesos, sem pastos e com tarefas/reprodução vazias; verificar que a resposta é 200 e contém os títulos dos blocos.

- [ ] **Step 2: Rodar os testes**

Run: `python -m pytest tests/test_paginas.py -k dashboard -v`
Expected: falha nos novos blocos/contexto.

- [ ] **Step 3: Implementar os agregadores**

Construir os dados no servidor, mantendo os cálculos atuais e sem gravar. Cada integração opcional deve ficar isolada em `try/except` com log, como `_cards_extras` já faz.

- [ ] **Step 4: Implementar o novo layout do dashboard**

Renderizar KPIs de estoque, peso, GMD, UA/ha e resultado; ações rápidas; alertas; composição; pastos/insumos; ocorrências e tendência. Usar texto para “estimado” e estados vazios orientados.

- [ ] **Step 5: Rodar testes e invariantes**

Run: `python -m pytest tests/test_paginas.py tests/test_calculos.py -v`
Expected: PASS.

---

### Task 4: Busca, filtros e ficha visual de animais

**Files:**
- Modify: `templates/animais.html`
- Modify: `templates/ficha_animal.html`
- Modify: `routes_animais.py`
- Test: `tests/test_paginas.py`
- Test: `tests/test_animais.py`

**Interfaces:**
- Consumes: cadastro por ID, `pesagem.resumo`, `pastos.situacao`, fotos e `reproducao.situacao` existentes.
- Produces: filtros GET não destrutivos e cartões de animal responsivos; nenhuma nova coluna nesta tarefa.

- [ ] **Step 1: Escrever testes de filtros**

Cobrir busca por ID/brinco, filtro por sexo/categoria/status e abertura da ficha sem registro de peso ou foto.

- [ ] **Step 2: Implementar filtros no servidor**

Usar query string, preservar valores selecionados e filtrar antes da renderização; sem alterar a origem dos dados.

- [ ] **Step 3: Implementar cartões e ficha**

Adicionar resumo por categoria, busca, ação de cadastro, peso/GMD, pasto, saúde, reprodução e linha do tempo disponível; mostrar vazio orientado quando faltar dado.

- [ ] **Step 4: Rodar testes**

Run: `python -m pytest tests/test_animais.py tests/test_paginas.py -v`
Expected: PASS.

---

### Task 5: Calendário operacional somente leitura

**Files:**
- Create: `calendario.py`
- Create: `routes_calendario.py`
- Create: `templates/calendario.html`
- Create: `tests/test_calendario.py`
- Modify: `app.py`
- Modify: `templates/base.html`

**Interfaces:**
- Produces: `calendario.eventos(dados, inicio=None, fim=None) -> list[dict]`, cada evento com `data`, `tipo`, `titulo`, `status`, `origem`, `url` opcional e `detalhes`.
- Consumes: `saude`, `reproducao`, `tarefas`, `Manejo` e `Visitas`; não grava.

- [ ] **Step 1: Escrever testes unitários**

Cobrir ordenação, filtros por tipo, datas inválidas ignoradas, eventos atrasados e ausência de cada fonte.

- [ ] **Step 2: Rodar o teste para verificar a falha**

Run: `python -m pytest tests/test_calendario.py -v`
Expected: falha porque `calendario.py` ainda não existe.

- [ ] **Step 3: Implementar normalização de eventos**

Converter cada origem para o contrato comum; usar `pd.to_datetime(..., dayfirst=True, errors='coerce')`; ignorar registros sem data válida.

- [ ] **Step 4: Implementar rota GET e template**

Adicionar `/calendario` com mês atual, próximos eventos, filtro por tipo e estados vazios. Registrar a rota em `app.py` e o link em Campo.

- [ ] **Step 5: Rodar testes**

Run: `python -m pytest tests/test_calendario.py tests/test_paginas.py -v`
Expected: PASS.

---

### Task 6: Pesagem, foto e histórico no fluxo móvel

**Files:**
- Modify: `templates/pesagem.html`
- Modify: `templates/peso_foto.html`
- Modify: `routes_animais.py`
- Modify: `pesagem.py`
- Test: `tests/test_pesagem.py`

**Interfaces:**
- Consumes: `pesagem.todas`, `pesagem.curva_evolucao_peso`, `peso_foto` e filas offline existentes.
- Produces: três modos visuais — balança, foto e histórico — mantendo a separação entre estimado e medido.

- [ ] **Step 1: Acrescentar testes para classificação de origem**

Verificar que peso de balança entra no GMD e peso estimado não entra, e que a tela identifica o valor estimado.

- [ ] **Step 2: Implementar abas/modos responsivos**

Reaproveitar as rotas existentes, adicionar ações grandes no celular e manter envio offline já existente.

- [ ] **Step 3: Integrar histórico**

Exibir curva, arrobas, GMD e animais sem pesagem recente, sem recalcular dados no JavaScript.

- [ ] **Step 4: Rodar testes**

Run: `python -m pytest tests/test_pesagem.py tests/test_paginas.py -v`
Expected: PASS.

---

### Task 7: Pastos, insumos e lotes no padrão visual

**Files:**
- Modify: `templates/pastos.html`
- Modify: `templates/lotes.html`
- Modify: `templates/comparar_insumos.html`
- Modify: `routes_pastos.py`
- Modify: `routes_lotes.py`
- Test: `tests/test_pastos.py`
- Test: `tests/test_lotes.py`

**Interfaces:**
- Consumes: `pastos.situacao`, `pastos.total_lotacao`, `insumos.previsao_todos` e `lotes` atuais.
- Produces: cartões de ocupação/descanso, estoque/previsão e desempenho de lotes; sem alterar cálculos FIFO ou lotação.

- [ ] **Step 1: Escrever testes de estados visuais**

Cobrir pasto ocupado, vazio, descansando, lotado, insumo sem previsão e lote sem peso.

- [ ] **Step 2: Implementar os cartões e filtros**

Usar classes de status com texto, dados aproximados marcados e layout de cartão móvel.

- [ ] **Step 3: Rodar testes**

Run: `python -m pytest tests/test_pastos.py tests/test_lotes.py -v`
Expected: PASS.

---

### Task 8: Sanidade e reprodução no dashboard/calendário

**Files:**
- Modify: `routes_dashboard.py`
- Modify: `templates/dashboard.html`
- Modify: `calendario.py`
- Test: `tests/test_saude.py`
- Test: `tests/test_reproducao.py`
- Test: `tests/test_calendario.py`

**Interfaces:**
- Consumes: alertas e indicadores já publicados por `saude.py` e `reproducao.py`.
- Produces: blocos de atenção sanitária/reprodutiva e eventos de parto, cobertura, diagnóstico e secagem.

- [ ] **Step 1: Escrever testes de alertas**

Cobrir vacina atrasada, brucelose sazonal, parto próximo, prenhez atrasada e ausência de alertas.

- [ ] **Step 2: Integrar sem duplicar regras**

Chamar os módulos existentes; não reimplementar intervalos sanitários ou cálculo reprodutivo no dashboard.

- [ ] **Step 3: Rodar testes**

Run: `python -m pytest tests/test_saude.py tests/test_reproducao.py tests/test_calendario.py -v`
Expected: PASS.

---

### Task 9: Avaliação visual do animal

**Files:**
- Create: `avaliacao_animal.py`
- Create: `templates/avaliacao_animal.html`
- Modify: `routes_animais.py`
- Modify: `config.py`
- Modify: `db.py`
- Create: `tests/test_avaliacao_animal.py`

**Interfaces:**
- Produces: `avaliacao_animal.validar(dados) -> dict` e leitura/gravação em uma nova aba somente se aprovada a migração de dados.

- [ ] **Step 1: Definir e testar critérios**

Usar escala de 1 a 5 para estrutura, precocidade, musculatura, umbigo, raça, aprumos e vigor reprodutivo; rejeitar valores fora da escala.

- [ ] **Step 2: Implementar persistência no fim da estrutura**

Criar a aba nova ou colunas somente no fim, sem alterar abas existentes; vincular por ID e registrar data/avaliador.

- [ ] **Step 3: Implementar tela na ficha**

Adicionar formulário e histórico de avaliações, com estados vazios e observações.

- [ ] **Step 4: Rodar testes**

Run: `python -m pytest tests/test_avaliacao_animal.py tests/test_paginas.py -v`
Expected: PASS.

---

### Task 10: Revisão financeira e relatórios

**Files:**
- Modify: `templates/lista.html`
- Modify: `templates/lotes.html`
- Modify: `templates/relatorios.html`
- Modify: `templates/dashboard.html`
- Test: `tests/test_calculos.py`
- Test: `tests/test_paginas.py`

**Interfaces:**
- Consumes: resultados atuais de `calculos.py` e `lotes.py`.
- Produces: apresentação consistente de custo, receita, margem, capital e resultado; nenhum cálculo novo sem teste de invariante.

- [ ] **Step 1: Escrever testes de apresentação e invariantes**

Verificar que os valores existentes aparecem com rótulos claros e que as três invariantes contábeis continuam verdadeiras.

- [ ] **Step 2: Aplicar cartões, filtros e listas móveis**

Não mudar a fonte nem a matemática; marcar estimativas e manter exportações.

- [ ] **Step 3: Rodar testes**

Run: `python -m pytest tests/test_calculos.py tests/test_paginas.py -v`
Expected: PASS.

---

### Task 11: Verificação completa e revisão visual

**Files:**
- Modify: qualquer arquivo necessário após os testes; não incluir dados reais.

- [ ] **Step 1: Rodar a suíte completa**

Run: `python -m pytest`
Expected: todos os testes passam.

- [ ] **Step 2: Verificar integridade do diff**

Run: `git diff --check`
Expected: nenhuma saída.

- [ ] **Step 3: Executar smoke test com cópia dos dados**

Usar `GADO_DATA_DIR` temporário e confirmar dashboard, calendário, animais, pesagem, pastos, lotes e relatórios sem alterar `gado_familia.xlsx` real.

- [ ] **Step 4: Revisar em desktop e celular**

Abrir `/`, `/animais`, `/animais/pesagem`, `/pastos`, `/calendario`, `/lotes` e `/relatorios`; verificar overflow, foco, estados vazios e tema claro/escuro.

- [ ] **Step 5: Corrigir regressões encontradas**

Aplicar somente correções necessárias ao escopo e repetir os testes afetados.
