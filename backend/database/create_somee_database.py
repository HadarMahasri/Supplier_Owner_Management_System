# backend/database/create_somee_database.py
"""
יצירת כל מסד הנתונים דרך Python - כולל טבלאות ונתוני דמו
הפעל מ-VS Code אחרי שיש לך את פרטי החיבור מ-Somee.com
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import urllib.parse

# Add parent directory to path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from backend/.env
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

def get_database_urls():
    """קבלת URL לחיבור SQL Server"""
    db_host = "Suppliers_Management_System.mssql.somee.com"
    db_user = "HadarM_SQLLogin_2"
    db_name = "Suppliers_Management_System"
    
    db_password = os.getenv("DB_PASSWORD")
    if not db_password:
        print("❌ לא נמצאה סיסמה ב-.env")
        return None, None, None
    
    database_url = f"mssql+pyodbc://{db_user}:{db_password}@{db_host}:1433/{db_name}?driver=ODBC+Driver+17+for+SQL+Server"
    
    return None, database_url, db_name

def create_database_if_not_exists():
    """מחובר ישירות ל-DB הקיים"""
    print("🔗 מתחבר למסד הנתונים הקיים...")
    return True  # DB כבר קיים

def create_tables():
    """יצירת כל 9 הטבלאות של הפרויקט"""
    
    try:
        print("📋 יוצר כל 9 הטבלאות...")
        
        import pyodbc
        password = os.getenv('DB_PASSWORD')
        connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=Suppliers_Management_System.mssql.somee.com;DATABASE=Suppliers_Management_System;UID=HadarM_SQLLogin_2;PWD={password}"
        
        conn = pyodbc.connect(connection_string, timeout=30)
        cursor = conn.cursor()
        
        # 1. Districts
        print("  📍 יוצר טבלת districts...")
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='districts' AND xtype='U')
            CREATE TABLE districts (
                id INT IDENTITY(1,1) PRIMARY KEY,
                name_he NVARCHAR(255) NOT NULL UNIQUE,
                name_en NVARCHAR(255) NULL,
                is_active BIT DEFAULT 1
            )
        """)
        
        # 2. Cities
        print("  🏙️ יוצר טבלת cities...")
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cities' AND xtype='U')
            CREATE TABLE cities (
                id INT IDENTITY(1,1) PRIMARY KEY,
                external_id NVARCHAR(64) NULL UNIQUE,
                district_id INT NOT NULL,
                name_he NVARCHAR(255) NOT NULL UNIQUE,
                name_en NVARCHAR(255) NULL,
                is_active BIT DEFAULT 1,
                updated_at DATETIME NULL,
                source NVARCHAR(128) NULL,
                FOREIGN KEY (district_id) REFERENCES districts(id)
            )
        """)
        
        # 3. Users
        print("  👥 יוצר טבלת users...")
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
            CREATE TABLE users (
                id INT IDENTITY(1,1) PRIMARY KEY,
                username NVARCHAR(255) UNIQUE NOT NULL,
                email NVARCHAR(255) UNIQUE NULL,
                password NVARCHAR(255) NOT NULL,
                company_name NVARCHAR(255) NULL,
                contact_name NVARCHAR(255) NULL,
                phone NVARCHAR(20) NULL,
                city_id INT NULL,
                street NVARCHAR(255) NULL,
                house_number NVARCHAR(32) NULL,
                opening_time TIME NULL,
                closing_time TIME NULL,
                userType NVARCHAR(20) NOT NULL CHECK (userType IN ('StoreOwner', 'Supplier')),
                FOREIGN KEY (city_id) REFERENCES cities(id)
            )
        """)
        
        # 4. Products
        print("  📦 יוצר טבלת products...")
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='products' AND xtype='U')
            CREATE TABLE products (
                id INT IDENTITY(1,1) PRIMARY KEY,
                supplier_id INT NOT NULL,
                product_name NVARCHAR(255) NOT NULL,
                unit_price DECIMAL(10, 2) NOT NULL,
                min_quantity INT NOT NULL,
                image_url NVARCHAR(255) DEFAULT NULL,
                FOREIGN KEY (supplier_id) REFERENCES users(id)
            )
        """)
        
        # 5. Orders
        print("  🛒 יוצר טבלת orders...")
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='orders' AND xtype='U')
            CREATE TABLE orders (
                id INT IDENTITY(1,1) PRIMARY KEY,
                owner_id INT NOT NULL,
                status NVARCHAR(20) NOT NULL CHECK (status IN (N'בתהליך', N'הושלמה', N'בוצעה')),
                supplier_id INT NOT NULL,
                created_date DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (owner_id) REFERENCES users(id),
                FOREIGN KEY (supplier_id) REFERENCES users(id)
            )
        """)
        
        # 6. Order Items  
        print("  📋 יוצר טבלת order_items...")
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='order_items' AND xtype='U')
            CREATE TABLE order_items (
                id INT IDENTITY(1,1) PRIMARY KEY,
                product_id INT NOT NULL,
                order_id INT NOT NULL,
                quantity INT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)
        
        # 7. Supplier Cities
        print("  🔗 יוצר טבלת supplier_cities...")
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='supplier_cities' AND xtype='U')
            CREATE TABLE supplier_cities (
                supplier_id INT NOT NULL,
                city_id INT NOT NULL,
                PRIMARY KEY (supplier_id, city_id),
                FOREIGN KEY (supplier_id) REFERENCES users(id),
                FOREIGN KEY (city_id) REFERENCES cities(id)
            )
        """)
        
        # 8. Supplier Districts
        print("  🔗 יוצר טבלת supplier_districts...")
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='supplier_districts' AND xtype='U')
            CREATE TABLE supplier_districts (
                supplier_id INT NOT NULL,
                district_id INT NOT NULL,
                PRIMARY KEY (supplier_id, district_id),
                FOREIGN KEY (supplier_id) REFERENCES users(id),
                FOREIGN KEY (district_id) REFERENCES districts(id)
            )
        """)
        
        # 9. Owner Supplier Links
        print("  🤝 יוצר טבלת owner_supplier_links...")
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='owner_supplier_links' AND xtype='U')
            CREATE TABLE owner_supplier_links (
                owner_id INT NOT NULL,
                supplier_id INT NOT NULL,
                status NVARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING','APPROVED','REJECTED')),
                created_at DATETIME DEFAULT GETDATE(),
                updated_at DATETIME NULL,
                PRIMARY KEY (owner_id, supplier_id),
                FOREIGN KEY (owner_id) REFERENCES users(id),
                FOREIGN KEY (supplier_id) REFERENCES users(id)
            )
        """)
        
        conn.commit()
        conn.close()
        
        print("✅ כל 9 הטבלאות נוצרו בהצלחה!")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה ביצירת טבלאות: {e}")
        return False

def insert_demo_data():
    """הוספת נתוני דמו מלאים לכל 9 הטבלאות"""
    
    try:
        print("📊 מוסיף נתוני דמו לכל הטבלאות...")
        
        import pyodbc
        password = os.getenv('DB_PASSWORD')
        connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=Suppliers_Management_System.mssql.somee.com;DATABASE=Suppliers_Management_System;UID=HadarM_SQLLogin_2;PWD={password}"
        
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        
        # 1. מחוזות
        print("  📍 מוסיף מחוזות...")
        districts = [
            ('מחוז המרכז', 'Central District'),
            ('מחוז תל אביב', 'Tel Aviv District'),
            ('מחוז ירושלים', 'Jerusalem District'),
            ('מחוז הצפון', 'Northern District'),
            ('מחוז הדרום', 'Southern District')
        ]
        
        for hebrew_name, english_name in districts:
            cursor.execute(f"""
                IF NOT EXISTS (SELECT * FROM districts WHERE name_he = N'{hebrew_name}')
                INSERT INTO districts (name_he, name_en, is_active) VALUES (N'{hebrew_name}', '{english_name}', 1)
            """)
        
        # 2. ערים
        print("  🏙️ מוסיף ערים...")
        cities = [
                    (1, 'פתח תקווה', 'Petah Tikva'),
                    (1, 'רמת גן', 'Ramat Gan'),
                    (1, 'בני ברק', 'Bnei Brak'),
                    (2, 'תל אביב', 'Tel Aviv'),
                    (2, 'רמת השרון', 'Ramat Hasharon'),
                    (3, 'ירושלים', 'Jerusalem'),
                    (3, 'בית שמש', 'Beit Shemesh'),
                    (4, 'חיפה', 'Haifa'),
                    (4, 'נצרת', 'Nazareth'),
                    (5, 'באר שבע', 'Beer Sheva'),
                    (5, 'אשדוד', 'Ashdod')
        ]
        
        for district_id, hebrew_name, english_name in cities:
            cursor.execute(f"""
                IF NOT EXISTS (SELECT * FROM cities WHERE name_he = N'{hebrew_name}')
                INSERT INTO cities (district_id, name_he, name_en, is_active) 
                VALUES ({district_id}, N'{hebrew_name}', '{english_name}', 1)
            """)
        
        # 3. ספקים
        print("  🏢 מוסיף ספקים...")
        suppliers = [
            ('supplier_catering', 'info@golden-catering.co.il', 'קייטרינג גולדן', 'יוסי כהן', '03-1234567', 4, 'רחוב הרצל', '45', '08:00:00', '18:00:00'),
            ('supplier_tech', 'contact@tech-tomorrow.co.il', 'טכנולוגיות המחר', 'דני לוי', '03-9999999', 4, 'הארבעה', '7', '09:00:00', '17:00:00'),
            ('supplier_construction', 'david@build-expert.co.il', 'מומחה בנייה דוד', 'דוד אברהם', '04-5555555', 8, 'שדרות הנשיא', '30', '07:00:00', '16:00:00'),
            ('supplier_office', 'office@office-plus.co.il', 'משרד פלוס', 'מיכל רוזן', '09-8888888', 1, 'רחוב התעשייה', '25', '08:30:00', '17:30:00'),
            ('supplier_logistics', 'info@fast-delivery.co.il', 'הובלות זריזות', 'אבי שמיר', '052-1234567', 10, 'כביש 1', '10', '06:00:00', '22:00:00')
        ]
        
        for username, email, company, contact, phone, city_id, street, house, open_time, close_time in suppliers:
            cursor.execute(f"""
                IF NOT EXISTS (SELECT * FROM users WHERE username = '{username}')
                INSERT INTO users (username, email, password, company_name, contact_name, phone, city_id, street, house_number, opening_time, closing_time, userType)
                VALUES ('{username}', '{email}', 'hashed_password', N'{company}', N'{contact}', '{phone}', {city_id}, N'{street}', '{house}', '{open_time}', '{close_time}', 'Supplier')
            """)
        
        # 4. בעלי חנויות (StoreOwners)
        print("  🏪 מוסיף בעלי חנויות...")
        store_owners = [
            ('store_owner1', 'manager@mystore.co.il', 'החנות שלי', 'רונית מנהלת', '03-5555555', 4),
            ('store_owner2', 'admin@supermarket.co.il', 'סופר מרקט ירושלים', 'משה בעלים', '02-6666666', 6)
        ]
        
        for username, email, company, contact, phone, city_id in store_owners:
            cursor.execute(f"""
                IF NOT EXISTS (SELECT * FROM users WHERE username = '{username}')
                INSERT INTO users (username, email, password, company_name, contact_name, phone, city_id, userType)
                VALUES ('{username}', '{email}', 'hashed_password', N'{company}', N'{contact}', '{phone}', {city_id}, 'StoreOwner')
            """)
        
        # 5. מוצרים
        print("  📦 מוסיף מוצרים...")
        products = [
            # קייטרינג גולדן
            ('supplier_catering', 'מגש כיבודי תבשילים גדול', 120.00, 5),
            ('supplier_catering', 'קינוח פירות העונה', 45.50, 10),
            ('supplier_catering', 'מגש סושי מעורב', 180.00, 3),
            
            # טכנולוגיות המחר
            ('supplier_tech', 'מחשב נייד Dell Latitude', 3500.00, 1),
            ('supplier_tech', 'עכבר אלחוטי Logitech', 85.00, 10),
            ('supplier_tech', 'מסך 27 אינץ 4K', 1200.00, 1),
            
            # בנייה דוד
            ('supplier_construction', 'שק צמנט 50 קילו', 25.00, 50),
            ('supplier_construction', 'בלוק בטון 20x20x40', 8.50, 100),
            
            # משרד פלוס
            ('supplier_office', 'כיסא משרדי ארגונומי', 850.00, 2),
            ('supplier_office', 'שולחן עבודה 160x80', 1200.00, 1),
            
            # הובלות זריזות
            ('supplier_logistics', 'שירות הובלה עד 500 קילו', 150.00, 1),
            ('supplier_logistics', 'שירות הובלה עד 1 טון', 280.00, 1)
        ]
        
        for supplier_username, product_name, price, min_qty in products:
            cursor.execute(f"""
                DECLARE @supplier_id INT = (SELECT id FROM users WHERE username = '{supplier_username}')
                IF @supplier_id IS NOT NULL AND NOT EXISTS (SELECT * FROM products WHERE supplier_id = @supplier_id AND product_name = N'{product_name}')
                INSERT INTO products (supplier_id, product_name, unit_price, min_quantity)
                VALUES (@supplier_id, N'{product_name}', {price}, {min_qty})
            """)
        
        # 6. חיבור ספקים לערים (supplier_cities)
        print("  🔗 מחבר ספקים לערים...")
        supplier_city_connections = [
            ('supplier_catering', [4, 1, 2, 3]),  # תל אביב, פתח תקווה, רמת גן, בני ברק
            ('supplier_tech', [4, 1, 2]),         # תל אביב, פתח תקווה, רמת גן
            ('supplier_construction', [8, 9]),    # חיפה, נצרת
            ('supplier_office', [1, 2, 4]),       # פתח תקווה, רמת גן, תל אביב
            ('supplier_logistics', [1, 2, 3, 4, 6, 8, 10, 11])  # כל הערים
        ]
        
        for supplier_username, city_ids in supplier_city_connections:
            for city_id in city_ids:
                cursor.execute(f"""
                    DECLARE @supplier_id INT = (SELECT id FROM users WHERE username = '{supplier_username}')
                    IF @supplier_id IS NOT NULL AND NOT EXISTS (SELECT * FROM supplier_cities WHERE supplier_id = @supplier_id AND city_id = {city_id})
                    INSERT INTO supplier_cities (supplier_id, city_id) VALUES (@supplier_id, {city_id})
                """)
        
        # 7. חיבור ספקים למחוזות (supplier_districts)
        print("  🔗 מחבר ספקים למחוזות...")
        supplier_district_connections = [
            ('supplier_catering', [1, 2]),      # מרכז, תל אביב
            ('supplier_tech', [1, 2]),          # מרכז, תל אביב
            ('supplier_construction', [4]),     # צפון
            ('supplier_office', [1]),           # מרכז
            ('supplier_logistics', [1, 2, 3, 4, 5])  # כל המחוזות
        ]
        
        for supplier_username, district_ids in supplier_district_connections:
            for district_id in district_ids:
                cursor.execute(f"""
                    DECLARE @supplier_id INT = (SELECT id FROM users WHERE username = '{supplier_username}')
                    IF @supplier_id IS NOT NULL AND NOT EXISTS (SELECT * FROM supplier_districts WHERE supplier_id = @supplier_id AND district_id = {district_id})
                    INSERT INTO supplier_districts (supplier_id, district_id) VALUES (@supplier_id, {district_id})
                """)
        
        # 8. קישורי אישור בין בעלי חנויות לספקים (owner_supplier_links)
        print("  🤝 מוסיף קישורי אישור...")
        cursor.execute("""
            DECLARE @owner1 INT = (SELECT id FROM users WHERE username = 'store_owner1')
            DECLARE @owner2 INT = (SELECT id FROM users WHERE username = 'store_owner2')
            DECLARE @supplier1 INT = (SELECT id FROM users WHERE username = 'supplier_catering')
            DECLARE @supplier2 INT = (SELECT id FROM users WHERE username = 'supplier_tech')
            
            IF @owner1 IS NOT NULL AND @supplier1 IS NOT NULL AND NOT EXISTS (SELECT * FROM owner_supplier_links WHERE owner_id = @owner1 AND supplier_id = @supplier1)
            INSERT INTO owner_supplier_links (owner_id, supplier_id, status) VALUES (@owner1, @supplier1, 'APPROVED')
            
            IF @owner1 IS NOT NULL AND @supplier2 IS NOT NULL AND NOT EXISTS (SELECT * FROM owner_supplier_links WHERE owner_id = @owner1 AND supplier_id = @supplier2)
            INSERT INTO owner_supplier_links (owner_id, supplier_id, status) VALUES (@owner1, @supplier2, 'PENDING')
        """)
        
        # 9. הזמנות דמו
        print("  🛒 מוסיף הזמנות דמו...")
        cursor.execute("""
            DECLARE @owner1 INT = (SELECT id FROM users WHERE username = 'store_owner1')
            DECLARE @supplier1 INT = (SELECT id FROM users WHERE username = 'supplier_catering')
            DECLARE @supplier2 INT = (SELECT id FROM users WHERE username = 'supplier_tech')
            
            IF @owner1 IS NOT NULL AND @supplier1 IS NOT NULL AND NOT EXISTS (SELECT * FROM orders WHERE owner_id = @owner1 AND supplier_id = @supplier1)
            INSERT INTO orders (owner_id, supplier_id, status) VALUES (@owner1, @supplier1, N'בתהליך')
            
            IF @owner1 IS NOT NULL AND @supplier2 IS NOT NULL
            INSERT INTO orders (owner_id, supplier_id, status) VALUES (@owner1, @supplier2, N'הושלמה')
        """)
        
        # 10. פריטי הזמנה
        print("  📋 מוסיף פריטי הזמנה...")
        cursor.execute("""
            DECLARE @order1 INT = (SELECT TOP 1 id FROM orders WHERE status = N'בתהליך')
            DECLARE @product1 INT = (SELECT id FROM products WHERE product_name = N'מגש כיבודי תבשילים גדול')
            
            IF @order1 IS NOT NULL AND @product1 IS NOT NULL AND NOT EXISTS (SELECT * FROM order_items WHERE order_id = @order1 AND product_id = @product1)
            INSERT INTO order_items (product_id, order_id, quantity) VALUES (@product1, @order1, 2)
        """)
        
        conn.commit()
        conn.close()
        
        print("✅ נתוני הדמו המלאים נוספו לכל הטבלאות!")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בהוספת נתוני דמו: {e}")
        return False

def show_summary():
    """הצגת סיכום מסד הנתונים"""
    server_url, database_url, db_name = get_database_urls()
    
    if not database_url:
        return
    
    try:
        print("\n📊 סיכום מסד הנתונים:")
        engine = create_engine(database_url, echo=False)
        
        with engine.connect() as connection:
            
            # ספירת רשומות בכל טבלה
            tables_data = [
                ("districts", "מחוזות"),
                ("cities", "ערים"), 
                ("users", "משתמשים"),
                ("products", "מוצרים"),
                ("orders", "הזמנות"),
                ("order_items", "פריטי הזמנה")
            ]
            
            for table_name, hebrew_name in tables_data:
                try:
                    result = connection.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.fetchone()[0]
                    print(f"  {hebrew_name}: {count}")
                except:
                    print(f"  {hebrew_name}: שגיאה בקריאה")
            
            # הצגת ספקים
            print("\n🏢 ספקים במערכת:")
            try:
                result = connection.execute(text("""
                    SELECT u.company_name, c.name_he, u.phone 
                    FROM users u 
                    LEFT JOIN cities c ON u.city_id = c.id 
                    WHERE u.userType = 'Supplier'
                """))
                
                for row in result:
                    company = row[0] or "ללא שם"
                    city = row[1] or "ללא עיר" 
                    phone = row[2] or "ללא טלפון"
                    print(f"  • {company} - {city} ({phone})")
                    
            except Exception as e:
                print(f"  שגיאה בקריאת ספקים: {e}")
                
    except Exception as e:
        print(f"❌ שגיאה בהצגת סיכום: {e}")

def main():
    """פונקציה ראשית"""
    print("🚀 מתחיל יצירת מסד נתונים ב-Somee.com...")
    print("=" * 60)
    
    # שלב 1: יצירת DB
    if not create_database_if_not_exists():
        print("❌ נכשל ביצירת מסד הנתונים")
        return
    
    # שלב 2: יצירת טבלאות
    if not create_tables():
        print("❌ נכשל ביצירת טבלאות")
        return
    
    # שלב 3: הוספת נתוני דמו
    if not insert_demo_data():
        print("❌ נכשל בהוספת נתוני דמו")
        return
    
    # סיכום
    show_summary()
    
    print("\n" + "=" * 60)
    print("🎉 מסד הנתונים נוצר בהצלחה!")
    print("📋 השלב הבא: הפעל את השרת עם: python main.py")
    print("🖥️ ואז את ה-Frontend עם: cd frontend && python main.py")

if __name__ == "__main__":
    main()