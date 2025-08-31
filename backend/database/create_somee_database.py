# backend/database/create_somee_database.py
"""
יצירה/שדרוג מסד הנתונים ל-SQL Server (Somee):
- יוצר את כלל הטבלאות הדרושות לפרויקט.
- דואג לשדרוג טבלת products עם stock + is_active.
- מוסיף נתוני דמו בסיסיים (אופציונלי).
- מציג סיכום מצב מסד הנתונים.

להרצה:
    python -m backend.database.create_somee_database
או:
    python backend/database/create_somee_database.py
"""

import os
import sys
from typing import Iterable
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# לאפשר ייבוא יחסי מחבילות backend/*
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# טעינת משתני סביבה
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

SOMEE_HOST = "Suppliers_Management_System.mssql.somee.com"
SOMEE_DB   = "Suppliers_Management_System"
SOMEE_USER = "HadarM_SQLLogin_2"
SOMEE_DSN  = "ODBC Driver 17 for SQL Server"


def _pyodbc_conn():
    import pyodbc
    pwd = os.getenv("DB_PASSWORD")
    if not pwd:
        raise RuntimeError("לא נמצאה סיסמה ב-.env (מפתח DB_PASSWORD)")
    conn_str = (
        f"DRIVER={{{SOMEE_DSN}}};SERVER={SOMEE_HOST};DATABASE={SOMEE_DB};"
        f"UID={SOMEE_USER};PWD={pwd}"
    )
    return pyodbc.connect(conn_str, timeout=30)


def _alchemy_engine():
    pwd = os.getenv("DB_PASSWORD")
    if not pwd:
        raise RuntimeError("לא נמצאה סיסמה ב-.env (מפתח DB_PASSWORD)")
    url = (
        f"mssql+pyodbc://{SOMEE_USER}:{pwd}@{SOMEE_HOST}:1433/{SOMEE_DB}"
        f"?driver={SOMEE_DSN.replace(' ', '+')}"
    )
    return create_engine(url, echo=False, future=True)


def create_database_if_not_exists() -> bool:
    # ב-Somee כבר יש DB; נוודא רק חיבור
    print("🔗 בדיקת חיבור למסד הנתונים הקיים...")
    try:
        with _pyodbc_conn() as _:
            pass
        print("✅ חיבור תקין.")
        return True
    except Exception as e:
        print(f"❌ חיבור נכשל: {e}")
        return False


def _exec_many(cursor, stmts: Iterable[str]):
    for s in stmts:
        cursor.execute(s)


def create_tables() -> bool:
    """
    יוצר את כלל הטבלאות אם חסרות, ומשדרג products עם stock + is_active במקרה הצורך.
    התאמה מלאה לשדות שבהם משתמשים ב-router וב-ORM model. 
    """
    try:
        print("📋 יצירה/שדרוג טבלאות...")
        conn = _pyodbc_conn()
        cur  = conn.cursor()

        # 1) DISTRICTS
        cur.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='districts' AND xtype='U')
        CREATE TABLE [dbo].[districts](
            id INT IDENTITY(1,1) PRIMARY KEY,
            name_he  NVARCHAR(255) NOT NULL UNIQUE,
            name_en  NVARCHAR(255) NULL,
            is_active BIT NOT NULL DEFAULT 1
        )""")

        # 2) CITIES
        cur.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cities' AND xtype='U')
        CREATE TABLE [dbo].[cities](
            id INT IDENTITY(1,1) PRIMARY KEY,
            external_id NVARCHAR(64) NULL UNIQUE,
            district_id INT NOT NULL,
            name_he  NVARCHAR(255) NOT NULL UNIQUE,
            name_en  NVARCHAR(255) NULL,
            is_active BIT NOT NULL DEFAULT 1,
            updated_at DATETIME NULL,
            source NVARCHAR(128) NULL,
            FOREIGN KEY (district_id) REFERENCES districts(id)
        )""")

        # 3) USERS
        cur.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
        CREATE TABLE [dbo].[users](
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(255) UNIQUE NOT NULL,
            email    NVARCHAR(255) UNIQUE NULL,
            password NVARCHAR(255) NOT NULL,
            company_name NVARCHAR(255) NULL,
            contact_name NVARCHAR(255) NULL,
            phone NVARCHAR(20) NULL,
            city_id INT NULL,
            street NVARCHAR(255) NULL,
            house_number NVARCHAR(32) NULL,
            opening_time TIME NULL,
            closing_time TIME NULL,
            userType NVARCHAR(20) NOT NULL CHECK (userType IN ('StoreOwner','Supplier')),
            FOREIGN KEY (city_id) REFERENCES cities(id)
        )""")

        # 4) PRODUCTS  (חשוב: תואם לשימוש ב-router ובמודל ה-ORM) 
        # fields: id, supplier_id, product_name, unit_price, min_quantity, image_url, stock, is_active
        cur.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='products' AND xtype='U')
        CREATE TABLE [dbo].[products](
            id INT IDENTITY(1,1) PRIMARY KEY,
            supplier_id  INT NOT NULL,
            product_name NVARCHAR(255) NOT NULL,
            unit_price   DECIMAL(10,2) NOT NULL,
            min_quantity INT NOT NULL,
            image_url    NVARCHAR(255) NULL,
            stock        INT NOT NULL DEFAULT 0,
            is_active    BIT NOT NULL DEFAULT 1,
            FOREIGN KEY (supplier_id) REFERENCES users(id)
        )""")

        # שדרוג products קיימת – הוספת stock / is_active אם חסר
        _exec_many(cur, (
            """
            IF NOT EXISTS (
                SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='products' AND COLUMN_NAME='stock'
            )
            ALTER TABLE [dbo].[products] ADD stock INT NOT NULL DEFAULT 0
            """,
            """
            IF NOT EXISTS (
                SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='products' AND COLUMN_NAME='is_active'
            )
            ALTER TABLE [dbo].[products] ADD is_active BIT NOT NULL DEFAULT 1
            """,
        ))

        # 5) ORDERS
        cur.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='orders' AND xtype='U')
        CREATE TABLE [dbo].[orders](
            id INT IDENTITY(1,1) PRIMARY KEY,
            owner_id INT NOT NULL,
            status NVARCHAR(20) NOT NULL CHECK (status IN (N'בתהליך', N'הושלמה', N'בוצעה')),
            supplier_id INT NOT NULL,
            created_date DATETIME DEFAULT GETDATE(),
            FOREIGN KEY (owner_id) REFERENCES users(id),
            FOREIGN KEY (supplier_id) REFERENCES users(id)
        )""")

        # 6) ORDER_ITEMS
        cur.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='order_items' AND xtype='U')
        CREATE TABLE [dbo].[order_items](
            id INT IDENTITY(1,1) PRIMARY KEY,
            product_id INT NOT NULL,
            order_id   INT NOT NULL,
            quantity   INT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (order_id)   REFERENCES orders(id)
        )""")

        # 7) SUPPLIER_CITIES
        cur.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='supplier_cities' AND xtype='U')
        CREATE TABLE [dbo].[supplier_cities](
            supplier_id INT NOT NULL,
            city_id     INT NOT NULL,
            PRIMARY KEY (supplier_id, city_id),
            FOREIGN KEY (supplier_id) REFERENCES users(id),
            FOREIGN KEY (city_id)     REFERENCES cities(id)
        )""")

        # 8) SUPPLIER_DISTRICTS
        cur.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='supplier_districts' AND xtype='U')
        CREATE TABLE [dbo].[supplier_districts](
            supplier_id INT NOT NULL,
            district_id INT NOT NULL,
            PRIMARY KEY (supplier_id, district_id),
            FOREIGN KEY (supplier_id) REFERENCES users(id),
            FOREIGN KEY (district_id) REFERENCES districts(id)
        )""")

        # 9) OWNER_SUPPLIER_LINKS
        cur.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='owner_supplier_links' AND xtype='U')
        CREATE TABLE [dbo].[owner_supplier_links](
            owner_id    INT NOT NULL,
            supplier_id INT NOT NULL,
            status NVARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING','APPROVED','REJECTED')),
            created_at DATETIME DEFAULT GETDATE(),
            updated_at DATETIME NULL,
            PRIMARY KEY (owner_id, supplier_id),
            FOREIGN KEY (owner_id)    REFERENCES users(id),
            FOREIGN KEY (supplier_id) REFERENCES users(id)
        )""")

        conn.commit()
        conn.close()
        print("✅ טבלאות נוצרו/שודרגו בהצלחה.")
        return True

    except Exception as e:
        print(f"❌ שגיאה ביצירה/שדרוג: {e}")
        return False


def insert_demo_data() -> bool:
    """נתוני דמו קצרים – רק אם חסר (Idempotent)."""
    try:
        print("📊 הוספת דמו...")
        conn = _pyodbc_conn()
        cur  = conn.cursor()

        # מחוזות (דוגמה קצרה)
        cur.execute("""
        IF NOT EXISTS (SELECT 1 FROM districts WHERE name_he = N'מחוז המרכז')
        INSERT INTO districts (name_he, name_en, is_active) VALUES (N'מחוז המרכז', 'Central District', 1)
        """)

        # ספק לדוגמה
        cur.execute("""
        IF NOT EXISTS (SELECT 1 FROM users WHERE username='supplier_demo')
        INSERT INTO users (username, email, password, company_name, contact_name, phone, userType)
        VALUES ('supplier_demo', 'demo@suppliers.co', 'hashed', N'ספק דמו', N'דני דמו', '03-0000000', 'Supplier')
        """)

        # מוצר לדוגמה (stock=0 ברירת מחדל)
        cur.execute("""
        DECLARE @sid INT = (SELECT id FROM users WHERE username='supplier_demo');
        IF @sid IS NOT NULL AND NOT EXISTS (SELECT 1 FROM products WHERE supplier_id=@sid AND product_name=N'מוצר דמו')
        INSERT INTO products (supplier_id, product_name, unit_price, min_quantity, image_url)
        VALUES (@sid, N'מוצר דמו', 12.90, 1, NULL)
        """)

        conn.commit()
        conn.close()
        print("✅ דמו הוסף/עודכן.")
        return True
    except Exception as e:
        print(f"❌ שגיאה בדמו: {e}")
        return False


def show_summary():
    """הצגת סיכום קצר (counts + רשימת ספקים)."""
    try:
        print("\n📈 סיכום DB:")
        eng = _alchemy_engine()
        with eng.connect() as c:
            for table, label in (
                ("districts", "מחוזות"),
                ("cities", "ערים"),
                ("users", "משתמשים"),
                ("products", "מוצרים"),
                ("orders", "הזמנות"),
                ("order_items", "פריטי הזמנה"),
            ):
                try:
                    cnt = c.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
                    print(f"  {label}: {cnt}")
                except Exception:
                    print(f"  {label}: שגיאה בקריאה")

            print("\n🏢 ספקים:")
            try:
                res = c.execute(text("""
                    SELECT TOP 5 u.company_name, u.phone
                    FROM users u
                    WHERE u.userType='Supplier'
                    ORDER BY u.id DESC
                """))
                for row in res:
                    name = row[0] or "ללא שם"
                    phone = row[1] or "-"
                    print(f"  • {name} ({phone})")
            except Exception as e:
                print(f"  שגיאה בקריאת ספקים: {e}")
    except Exception as e:
        print(f"❌ שגיאה בסיכום: {e}")


def main():
    print("🚀 התחלת תהליך יצירת/שדרוג DB (Somee)")
    print("=" * 60)

    if not create_database_if_not_exists():
        return
    if not create_tables():
        return
    insert_demo_data()
    show_summary()

    print("\n🎉 הסתיים. אפשר להפעיל את השרת FastAPI ולבדוק את ה-API.")


if __name__ == "__main__":
    main()
