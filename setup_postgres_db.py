import sqlite3

def add_new_columns():
    """Adiciona as colunas 'descricao', 'observacoes' e 'forma_pagamento' à tabela vendas."""
    conn = None
    try:
        conn = sqlite3.connect('vendas.db')
        c = conn.cursor()

        # Checa se as colunas já existem
        c.execute("PRAGMA table_info(vendas);")
        columns = [column[1] for column in c.fetchall()]

        if 'descricao_venda' not in columns:
            print("Adicionando a coluna 'descricao_venda'...")
            c.execute("ALTER TABLE vendas ADD COLUMN descricao_venda TEXT;")

        if 'observacoes' not in columns:
            print("Adicionando a coluna 'observacoes'...")
            c.execute("ALTER TABLE vendas ADD COLUMN observacoes TEXT;")

        if 'forma_pagamento' not in columns:
            print("Adicionando a coluna 'forma_pagamento'...")
            c.execute("ALTER TABLE vendas ADD COLUMN forma_pagamento TEXT;")

        conn.commit()
        print("Verificação e atualização do banco de dados concluídas.")

    except sqlite3.Error as e:
        print(f"Erro no banco de dados: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    add_new_columns()