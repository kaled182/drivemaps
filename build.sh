#!/bin/bash
set -e

echo "🛠️ Atualizando pip, setuptools e wheel..."
pip install --upgrade pip setuptools wheel

echo "📦 Instalando requirements.txt..."
pip install -r requirements.txt

# [Opcional] Instale dependências de sistema se necessário
# echo "🔧 Instalando libs do sistema (apt-get)..."
# apt-get update && apt-get install -y build-essential

echo "✅ Dependências Python instaladas:"
pip freeze

# [Opcional] Comando custom pós-install, por exemplo migrar banco
# echo "🎯 Rodando comandos pós-build..."
# python manage.py migrate

echo "🚀 Build concluído com sucesso!"
