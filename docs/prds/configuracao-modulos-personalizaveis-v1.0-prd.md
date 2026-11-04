# Configuração de Módulos Personalizáveis — PRD

## Descrição dos requisitos

### Contexto

- **Problema:** o menu atual expõe muitas áreas que alguns sítios não usam, enquanto links diretos continuam acessíveis.
- **Público-alvo:** usuários autenticados que têm acesso ao sítio selecionado.
- **Valor:** cada família simplifica o menu do seu sítio sem alterar dados ou configurações de outros sítios.

### Visão geral

- **Funcionalidades principais:**
  1. Página `/configuracoes/modulos` com controles para ativar e desativar módulos opcionais.
  2. Preferências compartilhadas por todos os usuários daquele sítio.
  3. Menu e resultados de busca rápida coerentes com as preferências.
  4. Bloqueio de acesso direto a páginas e APIs de módulos desativados.
- **Catálogo configurável do MVP:**
  - **Leite** — módulo principal, incluindo páginas e operações leiteiras.
  - **Conforto térmico e descanso** — módulo independente, aplicável a gado de corte e leite.
  - **Reprodução**.
  - **Genética e Confinamento** — controlados juntos como um grupo.
- **Sempre disponíveis e fora do controle deste MVP:** Animais e Manejo, Sanidade geral/Farmácia, Nutrição, Pastos, Cochos, Registros, Financeiro/Relatórios, Painel, Configurações, Ajuda e utilidades. Saúde do Leite (incluindo controle de mastite) pertence ao módulo Leite e é desativada junto com ele. O catálogo pode ser ampliado numa fase futura.
- **Fora do escopo:** presets por sistema produtivo, preferências pessoais por usuário, exclusão de dados, habilitação/desabilitação por rota individual e mudanças no banco Excel.
- **Cenários:** o usuário abre Configurações → Módulos, altera os controles e salva; ao navegar, os links ocultados deixam de aparecer; uma URL guardada de uma área desativada apresenta uma mensagem e encaminha para a página de módulos.

### Requisitos detalhados

- **Entrada e saída:** controles booleanos para os quatro grupos configuráveis; salvar mantém as demais chaves de `sitio_config.json`.
- **Interação:**
  - A tela deve indicar claramente o estado ligado/desligado e oferecer ação explícita para salvar.
  - A configuração é compartilhada pelo sítio, não é uma preferência pessoal.
  - Qualquer usuário autenticado com acesso ao sítio pode consultar e alterar as opções.
  - Ao bloquear uma página, redirecionar para `/configuracoes/modulos` com mensagem informativa.
  - Ao bloquear uma chamada de API/AJAX, responder HTTP 403 com JSON informativo; não redirecionar para HTML.
- **Persistência e inicialização:**
  - Guardar os estados no `sitio_config.json` da pasta do sítio atualmente ativo.
  - Sítios sem preferências salvas mantêm todos os módulos ativos, preservando o comportamento anterior.
  - Não exigir migração da planilha. Salvar deve preservar nome, donos, logotipo e outras configurações existentes.
  - Invalidar o cache da configuração após salvar, para que menu e bloqueios mudem imediatamente.
- **Independência:** Conforto térmico e descanso não depende do módulo Leite; pode ser usado no gado de corte com Leite desligado.
- **Casos de borda:** preferências ausentes ou parcialmente preenchidas usam `ativo` como padrão; valores desconhecidos são ignorados sem desativar módulos; opções recebidas no formulário são validadas por lista permitida; falha ao salvar deve ser apresentada como erro, sem mensagem de sucesso.

## Decisões de design

### Abordagem técnica

- **Arquitetura:** centralizar catálogo, estado efetivo e verificação de acesso num módulo de domínio pequeno (por exemplo, `modulos.py`), em vez de duplicar regras em cada template e rota.
- **Componentes e integração:**
  - Criar `GET /configuracoes/modulos` e `POST /configuracoes/modulos`, mantendo o padrão de autenticação, CSRF e mensagens já usado em `routes_usuarios.py`.
  - Usar o armazenamento por sítio já existente em `sitio_config.json` e os helpers de leitura, gravação e invalidação do cache de configuração.
  - Injetar o mapa de módulos efetivos nos templates; envolver links do drawer em `templates/base.html` nas condições correspondentes.
  - Filtrar também as sugestões de telas da busca rápida para não anunciar páginas desativadas.
  - Proteger endpoints por um mapa central de endpoints → módulo. A verificação deve ocorrer após a seleção/ativação do sítio na requisição e antes de qualquer efeito colateral.
  - Para páginas, usar redirecionamento com flash; para API/AJAX, JSON HTTP 403 com identificador/mensagem do módulo indisponível.
- **Armazenamento:** acrescentar uma chave versionável, por exemplo `modulos`, contendo os estados booleanos. Escritas devem preservar as outras propriedades; recomenda-se gravação atômica temporária + substituição do arquivo.
- **Interface:**
  - Manter o visual e os componentes do formulário de Configurações existente.
  - Agrupar Leite e Conforto visualmente, explicando a dependência entre ambos.
  - Exibir estado atual e resultado da gravação com texto, não apenas cor.
- **Superfícies a mapear:** além do menu, cobrir endpoints GET e POST, APIs, links internos das telas, atalhos da busca rápida e acessos por URL direta. A configuração e rotas sempre disponíveis nunca podem ser interceptadas.

### Restrições

- **Desempenho:** ler a configuração pelo cache existente; não reler o JSON repetidamente por cada item do menu.
- **Compatibilidade:** primeiro acesso a sítios existentes deixa todas as opções ativas; demais configurações e o fluxo multi-sítio permanecem inalterados.
- **Segurança:** exigir login e CSRF no salvamento; validar nomes/valores contra o catálogo fixo; bloquear antes de executar qualquer alteração; manter a configuração disponível mesmo com todos os módulos opcionais desligados. Qualquer usuário do sítio pode alterar o estado compartilhado, conforme decisão do solicitante.
- **Expansão:** um catálogo central permite adicionar novos módulos posteriormente sem criar esquemas de configuração divergentes.

### Avaliação de riscos

- **Risco de omissão de rota:** uma rota não mapeada poderia continuar disponível. Mitigar inventariando endpoints por módulo e adicionando testes que comparam o mapa com as rotas registradas.
- **Risco de indisponibilidade acidental:** valores ou chaves ausentes poderiam ocultar páginas existentes. Mitigar com padrão ativo, validação e testes de compatibilidade.
- **Risco multi-sítio/cache:** um sítio poderia herdar a preferência de outro ou continuar com menu antigo. Mitigar com testes de isolamento por sítio, cache segregado e invalidação após salvar.
- **Risco operacional:** qualquer usuário autorizado pode esconder áreas para todos no sítio. A página deve informar que a preferência é compartilhada e permitir reativar os módulos.
- **Risco de chamadas AJAX:** redirecionar API para HTML quebra os clientes; responder 403 JSON como comportamento separado.

## Critérios de aceitação

### Funcionais

- [ ] Usuário autenticado abre `/configuracoes/modulos`; usuário não autenticado segue o fluxo de login existente.
- [ ] A página mostra os quatro grupos configuráveis e indica que Conforto térmico e descanso é independente de Leite.
- [ ] Usuário com acesso ao sítio salva qualquer combinação válida; a alteração persiste no `sitio_config.json` daquele sítio.
- [ ] Sítio sem chave de módulos apresenta todos os grupos ativos e não perde nenhuma configuração atual.
- [ ] Após salvar, links das áreas desligadas desaparecem do menu e da busca rápida sem exigir novo login.
- [ ] Links de módulos ativos e módulos sempre disponíveis continuam visíveis.
- [ ] GET em página desativada redireciona à configuração com mensagem identificando a área bloqueada.
- [ ] POST em rota desativada não grava nem altera dados e redireciona à configuração com mensagem.
- [ ] Chamada direta a API desativada responde 403 JSON e não executa a operação.
- [ ] Com Leite desligado, suas rotas são bloqueadas; Conforto continua acessível se estiver ativo.
- [ ] Ativar todos os grupos restaura o acesso sem recarregar ou migrar dados.
- [ ] Configurações de módulos de sítios diferentes não vazam entre si.

### Qualidade

- [ ] O salvamento exige CSRF e rejeita opções não reconhecidas sem aceitar estados arbitrários.
- [ ] Escrita preserva as chaves existentes de `sitio_config.json` e falhas são exibidas como erro.
- [ ] Cada endpoint mapeado é coberto por teste para acesso ativo e bloqueado; APIs incluem verificação de resposta JSON.
- [ ] Testes incluem configuração ausente, parcial, inválida e isolamento multi-sítio.
- [ ] `python -m pytest` e `git diff --check` passam antes de disponibilizar.

### Aceitação do usuário

- [ ] Menu mais enxuto sem alterar o comportamento dos módulos na primeira implantação.
- [ ] Mensagens informam o motivo do bloqueio e como reativar o módulo.
- [ ] Atualizar a Ajuda com o caminho e a explicação de que as preferências são compartilhadas por sítio.

## Fases de execução

### Fase 1: Preparação e catálogo

**Objetivo:** identificar com precisão as superfícies pertencentes a cada grupo.

- [ ] Criar catálogo canônico de IDs, nomes, dependências e endpoints.
- [ ] Inventariar páginas, operações POST, APIs e atalhos de navegação dos quatro grupos.
- [ ] Definir padrão ativo para configuração ausente e validação de dados existentes.
- **Entregáveis:** catálogo de módulos e mapa de endpoints.
- **Estimativa:** 2–3 horas.

### Fase 2: Configuração e navegação

**Objetivo:** permitir salvar preferências e refletir o estado no menu.

- [ ] Criar a página e rota POST com autenticação, CSRF, validação e mensagens.
- [ ] Persistir as opções no arquivo do sítio sem alterar outras chaves e invalidar o cache.
- [ ] Condicionar os links do drawer e as sugestões da busca rápida.
- **Entregáveis:** tela funcional e navegação sincronizada.
- **Estimativa:** 4–6 horas.

### Fase 3: Proteção e integração

**Objetivo:** impedir que as rotas escondidas continuem acessíveis diretamente.

- [ ] Aplicar proteção centralizada após ativar o sítio e antes da execução das rotas.
- [ ] Implementar redirecionamento informativo para páginas e 403 JSON para APIs.
- [ ] Testar métodos de escrita, hierarquia Leite/Conforto e isolamento multi-sítio.
- **Entregáveis:** módulos protegidos em todas as superfícies mapeadas.
- **Estimativa:** 4–6 horas.

### Fase 4: Validação e publicação

**Objetivo:** confirmar compatibilidade e documentar o uso.

- [ ] Executar testes direcionados e a suíte completa.
- [ ] Verificar visualmente menu e configurações em computador e telemóvel.
- [ ] Atualizar Ajuda e changelog; revisar a lista final de endpoints protegidos.
- **Entregáveis:** funcionalidade pronta para publicação, cobertura e documentação.
- **Estimativa:** 2–3 horas.

---

**Versão do documento:** 1.0  
**Criado em:** 2026-11-03  
**Rodadas de esclarecimento:** 3  
**Pontuação de clareza:** 96/100
