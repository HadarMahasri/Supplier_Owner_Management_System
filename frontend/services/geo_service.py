# frontend/services/geo_service.py
import pyodbc, os
from dotenv import load_dotenv
load_dotenv()

def _conn_str() -> str:
    uid = os.getenv("DB_UID", "HadarM_SQLLogin_2")
    pwd = os.getenv("DB_PASSWORD", "")
    server = os.getenv("DB_SERVER", "Suppliers_Management_System.mssql.somee.com")
    db = os.getenv("DB_NAME", "Suppliers_Management_System")
    return (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={server};DATABASE={db};UID={uid};PWD={pwd};TrustServerCertificate=Yes;"
    )

def fetch_districts_with_cities():
    """מחזיר [{district_id, district_name, cities:[{city_id, city_name}]}]"""
    out = {}
    with pyodbc.connect(_conn_str(), timeout=10) as conn:
        cur = conn.cursor()
        # עדכני לשמות הטבלאות/עמודות אצלך
        cur.execute("""
            SELECT d.id as district_id, d.name as district_name, c.id as city_id, c.name as city_name
            FROM districts d
            JOIN cities c ON c.district_id = d.id
            ORDER BY d.name, c.name
        """)
        for district_id, district_name, city_id, city_name in cur.fetchall():
            out.setdefault(district_id, {"district_id": district_id, "district_name": district_name, "cities": []})
            out[district_id]["cities"].append({"city_id": city_id, "city_name": city_name})
    return list(out.values())
