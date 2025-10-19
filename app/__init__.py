 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/app/__init__.py b/app/__init__.py
index 1eb532b21aaac023a93fbe895a733ce9d7d6ca1c..96a02fdc7407339d826098278c1e4928cc24d903 100644
--- a/app/__init__.py
+++ b/app/__init__.py
@@ -1,74 +1,73 @@
 from flask import Flask, render_template
 from flask_session import Session
 from .routes import register_routes
+from .logging_config import configure_logging
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
 
-    # Configuração avançada do logger
-    logging.basicConfig(
-        level=logging.INFO,
-        format='%(asctime)s - %(levelname)s - %(message)s'
-    )
+    configure_logging()
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
-        'MAP_ID': 'ID do mapa',
         'SESSION_COOKIE_NAME': 'Nome do cookie de sessão'
     }
 
     missing = [key for key in required_configs if not app.config.get(key)]
     if missing:
         error_msg = "Configurações obrigatórias faltando:\n" + \
                    "\n".join(f"- {key}: {required_configs[key]}" for key in missing)
         app.logger.error(error_msg)
         raise ValueError("Configurações essenciais faltando no arquivo config.py ou variáveis de ambiente")
 
     # Apenas warning caso falte a key do Google
+    if not app.config.get('MAP_ID'):
+        app.logger.warning("⚠️ MAP_ID não definido. Usando funcionalidades padrão do mapa.")
+
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
 
 
EOF
)
