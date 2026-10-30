# Plano: Implementação de Gráficos do Sistema (Onda 8)

**Status:** Iniciado 2026-10-30  
**Prioridade:** Alta (impacto visual, decisões de negócio)  
**Esforço:** 3-4 sessões  
**Bloqueador:** Nenhum

---

## Ondas de Implementação

### Onda 8.1: Fundação (✅ FEITA)
- [x] Biblioteca graficos-sistema.js com 7 tipos base
- [x] Paletas de cores do CATALOGO.md
- [x] Integração com Chart.js 4.4.0 (já em base.html)

### Onda 8.2: Dashboard + Financeiro (TODO)

**Dashboard:**
- Gráfico de colunas: Resultado últimos 12 meses
- Gráfico de linhas: Evolução CMP/GPCab
- Gauge: Ocupação de pastos (%)
- Cards métrica: Já existem, estilizar conforme exemplos

**Financeiro:**
- Gráfico de linhas duplo-eixo: Receita vs Custo
- Gráfico de pizza: Resultado por membro
- Tabela com cores: Status de cada membro

**Arquivos a mexer:**
- `templates/dashboard.html` → adicionar 3 canvas + JS
- `templates/financeiro.html` → adicionar 3 canvas + JS
- `routes_dashboard.py` → passar dados para gráficos
- `routes_financeiro_novo.py` → passar dados para gráficos

---

### Onda 8.3: Leite (TODO)

**Painel Leite:**
- Gráfico de linhas: Produção dia/semana/mês
- Gráfico de linhas: CCS/CPP trending
- Gráfico de barras: Producao por vaca (top 10)
- Gauge: Saúde geral (% vacas saudáveis)

**Arquivos a mexer:**
- `templates/painel_leite.html`
- `routes_leite.py`

---

### Onda 8.4: Pastos + Reprodução (TODO)

**Pastos:**
- Gráfico de barras: Ocupação por pasto
- Gráfico de área: Evolução lotação
- Mapa já existe, mantém

**Reprodução:**
- Gráfico de pizza: Composição (Coberta/Prenha/Vazia/Pariu)
- Timeline: Próximos partos

**Arquivos a mexer:**
- `templates/pastos.html` / `routes_pastos.py`
- `templates/reproducao.html` / `routes_reproducao.py`

---

### Onda 8.5: Indicadores (TODO)

**GMD Unificado (que refiz):**
- Gráfico de linhas: GMD vs Pastagem (tempo)
- Gráfico de barras: Comparativo lotação
- Scatter: Correlação GMD/Lotação

**Outros Indicadores:**
- Lotes: Ganho de peso por lote
- Mortalidade: Série temporal

**Arquivos a mexer:**
- `templates/indicadores/gmd_unificado.html` (já existe)
- `routes_indicadores.py`

---

### Onda 8.6: Testes + Polish (TODO)

- Testar responsividade mobile/desktop
- Validar cores em tema claro/escuro
- Perfil de performance (Canvas vs SVG)
- Documentar uso da biblioteca

---

## Padrão de Implementação

Para cada gráfico:

1. **Backend** (route):
   ```python
   @app.route("/modulo")
   def modulo():
       dados_grafico = calcular_dados()  # dict com labels, data
       return render_template("modulo.html", **dados_grafico)
   ```

2. **HTML** (template):
   ```html
   <div class="grafico-container">
     <canvas id="grafico_resultado"></canvas>
   </div>
   <script src="{{ url_for('static', filename='js/graficos-sistema.js') }}"></script>
   <script>
     const ctx = document.getElementById('grafico_resultado').getContext('2d');
     grafico_colunas(ctx, {{ labels|tojson }}, {{ data|tojson }}, {
       tema: 'claro',
       label: 'Resultado (R$)',
       colors: ['#8ba753']
     });
   </script>
   ```

3. **CSS**: Reusar `.grafico-container` de base.html

---

## Estrutura de Dados Esperada

Cada rota passa ao template:

```python
{
    "grafico_resultado": {
        "labels": ["Jan", "Fev", "Mar", ...],
        "data": [1200, 1500, 900, ...],
        "tipo": "colunas"
    },
    "grafico_cmp": {
        "labels": ["Jan", "Fev", "Mar", ...],
        "datasets": [
            {"label": "CMP", "data": [2450, 2380, 2520]},
            {"label": "GPCab", "data": [120, 140, 130]}
        ],
        "tipo": "linhas"
    }
}
```

---

## Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Performance Canvas em mobile | Lazy-load gráficos, máx 3 por página |
| Cores ilegíveis em tema escuro | Testar WCAG contrast com checker |
| Dados desincronizados | Cache invalidado em cada POST (já temos) |
| Responsividade quebrada | Testar 320px, 768px, 1024px, 1440px |

---

## Checklist de Entrega

- [ ] Onda 8.2 Dashboard: 3 gráficos + testes
- [ ] Onda 8.2 Financeiro: 3 gráficos + testes
- [ ] Onda 8.3 Leite: 4 gráficos + testes
- [ ] Onda 8.4 Pastos: 3 gráficos + testes
- [ ] Onda 8.4 Reprodução: 2 gráficos + testes
- [ ] Onda 8.5 Indicadores: 3 gráficos + testes
- [ ] Onda 8.6 Testes integrados + Polish
- [ ] CHANGELOG.md atualizado
- [ ] Todos os testes passam

---

## Próximo Passo

Execute **Onda 8.2 (Dashboard)** quando pronto. Arquivo pronto em `static/js/graficos-sistema.js`.

