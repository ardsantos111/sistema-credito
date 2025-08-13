import os
import sys
import json
from urllib.parse import urlparse, unquote
import pg8000.dbapi

def test_connection():
    """Função para testar a conexão com o banco de dados na Vercel"""
    try:
        # Usar a URL do banco de dados correta diretamente
        database_url = "postgresql://postgres:Am461271%40am461271@db.guqrxjjrpmfbeftwmokz.supabase.co:5432/postgres"
        
        # Analisar a URL do banco de dados
        url = urlparse(database_url)
        
        # Decodificar a senha para lidar com caracteres especiais
        decoded_password = unquote(url.password) if url.password else None
        
        # Conectar ao banco de dados
        conn = pg8000.dbapi.connect(
            user=url.username,
            password=decoded_password,
            host=url.hostname,
            port=url.port,
            database=url.path[1:]
        )
        
        # Testar uma consulta simples
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        cur.close()
        conn.close()
        
        return {
            "success": True,
            "message": "Conexão com o banco de dados estabelecida com sucesso!",
            "database_version": version[0]
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Erro na conexão com o banco de dados: {str(e)}",
            "error_type": type(e).__name__
        }

def handler(event, context):
    """Handler para a Vercel"""
    result = test_connection()
    
    # Retornar resposta JSON
    return {
        "statusCode": 200 if result["success"] else 500,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(result, indent=2)
    }

# Para testes locais
if __name__ == "__main__":
    result = test_connection()
    print(json.dumps(result, indent=2))