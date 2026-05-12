#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🐄 SISTEMA DE GESTÃO DE GADO — SÍTIO SANTO ANTONIO
Família: Mãe, Deyvid e Nilson
Versão 3.0 — arquitetura modular com cálculos precisos

Módulos:
  config.py     — constantes e configurações
  db.py         — leitura/escrita do Excel
  ui_helper.py  — interface e inputs (Rich)
  calculos.py   — motor financeiro (CMP, GPCab, CTCab)
  registros.py  — CRUD: compras, gastos, vendas, manejo
  relatorios.py — relatórios, gráficos, alertas
  exportar.py   — importar/exportar Excel
  main.py       — menu principal (este arquivo)
"""

import sys
from db import inicializar, fazer_backup
from ui_helper import ui_aviso, ui_ok
from calculos import calcular_estoque
from db import carregar_todas

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.columns import Columns
    from rich.align import Align
    from rich.text import Text
    from rich.prompt import Prompt
    from rich import box
    RICH = True
    console = Console()
except ImportError:
    RICH = False
    console = None


# ── Menu visual ───────────────────────────────────────────────────────────────

def _menu_rich(estoque: int):
    console.clear()

    titulo = Text("SISTEMA DE GESTÃO DE GADO  v3.0", style="bold white", justify="center")
    sub    = Text("Sítio Santo Antonio  |  Família: Mãe, Deyvid e Nilson", style="dim white", justify="center")
    console.print(Panel(Align.center(Text.assemble(titulo, "\n", sub)),
                        border_style="bold green", padding=(1, 4)))

    cor_est = "bold green" if estoque > 0 else "bold red"
    console.print(Align.center(
        Panel(f"[{cor_est}]  Estoque atual: {estoque} cabeças  [/{cor_est}]",
              border_style="green", width=42)
    ))
    console.print()

    def bloco(titulo_b, itens, cor):
        t = Table(box=box.SIMPLE, show_header=True,
                  header_style=f"bold {cor}", border_style=cor, min_width=34)
        t.add_column(titulo_b, style="white")
        for num, label in itens:
            t.add_row(f"[bold {cor}]{num:>2}.[/bold {cor}]  {label}")
        return t

    c1 = bloco("📝 REGISTRAR", [
        ("1",  "Nova Compra"),
        ("2",  "Novo Gasto"),
        ("3",  "Nova Venda"),
        ("4",  "Registro de Manejo"),
    ], "cyan")

    c2 = bloco("📊 CONSULTAS", [
        ("5",  "Resumo Geral"),
        ("6",  "Resultado por Membro"),
        ("7",  "Listar Registros"),
        ("8",  "Relatório por Período"),
        ("9",  "Comparativo Anual"),
        ("10", "Estimativa do Rebanho"),
        ("11", "Fluxo de Caixa"),
        ("12", "Cotação IMEA"),
    ], "yellow")

    c3 = bloco("🔧 FERRAMENTAS", [
        ("13", "Editar Registro"),
        ("14", "Excluir Registro"),
        ("15", "Recibo Última Venda"),
        ("16", "Alertas do Rebanho"),
        ("17", "Importar Excel Antigo"),
        ("18", "Exportar Relatório Excel"),
        ("19", "Gráficos"),
        ("20", "Backup Manual"),
    ], "magenta")

    console.print(Columns([c1, c2, c3], equal=True, expand=True))
    console.print()
    console.rule("[dim]0 = Sair[/dim]")
    console.print()


def _menu_simples(estoque: int):
    print(f"\n{'═'*60}")
    print(f"  GESTÃO DE GADO v3.0 | Estoque: {estoque} cabeças")
    print(f"{'═'*60}")
    print("  [REGISTRAR]  1.Compra  2.Gasto  3.Venda  4.Manejo")
    print("  [CONSULTAS]  5.Resumo  6.Membros  7.Listar  8.Período")
    print("               9.Anual  10.Rebanho  11.Fluxo  12.IMEA")
    print("  [FERRAMENTAS] 13.Editar  14.Excluir  15.Recibo")
    print("               16.Alertas  17.Importar  18.Exportar")
    print("               19.Gráficos  20.Backup")
    print("  0. Sair")
    print(f"{'═'*60}")


# ── Mapeamento de ações ───────────────────────────────────────────────────────

def _get_acoes():
    from registros import (
        adicionar_compra, adicionar_gasto, adicionar_venda, adicionar_manejo,
        editar_registro, excluir_registro, recibo_ultima_venda,
    )
    from relatorios import (
        ver_resumo_geral, ver_resumo_por_membro, listar_registros,
        relatorio_por_periodo, comparativo_anual, estimativa_rebanho,
        ver_fluxo_caixa, ver_cotacao, verificar_alertas, gerar_graficos,
    )
    from exportar import importar_excel_antigo, exportar_relatorio_excel

    return {
        "1":  adicionar_compra,
        "2":  adicionar_gasto,
        "3":  adicionar_venda,
        "4":  adicionar_manejo,
        "5":  ver_resumo_geral,
        "6":  ver_resumo_por_membro,
        "7":  listar_registros,
        "8":  relatorio_por_periodo,
        "9":  comparativo_anual,
        "10": estimativa_rebanho,
        "11": ver_fluxo_caixa,
        "12": ver_cotacao,
        "13": editar_registro,
        "14": excluir_registro,
        "15": recibo_ultima_venda,
        "16": verificar_alertas,
        "17": importar_excel_antigo,
        "18": exportar_relatorio_excel,
        "19": gerar_graficos,
        "20": lambda: ui_ok(f"Backup salvo: {fazer_backup()}"),
    }


# ── Loop principal ────────────────────────────────────────────────────────────

def menu():
    acoes = _get_acoes()

    while True:
        dados   = carregar_todas()
        estoque = calcular_estoque(dados["Compras"], dados["Vendas"], dados["Manejo"])

        if RICH:
            _menu_rich(estoque)
            opcao = Prompt.ask("[bold cyan]  Escolha uma opção[/bold cyan]").strip()
        else:
            _menu_simples(estoque)
            opcao = input("  Opção: ").strip()

        if opcao == "0":
            if RICH:
                console.print("\n[bold green]  Até logo! Boas vendas! 🐄[/bold green]\n")
            else:
                print("\nAté logo!\n")
            break

        if opcao in acoes:
            try:
                acoes[opcao]()
            except KeyboardInterrupt:
                ui_aviso("Operação cancelada.")
        else:
            ui_aviso("Opção inválida!")

        if RICH:
            console.print()
            Prompt.ask("[dim]  Enter para continuar[/dim]", default="")
        else:
            input("\n  [Enter para continuar...]")


# ── Execução ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    fazer_backup()
    inicializar()
    menu()
