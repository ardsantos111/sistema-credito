import os
import pg8000.dbapi
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    try:
        # Conectar diretamente com os parâmetros separados para evitar problemas de codificação
        return pg8000.dbapi.connect(
            user="postgres",
            password="Am461271@am461271",
            host="db.guqrxjjrpmfbeftwmokz.supabase.co",
            port=5432,
            database="postgres"
        )
    except Exception as e:
        print(f"Erro na conexão com o banco: {str(e)}")
        return None

def setup_database():
    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()

        # Create tables
        cur.execute("""
            CREATE TABLE IF NOT EXISTS empresas (
                id SERIAL PRIMARY KEY,
                nome_empresa TEXT NOT NULL,
                cnpj TEXT
            );
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                empresa_id INTEGER REFERENCES empresas(id)
            );
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                cpf TEXT,
                endereco TEXT,
                empresa_id INTEGER REFERENCES empresas(id)
            );
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
            CREATE TABLE IF NOT EXISTS pagamentos (
                id SERIAL PRIMARY KEY,
                venda_id INTEGER REFERENCES vendas(id),
                valor REAL,
                data_vencimento TIMESTAMP,
                status TEXT
            );
            CREATE TABLE IF NOT EXISTS loja (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                endereco TEXT NOT NULL
            );
        """);

        # Insert default data for loja
        cur.execute("SELECT COUNT(*) FROM loja;")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO loja (nome, endereco) VALUES (%s, %s);", 
                      ("Sua Loja de Vendas Ltda.", "Av. Brasil, 1234 - Centro, Anápolis/GO"))

        conn.commit()
        print("Database setup completed successfully.")

    except Exception as e:
        print(f"Error setting up database: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    setup_database()