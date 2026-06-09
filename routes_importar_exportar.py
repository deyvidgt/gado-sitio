#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_importar_exportar.py — Sítio Santo Antonio
Rotas de importação de Excel antigo, exportação de relatório Excel e backup manual.
"""
import os
from flask import render_template, request, redirect, url_for, flash, send_file
from db import carregar_todas, salvar_linha, fazer_backup, safe_val, DATA_DIR
from extensions import (
    app, _agora, _validar_csrf, login_required,
    _fazer_backup_inteligente, _limpar_backups_antigos,
)


# ── Exportar relatório Excel ──────────────────────────────────────────────────

@app.route("/exportar")
@login_required
def exportar():
    """Gera e faz download do relatório Excel completo."""
    try:
        from exportar import exportar_relatorio_excel
        nome = exportar_relatorio_excel()
        return send_file(nome, as_attachment=True,
                         download_name=os.path.basename(nome),
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        flash(f"Erro ao gerar relatório: {e}", "error")
        return redirect(url_for("relatorios"))


# ── Importar Excel antigo ─────────────────────────────────────────────────────

@app.route("/importar", methods=["GET", "POST"])
@login_required
def importar():
    if request.method == "GET":
        return render_template("importar.html", concluido=False)

    _validar_csrf()

    arquivo = request.files.get("arquivo")
    if not arquivo or not arquivo.filename.endswith(".xlsx"):
        flash("Selecione um arquivo .xlsx válido.", "error")
        return render_template("importar.html", concluido=False)

    # Salvar temporariamente
    import tempfile, shutil
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    arquivo.save(tmp.name)
    tmp.close()

    try:
        import pandas as pd
        from openpyxl import load_workbook

        wb_ant = load_workbook(tmp.name, data_only=True)
        anos   = sorted([s for s in wb_ant.sheetnames if s.isdigit()])

        if not anos:
            flash("Nenhuma aba com ano (ex: 2024, 2025) encontrada no arquivo.", "error")
            return render_template("importar.html", concluido=False)

        # Backup antes de importar
        fazer_backup()

        nc, ng, nv = 0, 0, 0
        detalhes   = []

        for ano in anos:
            df = pd.read_excel(tmp.name, sheet_name=ano, header=None)

            cab_c   = safe_val(df, 0, 1)
            preco_c = safe_val(df, 0, 10)
            if cab_c and preco_c:
                cab_i = int(cab_c)
                base  = cab_i // 3
                salvar_linha("Compras", [
                    f"01/01/{ano}", cab_i, float(preco_c),
                    round(float(preco_c) / cab_i, 2) if cab_i > 0 else 0,
                    base, base, cab_i - base * 2,
                    f"Nelore/Garrotes — Importado {ano}", "Importação",
                ])
                nc += 1
                detalhes.append({"ano": ano, "tipo": "compra",
                                  "msg": f"Compra: {cab_i} cabeças por R$ {float(preco_c):,.2f}"})

            for ri in range(1, len(df)):
                vg = safe_val(df, ri, 6)
                dg = safe_val(df, ri, 7)
                if vg and isinstance(vg, (int, float)) and float(vg) > 0:
                    salvar_linha("Gastos", [
                        f"01/01/{ano}", "Manutenção/Outros", str(dg) if dg else "",
                        float(vg), 0, 0, "Importação",
                    ])
                    ng += 1

            # Vendas por membro
            mae_v  = safe_val(df, 1, 15) or 0
            dev_v  = safe_val(df, 2, 15) or 0
            nil_v  = safe_val(df, 3, 15) or 0
            mae_q  = safe_val(df, 1, 19) or 0
            dev_q  = safe_val(df, 2, 19) or 0
            nil_q  = safe_val(df, 3, 19) or 0

            tv = sum(float(x) for x in [mae_v, dev_v, nil_v]
                     if isinstance(x, (int, float)) and float(x) > 0)
            tq = sum(int(x) for x in [mae_q, dev_q, nil_q]
                     if isinstance(x, (int, float)) and float(x) > 0)

            data_v = str(safe_val(df, 1, 17) or f"31/12/{ano}")[:10]

            if tv > 0:
                salvar_linha("Vendas", [
                    data_v, tq, tv,
                    round(tv / tq, 2) if tq else 0,
                    safe_val(df, 0, 12) or 0,
                    int(mae_q), int(dev_q), int(nil_q),
                    float(mae_v), float(dev_v), float(nil_v),
                    0, 0, 0,
                    0, 0, 0,
                    0,
                    f"Importado de {ano}",
                ])
                nv += 1
                detalhes.append({"ano": ano, "tipo": "venda",
                                  "msg": f"Venda: {tq} cabeças por R$ {tv:,.2f}"})

        return render_template("importar.html", concluido=True,
                               anos=anos, nc=nc, ng=ng, nv=nv,
                               detalhes=detalhes)

    except Exception as e:
        import traceback
        flash(f"Erro na importação: {e}", "error")
        return render_template("importar.html", concluido=False)
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


# ── Backup manual ─────────────────────────────────────────────────────────────

@app.route("/backup", methods=["POST"])
@login_required
def backup():
    _validar_csrf()
    nome = _fazer_backup_inteligente(forcar=True)
    _limpar_backups_antigos()
    if nome:
        flash(f"✅ Backup salvo: {os.path.basename(nome)}", "success")
    else:
        flash("Backup já realizado recentemente.", "info")
    # Redirecionar de volta para a página anterior
    from flask import request as req
    referrer = req.referrer
    if referrer:
        return redirect(referrer)
    return redirect(url_for("dashboard"))
