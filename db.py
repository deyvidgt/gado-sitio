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


def _resolver_data_dir() -> str:
    """
    Resolve onde ficam os dados, independente de como o programa foi iniciado.

    Prioridade:
      1. Variável de ambiente GADO_DATA_DIR   (configuração manual)
      2. ~/gado-dados/                         (padrão PythonAnywhere — fora do Git)
      3. Pasta do executável (.exe)             (Windows compilado)
      4. Pasta do script atual                  (desenvolvimento)
    """
    # 1) Variável de ambiente explícita (útil para testes e outras hospedagens)
    if os.environ.get("GADO_DATA_DIR"):
        pasta = os.path.expanduser(os.environ["GADO_DATA_DIR"])
        os.makedirs(pasta, exist_ok=True)
        return pasta

    # 2) ~/gado-dados/ — pasta permanente fora do repositório Git
    #    Funciona no PythonAnywhere e em qualquer servidor Linux/Mac
    pasta_permanente = os.path.expanduser("~/gado-dados")
    if os.path.isdir(pasta_permanente):
        return pasta_permanente

    # 3) Modo .exe (PyInstaller/Windows)
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    # 4) Fallback: pasta do próprio script (desenvolvimento local)
    return os.path.dirname(os.path.abspath(__file__))


# DATA_DIR é onde ficam gado_familia.xlsx, usuarios.json e backups/
# É DIFERENTE da pasta do código — isso protege os dados do git pull
DATA_DIR = _resolver_data_dir()

from config import (
    ARQUIVO_DADOS,
    COLUNAS_COMPRAS, COLUNAS_GASTOS,
    COLUNAS_VENDAS, COLUNAS_MANEJO, COLUNAS_VISITAS, COLUNAS_ANIMAIS, COLUNAS_FOTOS,
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
}

# Caminho completo do arquivo de dados
ARQUIVO_PATH = os.path.join(DATA_DIR, ARQUIVO_DADOS)

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

        wb.create_sheet("Resumo")
        wb.save(ARQUIVO_PATH)
        print(f"✅ Arquivo de dados criado: {ARQUIVO_PATH}")
        return

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
