#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rotas de Importar, Exportar e Backup — Sítio Santo Antonio
Gerado automaticamente — não editar diretamente.
"""
from flask import render_template, request, redirect, url_for, flash, session, send_file, jsonify
import os, tempfile
import pandas as pd
from datetime import datetime, timedelta
from db import carregar_aba, carregar_todas, inicializar, fazer_backup
from calculos import (
    calcular_estoque, calcular_resumo_financeiro, calcular_todos_membros,
    calcular_fluxo_caixa, calcular_cmp_ate_data, calcular_gpcab_ate_data,
    calcular_cmp, calcular_gpcab, calcular_estoque_por_membro,
    calcular_indicadores_extras, calcular_gasto_por_tipo, calcular_evolucao_cmp,
)
from config import (TIPOS_GASTO, TIPOS_MANEJO, MEMBROS, NOMES_MEMBROS,
                    EMOJIS_MEMBROS, OPCOES_VISITA)
from extensions import (
    app, _agora, _validar_csrf, login_required,
    _get_dados_cache, _get_resumo_cache,
    salvar_linha, reescrever_aba,
    _fazer_backup_inteligente, _limpar_backups_antigos,
    _carregar_usuarios, _salvar_usuarios,
    _sha256, _hash_bcrypt, _bcrypt_disponivel, _verificar_hash,
    fmt_brl, fmt_data, parse_valor,
    _gerar_alertas, _calc_anual, BASE_DIR,
)


@app.route("/importar", methods=["GET", "POST"])
@login_required
def importar():
    if request.method == "POST":
        _validar_csrf()
        arquivo = request.files.get("arquivo")
        if not arquivo or not arquivo.filename.endswith(".xlsx"):
            flash("Envie um arquivo .xlsx válido.", "error")
            return redirect(url_for("importar"))
        from db import safe_val
        from openpyxl import load_workbook
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        arquivo.save(tmp.name)
        tmp.close()
        try:
            wb   = load_workbook(tmp.name, data_only=True)
            anos = sorted([s for s in wb.sheetnames if s.isdigit()])
            if not anos:
                flash("Nenhuma aba de ano encontrada.", "warning")
                return redirect(url_for("importar"))
            nc = ng = nv = 0
            detalhes = []
            for ano in anos:
                df_raw = pd.read_excel(tmp.name, sheet_name=ano, header=None)
                def _f(r, c):
                    try:
                        x = safe_val(df_raw, r, c)
                        return float(str(x).replace(",", ".")) if x not in (None, "") else 0.0
                    except Exception:
                        return 0.0
                cab_c = _f(0, 1)
                preco_c = _f(0, 10)
                if cab_c > 0 and preco_c > 0:
                    base = int(cab_c) // 3
                    salvar_linha("Compras", [f"01/01/{ano}", int(cab_c), preco_c,
                                             round(preco_c / int(cab_c), 2),
                                             base, base, int(cab_c) - base * 2,
                                             f"Nelore/Garrotes - Importado {ano}", "Importação"])
                    nc += 1
                    detalhes.append({"tipo": "compra", "ano": ano,
                                     "msg": f"Compra: {int(cab_c)} cabeças — R$ {preco_c:,.2f}"})
                gastos_ano = 0
                for ri in range(1, len(df_raw)):
                    vg = _f(ri, 6)
                    dg = safe_val(df_raw, ri, 7)
                    if vg > 0:
                        salvar_linha("Gastos", [f"01/01/{ano}", "Manutenção/Outros",
                                                str(dg).strip() if dg else "", vg, 0, 0, "Importação"])
                        ng += 1; gastos_ano += 1
                if gastos_ano:
                    detalhes.append({"tipo": "gasto", "ano": ano, "msg": f"{gastos_ano} gastos importados"})
                mae_v = _f(1, 15); dev_v = _f(2, 15); nil_v = _f(3, 15)
                mae_q = _f(1, 19); dev_q = _f(2, 19); nil_q = _f(3, 19)
                tv = mae_v + dev_v + nil_v
                tq = int(mae_q + dev_q + nil_q)
                raw_dv = safe_val(df_raw, 1, 17)
                try:
                    data_v = pd.Timestamp(raw_dv).strftime("%d/%m/%Y") if raw_dv else f"31/12/{ano}"
                except Exception:
                    data_v = f"31/12/{ano}"
                if tv > 0:
                    salvar_linha("Vendas", [data_v, tq, tv,
                                            round(tv / tq, 2) if tq else 0, _f(0, 12),
                                            int(mae_q), int(dev_q), int(nil_q),
                                            mae_v, dev_v, nil_v,
                                            0, 0, 0, 0, 0, 0, 0, f"Importado de {ano}"])
                    nv += 1
                    detalhes.append({"tipo": "venda", "ano": ano,
                                     "msg": f"Venda: {tq} cabeças — R$ {tv:,.2f}"})
            return render_template("importar.html", concluido=True, anos=anos,
                                   nc=nc, ng=ng, nv=nv, detalhes=detalhes)
        except Exception as e:
            flash(f"Erro na importação: {e}", "error")
            return redirect(url_for("importar"))
        finally:
            os.unlink(tmp.name)
    return render_template("importar.html", concluido=False, anos=[], detalhes=[])


# ══════════════════════════════════════════════════════════════════════════════
#  EXPORTAR / BACKUP
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/exportar")
@login_required
def exportar():
    from db import DATA_DIR
    nome = exportar_relatorio_excel()
    nome_abs = nome if os.path.isabs(nome) else os.path.join(DATA_DIR, nome)
    return send_file(nome_abs, as_attachment=True,
                     download_name=f"relatorio_gado_{_agora().strftime('%Y%m%d')}.xlsx")

@app.route("/backup", methods=["POST"])
@login_required
def backup():
    _validar_csrf()
    nome = fazer_backup()
    _limpar_backups_antigos()
    flash(f"Backup salvo: {nome}", "success")
    return redirect(url_for("dashboard"))


# ══════════════════════════════════════════════════════════════════════════════
