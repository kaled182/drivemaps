#!/bin/bash
# prebuild.sh - Script executado antes do build no Render

# Remove versões conflitantes
pip uninstall -y numpy pandas

# Instala as versões específicas com --no-cache-dir
pip install numpy==1.23.5 pandas==1.5.3 --no-cache-dir

# Instala os outros requirements
pip install -r requirements.txt
