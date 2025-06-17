# DriveMaps 🚗

Validador e organizador de endereços para estafetas em Portugal, pronto para múltiplas empresas e exportação para apps de rotas.

## Como Usar
1. Clone o repositório
2. Copie `.env.example` para `.env` e configure suas chaves
3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
4. Execute o servidor:
   ```
   flask run
   ```
5. Acesse `http://localhost:5000`

## Fluxo
- Cole endereços ou faça upload de planilhas.
- Valide e corrija os endereços.
- Exporte para MyWay (ou expanda para outros apps).

## Segurança
- Nunca suba `.env` com segredos para o repositório.
- Assegure-se de rodar com as variáveis de ambiente corretas.

## Extensão
- Adicione novas empresas criando classes em `app/services/importers.py`.
- Novos formatos de exportação podem ser criados em `app/services/exporters.py`.
