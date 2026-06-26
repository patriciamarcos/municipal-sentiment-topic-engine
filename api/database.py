import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

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

def get_connection():
    return pyodbc.connect(CONNECTION_STRING)

FONTE_MAP = {
    "news":     "googlenews",
    "reddit":   "reddit",
    "bluesky":  "bluesky",
    "youtube":  "youtube",
    "facebook": "facebook",
}