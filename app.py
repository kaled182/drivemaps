#!/usr/bin/env python3
from app import create_app
import os
import logging
from dotenv import load_dotenv
from werkzeug.serving import is_running_from_reloader

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
            logging.warning("AVISO: SECRET_KEY padrão em uso - INSECURO para produção!")
        logging.info("✅ Configurações verificadas com sucesso")
        return True
    except Exception as e:
        logging.error(f"❌ Falha na verificação de configurações: {str(e)}")
        raise

def start_server(app):
    """Inicia o servidor Flask para desenvolvimento local"""
    try:
        host = os.getenv('HOST', '127.0.0.1')
        port = int(os.getenv('PORT', 5000))
        debug_mode = app.config.get('DEBUG', True)
        
        logging.info(f"🚀 Iniciando servidor de DESENVOLVIMENTO em http://{host}:{port}")
        app.run(
            host=host,
            port=port,
            debug=debug_mode
        )
    except Exception as e:
        logging.error(f"❌ Falha ao iniciar servidor: {str(e)}")
        raise

# --- INICIALIZAÇÃO GLOBAL ---
# Estas linhas são executadas tanto pelo Gunicorn (na Render) quanto localmente.

# 1. Configura o logging
configure_logging()

# 2. Carrega variáveis de ambiente do arquivo .env (importante para create_app)
load_dotenv()

# 3. Cria a instância da aplicação Flask, que agora pode ser encontrada pelo Gunicorn
app = create_app()

# -----------------------------


if __name__ == '__main__':
    # Este bloco é executado APENAS quando você roda `python app.py` na sua máquina.
    # O Gunicorn na Render IGNORA esta parte.
    try:
        # A verificação de config já acontece dentro de create_app, mas podemos fazer de novo se quisermos.
        verify_config(app)
        # Inicia o servidor de desenvolvimento.
        start_server(app)
    except Exception as e:
        logging.critical(f"⛔ Falha crítica na inicialização local: {str(e)}")
        raise
