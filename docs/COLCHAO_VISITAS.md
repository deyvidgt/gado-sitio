# Registro de Estado do Colchão nas Visitas (v5.10.1+)

## O que é

Novo campo na **Seção 7: Conforto** do formulário de visitas que permite registrar o estado do colchão dos animais a cada visita ao sítio.

## Por que rastrear o colchão

- 🛏️ Colchão em bom estado = **animais mais confortáveis** e **menos mastite**
- 💰 Colchão desgastado = **lesões, inflamações**, maior incidência de doenças
- 📊 Histórico permite **planejar trocas** de forma preventiva
- ⚠️ Aviso automático quando precisa trocar urgente

## Como usar

### 1. Registrar uma visita

1. Acesse **🌾 Visitas** no menu
2. Clique em **🌾 Registrar Visita**
3. Preencha as seções até chegar em **🛏️ Conforto — Estado do Colchão**
4. Selecione o estado:
   - **✅ OK — bom estado**: Colchão está bom, sem necessidade de troca
   - **🟡 Alerta — próximo de trocar**: Começa a mostrar desgaste, agendar troca em 2-4 semanas
   - **🚨 Crítico — trocar urgente!**: Colchão danificado, trocar imediatamente
   - **— Não verificado**: (padrão) Não foi checado nesta visita

### 2. Sugestões automáticas

Se marcar "Alerta" ou "Crítico", o sistema gera automaticamente:
- 🟡 **Alerta**: "🛏️ Colchão em alerta — programar troca em breve."
- 🚨 **Crítico**: "🚨 Colchão crítico — TROCAR COM URGÊNCIA!"

Essas sugestões aparecem:
- ✅ No resumo da visita
- 📱 No aviso WhatsApp (se habilitado)
- 📋 No histórico de sugestões da visita

### 3. Visualizar histórico

Acesse **🌾 Visitas** para ver:
- Coluna "Estado Colchão" com o status de cada visita
- Ordenação por data (mais recente no topo)
- Filtro por ordem (crescente/decrescente)

## Relação com o módulo de leite

O campo "Estado Colchão" é **integrado ao módulo de leite** (v5.4):

- aba **Conforto** mantém registro detalhado do colchão (quando foi trocado, litros, marca)
- Página de alertas monitoram saúde (brucelose, mastite, higiene)
- Campo **"Estado Colchão"** nas visitas permite **acompanhamento por inspeção visual**

### Fluxo recomendado

1. **Visita ao sítio** → marca status do colchão
2. **Se Alerta** → agende revisão na próxima visita
3. **Se Crítico** → programe compra/troca imediatamente
4. **Após trocar** → registre nova linha em **Leite > Conforto** com data e detalhes

---

## Exemplos de estado

### ✅ OK — bom estado
- Colchão novo ou bem conservado
- Sem áreas danificadas
- Animais deitam sem reclamar

### 🟡 Alerta — próximo de trocar
- Começa a aparecer furos pequenos
- Algumas áreas mais macias/desgastadas
- Animais deitam menos confortáveis

### 🚨 Crítico — trocar urgente!
- Rasgos ou furos grandes
- Espuma saindo ou muito danificada
- Animais recusando deitar no colchão
- **COMPRE/TROQUE IMEDIATAMENTE** para evitar mastite

---

## Dicas de inspeção

| Aspecto | O que verificar | Ação |
|---------|-----------------|------|
| **Superfície** | Furos, rasgos, rachaduras | OK se nenhum ou poucos pequenos |
| **Firmeza** | Colchão cedendo em alguns pontos | Alerta se ceder demais |
| **Cheiro** | Mofo, umidade excessiva | Crítico se muito úmido/fungado |
| **Comportamento** | Animais deitando menos | Crítico se recusam deitar |
| **Sujeira** | Matéria orgânica, fezes acumuladas | OK se limpo regularmente |

---

## Integração com alertas

Quando você marca **Crítico**, o sistema:
- ✅ Cria sugestão "Colchão crítico — TROCAR COM URGÊNCIA!"
- 📱 Envia alerta via WhatsApp (se sugestões ativadas em Configurações)
- 📊 Aparece em **Alertas** como pendência importante

---

## Perguntas frequentes

**P: Qual é a vida útil de um colchão?**  
R: Geralmente 3-5 anos, dependendo de:
- Material (borracha, espuma de PU, látex)
- Frequência de limpeza
- Carga de animais
- Condições climáticas (umidade, temperatura)

**P: Como evitar desgaste rápido?**  
R: 
- ✅ Limpe regularmente com mangueira
- ✅ Deixe secar ao sol (mata fungos)
- ✅ Substitua palha/cama suja
- ✅ Drene bem a baia (evite água parada)

**P: Posso reparar um colchão crítico?**  
R: Pequenos furos podem ser remendados com kit de reparo, mas:
- ❌ Se muitos furos espalhados → melhor trocar
- ❌ Se estrutura comprometida → trocar

**P: Qual colchão comprar?**  
R: Depende de sua região e fornecedores locais. Consulte:
- 📱 Fornecedores regionais de insumos
- 👥 Recomendações de outros criadores
- 💰 Relação custo × durabilidade

---

## Ver também

- 🎯 [Módulo de Leite](./LEITE.md) — conforto térmico e bem-estar
- 📋 [Visitas ao Sítio](../CLAUDE.md#visitas) — registrar observações
- ⚠️ [Alertas WhatsApp](../CLAUDE.md#alertas-whatsapp) — receber notificações
