# Módulo Leiteiro — Especificação Técnica

**Data:** 26/10/2026  
**Status:** aprovada em conversa; aguardando revisão do documento antes do plano de implementação

## 1. Objetivo

Criar um módulo leiteiro completo para o Sítio Santo Antonio, integrado ao cadastro de animais, visitas, reprodução, fotos, alimentação, dashboard e relatórios, sem misturar automaticamente a produção leiteira com o resultado financeiro do gado de corte.

O módulo deve funcionar no computador e no celular, priorizando lançamentos rápidos no trabalho diário e consultas claras por vaca, período e situação produtiva.

## 2. Escopo

O módulo inclui:

- aba central de alertas operacionais, reunindo alertas do rebanho, leite, estoque, reprodução, tarefas e clima;
- previsão do tempo para a região de cada sítio, com condição atual, próximos dias e alertas úteis ao manejo;
- total de animais ativos no sítio, separado de vacas em lactação;
- identificação das vacas leiteiras por brinco já cadastrado;
- situação produtiva: em lactação, seca, pré-parto, recém-parida e inativa;
- data do último parto e previsão de secagem;
- registros de produção por vaca e ordenha;
- registro alternativo do total de uma ordenha, sem duplicar o volume;
- litros por vaca, por ordenha, por dia e por período;
- preço do leite, receita bruta e margem estimada;
- produtos de alimentação leiteira e informações nutricionais declaradas no rótulo;
- custo da alimentação leiteira quando houver preço e consumo informados;
- custos de tratamento leiteiro por animal, incluindo medicamento, veterinário, exame e procedimento;
- conforto térmico e descanso, com controle de sombra, água, ventilação, área de repouso, lotação e sinais observados;
- alertas de queda de produção, ausência de lançamento, parto, secagem e estoque;
- painel, ficha individual, relatórios, exportação e ajuda ilustrada.

Ficam fora do escopo inicial: integração automática com laticínio, emissão fiscal, controle de tanque por sensor, rastreamento de qualidade laboratorial obrigatório e prescrição veterinária.

## 3. Regras de preservação

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

## 4. Modelo de dados

### 4.1 Aba `Leite Produção`

Nova aba, criada ao final da planilha, com colunas nesta ordem:

1. `Data`
2. `Vaca ID`
3. `Brinco`
4. `Modo Registro` — `individual` ou `total`
5. `Ordenha` — `Manhã`, `Tarde`, `Noite` ou outro texto configurado
6. `Litros`
7. `CCS (células/mL)`
8. `CPP (UFC/mL)`
9. `Qualidade`
10. `Temperatura`
11. `Observação`
12. `Responsável`
13. `ID Envio`
14. `Criado Em`

`Vaca ID` liga o registro ao cadastro mesmo que o texto do brinco seja corrigido depois. Registro total não exige Vaca ID e representa o volume da ordenha inteira.

`ID Envio` evita duplicação em lançamentos offline, como já ocorre em Visitas e Fotos.

### 4.2 Aba `Leite Configuração`

Nova aba com uma linha de configuração por sítio:

1. `Preço por Litro`
2. `Meta Litros por Vaca`
3. `Queda de Alerta (%)`
4. `Dias sem Registro`
5. `Número de Ordenhas`
6. `Dias até Secagem`
7. `Observações`

Valores ausentes usam somente defaults de apresentação e são identificados como não configurados. O usuário poderá alterar os parâmetros na tela de configurações do leite.

### 4.3 Aba `Leite Alimentação`

Nova aba para produtos usados na produção leiteira:

1. `Produto`
2. `Fabricante`
3. `Categoria`
4. `Peso Saco (kg)`
5. `Proteína Bruta (%)`
6. `NDT/Energia (%)`
7. `Fibra (%)`
8. `Cálcio (%)`
9. `Fósforo (%)`
10. `Consumo Recomendado (g/cab/dia)`
11. `Preço por Saco (R$)`
12. `Lote`
13. `Validade`
14. `Observação`
15. `Ativo`

Aba `Leite Necessidades` para necessidades diárias configuradas por categoria produtiva:

1. `Categoria Produtiva`
2. `Nutriente ou Item`
3. `Valor Diário`
4. `Unidade`
5. `Fonte`
6. `Data Revisão`
7. `Observação`
8. `Ativo`

A categoria diferencia `Ração de lactação`, `Concentrado`, `Silagem`, `Mineral`, `Volumoso` e `Outro`. O sistema aceita produtos sem ficha nutricional completa.

A ficha de necessidades diárias deve permitir registrar, por categoria produtiva (`lactação`, `seca`, `pré-parto`, `recém-parida`), os valores disponíveis para acompanhamento por animal: água, matéria seca, proteína bruta, energia/NDT, fibra, cálcio, fósforo e mineralização. Cada necessidade deve ter valor, unidade, fonte ou observação e data de revisão. Campos sem orientação técnica ficam como “não informado”; o sistema não calcula uma recomendação clínica automaticamente.

O painel compara, quando houver dados compatíveis, a necessidade diária configurada com o consumo registrado de cada produto. Consumo de ração, sal, concentrado, silagem e volumoso continua sendo medido em sua própria unidade e não pode ser somado como se todos fossem o mesmo nutriente.

### 4.4 Aba `Leite Tratamentos`

Nova aba para registrar despesas de saúde relacionadas à atividade leiteira, sem alterar a aba `Gastos` nem o resultado oficial do gado de corte:

1. `Data`
2. `Vaca ID`
3. `Brinco`
4. `Tipo` — medicamento, veterinário, exame, procedimento ou outro
5. `Descrição`
6. `Produto/Serviço`
7. `Quantidade`
8. `Unidade`
9. `Custo (R$)`
10. `Responsável`
11. `Período de Carência`
12. `Observação`
13. `ID Envio`
14. `Criado Em`

O tratamento pode ser associado a uma vaca, ou ao rebanho leiteiro quando não houver animal específico. O custo entra na margem estimada do leite somente quando estiver nessa aba e tiver valor válido. A carência é informativa e deve aparecer na ficha da vaca e nos alertas; o sistema não libera automaticamente leite para venda.

### 4.5 Aba `Leite Conforto`

Nova aba para registrar observações de conforto térmico e descanso por data e local:

1. `Data`
2. `Local`
3. `Sombra`
4. `Água Disponível`
5. `Ventilação`
6. `Área de Descanso`
7. `Lotação`
8. `Estresse Térmico`
9. `Descanso Observado`
10. `Observação`
11. `Responsável`
12. `ID Envio`
13. `Criado Em`

Os valores são observacionais e configuráveis, sem transformar uma anotação em diagnóstico veterinário. O painel relaciona conforto com clima, produção, lotação e condição do colchão, mas não afirma causalidade automaticamente.

### 4.6 Aba `Leite Colchão`

Nova aba para acompanhar a cama/colchão da área leiteira, sua higiene, manutenção e custo:

1. `Data`
2. `Local`
3. `Material`
4. `Quantidade`
5. `Unidade`
6. `Custo (R$)`
7. `Fornecedor`
8. `Condição` — `limpa`, `boa`, `úmida`, `suja` ou `precisa trocar`
9. `Próxima Troca`
10. `Observação`
11. `Foto Antes`
12. `Foto Depois`
13. `Responsável`
14. `ID Envio`
15. `Criado Em`

O local pode identificar a sala de ordenha, baia, maternidade ou outro espaço configurado. A quantidade e a unidade ficam livres para registrar, por exemplo, fardos, sacos, carrinhos ou metros cúbicos, sem conversão automática quando a medida não for confiável.

O registro de colchão é operacional e não entra automaticamente no custo oficial do gado de corte. Quando marcado como custo leiteiro, pode alimentar o custo estimado da atividade leiteira. Fotos usam o mesmo mecanismo de armazenamento do projeto e podem ser anexadas antes e depois da troca.

### 4.5 Colunas finais na aba `Animais`

Se a implementação precisar de dados persistentes por animal, adicionar ao final:

- `Uso Produtivo` — `corte`, `leite` ou `ambos`;
- `Situação Leite` — `lactação`, `seca`, `pré-parto`, `inativa`;
- `Último Parto`;
- `Meta Leite (L/dia)`.

O cadastro de produção nunca cria uma nova cabeça nem altera o estoque financeiro.

## 5. Regras de produção

### 5.1 Registro individual

Cada linha representa uma vaca em uma ordenha. O total do dia por vaca é a soma dos registros individuais válidos no período.

Não aceitar litros negativos, texto inválido ou vaca que não exista. Litros zero é permitido para registrar que a vaca foi ordenhada e não produziu.

### 5.2 Registro total

O usuário pode registrar apenas o total da ordenha quando não quiser medir cada vaca. Esse registro entra no total do rebanho, mas não no ranking individual nem na média por vaca.

A tela deve mostrar claramente se o painel usa dados individuais, totais ou ambos. Nunca somar o mesmo volume individual e total como se fossem medições independentes.

### 5.3 Datas e períodos

Datas são gravadas em `dd/mm/aaaa`, seguindo o projeto. Leituras usam `dayfirst=True`. O painel oferece hoje, últimos 7 dias, últimos 30 dias e intervalo personalizado.

## 6. Cálculos

Criar um módulo `leite.py` somente para leitura, validação e cálculos:

- `carregar_producao()`;
- `carregar_configuracao()`;
- `carregar_alimentacao()`;
- `producao_dia()`;
- `resumo_periodo()`;
- `producao_por_animal()`;
- `situacao_lactacao()`;
- `alertas()`;
- `custo_alimentacao()`;
- `receita_estimada()`;
- `serie_diaria()`.

Indicadores:

- animais ativos no sítio;
- vacas leiteiras ativas;
- vacas em lactação;
- litros do dia;
- litros acumulados na semana;
- litros acumulados no mês;
- litros acumulados no período total registrado;
- litros de ontem;
- média de litros por dia no período selecionado;
- média de litros por mês no período selecionado;
- média de litros por animal no período selecionado;
- média por animal em lactação, considerando somente vacas com situação `lactação`;
- dias em lactação por animal, calculados desde o último parto até a data de referência;
- preço por litro;
- receita bruta estimada;
- custo conhecido da alimentação leiteira;
- custo conhecido dos tratamentos leiteiros;
- custo estimado por litro;
- margem estimada.

Quando preço ou custo não estiver configurado, mostrar “não informado” em vez de zero. O mesmo vale para qualidade e consumo.

## 7. Integração com outros módulos

### Animais e fotos

A tela reutiliza brinco, ID, dono, categoria, sexo, foto principal e ficha existentes. Somente fêmeas bovinas ativas podem ser selecionadas por padrão, com opção administrativa para corrigir exceções.

### Colchão/cama da área leiteira

O painel leiteiro mostra a condição atual do colchão, a última troca, os dias desde a troca, a próxima troca prevista e um alerta quando a condição exige ação. A visita ao sítio terá um registro rápido para condição e observação; o histórico detalhado fica em `/leite/colchao`. O custo do material pode ser associado à atividade leiteira, sem contaminar o cálculo financeiro do gado de corte.

### Reprodução

Partos e coberturas existentes alimentam a situação reprodutiva da vaca. O módulo não duplica eventos de reprodução. A data de parto pode ser corrigida na origem e a situação leiteira recalcula.

### Visitas

Visitas continuam sendo a fonte para contagem de sal, proteinado e ração do estoque geral. Produtos leiteiros podem ser vinculados ao consumo da atividade leiteira sem alterar o estoque do corte.

### Fotos

A ficha leiteira mostra a foto principal já armazenada no Drive, sem duplicar arquivos.

### Alertas e previsão do tempo

Criar a rota `/alertas` e o endpoint `/api/alertas`, com uma aba própria no menu. A tela centraliza alertas de produção leiteira, reprodução, manejo, tarefas, estoque de alimentação, nutrição e consumo, lotação, colchão/cama e previsão do tempo. Cada item deve informar a origem, a data, a prioridade (`ok`, `aviso` ou `ruim`) e a ação recomendada; a cor nunca aparece sem a palavra correspondente.

Na parte de nutrição e consumo, o sistema deve mostrar por produto os dados declarados no rótulo (proteína bruta, NDT/energia, fibra, cálcio e fósforo), peso do saco, consumo recomendado em g/cab/dia, consumo registrado quando houver, custo por saco e custo estimado por cabeça/litro. Campos ausentes aparecem como “não informado”. O sistema deve alertar quando houver consumo acima ou abaixo do recomendado, produto sem ficha nutricional, validade próxima, estoque insuficiente ou custo sem dados suficientes para cálculo. O consumo planejado não deve ser tratado como consumo real sem lançamento ou contagem correspondente.

A previsão do tempo deve usar uma fonte pública sem chave, preferencialmente Open-Meteo, consultada no servidor com timeout curto. A configuração do sítio deve guardar, ao final de `sitio_config.json`, `latitude`, `longitude` e `nome_regiao` (sem alterar configurações existentes). O sistema deve manter apenas o último resultado válido em cache por sítio, com horário da consulta e horário da previsão, e exibir “previsão indisponível” quando não houver resposta válida. Não bloquear o dashboard nem os lançamentos quando o serviço estiver fora do ar.

A aba deve mostrar:

- condição atual, temperatura, chuva, vento e horário da última atualização;
- previsão resumida dos próximos dias, sem prometer precisão além da fonte;
- aviso de chuva para orientar manejo, aplicação de produtos, troca do colchão e deslocamento entre pastos;
- alerta de calor ou frio intenso quando os limiares configurados forem atingidos;
- alertas vencidos, novos e resolvidos, sem apagar o histórico operacional automaticamente.

A coleta automática fica fora do primeiro passo: o sistema atualiza ao abrir a aba e por ação explícita “Atualizar previsão”, respeitando o cache. Notificações WhatsApp só serão adicionadas depois da tela local estar testada e dependerão das preferências existentes.

### Dashboard

Adicionar card resumido sem remover os cards existentes:

- animais ativos no sítio;
- vacas leiteiras ativas;
- vacas em lactação;
- média por vaca;
- receita estimada;
- link para lançar ordenha;
- alerta resumido quando houver queda ou lançamento pendente.

## 8. Rotas e telas

Criar os endpoints:

- `/leite` — painel do leite;
- `/leite/ordenha` — lançamento individual ou total;
- `/leite/editar/<id>` — edição de registro;
- `/leite/excluir/<id>` — exclusão protegida por CSRF e backup;
- `/leite/animais` — lista de vacas e situação;
- `/leite/animal/<id>` — ficha e histórico;
- `/leite/alimentacao` — produtos e nutrição;
- `/leite/relatorios` — consulta por período e exportação;
- `/alertas` — central de alertas e previsão do tempo;
- `/api/leite/resumo` — dados para gráficos e atualização do painel;
- `/api/alertas` — alertas normalizados e previsão em cache.

A tela de ordenha deve ter atalhos para data atual, ordenha atual, seleção múltipla de vacas e preenchimento rápido. No celular, cada vaca aparece como cartão; no desktop, pode haver tabela com campos editáveis.

## 9. Alertas

Classificar os alertas com texto e semáforo:

- `ok` — produção dentro da meta;
- `aviso` — queda próxima do limite ou registro pendente;
- `ruim` — queda acima do limite, parto/secagem urgente ou estoque insuficiente.

Alertas mínimos:

- queda percentual em relação à média recente;
- vaca em lactação sem registro pelo número configurado de dias;
- parto próximo;
- secagem próxima;
- vaca recém-parida;
- produto leiteiro próximo da validade;
- estoque leiteiro baixo quando houver consumo e contagem suficientes;
- tratamento em período de carência;
- custo de tratamento sem valor ou sem associação clara ao animal/rebanho;
- calor ou frio intenso sem registro adequado de sombra, água, ventilação ou descanso;
- lotação alta ou área de descanso inadequada.

WhatsApp só será integrado depois de os alertas locais estarem testados, respeitando as preferências por pessoa e nunca enviando em testes.

## 10. Relatórios e exportação

Relatórios devem permitir filtro por período, vaca, dono, situação e tipo de registro. Devem mostrar:

- produção diária e mensal;
- média por vaca;
- ranking de produção;
- evolução da lactação;
- vacas sem registro;
- receita estimada;
- custo e margem quando houver dados;
- alimentação e informação nutricional cadastrada.

Exportação deve reutilizar os mecanismos existentes e não alterar o arquivo de dados original.

## 11. Ajuda e prints

Atualizar `templates/ajuda.html` com uma seção leiteira detalhada:

1. identificar uma vaca leiteira;
2. mudar situação para lactação ou seca;
3. registrar ordenha por vaca;
4. registrar apenas o total da ordenha;
5. corrigir ou excluir um lançamento;
6. consultar a ficha e o histórico;
7. cadastrar produto e copiar dados do rótulo;
8. interpretar proteína, NDT, fibra, cálcio e fósforo;
9. entender custo por litro e margem;
10. usar os alertas e relatórios.

Prints previstos, com versões de computador (`p-`) e celular (`c-`):

- painel do leite;
- lançamento de ordenha;
- lista de vacas;
- ficha individual;
- cadastro de alimentação;
- relatório do leite.

Se o Drive não estiver configurado, a ajuda continua funcionando com texto e marcador de imagem indisponível. Nenhum print será inventado ou apresentado como dado real.

## 12. Testes obrigatórios

Criar testes para:

- migração das três abas novas;
- preservação das abas e colunas atuais;
- validação de litros inválidos;
- produção individual por dia;
- produção total sem ranking individual;
- prevenção de duplicidade por `ID Envio`;
- médias de 7 e 30 dias;
- queda de produção;
- vaca sem registro;
- parto e secagem integrados à reprodução;
- receita sem preço configurado;
- custo sem consumo configurado;
- alimentação nutricional sem campos obrigatórios;
- permissões e CSRF;
- dashboard com dados e sem dados;
- páginas GET sem erro;
- exportação sem gravação indevida;
- invariantes financeiras atuais intactas;
- aba de alertas com previsão disponível, indisponível e desatualizada;
- cache separado por sítio e sem bloqueio quando o serviço meteorológico falhar;
- coordenadas e região configuráveis sem expor dados de outros sítios.

Depois das fases de implementação:

- executar `python -m pytest` em cópia temporária;
- iniciar o Flask;
- revisar dashboard e todas as telas leiteiras no navegador;
- revisar largura móvel;
- conferir console sem erros novos;
- capturar prints da ajuda;
- atualizar textos da ajuda conforme as telas reais.

## 13. Critérios de aceite

O módulo será considerado pronto quando:

- uma pessoa conseguir registrar uma ordenha individual pelo celular em poucos passos;
- o total diário e a média por vaca estiverem corretos;
- o registro total não duplicar os registros individuais;
- a ficha da vaca mostrar histórico e situação produtiva;
- os alertas explicarem o que precisa ser feito;
- produtos nutricionais aparecerem com “não informado” quando o rótulo não tiver o dado;
- o dashboard mostrar o resumo sem derrubar o painel quando não houver registros;
- os relatórios filtrarem corretamente;
- os dados leiteiros não alterarem o resultado oficial do gado de corte;
- a ajuda refletir a interface real e conter os prints disponíveis;
- toda a suíte de testes passar.
