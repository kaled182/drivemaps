#!/usr/bin/env python3
from app import create_app
import os
import logging
from dotenv import load_dotenv
from werkzeug.serving import is_running_from_reloader

# Suas funções originais, sem nenhuma alteração.
def configure_logging():
    """Configura o sistema de logging para a aplicação"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log')  # Log para arquivo
        ]
    )

def verify_config(app):
    """Verificação completa das configurações com tratamento de erros"""
    required_configs = {
        'SECRET_KEY': 'Chave secreta para segurança da aplicação',
        'GOOGLE_API_KEY': 'Chave da API do Google Maps',
        'MAP_ID': 'ID do mapa para integração',
        'SESSION_TYPE': 'Tipo de armazenamento de sessão (filesystem/redis)',
        'SESSION_COOKIE_NAME': 'Nome do cookie de sessão'
    }
    try:
        missing = [key for key in required_configs if not app.config.get(key)]
        if missing:
            error_details = "\n".join([f"- {key}: {required_configs[key]}" for key in missing])
            error_msg = f"Configurações obrigatórias faltando:\n{error_details}"
            logging.error(error_msg)
            raise ValueError("Configurações essenciais não encontradas")
        if 'sua-chave-secreta' in app.config['SECRET_KEY']:
            logging.warning("AVISO: SECRET_KEY padrão em uso - INSEGURO para produção!")
        logging.info("✅ Configurações verificadas com sucesso")
        return True
    except Exception as e:
        logging.error(f"❌ Falha na verificação de configurações: {str(e)}")
        raise

def start_server(app):
    """Inicia o servidor Flask para desenvolvimento local"""
    try:
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 10000))
        debug_mode = app.config.get('DEBUG', False)
        if app.config.get('FLASK_ENV') == 'production':
            debug_mode = False
            logging.info("🏭 Modo produção ativado")
        logging.info(f"🔑 SECRET_KEY: {'Configurada' if app.config['SECRET_KEY'] else 'Faltando'}")
        logging.info(f"🗺️ MAP_ID: {app.config.get('MAP_ID', 'Não configurado')}")
        logging.info(f"🚀 Iniciando servidor em http://{host}:{port}")
        app.run(
            host=host,
            port=port,
            debug=debug_mode,
            use_reloader=debug_mode and not is_running_from_reloader()
        )
    except Exception as e:
        logging.error(f"❌ Falha ao iniciar servidor: {str(e)}")
        raise

# --- CORREÇÃO NA ORDEM DE INICIALIZAÇÃO ---
# Esta seção é executada quando o Gunicorn na Render importa o arquivo.

# 1. Configura o logging primeiro.
configure_logging()
# 2. Carrega as variáveis do .env (se houver).
load_dotenv()
# 3. AGORA, com tudo configurado, cria a aplicação.
app = create_app()

# -------------------------------------------

if __name__ == '__main__':
    # Este bloco é apenas para rodar localmente e é ignorado pelo Gunicorn.
    # As funções de configuração não são mais necessárias aqui, pois já foram chamadas acima.
    try:
        verify_config(app)
        start_server(app)
    except Exception as e:
        logging.critical(f"⛔ Falha crítica na inicialização: {str(e)}")
        raise
