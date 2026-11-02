## O que muda

Fecha a **Onda 14** e entrega a **v5.15** (cobertura zootécnica + usabilidade no campo).

### 🎯 Onda 14 — ponto de corte e relatórios PDF
Dois módulos existiam no código sem rota nem template (código morto). Agora têm tela e menu:

- **`/ponto-corte`** — simula vender hoje ou esperar 7/14/30 dias: arrobas = peso × rendimento ÷ 15, × preço da arroba, descontando o custo diário. GMD da última pesagem; preço e rendimento do `sitio_config.json`. Só cálculo, não grava.
- **`/relatorios/avancados`** — 6 PDFs de verdade (anual, vendas, sanitário, reprodutivo, leite, financeiro), ReportLab no mesmo visual do `/relatorio-pdf`.

### 🆕 v5.15 — lacunas zootécnicas e de campo
- **Filtro por dono em Animais** — os cards de dono (Geane/Deyvid/Nilson) viram filtro clicável: clicar filtra a listagem, o card ganha destaque na cor do brinco, clicar de novo (ou em "✖️ Limpar filtro") volta a mostrar todos. A busca de texto passa a combinar com o filtro — a função `filtrar()` era chamada no `oninput` mas **não existia**.
- **Estoque por faixa de peso × sexo** — matriz de arrobas × Macho/Fêmea na página de Pesagem (`pesagem.estoque_faixas_peso`), derivada do último peso de cada animal vivo. Sem campo novo.
- **Mortalidade por faixa etária** — matriz 0-4 / 5-12 / 13-24 / 25-36 / >36 meses com `%Part`, pela idade na `Data Saída` do cadastro (`indicadores_v58.mortalidade_por_faixa_etaria`).
- **Checklist de cocho no celular** — botões grandes (alvo de 56 px) para estado do cocho (Vazio/Normal/Cheio) e comportamento animal (Deitados/Parte em pé/Maioria em pé/Com fome), gravados na visita. Duas colunas novas **no fim** de `COLUNAS_VISITAS`; `db.inicializar()` migra sozinho.

### 🐛 Bugs corrigidos no caminho
- `ponto_corte.py` chamava funções inexistentes (`pesagem.peso_animal()`, `calculos._build_gastos_timeline()`).
- Relatório de leite lia colunas inexistentes — saía tudo zero.
- **Relatório financeiro subtraía as compras** (custo contado 2×).
- `/leite/comparativo` 500 com célula vazia de "Situação Leite" (NaN).
- `animais.html` tinha `{% block scripts %}` duplicado após a edição (corrigido, suíte verde).

## Testes

`python -m pytest` — **suíte completa verde**. Novos: `test_estoque_faixas_peso_cruza_sexo` (em `test_pesagem.py`) e `tests/test_mortalidade_faixa.py`.

## Notas

- Nenhuma coluna existente foi reordenada; as duas novas de Visitas vão no fim.
- O filtro por dono é 100% front-end (os `rows` já trazem o dono) — sem rota nem schema novo.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
