from flask import Flask, render_template, request, jsonify, redirect, url_for
from app.models import db, Endereco

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///enderecos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Página principal com mapa e tabela
@app.route("/")
def index():
    enderecos = Endereco.query.all()
    # Constrói lista para o mapa (coordenadas e info)
    locations = [
        {
            "id": e.id,
            "address_original": e.address_original,
            "address_atual": e.address_atual,
            "lat": e.lat,
            "lng": e.lng,
            "status": e.status or "OK"
        }
        for e in enderecos
    ]
    return render_template("map.html", locations=locations)

# Rota para importar endereços (simples, por texto ou arquivo)
@app.route("/importar", methods=["POST"])
def importar():
    # Exemplo: importar de textarea (campo 'enderecos')
    enderecos_texto = request.form.get("enderecos")
    if not enderecos_texto:
        return redirect(url_for("index"))

    linhas = [l.strip() for l in enderecos_texto.splitlines() if l.strip()]
    for line in linhas:
        # Suponha que geocodificação e extração de dados já foi feita
        novo_end = Endereco(
            address_original=line,
            address_atual=line,
            lat=None,
            lng=None,
            status="OK"
        )
        db.session.add(novo_end)
    db.session.commit()
    return redirect(url_for("index"))

# Rota para atualizar endereço após validação/movimentação do PIN
@app.route("/atualizar_endereco", methods=["POST"])
def atualizar_endereco():
    data = request.json
    eid = data.get("id")
    endereco = Endereco.query.get(eid)
    if not endereco:
        return jsonify({"status": "erro", "msg": "Endereço não encontrado"}), 404

    endereco.address_atual = data.get("address_atual", endereco.address_atual)
    endereco.lat = data.get("lat", endereco.lat)
    endereco.lng = data.get("lng", endereco.lng)
    endereco.status = data.get("status", endereco.status)
    db.session.commit()
    return jsonify({"status": "ok"})

# Rota para buscar endereço por id (AJAX)
@app.route("/endereco/<int:eid>")
def get_endereco(eid):
    endereco = Endereco.query.get(eid)
    if not endereco:
        return jsonify({"erro": "Endereço não encontrado"}), 404
    return jsonify({
        "id": endereco.id,
        "address_original": endereco.address_original,
        "address_atual": endereco.address_atual,
        "lat": endereco.lat,
        "lng": endereco.lng,
        "status": endereco.status
    })

# Utilitário para criar o banco (roda uma vez)
@app.cli.command("criar-db")
def criar_db():
    db.create_all()
    print("Banco de dados criado.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
