from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.utils.models import db, Endereco
from app.utils.normalize import linhas_para_enderecos

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
            "status": e.status or "OK",
            "id_pacote": getattr(e, "id_pacote", None)
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

    linhas = enderecos_texto.splitlines()
    pares = linhas_para_enderecos(linhas)
    for endereco, numero_pacote in pares:
        novo_end = Endereco(
            address_original=endereco,
            address_atual=endereco,
            lat=None,
            lng=None,
            status="OK",
            id_pacote=numero_pacote  # Retire se não houver esse campo no modelo
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
        "status": endereco.status,
        "id_pacote": getattr(endereco, "id_pacote", None)
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
