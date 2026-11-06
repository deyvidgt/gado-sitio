from app_sql import create_app
from models import Animal, Transacao

app = create_app("gado_familia_sql.db")
with app.app_context():
    animais = Animal.query.all()
    transacoes = Transacao.query.all()
    print(f"Animais: {len(animais)}")
    print(f"Transações: {len(transacoes)}")
