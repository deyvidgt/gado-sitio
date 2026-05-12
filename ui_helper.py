#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helpers de interface — entrada de dados e exibição com Rich
"""

from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    from rich.text import Text
    from rich.prompt import Prompt
    from rich.rule import Rule
    from rich.columns import Columns
    from rich.align import Align
    RICH = True
except ImportError:
    RICH = False

console = Console() if RICH else None

from config import MEMBROS, NOMES_MEMBROS, EMOJIS_MEMBROS


# ── Output ────────────────────────────────────────────────────────────────────

def ui_titulo(texto: str):
    if RICH:
        console.print()
        console.rule(f"[bold green]{texto}[/bold green]")
        console.print()
    else:
        print(f"\n=== {texto} ===\n")


def ui_ok(msg: str):
    if RICH:
        console.print(f"[bold green]✔[/bold green]  {msg}")
    else:
        print(f"✅ {msg}")


def ui_erro(msg: str):
    if RICH:
        console.print(f"[bold red]✘[/bold red]  {msg}")
    else:
        print(f"❌ {msg}")


def ui_aviso(msg: str):
    if RICH:
        console.print(f"[bold yellow]⚠[/bold yellow]  {msg}")
    else:
        print(f"⚠️  {msg}")


def ui_info(msg: str, indent: int = 2):
    if RICH:
        console.print(f"[dim]{'  ' * indent}{msg}[/dim]")
    else:
        print(f"{'  ' * indent}{msg}")


def ui_separador():
    if RICH:
        console.rule(style="dim green")
    else:
        print("─" * 60)


def ui_painel(titulo: str, conteudo: str, estilo: str = "green"):
    if RICH:
        console.print(Panel(conteudo, title=f"[bold]{titulo}[/bold]",
                            border_style=estilo, padding=(0, 2)))
    else:
        print(f"\n--- {titulo} ---\n{conteudo}\n")


def ui_tabela(titulo: str, colunas: list, linhas: list,
              estilos_col: dict | None = None, cor_header: str = "green"):
    if not RICH:
        print(f"\n{titulo}")
        print("  ".join(str(c) for c in colunas))
        for l in linhas:
            print("  ".join(str(v) for v in l))
        return

    t = Table(title=titulo, box=box.ROUNDED,
              header_style=f"bold white on {cor_header}",
              border_style="green", show_lines=True)

    estilos_col = estilos_col or {}
    for i, col in enumerate(colunas):
        t.add_column(col, style=estilos_col.get(i, ""), no_wrap=False)

    for linha in linhas:
        t.add_row(*[str(v) if v is not None else "" for v in linha])

    console.print(t)


def ui_destaque(label: str, valor: str, positivo: bool | None = None):
    """Exibe um par label/valor com cor condicional."""
    if not RICH:
        print(f"  {label}: {valor}")
        return
    if positivo is True:
        cor = "bold green"
    elif positivo is False:
        cor = "bold red"
    else:
        cor = "bold white"
    console.print(f"  [dim]{label}:[/dim] [{cor}]{valor}[/{cor}]")


# ── Input ─────────────────────────────────────────────────────────────────────

def ui_input(prompt: str, default=None) -> str:
    if RICH:
        sufixo = f" [dim][{default}][/dim]" if default is not None else ""
        return Prompt.ask(f"[cyan]  {prompt}[/cyan]{sufixo}",
                          default=str(default) if default is not None else "")
    else:
        suf = f" [{default}]" if default is not None else ""
        return input(f"  {prompt}{suf}: ").strip()


def ui_int(prompt: str, minv: int = 0, maxv: int = 999999,
           default: int | None = None) -> int:
    while True:
        s = ui_input(prompt, default)
        try:
            v = int(s)
            if minv <= v <= maxv:
                return v
            ui_aviso(f"Digite entre {minv} e {maxv}.")
        except (ValueError, TypeError):
            ui_aviso("Digite um número inteiro válido.")


def ui_float(prompt: str, default: float | None = None) -> float:
    while True:
        s = ui_input(prompt, default)
        try:
            return float(str(s).replace(",", "."))
        except (ValueError, AttributeError):
            ui_aviso("Digite um número válido (ex: 1234.56 ou 1234,56).")


def ui_data(prompt: str = "Data (dd/mm/aaaa)") -> str:
    hoje = datetime.now().strftime("%d/%m/%Y")
    while True:
        s = ui_input(prompt, hoje).strip()
        if not s:
            return hoje
        try:
            datetime.strptime(s, "%d/%m/%Y")
            return s
        except ValueError:
            ui_aviso("Formato inválido. Use dd/mm/aaaa")


def ui_data_simples(prompt: str) -> str:
    while True:
        s = ui_input(prompt).strip()
        try:
            datetime.strptime(s, "%d/%m/%Y")
            return s
        except ValueError:
            ui_aviso("Formato inválido. Use dd/mm/aaaa")


def ui_escolher_membro(prompt: str = "Membro:") -> str:
    ui_info(prompt)
    for i, m in enumerate(MEMBROS, 1):
        emoji = EMOJIS_MEMBROS.get(m, "")
        ui_info(f"  {i}. {emoji} {NOMES_MEMBROS.get(m, m)}")
    idx = ui_int("Escolha", 1, len(MEMBROS))
    return MEMBROS[idx - 1]


def ui_continuar():
    if RICH:
        Prompt.ask("[dim]  Enter para continuar[/dim]", default="")
    else:
        input("\n  [Enter para continuar...]")


def fmt_r(valor) -> str:
    """Formata valor em Reais. Aceita float, int, None e NaN sem explodir."""
    try:
        f = float(valor)
        if f != f:  # NaN check
            return "R$ —"
        return f"R$ {f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "R$ —"


def fmt_pct(valor: float) -> str:
    """Formata percentual."""
    sinal = "+" if valor > 0 else ""
    return f"{sinal}{valor:.1f}%"


def fmt_cabecas(n: int) -> str:
    return f"{n} cabeça{'s' if n != 1 else ''}"
