# Reformulação de módulos e layout — design

**Status:** aprovada para implementação faseada  
**Data:** 2026-10-26  
**Versão alvo:** próxima versão após v5.3

## 1. Objetivo

Evoluir o sistema do Sítio Santo Antonio para uma interface operacional, clara no celular e organizada por módulos. A tela inicial deve responder rapidamente a quatro perguntas:

1. Quantas cabeças estão no sítio e qual é o estado do rebanho?
2. O que exige atenção hoje?
3. Onde estão os animais e como estão ganhando peso?
4. Qual é a situação dos pastos, insumos e resultado financeiro?

A reformulação usa as imagens em `exemplos/` como referência de organização visual: painéis de corte, mapas de pasto, cartões de indicadores, linha do tempo de ocorrências e fluxos móveis. Não copia marcas, textos ou identidade visual de terceiros.

## 2. Restrições

- O aplicativo continua Flask, Jinja e CSS próprio em `templates/base.html`.
- A planilha continua sendo a fonte de dados. Não reordenar colunas existentes.
- Colunas novas entram somente no fim das listas de `config.py` e passam pela migração existente.
- Módulos de consulta devem reutilizar os motores existentes (`calculos.py`, `pesagem.py`, `pastos.py`, `saude.py`, `reproducao.py`, `tarefas.py` e `insumos.py`).
- Não criar uma aba nova para dados que já existem em Manejo, Tarefas ou Visitas.
- Não adicionar dependência apenas para componentes de interface.
- A matemática financeira e suas invariantes permanecem inalteradas.
- A interface deve continuar funcionando para sítios com membros configuráveis e para dois a oito membros.
- Acessibilidade mínima: foco visível, textos junto às cores de status, botões utilizáveis no celular e suporte a `prefers-reduced-motion`.

## 3. Direção visual

### 3.1 Conceito

**Central de manejo do sítio:** uma ferramenta de campo, não um painel corporativo. A tela combina verde de pasto, tons de terra e amarelo de identificação dos brincos. Métricas ficam compactas; ocorrências e ações ficam próximas do contexto que as explica.

### 3.2 Tokens

Os tokens existentes em `base.html` serão preservados e refinados, sem espalhar cores fixas nos templates:

- campo: verdes atuais para ações, navegação e estado normal;
- terra: `--gold` para compras, atenção e destaques de manejo;
- céu: `--info` para informações e pesagens;
- alerta: `--warn` e `--danger` para situações que pedem ação;
- fundo: creme claro no tema claro e verde quase preto no tema escuro.

A assinatura visual será uma faixa de **estado do sítio** no início do dashboard: estoque, peso/GMD, lotação e alertas em uma única leitura horizontal no desktop e empilhada no celular.

### 3.3 Tipografia e composição

- `Playfair Display` permanece apenas em títulos e valores de destaque.
- `DM Sans` permanece em navegação, formulários e dados.
- O layout usa cartões com bordas superiores de status, divisores finos e espaçamento consistente.
- Não usar gráficos circulares quando uma barra ou lista responder melhor no celular.
- Animações ficam restritas à entrada suave de conteúdo e respeitam redução de movimento.

## 4. Arquitetura de módulos

A navegação de `base.html` será agrupada assim, mantendo as rotas atuais:

### Visão geral

- Dashboard
- Família, quando houver vários sítios

### Rebanho

- Animais
- Pesagem
- Reprodução
- Fotos

### Campo

- Pastos
- Manejo
- Insumos
- Visitas
- Tarefas
- Calendário

### Financeiro

- Compras
- Gastos
- Vendas
- Lotes
- Relatórios

### Ferramentas

- Comando de voz
- Importar/Exportar
- Backups
- Ajuda
- Configurações

A nomenclatura exibida pode ser reorganizada, mas nomes de endpoints, permissões e URLs existentes não mudam nesta etapa.

## 5. Dashboard operacional

`routes_dashboard.py` continuará agregando dados; `templates/dashboard.html` ganhará uma composição em blocos:

1. **Estado do sítio:** cabeças, peso médio, GMD, UA/ha e resultado.
2. **Ações rápidas:** nova pesagem, novo manejo, mover pasto, nova compra e nova visita.
3. **Atenção agora:** alertas de saúde, reprodução, tarefas atrasadas, pastos lotados e animais sem pesagem.
4. **Rebanho:** composição por categoria/sexo e faixas de arrobas já calculadas por `pesagem.py`.
5. **Campo:** lotação, pastos em descanso e previsão de insumos.
6. **Ocorrências:** últimas compras, gastos, vendas, manejos e visitas, com links para as telas existentes.
7. **Tendência:** evolução de peso/GMD quando houver dados suficientes.

Cada bloco deve tolerar dados ausentes sem derrubar o dashboard. O cálculo permanece no servidor; o template apenas apresenta os resultados.

## 6. Calendário operacional

Será criado um módulo somente leitura que reúne eventos já registrados:

- vacinação, vermifugação e brucelose de `saude.py`;
- cobertura, diagnóstico, parto previsto e secagem de `reproducao.py`;
- tarefas de `tarefas.py`;
- pesagens e movimentações de pasto de `Manejo`;
- visitas de `Visitas`.

Arquivos previstos:

- `calendario.py`: normalização dos eventos em uma estrutura comum;
- `routes_calendario.py`: rota GET, filtros e paginação simples se necessária;
- `templates/calendario.html`: mês atual, próximos eventos e filtros por tipo;
- `tests/test_calendario.py`: datas, ordenação, eventos ausentes e filtros.

O calendário não grava dados e não cria aba nova. O registro continua ocorrendo nas telas existentes.

## 7. Animais, pesagem e foto

A ficha do animal será reorganizada em torno da identificação e do histórico:

- foto principal, brinco, sexo, categoria e dono;
- peso mais recente, arrobas, GMD e data da pesagem;
- situação sanitária e reprodutiva;
- linha do tempo de manejo, pesagens e fotos.

A tela de pesagem exibirá faixas de arrobas e curva de peso já implementadas, sem misturar estimativas de foto ao GMD oficial. `peso_foto.py` continuará registrando o peso bruto estimado e usando calibração somente quando houver pares válidos de balança.

Uma avaliação morfológica poderá ser incorporada à ficha apenas depois de definir colunas novas no fim da aba `Animais`. Nesta especificação ela fica fora da Fase 1 para não criar campos sem fluxo de gravação e sem necessidade confirmada.

## 8. Pastos, manejo e insumos

As telas existentes serão alinhadas visualmente ao novo padrão:

- mapa e cartões de pastos com ocupação, descanso e lotação;
- histórico de movimentações;
- estoque e previsão de término de sal, proteinado e ração;
- comparador de custo sem gravação;
- alertas de lotação e insumo baixo no dashboard e calendário quando aplicável.

A estrutura de dados atual de `Pastos`, `Manejo`, `Visitas` e `Gastos` permanece.

## 9. Financeiro e relatórios

As telas financeiras receberão a mesma hierarquia visual, sem mudança de cálculo:

- resumo no topo;
- cartões de custo, receita, margem e capital;
- listas móveis para registros;
- filtros e links para detalhes;
- avisos explícitos quando um número for estimado.

As invariantes de `calculos.py` deverão passar em qualquer alteração que toque no dashboard financeiro.

## 10. Fases de implementação

### Fase 1 — base visual e dashboard

Escopo:

- tokens e componentes reutilizáveis em `templates/base.html`;
- navegação agrupada;
- dashboard operacional;
- ações rápidas;
- estados vazios e responsividade;
- testes de renderização e rotas GET.

Fora da Fase 1: calendário novo, novas colunas, avaliação morfológica, novas integrações e alterações de cálculo.

### Fase 2 — calendário

Implementar `calendario.py`, rota, template e testes.

### Fase 3 — ficha e linha do tempo dos animais

Reorganizar ficha, fotos, indicadores de peso, saúde e reprodução.

### Fase 4 — pastos, insumos e manejo

Aprimorar telas e alertas usando os módulos existentes.

### Fase 5 — financeiro e relatórios

Aplicar a nova linguagem visual às consultas financeiras e validar as invariantes.

## 11. Critérios de aceite da Fase 1

- Todas as rotas GET existentes continuam respondendo sem erro 500.
- Dashboard funciona com planilha vazia, dados parciais, dois membros e oito membros.
- Dashboard não grava dados e não altera a planilha.
- Navegação mostra claramente o módulo ativo e funciona em celular.
- Tema claro e escuro permanecem legíveis.
- Status não depende apenas da cor.
- `python -m pytest` passa sem alterar o arquivo de dados real.
- `git diff --check` passa.
- A revisão visual confirma desktop e largura móvel.

## 12. Riscos e decisões adiadas

- **Excesso de informação no dashboard:** limitar cada bloco a uma decisão ou ação; detalhes ficam nas telas próprias.
- **Diferença entre dados estimados e medidos:** exibir `estimado`/`aproximado` junto do valor.
- **Planilha histórica com colunas antigas:** não mover colunas; usar as migrações existentes.
- **Avaliação visual do animal:** adiada até haver definição de campos e fluxo de persistência.
- **Mapa offline e sensores:** fora do escopo; dependem de decisões técnicas e de hardware.
- **Clonagem de referências externas:** proibida; a implementação usa padrões de interação, não marcas ou ativos de terceiros.
