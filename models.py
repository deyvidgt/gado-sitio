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

    @property
    def valor(self):
        return self.valor_total

Despesa = Gasto

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

class Fazenda(db.Model):
    __tablename__ = 'fazendas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)

class RegistroGenerico(db.Model):
    __tablename__ = 'registros_genericos'
    id = db.Column(db.Integer, primary_key=True)
    fazenda_id = db.Column(db.Integer, db.ForeignKey('fazendas.id'), nullable=False)
    aba = db.Column(db.String(50), nullable=False)
    dados_json = db.Column(db.Text, nullable=False)

class Medicamento(db.Model):
    __tablename__ = 'medicamentos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    principio_ativo = db.Column(db.String(100))
    lote = db.Column(db.String(60))
    bula = db.relationship('Bula', backref='medicamento', uselist=False, cascade='all, delete-orphan')

class Bula(db.Model):
    __tablename__ = 'bulas_estoque'
    id = db.Column(db.Integer, primary_key=True)
    medicamento_id = db.Column(db.Integer, db.ForeignKey('medicamentos.id'), nullable=False, unique=True)
    arquivo = db.Column(db.String(255), nullable=False)