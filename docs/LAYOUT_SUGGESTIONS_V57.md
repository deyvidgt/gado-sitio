# Sugestões de Layout para v5.7

**Data:** 2026-10-27  
**Análise de:** 60+ imagens de apps de gestão de gado (JetBov, Leigado, AgriWebb, exemplos customizados)

---

## 1. Resumo por Imagem

### 1.1 JetBov - Manejo de Curral (ArteAplicativoJetBovManejo.png)
- **Layout:** 3 telas lado a lado
- **Padrão:** Menu vertical em cada tela com ícones + texto
- **Navegação:** Abas tipo "Manejos de curral" → "Manejo de Pesagem" → "Vacinas/Mortes/Nascimentos"
- **Destaque:** Botão flutuante para Offline (sincronização posterior)
- **Componentes:** Checkboxes, radio buttons, inputs de data

### 1.2 AgriWebb - Pastagem (BR - AgriWebb Grazing Management.png)
- **Layout:** Overlay de dashboard sobre imagem aérea
- **Cards:** Métricas-chave (88 dias, 100+ dias, 16.21 UA, 0.03 UA/ha)
- **Dados:** Consumo, Lotação, Carga em tempo real
- **Visual:** Fundo com foto do pasto, card translúcido com dados

### 1.3 AgriWebb - Animal Individual (BR AgriWebb Homepage Feature - Animal Management.png)
- **Layout:** Animal com tags visuais (brinco, ID eletrônico, tag no rebanho)
- **Gráfico:** Linha de peso ao longo do tempo
- **Informações:** Classificação (Nelore Garrote), tags com cores

### 1.4 Dashboard Desktop (PainelCorte.png)
- **Layout:** Dashboard com múltiplas seções
- **Componentes:** Gráficos, tabelas, ocorrências
- **Sidebar:** Menu principal esquerdo (Painel, Cadastrar, Lançamento, Ocorrências, Financeiro)
- **Cores:** Verde para ações, branco para fundo

### 1.5 Peso por Câmera / AR (modulo pesar pela*.jpg)
- **Layout:** Overlay de resultado em tempo real
- **Visual:** Foto do animal com peso destacado (515.3 kg)
- **Marca:** "PESO RURAL" com logo
- **Interação:** Captura automática de medidas (perímetro do peito)

### 1.6 Monitoramento de Cocho (colcho*.png/jpeg)
- **Layout:** Foto do cocho + dashboard em card
- **Dados:** Volume (432 kg), dias restantes, consumo médio
- **Status:** Última salga, última leitura de cocho
- **Botão:** "+ Salgar cocho" em verde
- **Menu:** Bottom bar com opções de alimentação

### 1.7 Calendário (calendario.png)
- **Layout:** Calendário tradicional com múltiplos eventos
- **Eventos:** Reprodução, Parto, Cobertura em cores
- **Navegação:** Setas para mês anterior/próximo
- **Sidebar:** Menu principal (Painel, Cadastrar, Lançamento, Ocorrências, Financeiro, Calendário)

---

## 2. Padrões Encontrados

### 2.1 Navegação

#### Top Bar
- **Altura:** ~56px em mobile
- **Background:** Azul escuro (ex.: #1a3a52 ou similar)
- **Conteúdo:**
  - Botão voltar (`<`) esquerda
  - Título centralizado (negrito)
  - Botão de ação direita (+ para adicionar, ? para ajuda)
- **Status bar:** Hora, sinal, bateria (sempre visível em mobile)

#### Tabs Horizontais
- **Estilo:** Abas em fila (Lactating, Dry, Heifer, Beef)
- **Comportamento:** Slide horizontal, aba ativa com fundo/sublinhado
- **Tamanho:** ~50px altura, labels em branco
- **Interação:** Touch para trocar (sem necessidade de enviar formulário)

#### Bottom Bar de Navegação
- **5 ícones:** Página inicial (casa), Agenda, Relatórios, Conversa, Perfil
- **Badge:** Número em vermelho para notificações (ex.: "1" no Perfil)
- **Background:** Branco com sombra sutil
- **Ícones:** 24-28px, preto/cinza base, azul quando ativo

#### Menu Hamburger / Sidebar
- **Expandível:** Ícone no topo esquerdo abre/fecha
- **Itens:** Painel, Cadastrar, Lançamento, Ocorrências, Financeiro, Calendário
- **Visual:** Fundo cinza claro ou branco, items com ícone + texto
- **Destaque:** Item ativo com fundo colorido (azul/verde)

### 2.2 Cards e Componentes Reutilizáveis

#### Card de Status com Badge
```
┌─────────────────────────┐
│ Pasto Norte        [red]│  ← Badge: "Ocupado" em fundo rosa
│ 125 Animais        160   │  ← Tri-coluna: número grande + rótulo
│ Capacidade         48 ha │
├─────────────────────────┤
│ ████████░ 78% da cap.   │  ← Barra de progresso em red
└─────────────────────────┘
```
**Uso:** Pastos, Insumos, Animais

#### Tri-coluna (Número Grande)
```
┌──────────────┬──────────────┬──────────────┐
│      125     │      160     │    48 ha     │
│   Animais    │  Capacidade  │    Área      │
└──────────────┴──────────────┴──────────────┘
```
**CSS:** `.tri { display: grid; grid-template-columns: 1fr 1fr 1fr; }`

#### Barra de Progresso com Status
```
┌────────────────────────────────────┐
│ ████████░░░░ 78% da capacidade     │
└────────────────────────────────────┘
```
**Cores:**
- Verde (≤75%): Em pé
- Amarelo (76-90%): Aviso visual
- Vermelho (>90%): Crítico

#### Card de Métrica (KPI)
```
┌──────────────────┐
│  R$ 169.864,55   │  ← Número grande em verde/vermelho
│   Saldo atual    │  ← Label pequeno
└──────────────────┘
```
**Uso:** Dashboard financeiro, resumo de insumos

#### Lista com Ícones Laterais
```
┌─────────────────────────────────┐
│ Sugestão Troca De Lote     ► 🔔 │
│ 04/07/2025                       │
└─────────────────────────────────┘
┌─────────────────────────────────┐
│ Descartar leite (Dayse)    ► 🔔 │
│ Animal 3587                      │
└─────────────────────────────────┘
```
**Padrão:** Seta ou ícone à direita, rótulo pequeno em cinza

#### Formulário com Stepper
```
Step Indicator:
⊙ ── ○ ── ○ ── ○
 1     2    3    4
```
**Uso:** Assistentes multi-passo (Ração, Cadastro de Fazenda)

### 2.3 Dados Visuais

#### Gráfico de Peso
- **Tipo:** Linha simples, azul ou verde
- **Eixos:** Data (X), Peso em kg (Y)
- **Responsivo:** No mobile, rotular apenas pontos-chave
- **Interação:** Tap em ponto mostra data + peso

#### Gráfico de CCS / CPP
- **Tipo:** Linha com zona de alerta
- **Cores:** Verde (bom), Amarelo (aviso), Vermelho (crítico)
- **Labels:** Valores inline quando possível

#### Calendário
- **Grid:** 7 colunas (seg-dom)
- **Eventos:** Ponto colorido no dia ou badge pequeno
- **Cores:** Cada tipo de evento em cor diferente
  - Reprodução: Azul
  - Parto: Verde
  - Cobertura: Amarelo
  - Morte/Perda: Vermelho

#### Tabela Responsiva (Mobile)
- **Padrão:** Não usar `<table>` no mobile
- **Alternativa:** Lista de cards com campos lado a lado
```
┌────────────────────────┐
│ Produto: Ração         │
│ Qtd: 50 sacos          │
│ R$ 2.500,00            │
└────────────────────────┘
```

### 2.4 Formulários

#### Input Field Padrão
```
┌─────────────────────────────┐
│ Matéria Seca, kg            │ ← Label acima
│ ┌───────────────────────────┤
│ │ 23.63                     │ ← Input com value
│ └───────────────────────────┘
└─────────────────────────────┘
```
**Características:**
- Label acima do campo (não placeholder)
- Input com padding 12px
- Border-radius: 4-8px
- Foco: border em azul, shadow sutil

#### Select / Dropdown
```
Ration Group Selection:
┌──────────┬──────────┬──────────┬──────────┐
│ Lactating│   Dry    │  Heifer  │  Beef    │
└──────────┴──────────┴──────────┴──────────┘
```
**Estilo:** Abas no mobile, não dropdown tradicional

#### Radio Button / Checkbox
```
○ Deitado        ← Em pé: espaçamento 12px
○ Em pé
○ Em pé no cocho
```
**Tamanho:** 20x20px, spacing 8px do label

#### Toggle Switch
```
Sodomia: [○] Não  ← Estilo iOS-like
```

#### Botão de Ação
```
┌─────────────────┐
│  + CADASTRAR    │  ← Verde, uppercase, 48px height
└─────────────────┘
```
**Cores:**
- Ação primária: Verde (#2ecc71 ou similar)
- Ação secundária: Cinza
- Destrutiva: Vermelho (+ confirmação)

#### Contador (+/-)
```
Corn Silage     1 kg    [−][+]
```
**Estilo:** Botão pequeno 32x32px com ícone +/-

---

## 3. Cores e Ícones

### 3.1 Paleta de Cores

| Uso | Cor | Hex | Exemplo |
|-----|-----|-----|---------|
| **Header/Primary** | Azul Escuro | `#1a3a52` ou `#2c5aa0` | Top bar, botões primários |
| **Success/Ação** | Verde | `#2ecc71` ou `#27ae60` | Botão Cadastrar, Status Livre |
| **Warning** | Amarelo | `#f39c12` ou `#f1c40f` | Capacidade 75-90%, Aviso |
| **Danger/Crítico** | Vermelho | `#e74c3c` ou `#c0392b` | Capacidade >90%, Urgente |
| **Neutral** | Cinza | `#95a5a6` ou `#bdc3c7` | Labels, texto secundário |
| **Background** | Branco/Off-white | `#ffffff` ou `#f5f5f5` | Fundo, cards |
| **Hover** | Cinza claro | `#ecf0f1` | Hover de cards, links |

### 3.2 Ícones (Unicode + SVG)

| Ícone | Uso | Alternativa |
|-------|-----|-------------|
| 🔔 | Notificação, Tarefa urgente | 🚨, ⚠️ |
| 🎤 | Voz, Ditado | 🔊 |
| 📷 | Câmera, Foto | 🖼️ |
| 💬 | Comentário, Nota | 📝 |
| 👤 | Perfil, Usuário | 👥 |
| ➕ | Adicionar | ⊕ |
| ✏️ | Editar | ✐ |
| 🗑️ | Deletar | ✕ |
| ⬅️ | Voltar | ◀ |
| ➡️ | Próximo | ▶ |
| ⭐ | Favoritar, Importante | ★ |
| 📊 | Gráfico, Relatório | 📈 |
| 📅 | Calendário | 📆 |
| 🏠 | Home, Página inicial | 🏡 |
| 🐄 | Animal, Gado | 🐮 |
| 🌾 | Pasto, Forragem | 🌱 |
| 🍽️ | Alimentação, Cocho | 🥘 |
| 💰 | Financeiro, Valor | 💵 |
| 📈 | Crescimento, GMD | 📊 |

**Ícones Compostos (Material Design ou Font Awesome):**
- `home`, `add`, `edit`, `delete`, `calendar`, `chat`, `person`, `settings`, `arrow_back`

---

## 4. Responsividade (Mobile-First)

### 4.1 Breakpoints
```css
/* Mobile */
max-width: 480px;    /* Tela padrão de smartphone */

/* Tablet */
480px < width < 768px;

/* Desktop */
width > 768px;
```

### 4.2 Touch Targets
- **Mínimo:** 44x44px (WCAG AAA)
- **Ideal:** 48x56px
- **Espaçamento:** 8px entre elementos

### 4.3 Layout Responsivo

#### Mobile (< 480px)
- **Stack vertical:** Cards, listas em 1 coluna
- **Abas:** Todas as abas visíveis em scroll horizontal (não stack)
- **Inputs:** Full-width (100% - 16px padding)
- **Tabelas:** Converter para cards com labels

#### Tablet (480-768px)
- **Grid:** 2 colunas para KPIs
- **Cards:** 2 colunas onde apropriado
- **Landscape:** Considerar 3 colunas

#### Desktop (> 768px)
- **Sidebar:** Sempre visível (não hamburger)
- **Grid:** 3-4 colunas para dashboards
- **Tabelas:** Usar tabelas reais com scroll horizontal se necessário

### 4.4 Imagens Responsivas
- **Foto de animal:** `max-width: 100%; height: auto;`
- **Mapa do pasto:** Canvas responsive com `canvas-width/height`
- **Gráficos:** Redimensionar SVG/Chart.js no resize
- **Lazy loading:** Fotos de Drive com `loading="lazy"`

---

## 5. Componentes Reutilizáveis para v5.7

### 5.1 Novos Componentes de Layout

#### 1. Header Padrão (melhorado)
```html
<header class="header-v57">
  <button class="btn-voltar">←</button>
  <h1>Pastos</h1>
  <button class="btn-acao">+</button>
</header>
```
**CSS:**
```css
.header-v57 {
  background: linear-gradient(135deg, #1a3a52 0%, #2c5aa0 100%);
  color: white;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 56px;
}

.header-v57 h1 {
  font-size: 20px;
  font-weight: 600;
  flex: 1;
  text-align: center;
}

.btn-acao {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(255,255,255,0.2);
  color: white;
  border: none;
  font-size: 24px;
}
```

#### 2. Card com Badge de Status
```html
<div class="card-status">
  <div class="card-header">
    <h2>Pasto Norte</h2>
    <span class="badge badge-ocupado">Ocupado</span>
  </div>
  <div class="tri">
    <div class="tri-item">
      <div class="tri-num">125</div>
      <div class="tri-label">Animais</div>
    </div>
    <div class="tri-item">
      <div class="tri-num">160</div>
      <div class="tri-label">Capacidade</div>
    </div>
    <div class="tri-item">
      <div class="tri-num">48</div>
      <div class="tri-label">ha</div>
    </div>
  </div>
  <div class="barra">
    <i class="fill" style="width: 78%;"></i>
  </div>
  <div class="barra-label">78% da capacidade</div>
</div>
```
**CSS:**
```css
.card-status {
  background: white;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  color: white;
}

.badge-ocupado { background: #e74c3c; }
.badge-aviso { background: #f39c12; }
.badge-livre { background: #27ae60; }

.tri {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  margin: 12px 0;
  text-align: center;
}

.tri-num {
  font-size: 24px;
  font-weight: 700;
  color: #1a3a52;
}

.tri-label {
  font-size: 12px;
  color: #95a5a6;
  margin-top: 4px;
}

.barra {
  width: 100%;
  height: 8px;
  background: #ecf0f1;
  border-radius: 4px;
  overflow: hidden;
  margin: 12px 0;
}

.barra i {
  display: block;
  height: 100%;
  background: #e74c3c;
  transition: width 0.3s ease;
}

.barra.green i { background: #27ae60; }
.barra.yellow i { background: #f39c12; }
.barra.red i { background: #e74c3c; }

.barra-label {
  font-size: 12px;
  color: #7f8c8d;
}
```

#### 3. Card de Lista com Ícone
```html
<div class="card-lista">
  <div class="card-content">
    <div class="card-title">Sugestão Troca De Lote</div>
    <div class="card-date">04/07/2025</div>
  </div>
  <div class="card-icon">
    <span class="icon-notify">🔔</span>
  </div>
</div>
```
**CSS:**
```css
.card-lista {
  background: white;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  border-left: 4px solid #2c5aa0;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a3a52;
}

.card-date {
  font-size: 12px;
  color: #95a5a6;
  margin-top: 4px;
}

.card-icon {
  font-size: 20px;
}
```

#### 4. Formulário com Stepper
```html
<div class="stepper">
  <div class="step active">
    <div class="step-circle">1</div>
  </div>
  <div class="step-line"></div>
  <div class="step">
    <div class="step-circle">2</div>
  </div>
  <div class="step-line"></div>
  <div class="step">
    <div class="step-circle">3</div>
  </div>
  <div class="step-line"></div>
  <div class="step">
    <div class="step-circle">4</div>
  </div>
</div>
```
**CSS:**
```css
.stepper {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 20px 0;
  gap: 8px;
}

.step-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #ecf0f1;
  color: #7f8c8d;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  flex-shrink: 0;
}

.step.active .step-circle {
  background: #e74c3c;
  color: white;
}

.step-line {
  width: 2px;
  height: 2px;
  background: #bdc3c7;
  margin: 0 4px;
}
```

#### 5. Bottom Navigation (Tab Bar)
```html
<nav class="bottom-nav">
  <a class="nav-item active" href="/">
    <span class="nav-icon">🏠</span>
    <span class="nav-label">Página inicial</span>
  </a>
  <a class="nav-item" href="/agenda">
    <span class="nav-icon">📅</span>
    <span class="nav-label">Agenda</span>
  </a>
  <a class="nav-item" href="/relatorios">
    <span class="nav-icon">📊</span>
    <span class="nav-label">Relatórios</span>
  </a>
  <a class="nav-item" href="/chat">
    <span class="nav-icon">💬</span>
    <span class="nav-label">Conversar</span>
  </a>
  <a class="nav-item" href="/perfil">
    <span class="nav-icon">👤</span>
    <span class="nav-label">Perfil</span>
    <span class="badge-notify">1</span>
  </a>
</nav>
```
**CSS:**
```css
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-around;
  background: white;
  border-top: 1px solid #ecf0f1;
  box-shadow: 0 -2px 8px rgba(0,0,0,0.05);
  z-index: 100;
}

.nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 8px;
  text-decoration: none;
  color: #95a5a6;
  font-size: 12px;
  min-height: 60px;
  position: relative;
}

.nav-item.active {
  color: #2c5aa0;
}

.nav-icon {
  font-size: 24px;
  margin-bottom: 4px;
}

.badge-notify {
  position: absolute;
  top: 4px;
  right: 4px;
  background: #e74c3c;
  color: white;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
}
```

#### 6. Tabs Horizontais
```html
<div class="tabs-h">
  <button class="tab-btn active" data-tab="lactating">Lactating</button>
  <button class="tab-btn" data-tab="dry">Dry</button>
  <button class="tab-btn" data-tab="heifer">Heifer</button>
  <button class="tab-btn" data-tab="beef">Beef</button>
</div>
```
**CSS:**
```css
.tabs-h {
  display: flex;
  gap: 12px;
  background: white;
  padding: 12px;
  overflow-x: auto;
  scroll-behavior: smooth;
}

.tab-btn {
  padding: 8px 16px;
  border: 1px solid #bdc3c7;
  border-radius: 4px;
  background: white;
  color: #7f8c8d;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.tab-btn.active {
  background: #2c5aa0;
  color: white;
  border-color: #2c5aa0;
}
```

#### 7. Botão de Ação Grande
```html
<button class="btn-primary-large">+ CADASTRAR</button>
```
**CSS:**
```css
.btn-primary-large {
  width: 100%;
  padding: 16px;
  background: #27ae60;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 700;
  text-transform: uppercase;
  cursor: pointer;
  margin-top: 20px;
  box-shadow: 0 2px 8px rgba(39, 174, 96, 0.3);
  transition: all 0.2s ease;
}

.btn-primary-large:active {
  transform: scale(0.98);
  box-shadow: 0 1px 4px rgba(39, 174, 96, 0.2);
}
```

#### 8. Input com Label
```html
<div class="form-group">
  <label for="ms">Matéria Seca, kg</label>
  <input type="number" id="ms" value="23.63" class="form-input">
</div>
```
**CSS:**
```css
.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #1a3a52;
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  padding: 12px;
  border: 1px solid #bdc3c7;
  border-radius: 4px;
  font-size: 16px;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #2c5aa0;
  box-shadow: 0 0 0 3px rgba(44, 90, 160, 0.1);
}
```

### 5.2 Componentes Já Existentes para Manter
- `.metric` / `.metrics` (KPI, resumo)
- `.card` (card básico)
- `.badge` + `.badge-ok`, `.badge-aviso`, `.badge-ruim` (semáforo)
- `.barra` + `.aviso` / `.ruim` (barra com progresso)
- `.tri` (tri-coluna)
- `.linha` (card-linha para tabelas)

---

## 6. Acessibilidade

### 6.1 Cores + Palavras
- **Nunca** usar cor sozinha para comunicar estado
- **Sempre:** Adicionar badge/label com texto (ex.: "Ocupado" em vermelho + palavra)
- **Legendas:** Gráficos com legenda textual

### 6.2 Contraste
- **Texto em fundo claro:** WCAG AA (4.5:1)
- **Texto em fundo escuro:** WCAG AA (4.5:1)
- **UI elements:** WCAG AA (3:1)

### 6.3 Tamanho de Toque
- **Mínimo:** 44x44px (WCAG AAA)
- **Espaçamento:** 8px entre botões/links adjacentes

### 6.4 Alternativas de Texto
```html
<img src="pasto.jpg" alt="Mapa do Pasto Norte com 125 animais em 48 ha">
<svg role="img" aria-label="Gráfico de lotação">...</svg>
```

### 6.5 Labels Explícitos
```html
<!-- ❌ Ruim -->
<input type="text" placeholder="Peso">

<!-- ✅ Bom -->
<label for="peso">Peso (kg)</label>
<input type="text" id="peso" aria-label="Peso em quilogramas">
```

---

## 7. Performance

### 7.1 Lazy Loading
```html
<!-- Fotos do Drive -->
<img src="..." loading="lazy" width="100" height="100">

<!-- Scripts não-críticos -->
<script defer src="..."></script>
```

### 7.2 Compressão de Imagens
- **Fotos do animal:** 800-1200px, JPG 70-80% qualidade
- **Ícones:** SVG ou PNG com WebP fallback
- **Maps:** Canvas/SVG rasterizado em WebP

### 7.3 Cache e Service Worker
- **Cache estático:** CSS, JS, fontes (cache indefinido)
- **Cache dinâmico:** Imagens do Drive (cache 7 dias)
- **API:** Sem cache em leitura, refetch em POST/PUT

---

## 8. Implementação Recomendada para v5.7

### Fase 1: Componentes Base
1. Atualizar `.header-v57` com gradient azul
2. Implementar `.card-status` com badge
3. Melhorar `.tri` (alinhamento vertical)
4. Adicionar `.bottom-nav` (tab bar)
5. Implementar `.tabs-h` com scroll suave

### Fase 2: Formulários
1. Padronizar `.form-group` em todos os forms
2. Implementar stepper para multi-step
3. Adicionar validação visual (red border + msg)
4. Touch targets mínimo 44x44px

### Fase 3: Páginas
1. **Pastos:** Usar `.card-status` + `.barra` com lotação
2. **Insumos:** Comparador com `.tri` (R$/kg, R$/cab/dia, dias)
3. **Animais:** Peso com gráfico responsivo
4. **Tarefas:** Lista com `.card-lista` + ícones
5. **Painel:** KPIs em `.metric` + `.card-status` para pastos críticos

### Fase 4: Responsividade
1. Breakpoints media queries (480px, 768px)
2. Grid responsivo para dashboards
3. Converter tabelas em cards no mobile
4. Testar landscape em tablets

---

## 9. Especificações de Fonte

- **Headings (h1-h3):** 20-28px, weight 600-700
- **Body:** 14-16px, weight 400-500
- **Labels:** 12-13px, weight 500-600
- **Family:** System stack (segoe ui, roboto, -apple-system)

---

## 10. Referências Visuais

| Elemento | Imagem | Padrão |
|----------|--------|--------|
| Header azul | JetBov, Leigado | Top bar com voltar + título + ação |
| Card status | Pastos v5.2 | Badge + tri-coluna + barra |
| Tab horizontal | Ração (necessidades) | Abas em fila, scroll no mobile |
| Bottom nav | Necessidades Diárias | 5 ícones com badge de aviso |
| Formulário | Cadastro Fazenda | Labels + inputs + stepper |
| Gráfico | Peso, CCS, GMD | Linha com legenda, responsivo |
| Cor verde | Botão Cadastrar | Ação primária, sucesso |
| Cor vermelha | Ocupado, Urgente | Crítico, aviso alto |
| Cor amarela | Aviso, Parcialmente ocupado | Aviso médio, cautela |

---

## Conclusão

A v5.7 deve focar em **componentes reutilizáveis, responsividade mobile-first e acessibilidade**. Os padrões visuais já identificados (header azul, card-status, tri-coluna, barra de progresso) formam um sistema coerente que, quando aplicado sistematicamente, melhorará a usabilidade em mobile e a coesão visual do app.

**Próximos passos:**
1. Revisar `templates/base.html` e atualizar CSS com novos componentes
2. Criar guia de estilo (design tokens) em `static/design-tokens.css`
3. Aplicar componentes v5.7 em 3 páginas-piloto (Pastos, Painel, Tarefas)
4. Testar responsividade em 4 breakpoints (mobile 375px, 480px, 768px, 1024px)
5. Validar acessibilidade (WCAG AA) com aXe DevTools
