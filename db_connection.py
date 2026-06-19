import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURAÇÃO
# ============================================================

DB_SERVER   = os.getenv("DB_SERVER")
DB_NAME     = os.getenv("DB_NAME")
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

CONNECTION_STRING = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASSWORD};"
    f"TrustServerCertificate=yes;"
)


# ============================================================
# LIGAÇÃO
# ============================================================

def get_connection():
    """
    Cria e devolve uma ligação à base de dados.
    """
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        return conn

    except pyodbc.Error as e:
        print(f"ERRO AO LIGAR À BASE DE DADOS:")
        print(e)
        return None


def test_connection():
    """
    Testa a ligação à base de dados.
    """
    print(f"A ligar a: {DB_SERVER} / {DB_NAME}")

    conn = get_connection()

    if conn is None:
        print("FALHOU — não foi possível ligar à base de dados.")
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        row = cursor.fetchone()
        print(f"LIGAÇÃO OK")
        print(f"SQL Server: {row[0][:80]}")
        return True

    except pyodbc.Error as e:
        print(f"ERRO AO TESTAR LIGAÇÃO:")
        print(e)
        return False

    finally:
        conn.close()


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    test_connection()