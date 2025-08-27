# frontend/services/geo_service.py
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def _conn_str() -> str:
    return (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={os.getenv('DB_SERVER','Suppliers_Management_System.mssql.somee.com')};"
        f"DATABASE={os.getenv('DB_NAME','Suppliers_Management_System')};"
        f"UID={os.getenv('DB_UID','HadarM_SQLLogin_2')};PWD={os.getenv('DB_PASSWORD','')};"
        "TrustServerCertificate=Yes;"
    )

def fetch_districts_with_cities():
    """
    מחזיר מבנה:
    [
      { "district_id": int, "district_name": str, "cities": [ { "city_id": int, "city_name": str }, ... ] },
      ...
    ]
    משתמש ב: districts(id, name_he), cities(id, name_he, district_id)
    """
    out = {}
    sql = """
        SELECT d.id AS district_id, d.name_he AS district_name,
               c.id AS city_id, c.name_he AS city_name
        FROM districts d
        JOIN cities c ON c.district_id = d.id
        ORDER BY d.name_he, c.name_he
    """
    with pyodbc.connect(_conn_str(), timeout=12) as conn:
        cur = conn.cursor()
        cur.execute(sql)
        for did, dname, cid, cname in cur.fetchall():
            out.setdefault(did, {"district_id": did, "district_name": dname, "cities": []})
            out[did]["cities"].append({"city_id": cid, "city_name": cname})
    return list(out.values())
