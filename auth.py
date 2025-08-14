import pg8000.dbapi
from urllib.parse import urlparse, unquote
from werkzeug.security import check_password_hash, generate_password_hash
import os
from dotenv import load_dotenv
from datetime import datetime

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

class AppUser:
    def __init__(self, id, email, empresa_id, role, ativo):
        self.id = id
        self.email = email
        self.empresa_id = empresa_id
        self.role = role
        self.ativo = ativo
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active(self):
        return self.ativo
    
    @property
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)

def get_db_connection():
    try:
        # Usar credenciais corretas diretamente, ignorando variáveis de ambiente
        database_url = "postgresql://postgres:Am461271%40am461271@db.guqrxjjrpmfbeftwmokz.supabase.co:5432/postgres"
        # Remover espaços extras da URL
        database_url = database_url.strip()
        url = urlparse(database_url)
        decoded_password = unquote(url.password) if url.password else None
        
        # Garantir que a porta seja um inteiro
        port = url.port
        if isinstance(port, str):
            port = int(port.strip())
        
        # Criar contexto SSL
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        return pg8000.dbapi.connect(
            user=url.username,
            password=decoded_password,
            host=url.hostname,
            port=port,
            database=url.path[1:],
            timeout=30,
            ssl_context=ssl_context
        )
    except Exception as e:
        print(f"Erro na conexão com o banco: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def authenticate_user(email, password):
    """
    Autentica um usuário usando a tabela app_users
    Retorna um objeto AppUser se autenticado, None caso contrário
    """
    try:
        conn = get_db_connection()
        if not conn:
            return None
            
        cur = conn.cursor()
        
        # Buscar usuário por email
        cur.execute("""
            SELECT id, email, password, empresa_id, role, ativo 
            FROM app_users 
            WHERE email = %s AND ativo = TRUE
        """, (email,))
        
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if user_data and check_password_hash(user_data[2], password):
            return AppUser(
                id=user_data[0],
                email=user_data[1],
                empresa_id=user_data[3],
                role=user_data[4],
                ativo=user_data[5]
            )
            
        return None
        
    except Exception as e:
        print(f"Erro na autenticação: {str(e)}")
        return None

def load_user(user_id):
    """
    Carrega um usuário pelo ID
    Retorna um objeto AppUser se encontrado, None caso contrário
    """
    try:
        conn = get_db_connection()
        if not conn:
            return None
            
        cur = conn.cursor()
        
        # Buscar usuário por ID
        cur.execute("""
            SELECT id, email, empresa_id, role, ativo 
            FROM app_users 
            WHERE id = %s AND ativo = TRUE
        """, (user_id,))
        
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if user_data:
            return AppUser(
                id=user_data[0],
                email=user_data[1],
                empresa_id=user_data[2],
                role=user_data[3],
                ativo=user_data[4]
            )
            
        return None
        
    except Exception as e:
        print(f"Erro ao carregar usuário: {str(e)}")
        return None

def get_user_companies(user_id):
    """
    Retorna as empresas às quais o usuário tem acesso
    """
    try:
        conn = get_db_connection()
        if not conn:
            return []
            
        cur = conn.cursor()
        
        # Para master users, retornar todas as empresas ativas
        cur.execute("SELECT role FROM app_users WHERE id = %s", (user_id,))
        user_role = cur.fetchone()
        
        if user_role and user_role[0] == 'master':
            # Master user - todas as empresas ativas
            cur.execute("""
                SELECT id, nome_empresa, cnpj, ativo, plano 
                FROM empresas 
                WHERE ativo = TRUE 
                ORDER BY nome_empresa
            """)
        else:
            # Usuário normal - apenas empresas onde está associado
            cur.execute("""
                SELECT e.id, e.nome_empresa, e.cnpj, e.ativo, e.plano
                FROM empresas e
                JOIN app_users au ON au.empresa_id = e.id
                WHERE au.id = %s AND e.ativo = TRUE
                ORDER BY e.nome_empresa
            """, (user_id,))
        
        companies = cur.fetchall()
        cur.close()
        conn.close()
        
        return [(company[0], company[1], company[2], company[3], company[4]) for company in companies]
        
    except Exception as e:
        print(f"Erro ao buscar empresas do usuário: {str(e)}")
        return []

def update_last_access(user_id):
    """
    Atualiza a data/hora do último acesso do usuário
    """
    try:
        conn = get_db_connection()
        if not conn:
            return
            
        cur = conn.cursor()
        cur.execute("""
            UPDATE app_users 
            SET ultimo_acesso = %s 
            WHERE id = %s
        """, (datetime.now(), user_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Erro ao atualizar último acesso: {str(e)}")

def create_user(email, password_hash, role='user', empresa_id=None):
    """
    Cria um novo usuário na tabela app_users
    """
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        cur = conn.cursor()
        
        # Verificar se usuário já existe
        cur.execute("SELECT id FROM app_users WHERE email = %s", (email,))
        if cur.fetchone():
            cur.close()
            conn.close()
            return False
            
        # Criar novo usuário
        cur.execute("""
            INSERT INTO app_users (email, password, role, empresa_id, ativo) 
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (email, password_hash, role, empresa_id, True))
        
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return user_id
        
    except Exception as e:
        print(f"Erro ao criar usuário: {str(e)}")
        return False

def user_has_permission(user_id, permission_name):
    """
    Verifica se um usuário tem uma permissão específica
    """
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        cur = conn.cursor()
        
        # Buscar role do usuário
        cur.execute("SELECT role FROM app_users WHERE id = %s", (user_id,))
        user_role = cur.fetchone()
        
        if not user_role:
            cur.close()
            conn.close()
            return False
            
        role = user_role[0]
        
        # Master users têm todas as permissões
        if role == 'master':
            cur.close()
            conn.close()
            return True
            
        # Verificar permissão específica para a role
        cur.execute("""
            SELECT rp.permitido
            FROM role_permissoes rp
            JOIN permissoes p ON rp.permissao_id = p.id
            WHERE rp.role = %s AND p.nome = %s
        """, (role, permission_name))
        
        permission = cur.fetchone()
        cur.close()
        conn.close()
        
        return permission and permission[0]
        
    except Exception as e:
        print(f"Erro ao verificar permissão: {str(e)}")
        return False

# Test functions
if __name__ == "__main__":
    # Testar conexão
    print("Testando conexão com o banco de dados...")
    conn = get_db_connection()
    if conn:
        print("✓ Conexão bem-sucedida!")
        conn.close()
    else:
        print("✗ Falha na conexão!")
        
    # Testar autenticação
    print("\nTestando autenticação...")
    user = authenticate_user("master@sistema.com", "Master123@")
    if user:
        print(f"✓ Usuário autenticado: {user.email} (Role: {user.role})")
        
        # Testar carga de usuário
        print("\nTestando carga de usuário...")
        loaded_user = load_user(user.id)
        if loaded_user:
            print(f"✓ Usuário carregado: {loaded_user.email} (Role: {loaded_user.role})")
        else:
            print("✗ Falha ao carregar usuário")
            
        # Testar empresas do usuário
        print("\nTestando empresas do usuário...")
        companies = get_user_companies(user.id)
        print(f"✓ Encontradas {len(companies)} empresas para o usuário")
        for company in companies:
            print(f"  - {company[1]} ({company[2]})")
            
        # Testar atualização de último acesso
        print("\nTestando atualização de último acesso...")
        update_last_access(user.id)
        print("✓ Último acesso atualizado")
        
        # Testar criação de usuário
        print("\nTestando criação de usuário...")
        password_hash = generate_password_hash("Test123@")
        user_id = create_user("test@empresa.com", password_hash, "vendedor")
        if user_id:
            print(f"✓ Usuário criado com ID {user_id}")
        else:
            print("✗ Falha ao criar usuário (pode já existir)")
            
        # Testar permissões
        print("\nTestando permissões...")
        has_permission = user_has_permission(user.id, "criar_venda")
        print(f"✓ Usuário tem permissão 'criar_venda': {has_permission}")
        
    else:
        print("✗ Falha na autenticação!")
    
    print("\nTeste concluído!")