# DriveMaps 🚗

Gere rotas otimizadas para motoristas usando Flask + Google Maps API.

## Como Usar
1. Clone o repositório
2. Crie um `.env` baseado em `.env.example`
3. Execute `pip install -r requirements.txt`
4. Acesse `http://localhost:5000`

## Deploy no Render
- Configuração automática via `render.yaml`
- Comando de start: `gunicorn 'app:create_app()'`