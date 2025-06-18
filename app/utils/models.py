from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Endereco(db.Model):
    __tablename__ = "enderecos"

    id = db.Column(db.Integer, primary_key=True)
    address_original = db.Column(db.String(512), nullable=False)
    address_atual = db.Column(db.String(512), nullable=False)
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    status = db.Column(db.String(32))
