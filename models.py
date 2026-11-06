#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
models.py — Sítio Santo Antonio (v6.0 - SQLAlchemy Models com Multi-Tenancy)
"""

from datetime import datetime
from extensions import db

class Fazenda(db.Model):
    __tablename__ = 'fazendas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    fazenda_id = db.Column(db.Integer, db.ForeignKey('fazendas.id'), nullable=True, index=True)
    hash_senha = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AnimalModel(db.Model):
    __tablename__ = 'animais'
    id = db.Column(db.Integer, primary_key=True)
    fazenda_id = db.Column(db.Integer, db.ForeignKey('fazendas.id'), nullable=False, index=True)
    brinco = db.Column(db.String(50), nullable=False, index=True)
    categoria = db.Column(db.String(50))
    sexo = db.Column(db.String(20))
    raca = db.Column(db.String(50))
    nascimento = db.Column(db.Date)
    peso_atual = db.Column(db.Float)
    pasto_id = db.Column(db.String(50))
    status = db.Column(db.String(30), default='Ativo')
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CompraModel(db.Model):
    __tablename__ = 'compras'
    id = db.Column(db.Integer, primary_key=True)
    fazenda_id = db.Column(db.Integer, db.ForeignKey('fazendas.id'), nullable=False, index=True)
    data = db.Column(db.Date, index=True)
    lote = db.Column(db.String(100))
    quantidade = db.Column(db.Integer)
    valor_total = db.Column(db.Float)
    membro = db.Column(db.String(50))
    observacoes = db.Column(db.Text)

class VendaModel(db.Model):
    __tablename__ = 'vendas'
    id = db.Column(db.Integer, primary_key=True)
    fazenda_id = db.Column(db.Integer, db.ForeignKey('fazendas.id'), nullable=False, index=True)
    data = db.Column(db.Date, index=True)
    quantidade = db.Column(db.Integer)
    valor_total = db.Column(db.Float)
    membro = db.Column(db.String(50))
    observacoes = db.Column(db.Text)

class GastoModel(db.Model):
    __tablename__ = 'gastos'
    id = db.Column(db.Integer, primary_key=True)
    fazenda_id = db.Column(db.Integer, db.ForeignKey('fazendas.id'), nullable=False, index=True)
    data = db.Column(db.Date, index=True)
    categoria = db.Column(db.String(100))
    descricao = db.Column(db.String(255))
    valor_total = db.Column(db.Float)
    membro = db.Column(db.String(50))

class ManejoModel(db.Model):
    __tablename__ = 'manejo'
    id = db.Column(db.Integer, primary_key=True)
    fazenda_id = db.Column(db.Integer, db.ForeignKey('fazendas.id'), nullable=False, index=True)
    data = db.Column(db.Date, index=True)
    tipo = db.Column(db.String(100))
    brincos = db.Column(db.Text)
    descricao = db.Column(db.Text)
    responsavel = db.Column(db.String(50))

class CochoModel(db.Model):
    __tablename__ = 'cochos'
    id = db.Column(db.Integer, primary_key=True)
    fazenda_id = db.Column(db.Integer, db.ForeignKey('fazendas.id'), nullable=False, index=True)
    cocho_id = db.Column(db.String(50), nullable=False)
    nome = db.Column(db.String(100))
    tipo = db.Column(db.String(50))
    local = db.Column(db.String(100))
    capacidade = db.Column(db.Float)
    volume_atual = db.Column(db.Float)
    ativo = db.Column(db.String(10), default='Sim')

class RegistroGenerico(db.Model):
    __tablename__ = 'registros_genericos'
    id = db.Column(db.Integer, primary_key=True)
    fazenda_id = db.Column(db.Integer, db.ForeignKey('fazendas.id'), nullable=False, index=True)
    aba = db.Column(db.String(50), nullable=False, index=True)
    dados_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

