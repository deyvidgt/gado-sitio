# Módulo Leiteiro Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar um módulo leiteiro completo, responsivo e separado financeiramente do gado de corte, com produção, CCS/CPP, colchão/cama, alimentação, alertas, relatórios, dashboard, ajuda e prints reais.

**Architecture:** Criar `leite.py` como fonte única de validação e cálculos, novas abas migradas no Excel e rotas Flask separadas. Reutilizar animais, fotos, reprodução, visitas, exportação e componentes visuais existentes sem alterar a matemática de `calculos.py` nem misturar receita/custo leiteiro ao resultado oficial do corte.

**Tech Stack:** Flask, Jinja2, pandas, openpyxl, pytest, Chart.js já usado pelo dashboard, Google Drive já usado por Fotos/Ajuda.

**Spec:** `docs/superpowers/specs/2026-10-26-modulo-leiteiro-design.md`

## Global Constraints

- Não alterar nem reordenar colunas existentes.
- Colunas novas entram somente no final das listas de `config.py`.
- Abas novas são criadas por migração em `db.inicializar()`.
- Testes que gravam usam a cópia temporária da planilha.
- O resultado oficial do gado de corte permanece baseado em `calculos.py`.
- Receita do leite não entra em Vendas nem no resultado de corte.
- Alimentação marcada como leiteira não entra automaticamente nos Gastos rateados do gado de corte.
- Membros continuam configuráveis por sítio; não usar nomes nem divisões fixas.
- Cada pedido usa o sítio ativo da sessão e respeita a trava de múltiplos sítios.
- Nenhum valor nutricional será inventado: campo vazio aparece como “não informado”.
- CCS será exibida em células/mL e CPP em UFC/mL; ambos são opcionais.
- Registro total e registros individuais não podem somar o mesmo volume duas vezes.
- A ajuda só exibirá prints realmente disponíveis; não criar imagens fictícias.
- A aba `/alertas` reunirá alertas locais e previsão do tempo sem bloquear o restante do sistema.
- A previsão usará Open-Meteo sem chave, com timeout curto, cache separado por sítio e indicação de indisponibilidade/desatualização.
- Coordenadas e nome da região ficam em `sitio_config.json`, sem alterar configurações existentes.

## Review Focus

- Registro offline repetido com o mesmo `ID Envio`: deve ser idempotente e não criar produção duplicada.
- Mistura de registros individuais e totais no mesmo dia/ordenha: deve deixar a origem clara e não contar o volume duas vezes.
- Datas inválidas, litros negativos, CCS/CPP inválidos e decimais com vírgula: devem gerar validação compreensível, sem gravar lixo.
- Animal vendido, morto, macho ou inexistente selecionado na ordenha: deve ser recusado ou explicitamente permitido apenas por configuração, sem alterar estoque financeiro.
- Configuração ausente de preço, meta, consumo ou custo: deve aparecer como “não informado”, nunca como zero enganoso.
- Animais ativos, vacas leiteiras ativas e vacas em lactação: devem ser contagens distintas, sem incluir animais baixados ou vacas secas na lactação.
- Serviço meteorológico fora do ar, resposta incompleta ou cache vencido: a aba deve mostrar o estado claramente e o restante do sistema deve continuar funcionando.
- Sítios com coordenadas diferentes: cada pedido deve consultar e exibir somente o clima do sítio ativo.
- Consumo planejado sem lançamento real: deve aparecer separado e não pode ser usado como consumo efetivo.
- Ficha nutricional incompleta: deve mostrar “não informado” e gerar alerta de cadastro, não preencher valores automaticamente.
- Tratamento sem custo, animal ou período de carência: deve permanecer identificável e não entrar silenciosamente na margem.

---

### Task 1: Modelo de dados e migração

**Files:**
- Create: `tests/test_leite_migracao.py`
- Modify: `config.py`
- Modify: `db.py`
- Modify: `tests/test_db.py` ou teste de migração existente

**Interfaces:**
- Consumes: `db.inicializar()` e padrão de `COLUNAS_*` existente.
- Produces: constantes `COLUNAS_LEITE_PRODUCAO`, `COLUNAS_LEITE_CONFIG`, `COLUNAS_LEITE_ALIMENTACAO`, `COLUNAS_LEITE_NECESSIDADES`, `COLUNAS_LEITE_TRATAMENTOS`, `COLUNAS_LEITE_CONFORTO`, `COLUNAS_LEITE_COLCHAO`; abas migradas com as colunas exatas da especificação.

- [ ] **Step 1: Write the failing test**

Criar testes que inicializem uma cópia temporária e verifiquem as cinco abas novas, suas colunas e a preservação da ordem/conteúdo das abas existentes. Incluir teste de migração repetida sem duplicar colunas.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_leite_migracao.py -q`

Expected: FAIL porque as constantes/abas novas ainda não existem.

- [ ] **Step 3: Implement migration**

Adicionar as listas de colunas no final de `config.py` e incluir as abas na migração padrão de `db.inicializar()`. Não alterar listas já existentes. Usar os nomes exatos: `Leite Produção`, `Leite Configuração`, `Leite Alimentação`, `Leite Necessidades`, `Leite Tratamentos`, `Leite Conforto` e `Leite Colchão`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_leite_migracao.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config.py db.py tests/test_leite_migracao.py
git commit -m "feat(leite): add spreadsheet tabs and migration"
```

### Task 2: Motor de produção, configuração e custos

**Files:**
- Create: `leite.py`
- Create: `tests/test_leite.py`

**Interfaces:**
- Consumes: DataFrames das quatro abas novas, `animais.carregar()`, `reproducao.situacao()` e datas normalizadas pelo padrão do projeto.
- Produces: `validar_producao(dados)`, `producao_dia(df, data)`, `resumo_periodo(df, inicio, fim, animais, config)`, `producao_por_animal(df, inicio, fim)`, `serie_diaria(df, inicio, fim)`, `situacao_lactacao(animais, manejo, config, hoje)`, `receita_estimada(litros, preco)`, `custo_alimentacao(df_alimentacao, registros, inicio, fim)` e `alertas(...)`.

- [ ] **Step 1: Write failing tests**

Cobrir litros individuais por dia, litros acumulados no dia/semana/mês/total, soma por vaca, média de litros por dia, média por mês, média por animal, média por animal em lactação, dias em lactação por animal desde o último parto, registro total sem ranking individual, receita com preço, “não informado” sem preço, CCS/CPP opcionais, datas brasileiras, litros negativos, valores inválidos e mistura individual/total sem duplicação.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_leite.py -q`

Expected: FAIL por módulo/funções ausentes.

- [ ] **Step 3: Implement the calculation module**

Implementar somente leitura, validação e cálculo. Separar registros individuais de totais por `Modo Registro` e aplicar uma regra explícita: quando houver individual e total para a mesma data/ordenha, o resumo usa os individuais e marca o total como substituído, sem somar ambos. Valores ausentes de preço/custo/meta retornam `None` e rótulo posterior de “não informado”.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_leite.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add leite.py tests/test_leite.py
git commit -m "feat(leite): add production and cost calculations"
```

### Task 3: Gravação, edição e lançamento de ordenha

**Files:**
- Create: `routes_leite.py`
- Create: `templates/leite_ordenha.html`
- Create: `templates/leite_editar.html`
- Create: `tests/test_leite_rotas.py`
- Modify: `app.py`

**Interfaces:**
- Consumes: `leite.validar_producao`, `leite.producao_dia`, animais vivos e helpers de gravação/backup existentes.
- Produces: `/leite/ordenha`, `/leite/editar/<id>`, `/leite/excluir/<id>`, função de gravação idempotente por `ID Envio` e contexto de vacas selecionáveis.

- [ ] **Step 1: Write failing route tests**

Testar GET 200, formulário CSRF, gravação individual, gravação total, rejeição de litros negativos, rejeição de animal inválido, duplicidade por `ID Envio`, edição e exclusão com backup.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_leite_rotas.py -q`

Expected: FAIL porque as rotas e templates ainda não existem.

- [ ] **Step 3: Implement routes and forms**

Seguir o padrão de `routes_*`: autenticação, CSRF, sítio ativo, trava de gravação e `salvar_linha`/`reescrever_aba`. O formulário deve permitir modo individual ou total, data, ordenha, litros, CCS, CPP, temperatura, qualidade, observação e responsável. No celular, renderizar cartões; no desktop, tabela/formulário compacto.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_leite_rotas.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add routes_leite.py templates/leite_ordenha.html templates/leite_editar.html tests/test_leite_rotas.py app.py
git commit -m "feat(leite): add milking entry workflow"
```

### Task 4: Vacas leiteiras e fichas individuais

**Files:**
- Create: `templates/leite_animais.html`
- Create: `templates/leite_animal.html`
- Create: `tests/test_leite_animais.py`
- Modify: `animais.py` only if a shared helper is required
- Modify: `routes_leite.py`

**Interfaces:**
- Consumes: animais vivos, fotos principais, `leite.producao_por_animal`, `situacao_lactacao` e reprodução existente.
- Produces: `/leite/animais`, `/leite/animal/<id>`, filtros por situação/dono/busca e histórico individual.

- [ ] **Step 1: Write failing tests**

Testar contagens distintas de animais ativos, vacas leiteiras ativas e vacas em lactação; testar lista de fêmeas ativas, filtros, animal sem produção, histórico por período, foto principal, situação de lactação e exclusão de animal vendido/morto da seleção padrão.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_leite_animais.py -q`

Expected: FAIL por rotas/templates/contexto ausentes.

- [ ] **Step 3: Implement list and detail pages**

Reutilizar `ficha_animal`, fotos e chips de brinco sem duplicar cadastro. Mostrar litros do dia, média recente, dias desde parto, situação, meta e alertas. Permitir correção de situação leiteira sem modificar o estoque financeiro.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_leite_animais.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/leite_animais.html templates/leite_animal.html tests/test_leite_animais.py routes_leite.py animais.py
git commit -m "feat(leite): add dairy herd pages"
```

### Task 5: Alimentação leiteira e ficha nutricional

**Files:**
- Create: `templates/leite_alimentacao.html`
- Create: `tests/test_leite_alimentacao.py`
- Modify: `routes_leite.py`

**Interfaces:**
- Consumes: abas `Leite Alimentação` e `Leite Necessidades`, `leite.custo_alimentacao` e componentes de formulário existentes.
- Produces: `/leite/alimentacao`, cadastro/edição/arquivamento de produto e apresentação de nutrição.

- [ ] **Step 1: Write failing tests**

Testar cadastro com produto e fabricante, campos opcionais de proteína/NDT/fibra/cálcio/fósforo, valor ausente mostrado como “não informado”, consumo/preço, necessidades diárias por categoria produtiva com unidade/fonte/data de revisão e preservação de produto arquivado.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_leite_alimentacao.py -q`

Expected: FAIL por rota e persistência ausentes.

- [ ] **Step 3: Implement product management**

Criar formulário sem valores padrão nutricionais inventados. Validar percentuais e valores monetários não negativos. Mostrar rótulo do produto, consumo recomendado, preço por saco, validade e status ativo.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_leite_alimentacao.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/leite_alimentacao.html tests/test_leite_alimentacao.py routes_leite.py
 git commit -m "feat(leite): add feed nutrition records"
```

### Task 6: Colchão/cama da área leiteira

**Files:**
- Create: `templates/leite_colchao.html`
- Create: `tests/test_leite_colchao.py`
- Modify: `routes_leite.py`
- Modify: `templates/visitas.html` or corresponding visit form
- Modify: `leite.py`

**Interfaces:**
- Consumes: abas `Leite Colchão` e `Leite Conforto`, fotos/Drive existente, previsão do tempo e status da visita.
- Produces: `/leite/colchao`, registro de condição, troca, material, quantidade, custo, próxima troca e fotos antes/depois; `situacao_colchao(registros, hoje)`.

- [ ] **Step 1: Write failing tests**

Testar condições válidas, próxima troca, dias desde a troca, alerta para `úmida`, `suja` e `precisa trocar`, custo leiteiro separado e registro rápido de visita.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_leite_colchao.py -q`

Expected: FAIL por cálculo/rotas ausentes.

- [ ] **Step 3: Implement history and status**

Criar tela de histórico e cartão de situação atual. Usar fotos existentes quando anexadas; se Drive não estiver disponível, manter o registro textual. Não converter unidades de material automaticamente.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_leite_colchao.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/leite_colchao.html tests/test_leite_colchao.py routes_leite.py leite.py templates/visitas.html
 git commit -m "feat(leite): track bedding condition and changes"
```

### Task 7: Painel, alertas e integração com dashboard

**Files:**
- Create: `templates/leite.html`
- Create: `tests/test_leite_dashboard.py`
- Modify: `routes_leite.py`
- Modify: `routes_dashboard.py`
- Modify: `templates/dashboard.html`
- Modify: `templates/base.html`

**Interfaces:**
- Consumes: todos os cálculos anteriores, `alertas`, colchão, produção, animais e alimentação.
- Produces: `/leite`, `/api/leite/resumo`, card do leite no dashboard, links de navegação e alertas textuais/semaforizados.

- [ ] **Step 1: Write failing tests**

Testar dashboard com e sem produção, acumulados do dia/semana/mês/total, resumo de hoje/7/30 dias, médias por dia/mês/animal e por animal em lactação, dias em lactação por animal, vacas em lactação, receita sem preço, alertas de queda/sem registro/parto/secagem, card de colchão e card do dashboard sem 500.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_leite_dashboard.py -q`

Expected: FAIL porque o painel e o endpoint ainda não existem.

- [ ] **Step 3: Implement panel and API**

Criar painel com KPIs, gráficos Chart.js, filtros de período e cartões de vacas. Usar `None`/“não informado” para dados ausentes. Inserir link “Leite” no grupo Rebanho ou Campo, mantendo o menu mobile. Não deixar erro do módulo derrubar o dashboard principal: capturar falhas e retornar estado vazio com log.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_leite_dashboard.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/leite.html tests/test_leite_dashboard.py routes_leite.py routes_dashboard.py templates/dashboard.html templates/base.html
 git commit -m "feat(leite): add dairy dashboard and alerts"
```

### Task 8: Central de alertas, nutrição, consumo e previsão do tempo

**Files:**
- Create: `alertas.py`
- Create: `tempo.py`
- Create: `routes_alertas.py`
- Create: `templates/alertas.html`
- Create: `tests/test_alertas.py`
- Modify: `sitios.py` ou módulo de configuração do sítio
- Modify: `config.py` somente se houver constantes de limiar
- Modify: `templates/base.html`
- Modify: `app.py`

**Interfaces:**
- Consumes: alertas de `leite.py`, `insumos.py`, `reproducao.py`, `tarefas.py`, `pastos.py`, colchão/cama e dados meteorológicos em cache.
- Produces: `tempo.previsao(sitio_slug, config_sitio)`, `alertas.todos(dados, hoje)`, `/alertas` e `/api/alertas`.

- [ ] **Step 1: Write failing tests**

Testar a aba central com alertas de leite, reprodução, tarefas, estoque, nutrição/consumo, colchão e clima. Testar que campos nutricionais ausentes aparecem como “não informado”, que consumo planejado fica separado do consumo real e que excesso/falta de consumo gera prioridade correta.

Testar `tempo.previsao` com resposta válida, timeout, JSON incompleto, cache recente, cache vencido e dois sítios com coordenadas diferentes. A falha meteorológica deve retornar estado indisponível sem lançar erro para o dashboard ou para os lançamentos.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_alertas.py -q`

Expected: FAIL porque a central, o cliente de previsão e os normalizadores ainda não existem.

- [ ] **Step 3: Implement the alert and weather modules**

Criar `tempo.py` com cliente servidor para Open-Meteo, timeout curto, validação dos campos necessários e cache por sítio contendo resposta, região e horários. Usar somente latitude/longitude/nome da região do sítio ativo; não enviar dados de outros sítios. Não fazer coleta automática em background nesta fase.

Criar `alertas.py` para normalizar cada item em `origem`, `titulo`, `detalhe`, `prioridade`, `data` e `acao`. Incluir nutrição e consumo com distinção entre recomendado, planejado, lançado/contado e efetivo. Não transformar consumo recomendado em consumo real.

Criar a rota e template com condição atual, temperatura, chuva, vento, atualização, próximos dias, alertas novos/vencidos/resolvidos e ações recomendadas. Adicionar “Atualizar previsão” com proteção existente, respeitando cache. Mostrar o texto junto do semáforo e manter o sistema utilizável quando a previsão estiver indisponível.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_alertas.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add alertas.py tempo.py routes_alertas.py templates/alertas.html tests/test_alertas.py sitios.py config.py templates/base.html app.py
git commit -m "feat(alertas): add alerts and weather panel"
```

### Task 9: Relatórios, exportação e configurações

**Files:**
- Create: `templates/leite_relatorios.html`
- Create: `tests/test_leite_relatorios.py`
- Modify: `routes_leite.py`
- Modify: `exportar.py` e/ou `relatorios.py`
- Modify: `templates/configuracoes.html` quando houver seção apropriada

**Interfaces:**
- Consumes: `leite.resumo_periodo`, `serie_diaria`, `producao_por_animal`, configuração e alimentação.
- Produces: `/leite/relatorios`, filtros, Excel/PDF e edição dos parâmetros do leite.

- [ ] **Step 1: Write failing tests**

Testar filtros de data, animal e situação, produção diária/mensal, ranking, vacas sem registro, CCS/CPP no relatório, receita/custo/margem e exportação que não altera a planilha de dados.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_leite_relatorios.py -q`

Expected: FAIL por rotas/exportação ausentes.

- [ ] **Step 3: Implement reports and config**

Reutilizar mecanismos de exportação e PDF existentes. Incluir parâmetros de preço, meta, queda, dias sem registro, ordenhas e secagem. Mostrar aviso quando o relatório não tiver preço/custo suficiente.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_leite_relatorios.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/leite_relatorios.html tests/test_leite_relatorios.py routes_leite.py exportar.py relatorios.py templates/configuracoes.html
 git commit -m "feat(leite): add reports and dairy settings"
```

### Task 10: Ajuda detalhada e prints reais

**Files:**
- Modify: `templates/ajuda.html`
- Create: `tests/test_ajuda_leite.py`
- Modify: `docs/FOTOS_DRIVE.md` only if the upload naming needs documentation
- Create only after browser review: `docs/prints-ajuda-leite/` local staging files, if appropriate

**Interfaces:**
- Consumes: rotas e telas leiteiras implementadas, mecanismo `routes_ajuda.py`/Drive e convenção `p-`/`c-`.
- Produces: seção detalhada de ajuda, links de índice e referências para prints reais de painel, ordenha, vacas, ficha, alimentação, colchão e relatórios.

- [ ] **Step 1: Write failing tests**

Testar `/ajuda` contendo a seção leiteira, instruções de CCS/CPP, colchão/cama, registro individual/total, alimentação e links para as rotas. Testar que a página funciona com Drive indisponível.

- [ ] **Step 2: Run test to verify failure**

Run: `python -m pytest tests/test_ajuda_leite.py -q`

Expected: FAIL porque a seção leiteira ainda não existe.

- [ ] **Step 3: Implement help text**

Adicionar passo a passo em português, sem afirmar dados que não estejam registrados. Explicar CCS em células/mL, CPP em UFC/mL, “não informado”, diferença entre total e individual, leitura dos alertas e controle do colchão.

- [ ] **Step 4: Run test to verify pass**

Run: `python -m pytest tests/test_ajuda_leite.py -q`

Expected: PASS.

- [ ] **Step 5: Capture and stage real prints**

Após a revisão visual, capturar versões desktop e celular das telas reais. Nomear conforme a convenção usada pela ajuda, por exemplo `p-leite-painel.png`, `c-leite-ordenha.png`, `p-leite-alimentacao.png` e `p-leite-colchao.png`. Enviar ao Drive somente com autorização e nunca apresentar uma imagem não capturada como print real.

- [ ] **Step 6: Commit**

```bash
git add templates/ajuda.html tests/test_ajuda_leite.py
git commit -m "docs(leite): add dairy help guide"
```

### Task 11: Integração, regressão e revisão visual

**Files:**
- Modify: testes existentes somente para corrigir regressões comprovadas
- Create: `tests/test_leite_integracao.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: todos os módulos e rotas anteriores.
- Produces: suíte final verde, verificação de invariantes e evidência visual desktop/mobile.

- [ ] **Step 1: Write failing integration tests**

Testar que:

- a inicialização migra abas sem alterar dados antigos;
- produção leiteira não muda `calculos.calcular_todos_membros`;
- compra/venda/morte/nascimento continuam iguais;
- todas as páginas GET leiteiras retornam 200;
- dashboard continua 200 com planilha sem registros leiteiros;
- CSRF e autenticação permanecem ativos;
- menu não é coberto por mapa ou cards novos em 390px e desktop.

- [ ] **Step 2: Run focused integration tests**

Run: `python -m pytest tests/test_leite_integracao.py tests/test_calculos.py tests/test_paginas.py -q`

Expected: PASS.

- [ ] **Step 3: Run full suite**

Run: `python -m pytest -q`

Expected: todos os testes passam; avisos externos, se houver, são reportados sem mascarar falhas.

- [ ] **Step 4: Run the app and review real flows**

Run: `python app.py`

Revisar no navegador:

1. dashboard com e sem dados;
2. lançamento individual no desktop e celular;
3. lançamento total e prevenção de duplicidade;
4. lista/ficha da vaca;
5. CCS/CPP e ficha nutricional;
6. colchão/cama com status e fotos;
7. alertas, nutrição, consumo e previsão do tempo;
8. relatórios e exportação;
9. ajuda com prints disponíveis;
10. menu mobile e mapa sem sobreposição.

Ler console do navegador e corrigir erros reais com teste de regressão antes do ajuste.

- [ ] **Step 5: Update changelog**

Adicionar a mudança em `[Não lançado]`, incluindo produção, qualidade, alimentação leiteira, colchão/cama, relatórios e ajuda.

- [ ] **Step 6: Commit final**

```bash
git add tests/test_leite_integracao.py CHANGELOG.md
git commit -m "feat(leite): complete dairy management module"
```
