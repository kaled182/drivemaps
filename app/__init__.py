from flask import Flask
from flask_session import Session
from .routes import register_routes
import os
import logging
from werkzeug.http import dump_cookie

def create_app():
    app = Flask(__name__)
    
    # Configuração do logger
    logging.basicConfig(level=logging.INFO)
    app.logger.info("Iniciando a aplicação...")
    
    # Carrega configurações
    app.config.from_object('config.Config')
    app.logger.info(f"Ambiente: {app.config['FLASK_ENV']}")
    
    # Verificação crítica das configurações
    required_keys = ['SECRET_KEY', 'GOOGLE_API_KEY', 'MAP_ID']
    missing = [key for key in required_keys if not app.config.get(key)]
    if missing:
        app.logger.error(f"Configurações faltando: {', '.join(missing)}")
        raise ValueError(f"Variáveis de ambiente obrigatórias faltando: {', '.join(missing)}")

    # Configuração do diretório de sessão
    if app.config['SESSION_TYPE'] == 'filesystem':
        try:
            os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
            app.logger.info(f"Diretório de sessão: {app.config['SESSION_FILE_DIR']}")
        except Exception as e:
            app.logger.error(f"Erro ao criar diretório de sessão: {str(e)}")
            raise
    
    # Inicialização robusta da sessão
    try:
        sess = Session()
        sess.init_app(app)
        
        # Garante que o session_cookie_name está definido
        if not hasattr(app, 'session_cookie_name'):
            app.session_cookie_name = app.config['SESSION_COOKIE_NAME']
            
        app.logger.info("Sessão configurada com sucesso")
    except Exception as e:
        app.logger.error(f"Falha ao configurar sessão: {str(e)}")
        raise
    
    # Registra as rotas
    register_routes(app)
    
    return app
