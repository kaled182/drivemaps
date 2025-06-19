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
    
    # Patch para o problema de bytes/string
    if not hasattr(app, 'session_cookie_name'):
        app.session_cookie_name = app.config['SESSION_COOKIE_NAME']
    
    # Configuração do diretório de sessão
    if app.config['SESSION_TYPE'] == 'filesystem':
        try:
            os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
            app.logger.info(f"Diretório de sessão: {app.config['SESSION_FILE_DIR']}")
        except Exception as e:
            app.logger.error(f"Erro ao criar diretório de sessão: {str(e)}")
            raise
    
    # Inicialização da sessão com tratamento de erro
    try:
        sess = Session()
        sess.init_app(app)
        
        # Patch adicional para garantir que o session_id seja string
        original_save_session = sess.save_session
        
        def patched_save_session(*args, **kwargs):
            try:
                # Garante que o session_id seja string
                if 'session_id' in kwargs and isinstance(kwargs['session_id'], bytes):
                    kwargs['session_id'] = kwargs['session_id'].decode('utf-8')
                return original_save_session(*args, **kwargs)
            except Exception as e:
                app.logger.error(f"Erro ao salvar sessão: {str(e)}")
                raise
                
        sess.save_session = patched_save_session
        
        app.logger.info("Sessão configurada com sucesso")
    except Exception as e:
        app.logger.error(f"Falha ao configurar sessão: {str(e)}")
        raise
    
    # Registra as rotas
    register_routes(app)
    
    return app
