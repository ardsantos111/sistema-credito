# App Crediário

Esta é uma aplicação Flask para gerenciar vendas e pagamentos.

## Configuração

1. **Instale as dependências:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure o banco de dados:**

   ### Usando Supabase (recomendado)
   
   - Crie uma conta no [Supabase](https://supabase.io/) e um novo projeto.
   - Obtenha as credenciais de conexão do seu projeto Supabase.
   - Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:
   
     ```
     SECRET_KEY='sua_chave_super_secreta'
     DATABASE_URL='postgresql://postgres:SUA_SENHA@db.seu_projeto.supabase.co:5432/postgres'
     ```
   
   - Você também pode copiar o arquivo `.env.example` e atualizar com suas credenciais:
   
     ```bash
     cp .env.example .env
     ```

   ### Usando PostgreSQL local
   
   - Certifique-se de que você tenha um banco de dados PostgreSQL em execução.
   - Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:
   
     ```
     SECRET_KEY='sua_chave_super_secreta'
     DATABASE_URL='postgresql://usuario:senha@localhost:5432/banco_de_dados'
     ```

3. **Configure o banco de dados:**

   - Execute o script de configuração do banco de dados:
   
     ```bash
     python setup_database.py
     ```

4. **Execute a aplicação:**

   ```bash
   flask run
   ```

## Implantação na Vercel

Ao implantar na Vercel, certifique-se de definir as variáveis de ambiente `SECRET_KEY` e `DATABASE_URL` nas configurações do projeto Vercel.