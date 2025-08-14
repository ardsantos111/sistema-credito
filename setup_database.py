import os
import pg8000.dbapi
from dotenv import load_dotenv
from urllib.parse import urlparse, unquote

load_dotenv()

# Usar a URL do banco de dados correta diretamente
DATABASE_URL = "postgresql://postgres:Am461271%40am461271@db.guqrxjjrpmfbeftwmokz.supabase.co:5432/postgres"

def get_db_connection():
    try:
        # Usar a URL do banco de dados correta diretamente
        database_url = DATABASE_URL
        
        # Remover espaços extras da URL
        database_url = database_url.strip()
        
        # Analisar a URL do banco de dados
        url = urlparse(database_url)
        
        # Decodificar a senha para lidar com caracteres especiais
        decoded_password = unquote(url.password) if url.password else None
        
        # Garantir que a porta seja um inteiro
        port = url.port
        if isinstance(port, str):
            port = int(port.strip())
        
        # Conectar ao banco de dados
        return pg8000.dbapi.connect(
            user=url.username,
            password=decoded_password,
            host=url.hostname,
            port=port,
            database=url.path[1:],
            timeout=30
        )
    except Exception as e:
        print(f"Erro na conexão com o banco: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def setup_database():
    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()

        # Create tables with enhanced multi-company structure
        cur.execute("""
            -- Empresas table
            CREATE TABLE IF NOT EXISTS empresas (
                id SERIAL PRIMARY KEY,
                nome_empresa TEXT NOT NULL,
                cnpj TEXT,
                ativo BOOLEAN DEFAULT TRUE,
                plano TEXT DEFAULT 'gratis',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_ativacao DATE,
                data_expiracao DATE
            );
            
            -- Users table with role support
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                empresa_id INTEGER REFERENCES empresas(id), -- NULL for master users
                role TEXT DEFAULT 'user', -- master, admin, vendedor, supervisor, etc.
                ativo BOOLEAN DEFAULT TRUE,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultimo_acesso TIMESTAMP
            );
            
            -- Clients table
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                cpf TEXT,
                endereco TEXT,
                empresa_id INTEGER REFERENCES empresas(id)
            );
            
            -- Sales table
            CREATE TABLE IF NOT EXISTS vendas (
                id SERIAL PRIMARY KEY,
                cliente_id INTEGER REFERENCES clientes(id),
                empresa_id INTEGER REFERENCES empresas(id),
                user_id INTEGER REFERENCES users(id),
                valor_total REAL,
                valor_entrada REAL,
                num_parcelas INTEGER,
                data_venda TIMESTAMP,
                status TEXT,
                descricao_venda TEXT,
                observacoes TEXT,
                forma_pagamento TEXT
            );
            
            -- Payments table
            CREATE TABLE IF NOT EXISTS pagamentos (
                id SERIAL PRIMARY KEY,
                venda_id INTEGER REFERENCES vendas(id),
                valor REAL,
                data_vencimento TIMESTAMP,
                data_pagamento TIMESTAMP,
                status TEXT,
                forma_pagamento TEXT
            );
            
            -- Store info table
            CREATE TABLE IF NOT EXISTS loja (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                endereco TEXT NOT NULL
            );
            
            -- Permissions table
            CREATE TABLE IF NOT EXISTS permissoes (
                id SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL,
                descricao TEXT,
                categoria TEXT
            );
            
            -- Role permissions table
            CREATE TABLE IF NOT EXISTS role_permissoes (
                id SERIAL PRIMARY KEY,
                role TEXT NOT NULL,
                permissao_id INTEGER REFERENCES permissoes(id),
                permitido BOOLEAN DEFAULT TRUE
            );
        """)

        # Insert default permissions
        cur.execute("SELECT COUNT(*) FROM permissoes;")
        if cur.fetchone()[0] == 0:
            permissoes_padrao = [
                # Vendas
                ('criar_venda', 'Criar nova venda', 'vendas'),
                ('editar_venda', 'Editar vendas existentes', 'vendas'),
                ('excluir_venda', 'Excluir vendas', 'vendas'),
                ('visualizar_vendas', 'Visualizar todas as vendas', 'vendas'),
                
                # Clientes
                ('criar_cliente', 'Criar novo cliente', 'clientes'),
                ('editar_cliente', 'Editar clientes existentes', 'clientes'),
                ('excluir_cliente', 'Excluir clientes', 'clientes'),
                ('visualizar_clientes', 'Visualizar todos os clientes', 'clientes'),
                
                # Pagamentos
                ('registrar_pagamento', 'Registrar pagamentos', 'pagamentos'),
                ('editar_pagamento', 'Editar pagamentos', 'pagamentos'),
                ('visualizar_pagamentos', 'Visualizar todos os pagamentos', 'pagamentos'),
                
                # Relatórios
                ('gerar_relatorios', 'Gerar relatórios', 'relatorios'),
                ('exportar_dados', 'Exportar dados', 'relatorios'),
                
                # Usuários
                ('gerenciar_usuarios', 'Gerenciar usuários da empresa', 'usuarios'),
                ('definir_permissoes', 'Definir permissões de usuários', 'usuarios'),
                
                # Configurações
                ('configurar_sistema', 'Configurar parâmetros do sistema', 'configuracoes'),
                ('gerenciar_empresa', 'Gerenciar dados da empresa', 'configuracoes')
            ]
            
            for nome, descricao, categoria in permissoes_padrao:
                cur.execute(
                    "INSERT INTO permissoes (nome, descricao, categoria) VALUES (%s, %s, %s)",
                    (nome, descricao, categoria)
                )

        # Insert default role permissions
        cur.execute("SELECT COUNT(*) FROM role_permissoes;")
        if cur.fetchone()[0] == 0:
            # Master user permissions (all permissions)
            cur.execute("SELECT id FROM permissoes")
            todas_permissoes = cur.fetchall()
            for permissao in todas_permissoes:
                cur.execute(
                    "INSERT INTO role_permissoes (role, permissao_id, permitido) VALUES (%s, %s, %s)",
                    ('master', permissao[0], True)
                )
            
            # Admin permissions (most permissions except master-only)
            permissoes_admin = ['criar_venda', 'editar_venda', 'visualizar_vendas', 
                              'criar_cliente', 'editar_cliente', 'visualizar_clientes',
                              'registrar_pagamento', 'editar_pagamento', 'visualizar_pagamentos',
                              'gerar_relatorios', 'exportar_dados', 'gerenciar_usuarios']
            
            for nome_permissao in permissoes_admin:
                cur.execute("SELECT id FROM permissoes WHERE nome = %s", (nome_permissao,))
                permissao = cur.fetchone()
                if permissao:
                    cur.execute(
                        "INSERT INTO role_permissoes (role, permissao_id, permitido) VALUES (%s, %s, %s)",
                        ('admin', permissao[0], True)
                    )
            
            # Vendedor permissions (basic permissions)
            permissoes_vendedor = ['criar_venda', 'visualizar_vendas', 
                                 'criar_cliente', 'visualizar_clientes',
                                 'registrar_pagamento', 'visualizar_pagamentos']
            
            for nome_permissao in permissoes_vendedor:
                cur.execute("SELECT id FROM permissoes WHERE nome = %s", (nome_permissao,))
                permissao = cur.fetchone()
                if permissao:
                    cur.execute(
                        "INSERT INTO role_permissoes (role, permissao_id, permitido) VALUES (%s, %s, %s)",
                        ('vendedor', permissao[0], True)
                    )

        # Insert default data for loja
        cur.execute("SELECT COUNT(*) FROM loja;")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO loja (nome, endereco) VALUES (%s, %s);", 
                      ("Sua Loja de Vendas Ltda.", "Av. Brasil, 1234 - Centro, Anápolis/GO"))

        conn.commit()
        print("Database setup completed successfully.")

    except Exception as e:
        print(f"Error setting up database: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    setup_database()