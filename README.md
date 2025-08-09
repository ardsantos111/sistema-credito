# App Crediário

Esta é uma aplicação Flask para gerenciar vendas e pagamentos.

## Configuração

1. **Instale as dependências:**

   - **Windows:**
     - Baixe e instale os binários do PostgreSQL no [site oficial](https://www.postgresql.org/download/windows/).
     - Certifique-se de adicionar o diretório `bin` da sua instalação do PostgreSQL à variável de ambiente `PATH`.
     - Instale as dependências:
       ```bash
       pip install -r requirements.txt
       ```

   - **Linux/macOS:**
     ```bash
     pip install -r requirements.txt
     ```

2. **Configure o banco de dados:**

   - Certifique-se de que você tenha um banco de dados PostgreSQL em execução.
   - Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:

     ```
     SECRET_KEY='sua_chave_super_secreta'
     DATABASE_URL='postgresql://usuario:senha@host:porta/banco_de_dados'
     ```

   - Execute o script de configuração do banco de dados:

     ```bash
     python setup_database.py
     ```

3. **Execute a aplicação:**

   ```bash
   flask run
   ```

## Implantação na Vercel

Ao implantar na Vercel, certifique-se de definir as variáveis de ambiente `SECRET_KEY` e `DATABASE_URL` nas configurações do projeto Vercel.