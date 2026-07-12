"""
Executa uma vez para criar o banco de dados e a tabela de contatos.
Uso: python init_db.py
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SQL_CRIAR_TABELA = """
CREATE TABLE IF NOT EXISTS contatos (
    id         SERIAL PRIMARY KEY,
    nome       VARCHAR(200)  NOT NULL,
    email      VARCHAR(200)  NOT NULL,
    telefone   VARCHAR(50),
    area       VARCHAR(100),
    mensagem   TEXT          NOT NULL,
    criado_em  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    lido       BOOLEAN       DEFAULT FALSE
);
"""

def main():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
        )
        cur = conn.cursor()
        cur.execute(SQL_CRIAR_TABELA)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Tabela 'contatos' criada com sucesso!")
    except Exception as e:
        print(f"❌ Erro: {e}")
        print("\nVerifique os dados no arquivo .env e se o PostgreSQL está rodando.")

if __name__ == "__main__":
    main()
