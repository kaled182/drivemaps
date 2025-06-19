#!/usr/bin/env python3
from app import create_app
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env (apenas desenvolvimento)
load_dotenv()

# Cria a aplicação Flask
app = create_app()

def verify_config():
    """Verificação completa das configurações"""
    required_keys = [
        'SECRET_KEY',
        'GOOGLE_API_KEY',
        'MAP_ID',
        'SESSION_TYPE',
        'SESSION_COOKIE_NAME'
    ]
    
    missing = [key for key in required_keys if not app.config.get(key)]
    if missing:
        error_msg = f"Configurações obrigatórias faltando: {', '.join(missing)}"
        app.logger.error(error_msg)
        raise ValueError(error_msg)
    
    app.logger.info("✓ Configurações verificadas com sucesso")

if __name__ == '__main__':
    # Verifica configurações antes de iniciar
    verify_config()
    
    # Configurações do servidor
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 10000))
    
    app.logger.info(f"🔑 SECRET_KEY configurada: {'Sim' if app.config['SECRET_KEY'] else 'Não'}")
    app.logger.info(f"🗺️ MAP_ID: {app.config.get('MAP_ID', 'Não configurado')}")
    app.logger.info(f"🚀 Iniciando servidor em http://{host}:{port}")
    
    app.run(
        host=host,
        port=port,
        debug=app.config['DEBUG'],
        use_reloader=False
    )
