# App Crediário

Esta é uma aplicação Flask para gerenciar vendas e pagamentos.

## Configuração

1. **Instale as dependências:**

   ### Para implantação na Vercel (ambiente de produção):
   ```bash
   pip install -r requirements.txt
   ```

   ### Para uso local (ambiente de desenvolvimento):
   ```bash
   pip install -r requirements-local.txt
   ```

2. **Configure o banco de dados:**

   ### Para uso local:
   Certifique-se de que você tenha um banco de dados PostgreSQL em execução.
   Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:

   ```
   SECRET_KEY='sua_chave_super_secreta'
   DATABASE_URL='postgresql://usuario:senha@localhost:5432/banco_de_dados'
   ```

   ### Para uso na Vercel:
   Configure as variáveis de ambiente no painel do Vercel:
   - `SECRET_KEY`: Uma chave secreta segura
   - `DATABASE_URL`: URL de conexão com o banco de dados PostgreSQL

3. **Configure o banco de dados:**

   - Execute o script de configuração do banco de dados:

     ```bash
     python setup_database.py
     ```

4. **Execute a aplicação:**

   ### Para implantação na Vercel (ambiente de produção):
   ```bash
   flask run
   ```

   ### Para uso local (ambiente de desenvolvimento):
   ```bash
   python run.py
   ```

## Funcionalidades

- **Geração de contratos em PDF**: Disponível apenas no ambiente local devido a limitações do ambiente da Vercel.
- **Gestão de vendas e pagamentos**: Cadastro de clientes, registro de vendas e acompanhamento de pagamentos.
- **Dashboard**: Visão geral das vendas recentes e pagamentos pendentes.

## Roadmap de Melhorias

Para ver o roadmap completo de melhorias planejadas, consulte o arquivo [ROADMAP.md](ROADMAP.md).

Atualmente estamos trabalhando na **Categoria 1: Interface do Usuário**.

## Implantação na Vercel

Ao implantar na Vercel, certifique-se de definir as variáveis de ambiente `SECRET_KEY` e `DATABASE_URL` nas configurações do projeto Vercel.

### Variáveis de Ambiente Necessárias:

1. `SECRET_KEY`: Uma chave secreta segura para proteção de sessões
2. `DATABASE_URL`: URL de conexão com o banco de dados PostgreSQL

## Segurança

- Nunca commite arquivos `.env` contendo credenciais reais
- Use o arquivo `.gitignore` para evitar que credenciais sejam expostas
- Sempre use variáveis de ambiente para configurações sensíveis em produção