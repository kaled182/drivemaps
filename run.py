#!/usr/bin/env python3
# run.py - Ponto de entrada principal da aplicação

from app import create_app
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Cria a aplicação Flask
app = create_app()

if __name__ == '__main__':
    # Configurações do servidor de desenvolvimento
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True') == 'True'
    
    # Verifica se o diretório de sessões existe (se usando filesystem)
    if app.config['SESSION_TYPE'] == 'filesystem':
        session_dir = app.config.get('SESSION_FILE_DIR')
        if session_dir and not os.path.exists(session_dir):
            os.makedirs(session_dir)
            print(f"Diretório de sessão criado em: {session_dir}")
    
    print(f"Iniciando servidor Flask em http://{host}:{port}")
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True,
        use_reloader=debug
    )
