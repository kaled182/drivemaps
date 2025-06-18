from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Endereco(db.Model):
    __tablename__ = 'enderecos'

    id = db.Column(db.Integer, primary_key=True)
    address_original = db.Column(db.String(255), nullable=False)   # Endereço importado original
    address_atual = db.Column(db.String(255), nullable=False)      # Endereço ajustado manualmente, começa igual ao original
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    order_number = db.Column(db.String(64), nullable=True)
    cep = db.Column(db.String(16), nullable=True)
    importacao_tipo = db.Column(db.String(32), nullable=True)
    status = db.Column(db.String(32), nullable=True, default="OK") # Para controle/validação futura
    id_pacote = db.Column(db.String(20), nullable=True)            # Número sequencial do pacote

    def __repr__(self):
        return f"<Endereco {self.id} - {self.address_atual}>"
