import sqlite3

def setup_loja_table():
    """Cria a tabela 'loja' se ela não existir e insere dados padrão."""
    conn = None
    try:
        conn = sqlite3.connect('vendas.db')
        c = conn.cursor()

        # Cria a tabela 'loja' se ela não existir
        c.execute("""
            CREATE TABLE IF NOT EXISTS loja (
                id INTEGER PRIMARY KEY,
                nome TEXT NOT NULL,
                endereco TEXT NOT NULL
            );
        """)

        # Verifica se já existe um registro na tabela 'loja'
        c.execute("SELECT COUNT(*) FROM loja;")
        if c.fetchone()[0] == 0:
            # Se não houver, insere um registro padrão
            print("Tabela 'loja' criada. Inserindo dados padrão...")
            c.execute("INSERT INTO loja (nome, endereco) VALUES (?, ?);", 
                      ("Sua Loja de Vendas Ltda.", "Av. Brasil, 1234 - Centro, Anápolis/GO"))
        else:
            print("A tabela 'loja' já existe e contém dados. Nenhuma alteração foi feita.")

        conn.commit()
        print("Verificação e atualização do banco de dados para a tabela 'loja' concluídas.")

    except sqlite3.Error as e:
        print(f"Erro no banco de dados: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    setup_loja_table()