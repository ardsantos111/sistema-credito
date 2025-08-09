import sqlite3

def ensure_user_id_column():
    """Verifica se a coluna 'user_id' existe e a cria se necessário."""
    conn = None
    try:
        conn = sqlite3.connect('vendas.db')
        c = conn.cursor()
        
        c.execute("PRAGMA table_info(vendas);")
        columns = [column[1] for column in c.fetchall()]

        if 'user_id' not in columns:
            print("Coluna 'user_id' não encontrada. Adicionando...")
            c.execute("ALTER TABLE vendas ADD COLUMN user_id INTEGER;")
            conn.commit()
            print("Coluna 'user_id' adicionada com sucesso.")
        else:
            print("A coluna 'user_id' já existe. Nenhuma alteração foi feita.")

    except sqlite3.Error as e:
        print(f"Erro no banco de dados: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    ensure_user_id_column()