# DriveMaps – Estrutura Modular

## Como usar

1. Copie `.env.example` para `.env` e preencha as chaves.
2. Instale dependências:
   ```
   pip install -r requirements.txt
   ```
3. Rode o app:
   ```
   flask run
   ```
4. Use `/import_planilha` para importar arquivos de diferentes empresas.

## Como expandir

- Para adicionar nova empresa, crie uma nova classe em `services/importers.py` herdando de `BaseImporter`.
- Centralize validações e normalizações nos arquivos `services/validators.py` e `utils/normalize.py`.

## Segurança

- Nunca suba seu `.env` para o repositório.
- Troque suas chaves se já subiu anteriormente.
