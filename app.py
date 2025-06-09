from flask import Flask, request, render_template_string, send_file, redirect, url_for, session
import re
import csv
import io
import requests
import os

app = Flask(__name__)
app.secret_key = "umasecretqualquer123"  # Segurança mínima para session

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

def valida_endereco_google(address, api_key=GOOGLE_API_KEY):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "region": "pt", "key": api_key}
    try:
        response = requests.get(url, params=params, timeout=8)
        data = response.json()
        if data.get('status') == 'OK':
            result = data['results'][0]
            return "OK", result['formatted_address'], result['geometry']['location']
        else:
            return "NÃO ENCONTRADO", "", ""
    except Exception as e:
        return "ERRO API", "", ""

HTML_FORM = """
<!DOCTYPE html>
<html>
<head>
    <title>MapsDrive – Gerador de CSV para MyWay</title>
    <style>
        body { background: #f2f6ff; font-family: Arial; }
        .container { max-width: 700px; margin: auto; background: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 0 16px #bbb; }
        button { background: #1976d2; color: white; padding: 12px 26px; border: none; border-radius: 5px; font-size: 1.1em; margin-top: 12px; }
        h2 { color: #1976d2; }
    </style>
</head>
<body>
<div class="container">
    <h2>MapsDrive – Gerador de CSV para MyWay</h2>
    <form action="/preview" method="post">
        <label>Cole sua lista de endereços:</label><br>
        <textarea name="enderecos" rows="16" style="width:100%; font-size:1.1em" placeholder="Cole aqui sua lista bruta..."></textarea><br>
        <button type="submit">Pré-visualizar</button>
    </form>
</div>
</body>
</html>
"""

HTML_PREVIEW = """
<!DOCTYPE html>
<html>
<head>
    <title>MapsDrive – Pré-visualização</title>
    <style>
        body { background: #f2f6ff; font-family: Arial; }
        .container { max-width: 900px; margin: auto; background: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 0 16px #bbb; }
        table { border-collapse: collapse; width: 100%; margin-top: 18px; }
        th, td { border: 1px solid #ccc; padding: 7px; text-align: left; }
        .ok { background: #e3faea; }
        .erro { background: #f9d7d7; }
        input[type="text"] { width: 98%; font-size:1.08em; }
        button { background: #1976d2; color: white; padding: 10px 24px; border: none; border-radius: 5px; font-size: 1em; margin-top: 12px; }
        h2 { color: #1976d2; }
    </style>
</head>
<body>
<div class="container">
    <h2>Pré-visualização dos Endereços</h2>
    <form action="/generate" method="post">
        <table>
            <tr>
                <th>#</th>
                <th>Endereço</th>
                <th>Status</th>
                <th>Corrigir/Confirmar</th>
            </tr>
            {% for item in lista %}
            <tr class="{{ 'ok' if item['status'] == 'OK' else 'erro' }}">
                <td>{{ loop.index }}</td>
                <td>
                    <input type="hidden" name="numero_pacote_{{ loop.index0 }}" value="{{item['order_number']}}">
                    <input type="hidden" name="cep_{{ loop.index0 }}" value="{{item['cep']}}">
                    <input type="text" name="endereco_{{ loop.index0 }}" value="{{item['address']}}" {% if item['status']=='OK' %}re_
