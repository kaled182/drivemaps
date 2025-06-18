from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.utils.models import db, Endereco

main_routes = Blueprint("main_routes", __name__)

# Página principal com mapa e tabela
@main_routes.route("/")
def index():
    enderecos = Endereco.query.all()
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

# Rota para importar endereços (por texto ou arquivo)
@main_routes.route("/importar", methods=["POST"])
def importar():
    enderecos_texto = request.form.get("enderecos")
    if not enderecos_texto:
        return redirect(url_for("main_routes.index"))

    linhas = [l.strip() for l in enderecos_texto.splitlines() if l.strip()]
    for line in linhas:
        novo_end = Endereco(
            address_original=line,
            address_atual=line,
            lat=None,
            lng=None,
            status="OK"
        )
        db.session.add(novo_end)
    db.session.commit()
    return redirect(url_for("main_routes.index"))

# Rota para atualizar endereço após validação/movimentação do PIN
@main_routes.route("/atualizar_endereco", methods=["POST"])
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
@main_routes.route("/endereco/<int:eid>")
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

# Utilitário para criar o banco (roda uma vez pelo terminal)
@main_routes.cli.command("criar-db")
def criar_db():
    db.create_all()
    print("Banco de dados criado.")

# ROTA TEMPORÁRIA PARA CRIAR BANCO VIA HTTP (REMOVA DEPOIS DE USAR!)
@main_routes.route("/criar-banco-uma-vez")
def criar_banco_uma_vez():
    db.create_all()
    return "Banco de dados criado! (Pode remover esta rota agora)"
