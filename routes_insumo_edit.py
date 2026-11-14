@app.route("/insumos/editar/<int:insumo_id>", methods=["GET", "POST"])
@login_required
def editar_insumo(insumo_id):
    from models import Insumo
    from extensions import db as db_sqla
    ins = Insumo.query.get_or_404(insumo_id)
    if request.method == "POST":
        _validar_csrf()
        f = request.form
        ins.nome = f.get("nome", ins.nome).strip()
        ins.categoria = f.get("categoria", ins.categoria).strip()
        ins.peso_saco = parse_valor(f.get("peso_saco", ins.peso_saco))
        ins.quantidade = parse_valor(f.get("quantidade", ins.quantidade))
        db_sqla.session.commit()
        flash("Insumo atualizado com sucesso!", "success")
        return redirect(url_for("estoque_insumos"))
    return render_template("form_insumo.html", ins=ins, CATEGORIAS=CATEGORIAS_GASTO)

@app.route("/insumos/excluir/<int:insumo_id>", methods=["POST"])
@login_required
def excluir_insumo(insumo_id):
    from models import Insumo
    from extensions import db as db_sqla
    _validar_csrf()
    ins = Insumo.query.get_or_404(insumo_id)
    db_sqla.session.delete(ins)
    db_sqla.session.commit()
    flash("Insumo removido do estoque.", "success")
    return redirect(url_for("estoque_insumos"))
