import os
import pg8000.dbapi
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

def test_tables():
    try:
        # Conectar diretamente com os parâmetros separados
        conn = pg8000.dbapi.connect(
            user="postgres",
            password="Am461271@am461271",
            host="db.guqrxjjrpmfbeftwmokz.supabase.co",
            port=5432,
            database="postgres"
        )
        
        print("Connection successful!")
        cur = conn.cursor()
        
        # Verificar se as tabelas foram criadas
        tables = ['empresas', 'users', 'clientes', 'vendas', 'pagamentos', 'loja']
        
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table};")
                count = cur.fetchone()[0]
                print(f"Tabela '{table}' existe e contém {count} registros.")
            except Exception as e:
                print(f"Erro ao acessar tabela '{table}': {str(e)}")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_tables()