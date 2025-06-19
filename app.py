#!/usr/bin/env python3
from app import create_app
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Cria a aplicação Flask
app = create_app()

def verify_config():
    """Verificação completa das configurações"""
    required_keys = [
        'SECRET_KEY',
        'SESSION_TYPE',
        'SESSION_COOKIE_NAME',
        'SESSION_FILE_DIR',
        'SESSION_PERMANENT',
        'SESSION_USE_SIGNER'
    ]
    
    missing = [key for key in required_keys if not app.config.get(key)]
    if missing:
        error_msg = f"Configurações obrigatórias faltando: {', '.join(missing)}"
        app.logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Verifica se está usando a SECRET_KEY padrão (insegura)
    if 'sua-chave-secreta' in app.config['SECRET_KEY']:
        app.logger.warning("AVISO: SECRET_KEY padrão em uso - INSECURO para produção!")
    
    app.logger.info("✓ Todas as configurações verificadas")

if __name__ == '__main__':
    # Verifica configurações antes de iniciar
    verify_config()
    
    # Configurações do servidor
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 10000))
    
    app.logger.info(f"🔑 SECRET_KEY configurada: {'Sim' if app.config['SECRET_KEY'] else 'Não'}")
    app.logger.info(f"🚀 Iniciando servidor em http://{host}:{port}")
    
    app.run(
        host=host,
        port=port,
        debug=app.config['DEBUG'],
        use_reloader=False  # Melhor para produção
    )
