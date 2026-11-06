from extensions import db
from datetime import datetime

class Animal(db.Model):
    __tablename__ = 'animais'
    id = db.Column(db.String, primary_key=True)
    brinco_cor = db.Column(db.String)
    brinco_num = db.Column(db.Integer)
    dono = db.Column(db.String)
    categoria = db.Column(db.String)
    sexo = db.Column(db.String)
    raca = db.Column(db.String)
    status = db.Column(db.String)
    observacoes = db.Column(db.String)

class Compra(db.Model):
    __tablename__ = 'compras'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime)
    qtd_cabecas = db.Column(db.Integer)
    valor_total = db.Column(db.Float)
    descricao = db.Column(db.String)
    registrado_por = db.Column(db.String)

class Gasto(db.Model):
    __tablename__ = 'gastos'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime)
    tipo = db.Column(db.String)
    valor_total = db.Column(db.Float)
    categoria = db.Column(db.String)
    registrado_por = db.Column(db.String)

class Venda(db.Model):
    __tablename__ = 'vendas'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime)
    qtd_cabecas = db.Column(db.Integer)
    valor_total = db.Column(db.Float)

class Manejo(db.Model):
    __tablename__ = 'manejo'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.DateTime)
    tipo = db.Column(db.String)
    qtd_cabecas = db.Column(db.Integer)
    descricao = db.Column(db.String)
