#!/usr/bin/env python3
# run.py - Ponto de entrada principal da aplicação

from app import create_app
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env (apenas para desenvolvimento)
load_dotenv()  # Isso será ignorado no Render, que usa variáveis de ambiente reais

# Cria a aplicação Flask
app = create_app()

def verify_config():
    """Verifica as configurações essenciais antes de iniciar"""
    if not app.config['SECRET_KEY'] or app.config['SECRET_KEY'] == 'sua-chave-secreta':
        raise ValueError("SECRET_KEY não configurada corretamente. Defina no Render.com")
    
    if app.config['SESSION_TYPE'] == 'filesystem':
        session_dir = app.config.get('SESSION_FILE_DIR')
        if session_dir:
            if not os.path.exists(session_dir):
                os.makedirs(session_dir)
                print(f"✓ Diretório de sessão criado em: {session_dir}")
            else:
                print(f"✓ Diretório de sessão já existe em: {session_dir}")

if __name__ == '__main__':
    # Verifica configurações antes de iniciar
    verify_config()
    
    # Configurações do servidor (compatível com Render)
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 10000))  # Render usa a porta 10000
    
    print(f"🔑 SECRET_KEY configurada: {'Sim' if app.config['SECRET_KEY'] else 'Não'}")
    print(f"🚀 Iniciando servidor em http://{host}:{port}")
    
    app.run(
        host=host,
        port=port,
        # Desativa debug em produção (seguro para Render)
        debug=os.getenv('DEBUG_MODE', 'False') == 'True'
    )
