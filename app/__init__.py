from flask import Flask
from flask_session import Session
from .routes import register_routes
import os
import logging

def create_app():
    # Inicializa o aplicativo Flask
    app = Flask(__name__)
    
    # Configuração do logger
    logging.basicConfig(level=logging.INFO)
    app.logger.info("Iniciando a aplicação...")
    
    # Carrega configurações
    app.config.from_object('config.Config')
    app.logger.info("Configurações carregadas")
    
    # Verificação crítica das configurações
    if not app.config.get('SESSION_COOKIE_NAME'):
        app.logger.error("SESSION_COOKIE_NAME não configurado!")
        raise RuntimeError("Configuração de sessão incompleta")
    
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
        
        # Garantia adicional para o session_cookie_name
        if not hasattr(app, 'session_cookie_name'):
            app.session_cookie_name = app.config['SESSION_COOKIE_NAME']
            
        app.logger.info("Sessão configurada com sucesso")
    except Exception as e:
        app.logger.error(f"Falha ao configurar sessão: {str(e)}")
        raise
    
    # Registra as rotas
    register_routes(app)
    
    return app
