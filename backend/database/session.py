# backend/database/session.py
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DB_HOST = os.getenv("DB_HOST", "").strip()
    DB_NAME = os.getenv("DB_NAME", "").strip()
    DB_USER = os.getenv("DB_USER", "").strip()
    DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()
    DB_PORT = os.getenv("DB_PORT", "1433").strip()

    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
        raise RuntimeError("Missing DB env vars (DB_HOST/DB_NAME/DB_USER/DB_PASSWORD). No SQLite fallback.")

    # בחרי 18 אם מותקן אצלך; אחרת החליפי ל-17 בשורה הבאה
    odbc_str = (
        "DRIVER=ODBC Driver 17 for SQL Server;"
        f"SERVER={DB_HOST},{DB_PORT};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=30;"
    )
    DATABASE_URL = "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc_str)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
