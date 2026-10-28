#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations  # compatibilidade Python 3.9+
"""
Camada de acesso a dados — leitura, escrita e backup do Excel

IMPORTANTE — onde ficam os dados:
  Os dados (gado_familia.xlsx, usuarios.json, backups/) ficam em ~/gado-dados/,
  FORA do repositório Git. Assim o git pull nunca mais apaga seus dados.

  Hierarquia de busca do DATA_DIR:
    1. ~/gado-dados/          → pasta permanente fora do Git (produção)
    2. Pasta do executável    → modo .exe (Windows)
    3. Pasta do script        → desenvolvimento local
"""

import os, sys
import json
import shutil
import threading
from contextlib import contextmanager
import pandas as pd
from datetime import datetime
from openpyxl import Workbook, load_workbook


# Mora em pasta_dados.py (o config também precisa, e config não pode importar db).
from pasta_dados import _resolver_data_dir  # noqa: E402,F401


# DATA_DIR é onde ficam gado_familia.xlsx, usuarios.json e backups/
# É DIFERENTE da pasta do código — isso protege os dados do git pull
DATA_DIR = _resolver_data_dir()

from config import (
    ARQUIVO_DADOS,
    COLUNAS_COMPRAS, COLUNAS_GASTOS,
    COLUNAS_VENDAS, COLUNAS_MANEJO, COLUNAS_VISITAS, COLUNAS_ANIMAIS, COLUNAS_FOTOS,
    COLUNAS_PASTOS, COLUNAS_TAREFAS, COLUNAS_MEDICACOES, COLUNAS_LEITE_PRODUCAO, COLUNAS_LEITE_CONFIG,
    COLUNAS_LEITE_ALIMENTACAO, COLUNAS_LEITE_NECESSIDADES, COLUNAS_LEITE_TRATAMENTOS,
    COLUNAS_LEITE_CONFORTO, COLUNAS_LEITE_COLCHAO,
    COLUNAS_VOLUMOSOS, COLUNAS_CONSUMO_VOLUMOSOS,
    COLUNAS_ENGORDA_PASTAGEM, COLUNAS_GMD_LOTACAO, COLUNAS_RACAO_CONSUMO,
    COLUNAS_MORTALIDADE_BEZERROS,
)

# Mapa aba → colunas esperadas, usado para migrar colunas novas sem perder dados.
_SCHEMA_ABAS = {
    "Compras": COLUNAS_COMPRAS,
    "Gastos":  COLUNAS_GASTOS,
    "Vendas":  COLUNAS_VENDAS,
    "Manejo":  COLUNAS_MANEJO,
    "Visitas": COLUNAS_VISITAS,
    "Animais": COLUNAS_ANIMAIS,   # v4.3 — criada sozinha no arquivo existente
    "Fotos":   COLUNAS_FOTOS,     # v4.4
    "Pastos":  COLUNAS_PASTOS,    # v5.2
    "Tarefas": COLUNAS_TAREFAS,   # v5.3
    "Medicações": COLUNAS_MEDICACOES,  # v5.7 — histórico de medicações
    "Leite Produção": COLUNAS_LEITE_PRODUCAO,
    "Leite Configuração": COLUNAS_LEITE_CONFIG,
    "Leite Alimentação": COLUNAS_LEITE_ALIMENTACAO,
    "Leite Necessidades": COLUNAS_LEITE_NECESSIDADES,
    "Leite Tratamentos": COLUNAS_LEITE_TRATAMENTOS,
    "Leite Conforto": COLUNAS_LEITE_CONFORTO,
    "Leite Colchão": COLUNAS_LEITE_COLCHAO,
    "Volumosos": COLUNAS_VOLUMOSOS,
    "Consumo Volumosos": COLUNAS_CONSUMO_VOLUMOSOS,
    "Engorda Pastagem": COLUNAS_ENGORDA_PASTAGEM,  # v5.8
    "GMD Lotação": COLUNAS_GMD_LOTACAO,  # v5.8
    "Ração Consumo": COLUNAS_RACAO_CONSUMO,  # v5.8
    "Mortalidade Bezerros": COLUNAS_MORTALIDADE_BEZERROS,  # v5.8
    "Confinamento Lotes": COLUNAS_CONFINAMENTO_LOTES,  # v5.10
    "Genética": COLUNAS_GENETICA,  # v5.10
}

# Caminho completo do arquivo de dados
ARQUIVO_PATH = os.path.join(DATA_DIR, ARQUIVO_DADOS)

# Pasta da família: usuários, chave de sessão, bloqueios de login e sitios.json.
# DATA_DIR/ARQUIVO_PATH apontam para o sítio do pedido (sitios.ativar → usar_pasta).
RAIZ = DATA_DIR


def usar_pasta(pasta: str) -> None:
    """Passa a ler/gravar os dados do sítio que mora em `pasta`."""
    global DATA_DIR, ARQUIVO_PATH
    os.makedirs(pasta, exist_ok=True)
    DATA_DIR = pasta
    ARQUIVO_PATH = os.path.join(pasta, ARQUIVO_DADOS)

# Garantir que a pasta de dados existe (cria ~/gado-dados/ se necessário)
os.makedirs(DATA_DIR, exist_ok=True)

# Log no boot para confirmar onde estão os dados
print(f"📂 Dados em: {DATA_DIR}", flush=True)
print(f"📊 Arquivo:  {ARQUIVO_PATH}", flush=True)


# ── Backup ────────────────────────────────────────────────────────────────────

def fazer_backup() -> str | None:
    if not os.path.exists(ARQUIVO_PATH):
        return None
    backup_dir = os.path.join(DATA_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    nome = os.path.join(backup_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    with _trava_escrita():   # nunca copiar no meio de uma gravação
        shutil.copy(ARQUIVO_PATH, nome)
    return nome


# ── Inicialização ─────────────────────────────────────────────────────────────

# Padrões da v4.0 que mudaram na v4.1 (calendário 5-7-9 da Embrapa).
_PADROES_ANTIGOS = {"Vermifugação": 120}


def get_alertas_saude() -> dict:
    """
    Intervalos (em dias) dos alertas de saúde EFETIVOS: começa dos padrões em
    config.ALERTAS_SAUDE e aplica os ajustes salvos pelo usuário em
    sitio_config.json (chave "alertas_saude"). Mantém os mesmos tipos; só os dias
    podem mudar. Fonte única usada pelo calendário, alertas e WhatsApp.
    """
    from config import ALERTAS_SAUDE as _DEFAULT
    base = dict(_DEFAULT)
    try:
        cfg_path = os.path.join(DATA_DIR, "sitio_config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, encoding="utf-8") as f:
                salvos = (json.load(f) or {}).get("alertas_saude", {}) or {}
            for tipo in base:
                try:
                    v = int(salvos[tipo])
                    # v4.1: o formulário salva TODOS os campos, então um valor igual ao
                    # padrão antigo quase sempre é "não mexi". Usa o padrão novo.
                    if _PADROES_ANTIGOS.get(tipo) == v:
                        continue
                    if v > 0:
                        base[tipo] = v
                except (KeyError, TypeError, ValueError):
                    pass
    except Exception:
        pass
    return base


def _garantir_colunas(ws, colunas) -> bool:
    """
    Garante que o cabeçalho (1ª linha) de `ws` contenha as `colunas` do esquema,
    na ordem, SEM apagar dados. Retorna True se alterou algo.

    Passos:
      1) Preenche POR POSIÇÃO os cabeçalhos vazios conforme o esquema. Assim, um
         valor gravado numa coluna órfã (ex.: "Perda De" salvo antes de a coluna
         existir → "Mae" na col6 sem cabeçalho) passa a ser lido corretamente.
      2) Remove colunas DUPLICADAS: mantém a 1ª; se a duplicata tiver dado e a 1ª
         estiver vazia, move o dado antes de apagar.
      3) Acrescenta no fim qualquer coluna do esquema que ainda falte.
    """
    mudou = False

    # 1) Preenche posicionalmente cabeçalhos vazios/órfãos
    header = [c.value for c in ws[1]]
    for i, nome in enumerate(colunas):
        atual = header[i] if i < len(header) else None
        if atual is None or str(atual).strip() == "":
            ws.cell(row=1, column=i + 1, value=nome)
            mudou = True

    # 2) Remove duplicatas de cabeçalho (mantendo dados)
    header = [c.value for c in ws[1]]
    vistos, apagar = {}, []
    for idx, name in enumerate(header, start=1):
        if name is None or str(name).strip() == "":
            continue
        chave = str(name).strip()
        if chave in vistos:
            primeiro = vistos[chave]
            for r in range(2, ws.max_row + 1):
                v = ws.cell(row=r, column=idx).value
                if v not in (None, "") and ws.cell(row=r, column=primeiro).value in (None, ""):
                    ws.cell(row=r, column=primeiro, value=v)
            apagar.append(idx)
        else:
            vistos[chave] = idx
    for idx in sorted(apagar, reverse=True):
        ws.delete_cols(idx)
        mudou = True

    # 3) Acrescenta no fim o que ainda faltar
    header = [c.value for c in ws[1]]
    for nome in colunas:
        if nome not in header:
            ws.cell(row=1, column=len(header) + 1, value=nome)
            header.append(nome)
            mudou = True

    return mudou


def _conferir_donos_do_arquivo():
    """As colunas "Qtd <dono>" da aba Compras têm que ser as dos donos configurados.
    Se não forem (alguém trocou os donos de um sítio que já tem dados), a migração
    poria as colunas novas no fim e a gravação posicional cairia nas colunas erradas."""
    from config import MEMBROS
    wb = load_workbook(ARQUIVO_PATH, read_only=True)
    try:
        if "Compras" not in wb.sheetnames:
            return
        cab = [str(c.value or "") for c in next(wb["Compras"].iter_rows(max_row=1))]
    finally:
        wb.close()
    no_arquivo = [c[4:] for c in cab if c.startswith("Qtd ") and c != "Qtd Cabeças"]
    if no_arquivo and no_arquivo != list(MEMBROS):
        raise RuntimeError(
            f"Os donos do arquivo ({', '.join(no_arquivo)}) não são os do sitio_config.json "
            f"({', '.join(MEMBROS)}). Trocar os donos só vale para um sítio novo.")


def inicializar():
    """
    Cria o arquivo de dados em DATA_DIR se não existir.
    Se já existe mas falta a aba Visitas, adiciona sem perder dados.
    """
    if not os.path.exists(ARQUIVO_PATH):
        wb = Workbook()

        ws_comp = wb.active
        ws_comp.title = "Compras"
        ws_comp.append(COLUNAS_COMPRAS)

        ws_gast = wb.create_sheet("Gastos")
        ws_gast.append(COLUNAS_GASTOS)

        ws_vend = wb.create_sheet("Vendas")
        ws_vend.append(COLUNAS_VENDAS)

        ws_man = wb.create_sheet("Manejo")
        ws_man.append(COLUNAS_MANEJO)

        ws_vis = wb.create_sheet("Visitas")
        ws_vis.append(COLUNAS_VISITAS)

        ws_ani = wb.create_sheet("Animais")
        ws_ani.append(COLUNAS_ANIMAIS)

        wb.create_sheet("Fotos").append(COLUNAS_FOTOS)
        wb.create_sheet("Pastos").append(COLUNAS_PASTOS)
        wb.create_sheet("Tarefas").append(COLUNAS_TAREFAS)
        wb.create_sheet("Medicações").append(COLUNAS_MEDICACOES)
        wb.create_sheet("Leite Produção").append(COLUNAS_LEITE_PRODUCAO)
        wb.create_sheet("Leite Configuração").append(COLUNAS_LEITE_CONFIG)
        wb.create_sheet("Leite Alimentação").append(COLUNAS_LEITE_ALIMENTACAO)
        wb.create_sheet("Leite Necessidades").append(COLUNAS_LEITE_NECESSIDADES)
        wb.create_sheet("Leite Tratamentos").append(COLUNAS_LEITE_TRATAMENTOS)
        wb.create_sheet("Leite Conforto").append(COLUNAS_LEITE_CONFORTO)
        wb.create_sheet("Leite Colchão").append(COLUNAS_LEITE_COLCHAO)
        wb.create_sheet("Volumosos").append(COLUNAS_VOLUMOSOS)
        wb.create_sheet("Consumo Volumosos").append(COLUNAS_CONSUMO_VOLUMOSOS)

        wb.create_sheet("Resumo")
        wb.save(ARQUIVO_PATH)
        print(f"✅ Arquivo de dados criado: {ARQUIVO_PATH}")
        return

    _conferir_donos_do_arquivo()
    # Arquivo já existe — migrar abas/colunas que faltam SEM apagar dados.
    try:
        with _trava_escrita():
            wb = load_workbook(ARQUIVO_PATH)
            alterado = False
            for aba, colunas in _SCHEMA_ABAS.items():
                if aba not in wb.sheetnames:
                    ws = wb.create_sheet(aba)
                    ws.append(colunas)
                    alterado = True
                    print(f"✅ Aba '{aba}' criada no arquivo existente.")
                    continue
                if _garantir_colunas(wb[aba], colunas):
                    alterado = True
                    print(f"✅ Colunas garantidas em '{aba}'.")
            if alterado:
                _salvar_atomico(wb)
    except Exception as e:
        print(f"⚠️  Não foi possível migrar as abas: {e}")


# ── Leitura ───────────────────────────────────────────────────────────────────

def _preparar_df(df: pd.DataFrame) -> pd.DataFrame:
    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(
            df["Data"], dayfirst=True, format="mixed", errors="coerce"
        )
    return df.dropna(how="all").reset_index(drop=True)


def carregar_aba(aba: str) -> pd.DataFrame:
    """Carrega uma aba do Excel como DataFrame."""
    try:
        return _preparar_df(pd.read_excel(ARQUIVO_PATH, sheet_name=aba))
    except Exception:
        return pd.DataFrame()


_ABAS_PRINCIPAIS = ["Compras", "Gastos", "Vendas", "Manejo", "Visitas"]


def carregar_todas() -> dict[str, pd.DataFrame]:
    """Carrega todas as abas de uma vez — abre o arquivo UMA vez só (antes eram
    5 leituras completas do .xlsx a cada recarga do cache)."""
    try:
        brutas = pd.read_excel(ARQUIVO_PATH, sheet_name=_ABAS_PRINCIPAIS)
        return {aba: _preparar_df(brutas[aba]) for aba in _ABAS_PRINCIPAIS}
    except Exception:
        # Aba faltando/arquivo estranho: lê uma a uma (aba ausente vira vazia).
        return {aba: carregar_aba(aba) for aba in _ABAS_PRINCIPAIS}


def versao_arquivo():
    """Assinatura (mtime, tamanho) do .xlsx — muda a cada gravação, inclusive de
    outro processo (Task do WhatsApp, outro worker do servidor). Usada pelo cache."""
    try:
        st = os.stat(ARQUIVO_PATH)
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


# ── Escrita ───────────────────────────────────────────────────────────────────

def _preparar_valor(v):
    """Converte tipos Python/Pandas para valores compatíveis com Excel."""
    if isinstance(v, pd.Timestamp):
        return v.strftime("%d/%m/%Y")

    if isinstance(v, str) and len(v) >= 10 and v[4:5] == "-" and v[7:8] == "-":
        try:
            return datetime.strptime(v[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            pass

    if isinstance(v, float) and (pd.isna(v) or v != v):
        return None

    # NaT (data vazia) não é Timestamp nem float — ia parar na planilha como "NaT".
    if v is pd.NaT:
        return None

    return v


_trava_thread = threading.RLock()


@contextmanager
def _trava_escrita():
    """
    Uma gravação por vez no .xlsx. Cada gravação é "abre → altera → salva o
    arquivo inteiro": duas ao mesmo tempo (duas pessoas salvando, ou a Task do
    WhatsApp) faziam a segunda apagar o que a primeira gravou. Lock de thread +
    trava de arquivo (vale entre processos/workers do servidor).
    """
    with _trava_thread:
        fh = open(os.path.join(DATA_DIR, ".gado.lock"), "a+")
        try:
            try:
                if os.name == "nt":
                    import msvcrt
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            except (ImportError, OSError):
                pass   # sem trava de arquivo, ao menos o lock da thread vale
            yield
        finally:
            try:
                if os.name == "nt":
                    import msvcrt
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            except (ImportError, OSError):
                pass
            fh.close()   # no Linux, fechar já solta o flock


def _salvar_atomico(wb):
    """Salva num arquivo temporário e troca de uma vez: se o processo cair no meio
    do save (timeout, falta de cota), o .xlsx antigo continua inteiro — antes o
    arquivo podia ficar truncado/corrompido e o site parava de abrir."""
    tmp = ARQUIVO_PATH + ".tmp"
    wb.save(tmp)
    os.replace(tmp, ARQUIVO_PATH)


def salvar_linha(aba: str, linha: list):
    """Adiciona uma linha ao final de uma aba.

    Auto-corrige o cabeçalho antes de gravar: garante que as colunas do esquema
    existam (e na posição certa), para o valor nunca cair numa coluna sem nome —
    não depende da migração do boot ter rodado.
    """
    with _trava_escrita():
        wb = load_workbook(ARQUIVO_PATH)
        ws = wb[aba]
        if aba in _SCHEMA_ABAS:
            _garantir_colunas(ws, _SCHEMA_ABAS[aba])
        ws.append([_preparar_valor(v) for v in linha])
        _salvar_atomico(wb)


def alterar_aba(aba: str, mudar):
    """Lê a aba, deixa `mudar(df)` alterá-la e grava — tudo sob a mesma trava.
    Sem isso, uma gravação feita entre a leitura e a escrita se perdia."""
    with _trava_escrita():
        wb = load_workbook(ARQUIVO_PATH)
        ws = wb[aba]
        linhas = list(ws.iter_rows(values_only=True))
        # Valores crus (sem converter datas): a data que não lê como data fica como está.
        # Linhas vazias saem, como em carregar_aba, para o índice bater com a tela.
        df = pd.DataFrame(linhas[1:], columns=list(linhas[0])) if linhas else pd.DataFrame()
        df = df.dropna(how="all").reset_index(drop=True)
        df = mudar(df)
        if ws.max_row > 1:
            ws.delete_rows(2, ws.max_row - 1)
        for _, row in df.iterrows():
            ws.append([_preparar_valor(v) for v in row])
        _salvar_atomico(wb)


def reescrever_aba(aba: str, df: pd.DataFrame):
    """Reescreve completamente uma aba a partir de um DataFrame."""
    with _trava_escrita():
        wb = load_workbook(ARQUIVO_PATH)
        ws = wb[aba]

        # Apaga as linhas antigas (não só os valores): antes as linhas ficavam vazias e
        # o append gravava DEPOIS delas — a aba dobrava de tamanho a cada edição/exclusão.
        if ws.max_row > 1:
            ws.delete_rows(2, ws.max_row - 1)

        for _, row in df.iterrows():
            ws.append([_preparar_valor(v) for v in row])

        _salvar_atomico(wb)


# ── Utilitários ───────────────────────────────────────────────────────────────

def safe_val(df: pd.DataFrame, row: int, col: int):
    """Lê uma célula de forma segura, retorna None em caso de erro."""
    try:
        v = df.iloc[row, col]
        return v if pd.notna(v) else None
    except Exception:
        return None
