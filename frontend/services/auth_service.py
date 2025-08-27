# frontend/services/auth_service.py
import os
from typing import Tuple, Optional, Dict
from dotenv import load_dotenv
import pyodbc

load_dotenv()  # אם ה-.env נמצא ב-backend, אפשר: load_dotenv(os.path.join(os.path.dirname(__file__), "../../backend/.env"))

def _conn_str() -> str:
    return (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={os.getenv('DB_SERVER','Suppliers_Management_System.mssql.somee.com')};"
        f"DATABASE={os.getenv('DB_NAME','Suppliers_Management_System')};"
        f"UID={os.getenv('DB_UID','HadarM_SQLLogin_2')};PWD={os.getenv('DB_PASSWORD','')};"
        "TrustServerCertificate=Yes;"
    )

def _time_norm(t: Optional[str]) -> Optional[str]:
    """קולט 'HH:MM' או 'HH:MM:SS' או None/'' ומחזיר TIME תקין ל-SQL (או None)."""
    if not t:
        return None
    t = t.strip()
    if not t:
        return None
    # אם פורמט HH:MM – נרחיב לשניות
    if len(t) == 5 and t.count(":") == 1:
        return t + ":00"
    return t  # נניח תקין

class AuthService:
    # ---------- LOGIN ----------
    def verify_login(self, username: str, password: str, role: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        try:
            with pyodbc.connect(_conn_str(), timeout=10) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, username, email, company_name, contact_name, phone,
                           city_id, street, house_number, opening_time, closing_time, userType
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
                "company_name": row.company_name,
                "contact_name": row.contact_name,
                "phone": row.phone,
                "city_id": row.city_id,
                "street": row.street,
                "house_number": row.house_number,
                "opening_time": str(row.opening_time) if row.opening_time else None,
                "closing_time": str(row.closing_time) if row.closing_time else None,
                "role": row.userType,
            }
            return True, user, None

        except Exception as e:
            return False, None, f"שגיאת חיבור למסד: {e}"

    # ---------- SIGNUP ----------
    def register_user(self, payload: Dict) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        payload דוגמה:
        {
          username, email, password, userType ('Supplier'|'StoreOwner'),
          companyName, contactName, phone,
          city_id, street, house_number, opening_time, closing_time,
          serviceCities: list[int]  # לרק לספק
        }
        """
        try:
            with pyodbc.connect(_conn_str(), timeout=15) as conn:
                cur = conn.cursor()

                # אימייל ייחודי (אם מולא)
                if payload.get("email"):
                    cur.execute("SELECT COUNT(1) FROM users WHERE email = ?", (payload["email"],))
                    if cur.fetchone()[0] > 0:
                        return False, None, "האימייל כבר בשימוש"

                # שם משתמש ייחודי
                cur.execute("SELECT COUNT(1) FROM users WHERE username = ?", (payload["username"],))
                if cur.fetchone()[0] > 0:
                    return False, None, "שם המשתמש כבר בשימוש"

                # נורמליזציה של שעות
                open_time = _time_norm(payload.get("opening_time"))
                close_time = _time_norm(payload.get("closing_time"))

                # הכנסה ל-users (כולל שדות כתובת/שעות — גם אם None)
                cur.execute("""
                    INSERT INTO users
                        (username, email, password, company_name, contact_name, phone,
                         city_id, street, house_number, opening_time, closing_time, userType)
                    OUTPUT INSERTED.ID
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    payload["username"],
                    payload.get("email"),
                    payload["password"],  # לפרודקשן מומלץ להחליף ל-bcrypt
                    payload.get("companyName"),
                    payload.get("contactName"),
                    payload.get("phone"),
                    payload.get("city_id"),
                    payload.get("street"),
                    payload.get("house_number"),
                    open_time,
                    close_time,
                    payload["userType"],
                ))
                user_id = cur.fetchone()[0]

                # אם ספק: קישור לערים בטבלת supplier_cities
                if payload["userType"] == "Supplier":
                    for cid in payload.get("serviceCities", []):
                        cur.execute("""
                            IF NOT EXISTS (SELECT 1 FROM supplier_cities WHERE supplier_id=? AND city_id=?)
                            INSERT INTO supplier_cities (supplier_id, city_id) VALUES (?, ?)
                        """, (user_id, cid, user_id, cid))

                conn.commit()
                return True, user_id, None

        except Exception as e:
            return False, None, f"שגיאת רישום: {e}"
