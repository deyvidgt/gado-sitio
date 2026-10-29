# Estrutura do Menu Reorganizado (v5.10+)

**Data:** 2026-10-28  
**Commit:** 39fa519

## Visão Geral

O menu foi reorganizado em **12 categorias lógicas** para melhor navegação e discoverabilidade de funcionalidades. Cada seção agrupa funcionalidades relacionadas com emojis consistentes.

## Estrutura por Categoria

### 1. **Início & Alertas** 
Hub de entrada do sistema
- 🏠 **Dashboard** → `/dashboard` — painel principal
- 👨‍👩‍👧 **Família** → `/familia` — painel da família (vários sítios)
- 🔔 **Avisos & Alertas** → `/alertas` — central de alertas

### 2. **Animais & Genealogia** 
Cadastro e acompanhamento de animais
- 🐄 **Animais** → `/animais` — lista geral de animais
- ⚖️ **Pesagem** → `/pesagem` — histórico de pesos
- 🐮 **Animais Leite** → `/leite/animais` — vacas leiteiras (subitem)

### 3. **Saúde & Veterinária** 
Monitoramento de saúde e doenças
- 💊 **Mastite & Qualidade** → `/leite/saude` — qualidade do leite (CCS/CPP)
- 🩺 **Doenças & Carência** → `/doencas` — rastreamento de doenças e períodos de carência

### 4. **Reprodução & Partos** 
Gestão reprodutiva
- 🐮 **Reprodução** → `/reproducao` — coberturas, diagnósticos
- 🍼 **Previsão de Partos** → `/partos` — calendário de partos (Onda 3)

### 5. **Nutrição & Alimentação** 
Módulo de nutrição e ração
- 🥛 **Painel Leite** → `/leite` — resumo leiteiro
  - 🍽️ **Nutrição** → `/leite/nutricao` — necessidades nutricionais (subitem)
  - 📊 **Consumo** → `/leite/consumo` — consumo de rações (subitem)
- 🌾 **Volumosos** → `/volumosos` — gestão de volumosos
- 🧂 **Insumos & Estoque** → `/insumos/comparar` — preços e estoque
- 🧮 **Calculador Ração** → `/racao/calculador` — cálculo de necessidades nutricionais (v5.10)
- 📉 **Conversão Alimentar** → `/nutrição/conversão` — eficiência alimentar (Onda 5)

### 6. **Pastos & Manejo** 
Gestão de pastagens e práticas de manejo
- 🗺️ **Pastos** → `/pastos` — mapa de pastos com Leaflet
  - 📍 **Ocupação & Rotação** → `/pastos/ocupação` — lotação dinâmica (Onda 6) (subitem)
- 🌿 **Manejo** → `/manejo` — registro de atividades de manejo
  - 🏠 **Conforto Térmico** → `/leite/conforto` — monitoramento de conforto (subitem)
  - 🛏️ **Colchão** → `/leite/colchao` — histórico de colchões (subitem)

### 7. **Confinamento & Engorda** 
Gestão de confinamento
- 🏚️ **Confinamento** → `/confinamento` — ciclos de confinamento

### 8. **Genética** 
Análise genética e consanguinidade
- 🧬 **Genética & Consanguinidade** → `/genetica` — coef. Wright, progênie (Onda 4)

### 9. **Registros & Eventos** 
Transações e eventos principais
- 📦 **Compras** → `/compras` — registro de compras
- 💸 **Gastos** → `/gastos` — registro de despesas
- 🤝 **Vendas** → `/vendas` — registro de vendas
- 🗓️ **Visitas** → `/visitas` — visitas ao sítio
- 📋 **Tarefas** → `/tarefas` — agenda de tarefas
- 📅 **Calendário** → `/calendario` — calendário unificado (v5.10)

### 10. **Lotes & Indicadores** 
Análise econômica e indicadores de desempenho
- 📦 **Lotes** → `/lotes` — painel econômico por lote (FIFO)
  - 🌾 **GMD vs Pastagem** → `/indicadores/engorda-pastagem` (subitem)
  - 📊 **GMD vs Lotação** → `/indicadores/gmd-lotacao` (subitem)
  - 🥣 **Ração Consumo** → `/indicadores/racao-consumo` (subitem)
  - 🐂 **Mortalidade** → `/indicadores/mortalidade-bezerros` (subitem)
- 📈 **Relatórios** → `/relatorios` — relatórios customizados

### 11. **Financeiro** 
Análise financeira
- 💰 **Financeiro** → `/financeiro` — resumo financeiro geral
  - 📊 **Resultado Membro** → `/resultado` (subitem)
  - 📈 **Comparativo Anual** → `/comparativo-anual` (subitem)
  - 📊 **Fluxo Caixa** → `/fluxo-caixa` (subitem)
  - 🐄 **Fluxo Animais** → `/fluxo-animais` (subitem)
- 📲 **Lembretes WhatsApp** → `/lembretes-whatsapp` — gerenciar lembretes

### 12. **Utilidades & Admin** 
Ferramentas e configurações
- ➕ **Registrar Visita** → `/visitas/nova` — entrada rápida de visita
- 🎤 **Comando de Voz** → `/voz` — interface de voz
- ❓ **Ajuda** → `/ajuda` — manual do sistema
- 🌤️ **Tempo** → `/tempo` — previsão do tempo
- ⚙️ **Configurações** → `/configuracoes` — settings do sistema
- 🚪 **Sair** → `/logout` — logout (em vermelho para destaque)

---

## Funcionalidades por Onda

| Onda | Funcionalidade | Categoria | Rota |
|------|---|---|---|
| **1** | Mastite Prediction | Saúde & Veterinária | `/leite/saude` ✅ |
| **2** | Doenças & Carência | Saúde & Veterinária | `/doencas` ✅ |
| **3** | Previsão de Partos | Reprodução & Partos | `/partos` ✅ |
| **4** | Consanguinidade | Genética | `/genetica` ✅ |
| **5** | Conversão Alimentar | Nutrição & Alimentação | `/nutrição/conversão` ✅ |
| **6** | Ocupação de Pastos | Pastos & Manejo | `/pastos/ocupação` ✅ |
| **7** | Testes | — | — ✅ |

---

## Mudanças Implementadas

### Antes (Desorganizado)
- 40+ links em sequência aleatória
- Sem agrupamento por módulo
- Funcionalidades críticas sem acesso direto
- Difícil descoberta de novos recursos

### Depois (Organizado)
- **12 seções lógicas** com separadores visuais
- **Sub-itens indentados** (13px) para relações pai-filho
- **Todos os 7 módulos** com acesso direto
- **Emojis consistentes** por categoria
- **Ordem de prioridade:** Início → Animais → Saúde → Reprodução → Nutrição → Pastos → Genética → Registros → Indicadores → Financeiro → Utilidades → Admin

---

## Guia de Manutenção

### Adicionar novo link
1. Escolha a categoria apropriada (ex: "Nutrição & Alimentação")
2. Adicione entre as tags de comentário da seção
3. Use emojis da categoria (🥛 = leite, 🧬 = genética, etc)
4. Se for sub-item, use `style="font-size:13px;padding-left:28px"` e inicie com 2 espaços

### Remover link
1. Procure a seção no menu
2. Remova a linha `<a href="...">` completa
3. Se deixou seção vazia, considere remover a seção toda

### Reorganizar seções
1. Mantenha a ordem lógica (Início → Core → Analytics → Admin)
2. Sempre inclua `<hr>` entre seções
3. Atualize este arquivo com a nova ordem

---

## Notas Técnicas

- **Menu é drawer-based:** Fixed sidebar direito, toggle com button
- **Responsivo:** Funciona em desktop e mobile
- **Tema:** Herda cores de `base.html` (light/dark mode)
- **Acessibilidade:** Todos os links têm `class="drawer-link"` para CSS unificado

---

**Última atualização:** 2026-10-28 | **Autor:** Claude Code
