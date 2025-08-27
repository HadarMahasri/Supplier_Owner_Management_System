# backend/database/seed_more_israel_cities.py
import os
import pyodbc
from dotenv import load_dotenv

# טוען סיסמה מ-backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

def conn_str():
    return (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=Suppliers_Management_System.mssql.somee.com;"
        "DATABASE=Suppliers_Management_System;"
        f"UID={os.getenv('DB_UID','HadarM_SQLLogin_2')};PWD={os.getenv('DB_PASSWORD','')};"
        "TrustServerCertificate=Yes;"
    )

# מיפוי מחוזות לפי ה-IDs שנוצרו אצלך
CENTRAL   = 1  # מחוז המרכז
TEL_AVIV  = 2  # מחוז תל אביב
JERUSALEM = 3  # מחוז ירושלים
NORTH     = 4  # מחוז הצפון
SOUTH     = 5  # מחוז הדרום

# רשימה רחבה של ערים (אפשר להרחיב/לשנות לפי הצורך)
SEED = [
    # מרכז (1)
    (CENTRAL,  "כפר סבא",      "Kfar Saba"),
    (CENTRAL,  "רעננה",        "Ra'anana"),
    (CENTRAL,  "הוד השרון",    "Hod HaSharon"),
    (CENTRAL,  "נתניה",        "Netanya"),
    (CENTRAL,  "ראש העין",     "Rosh HaAyin"),
    (CENTRAL,  "גבעת שמואל",   "Giv'at Shmuel"),
    (CENTRAL,  "מודיעין-מכבים-רעות", "Modiin-Maccabim-Reut"),
    (CENTRAL,  "לוד",          "Lod"),
    (CENTRAL,  "רמלה",         "Ramla"),
    (CENTRAL,  "רחובות",       "Rehovot"),
    (CENTRAL,  "נס ציונה",     "Ness Ziona"),
    (CENTRAL,  "גבעתיים",      "Giv'atayim"),
    (CENTRAL,  "ראשון לציון",  "Rishon LeZion"),
    (CENTRAL,  "קריית אונו",   "Kiryat Ono"),
    (CENTRAL,  "יהוד-מונוסון", "Yehud-Monosson"),

    # תל אביב (2)
    (TEL_AVIV, "חולון",        "Holon"),
    (TEL_AVIV, "בת ים",        "Bat Yam"),
    (TEL_AVIV, "הרצליה",      "Herzliya"),
    (TEL_AVIV, "אור יהודה",   "Or Yehuda"),
    (TEL_AVIV, "תל אביב-יפו", "Tel Aviv-Yafo"),

    # ירושלים (3)
    (JERUSALEM, "מעלה אדומים", "Ma'ale Adumim"),
    (JERUSALEM, "ביתר עילית",  "Beitar Illit"),
    (JERUSALEM, "אבו גוש",     "Abu Ghosh"),
    (JERUSALEM, "גבעת זאב",    "Giv'at Ze'ev"),

    # צפון (4)
    (NORTH, "נהריה",           "Nahariya"),
    (NORTH, "עכו",             "Akko"),
    (NORTH, "טבריה",           "Tiberias"),
    (NORTH, "צפת",             "Safed"),
    (NORTH, "קריית שמונה",     "Kiryat Shmona"),
    (NORTH, "יקנעם עילית",     "Yokneam Illit"),
    (NORTH, "מגדל העמק",       "Migdal HaEmek"),
    (NORTH, "נוף הגליל",       "Nof HaGalil"),
    (NORTH, "עפולה",           "Afula"),
    (NORTH, "כרמיאל",          "Karmiel"),
    (NORTH, "קריית אתא",       "Kiryat Ata"),
    (NORTH, "קריית ים",        "Kiryat Yam"),
    (NORTH, "קריית מוצקין",    "Kiryat Motzkin"),
    (NORTH, "טירת כרמל",       "Tirat Carmel"),

    # דרום (5)
    (SOUTH, "אשקלון",          "Ashkelon"),
    (SOUTH, "אילת",            "Eilat"),
    (SOUTH, "קריית גת",        "Kiryat Gat"),
    (SOUTH, "קריית מלאכי",     "Kiryat Malakhi"),
    (SOUTH, "דימונה",          "Dimona"),
    (SOUTH, "ירוחם",           "Yeruham"),
    (SOUTH, "שדרות",           "Sderot"),
    (SOUTH, "נתיבות",          "Netivot"),
    (SOUTH, "אופקים",          "Ofakim"),
    (SOUTH, "רהט",             "Rahat"),
    (SOUTH, "להבים",           "Lehavim"),
]

def main():
    pw = os.getenv("DB_PASSWORD")
    if not pw:
        print("❌ חסרה סיסמה ב-.env (DB_PASSWORD)")
        return

    with pyodbc.connect(conn_str(), timeout=20) as conn:
        cur = conn.cursor()
        print("🏙️ מוסיף/משלים ערים לטבלת cities ...")
        for district_id, name_he, name_en in SEED:
            cur.execute("""
                IF NOT EXISTS (SELECT 1 FROM cities WHERE name_he = ?)
                INSERT INTO cities (district_id, name_he, name_en, is_active)
                VALUES (?, ?, ?, 1)
            """, (name_he, district_id, name_he, name_en))
        conn.commit()
    print("✅ הושלם. אפשר לרענן את מסך ההרשמה ולראות יותר ערים.")

if __name__ == "__main__":
    main()
