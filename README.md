# PAACK – Gerador de CSV com Validação Google

## O que faz
- Recebe lista de endereços no padrão PAACK
- Extrai endereço, código postal e número do pacote
- Valida automaticamente cada endereço via Google Maps API
- Exporta arquivo CSV pronto para apps de roteamento ou auditoria

## Como rodar localmente
```bash
pip install -r requirements.txt
python app.py

---

## **4. Deploy no Render – Passo a Passo**

**A. ZIP ou GitHub**
- Coloque os 3 arquivos (`app.py`, `requirements.txt`, `README.md`) em uma pasta no seu computador.
- Compacte em `.zip` ou suba para um repositório GitHub (privado ou público).

**B. No [https://render.com/](https://render.com/)**
1. Após login, clique em **"New +" > "Web Service"**.
2. Escolha "Deploy from a Git repository" **ou** "Manual Deploy" (upload .zip).
3. Siga as instruções:
    - **Build command:** (deixe em branco, Render instala via requirements.txt)
    - **Start command:**  
      ```
      gunicorn app:app
      ```
4. Confirme o Python (Render detecta automaticamente pelo arquivo requirements.txt).
5. Aguarde alguns minutos.  
   O endereço do seu app ficará disponível assim que aparecer "Live" no painel.

---

## **Pronto!**

Assim, qualquer pessoa pode acessar, colar a lista de endereços e baixar o CSV validado.

---

**Se quiser, faço uma tela extra mostrando os endereços não validados, ou já deixo com logotipo personalizado, etc. Me avise!**

Se surgir qualquer erro durante o deploy, só colar aqui a mensagem que eu te ajudo a corrigir!
