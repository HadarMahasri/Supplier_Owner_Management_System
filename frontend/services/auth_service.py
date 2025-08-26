# frontend/services/auth_service.py
import os
from typing import Tuple, Optional, Dict, Iterable
from dotenv import load_dotenv

# טוען .env; אם הוא ב-backend, צייני נתיב מפורש:
load_dotenv()  # או: load_dotenv(os.path.join(os.path.dirname(__file__), "../../backend/.env"))

import pyodbc

def _conn_str() -> str:
    uid = os.getenv("DB_UID", "HadarM_SQLLogin_2")
    pwd = os.getenv("DB_PASSWORD", "")
    server = os.getenv("DB_SERVER", "Suppliers_Management_System.mssql.somee.com")
    db = os.getenv("DB_NAME", "Suppliers_Management_System")
    return (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={server};DATABASE={db};UID={uid};PWD={pwd};TrustServerCertificate=Yes;"
    )

class AuthService:
    """לוגיקת אימות/הרשמה מול מסד Somee (SQL Server)"""

    # ---- LOGIN ----
    def verify_login(self, username: str, password: str, role: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        try:
            with pyodbc.connect(_conn_str(), timeout=10) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, username, email, company_name, contact_name, userType
                    FROM users
                    WHERE username=? AND password=?
                """, (username, password))
                row = cur.fetchone()
            if not row:
                return False, None, "שם משתמש או סיסמה שגויים"
            if str(row.userType) != role:
                return False, None, "התפקיד שנבחר אינו תואם למשתמש"
            user = {
                "id": row.id,
                "username": row.username,
                "email": row.email,
                "company_name": getattr(row, "company_name", None),
                "contact_name": getattr(row, "contact_name", None),
                "role": row.userType,
            }
            return True, user, None
        except Exception as e:
            return False, None, f"שגיאת חיבור למסד: {e}"

    # ---- SIGNUP ----
    def register_user(self, payload: Dict) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        payload: {
          username, email, password, userType ('Supplier'|'StoreOwner'),
          companyName?, contactName, phone,
          city_id?, street?, house_number?, opening_time?, closing_time?,
          serviceCities?: list[int]   # לספק
        }
        """
        try:
            with pyodbc.connect(_conn_str(), timeout=15) as conn:
                cur = conn.cursor()

                # אימייל ייחודי?
                cur.execute("SELECT COUNT(1) FROM users WHERE email=?", (payload["email"],))
                if cur.fetchone()[0] > 0:
                    return False, None, "האימייל כבר בשימוש"

                # יצירת משתמש
                cur.execute("""
                    INSERT INTO users (username, email, password, company_name, contact_name, phone, userType)
                    OUTPUT INSERTED.ID
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    payload["username"], payload["email"], payload["password"],
                    payload.get("companyName"), payload["contactName"], payload["phone"], payload["userType"]
                ))
                user_id = cur.fetchone()[0]

                if payload["userType"] == "StoreOwner":
                    # טבלת חנויות (דוגמה)
                    cur.execute("""
                        INSERT INTO stores (user_id, city_id, street, house_number, opening_time, closing_time)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (user_id, payload["city_id"], payload["street"], payload["house_number"],
                          payload["opening_time"], payload["closing_time"]))

                elif payload["userType"] == "Supplier":
                    # קישור ערי שירות (דוגמה לטבלת many-to-many)
                    for cid in payload.get("serviceCities", []):
                        cur.execute("""
                            INSERT INTO supplier_service_cities (user_id, city_id) VALUES (?, ?)
                        """, (user_id, cid))

                conn.commit()
                return True, user_id, None

        except Exception as e:
            return False, None, f"שגיאת רישום: {e}"
