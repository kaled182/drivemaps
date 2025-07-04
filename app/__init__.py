from flask import Flask, render_template
from flask_session import Session
from .routes import register_routes
import os
import logging
from werkzeug.http import dump_cookie

def create_app():
    """Factory function para criar e configurar a aplicação Flask"""

    # Inicializa o app Flask com configurações de templates e arquivos estáticos
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static',
        static_url_path=''
    )

    # Configuração avançada do logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    app.logger.info("🚀 Inicializando aplicação DriveMaps...")

    # Carrega configurações com verificação
    try:
        app.config.from_object('config.Config')
        app.logger.info(f"⚙️ Ambiente: {app.config.get('FLASK_ENV', 'production').upper()}")
    except Exception as e:
        app.logger.error(f"❌ Erro ao carregar configurações: {str(e)}")
        raise

    # Verificação reforçada das configurações essenciais (sem GOOGLE_API_KEY)
    required_configs = {
        'SECRET_KEY': 'Chave secreta para segurança',
        'MAPBOX_TOKEN': 'Token do Mapbox',
        'MAP_ID': 'ID do mapa',
        'SESSION_COOKIE_NAME': 'Nome do cookie de sessão'
    }

    missing = [key for key in required_configs if not app.config.get(key)]
    if missing:
        error_msg = "Configurações obrigatórias faltando:\n" + \
                   "\n".join(f"- {key}: {required_configs[key]}" for key in missing)
        app.logger.error(error_msg)
        raise ValueError("Configurações essenciais faltando no arquivo config.py ou variáveis de ambiente")

    # Apenas warning caso falte a key do Google
    if not app.config.get('GOOGLE_API_KEY'):
        app.logger.warning("⚠️ GOOGLE_API_KEY não definida! Validações de endereço Google desativadas.")

    # Configuração de sessão com tratamento robusto
    try:
        if app.config['SESSION_TYPE'] == 'filesystem':
            session_dir = app.config['SESSION_FILE_DIR']
            os.makedirs(session_dir, exist_ok=True)
            app.logger.info(f"📂 Sessões serão armazenadas em: {session_dir}")

            if app.config.get('CLEAN_OLD_SESSIONS', True):
                clean_old_sessions(session_dir)

        Session().init_app(app)
        app.session_cookie_name = app.config['SESSION_COOKIE_NAME']
        app.logger.info("🔒 Sessão configurada com sucesso")
    except Exception as e:
        app.logger.error(f"❌ Falha crítica na configuração de sessão: {str(e)}")
        raise

    # Rota para favicon (ajustada para o caminho correto)
    @app.route('/favicon.ico')
    def favicon():
        return app.send_static_file('images/favicon.ico')

    # Error handler 404 deve ser registrado ANTES das outras rotas
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    # Registro de rotas principais
    try:
        register_routes(app)
        app.logger.info("🛣️ Rotas registradas com sucesso")
    except Exception as e:
        app.logger.error(f"❌ Falha ao registrar rotas: {str(e)}")
        raise

    # Configurações específicas para produção
    if app.config.get('FLASK_ENV') == 'production':
        app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax'
        )
        app.logger.info("🏭 Configurações de produção ativadas")

    # Inserção da variável 'now' globalmente para os templates
    from datetime import datetime

    @app.context_processor
    def inject_now():
        return {'now': datetime.now}

    # --- CSP Corrigido para liberar Mapbox, Google, Bootstrap, CDNs ---
    @app.after_request
    def set_csp(response):
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' "
            "https://maps.googleapis.com https://maps.gstatic.com "
            "https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com "
            "https://api.mapbox.com 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' https://fonts.googleapis.com "
            "https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://api.mapbox.com 'unsafe-inline'; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src * data: https://api.mapbox.com https://events.mapbox.com; "
            "connect-src 'self' https://api.mapbox.com https://events.mapbox.com https://maps.googleapis.com https://maps.gstatic.com https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "worker-src 'self' blob:;"  # <-- LINHA ADICIONADA PARA CORRIGIR O ERRO
        )
        return response

    return app


def clean_old_sessions(session_dir, max_age=86400):
    """Limpa sessões antigas do sistema de arquivos"""
    from glob import glob
    import time

    now = time.time()
    for session_file in glob(os.path.join(session_dir, 'session_*')):
        if os.stat(session_file).st_mtime < now - max_age:
            try:
                os.remove(session_file)
            except Exception as e:
                logging.warning(f"Falha ao remover sessão antiga {session_file}: {str(e)}")
