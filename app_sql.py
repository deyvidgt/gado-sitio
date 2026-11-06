from flask import Flask
from models import db
from database import init_db

def create_app(db_path="sitio.db"):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev'
    # Inicializa o db (instância de models.py) com a aplicação
    init_db(app, db_path)
    return app

# Exemplo de uso para inicializar o banco:
# app = create_app()
# with app.app_context():
#     db.create_all()
