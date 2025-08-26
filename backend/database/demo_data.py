# backend/database/demo_data.py
"""יצירת נתוני דמו למערכת הספקים"""

from sqlalchemy.orm import Session
from models.supplier_model import Supplier, Category, Base
from config.database import engine, SessionLocal
import uuid

def create_demo_data():
    """יצירת נתוני דמו"""
    
    # יצירת הטבלאות
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # בדיקה אם כבר יש נתונים
        existing_suppliers = db.query(Supplier).first()
        if existing_suppliers:
            print("✅ נתוני דמו כבר קיימים")
            return
        
        # יצירת קטגוריות
        categories = [
            Category(
                id=uuid.uuid4(),
                name="food_beverages",
                name_hebrew="מזון ומשקאות",
                description="ספקי מזון, קייטרינג ומשקאות",
                icon="utensils"
            ),
            Category(
                id=uuid.uuid4(),
                name="construction",
                name_hebrew="בנייה ותשתיות", 
                description="קבלנים, חומרי בנייה וכלים",
                icon="hammer"
            ),
            Category(
                id=uuid.uuid4(),
                name="technology",
                name_hebrew="טכנולוגיה וציוד",
                description="מחשבים, תוכנה ואלקטרוניקה",
                icon="laptop"
            ),
            Category(
                id=uuid.uuid4(),
                name="office",
                name_hebrew="ציוד משרדי",
                description="ריהוט, מכשירים ושירותי משרד",
                icon="briefcase"
            ),
            Category(
                id=uuid.uuid4(),
                name="logistics",
                name_hebrew="לוגיסטיקה ומשלוחים",
                description="חברות הובלה ואחסנה",
                icon="truck"
            )
        ]
        
        for category in categories:
            db.add(category)
        
        # יצירת ספקי דמו
        demo_suppliers = [
            # מזון ומשקאות
            Supplier(
                id=uuid.uuid4(),
                name="קייטרינג גולדן",
                category="מזון ומשקאות",
                subcategory="קייטרינג",
                description="שירותי קייטרינג מקצועיים לאירועים עסקיים ופרטיים",
                contact_info={
                    "phone": "03-1234567",
                    "email": "info@golden-catering.co.il",
                    "website": "www.golden-catering.co.il"
                },
                address={
                    "street": "רחוב הרצל 45",
                    "city": "תל אביב",
                    "country": "ישראל",
                    "postal_code": "6777845"
                },
                location={"lat": 32.0853, "lng": 34.7818},
                rating=4.7,
                review_count=156,
                price_range="medium",
                delivery_areas=["תל אביב", "רמת גן", "בני ברק"],
                verified=True,
                featured=True
            ),
            Supplier(
                id=uuid.uuid4(),
                name="תבלינים ובשמים אברהם",
                category="מזון ומשקאות",
                subcategory="חומרי גלם",
                description="ספק מוביל של תבלינים איכותיים למסעדות",
                contact_info={
                    "phone": "02-9876543",
                    "email": "avraham@spices.co.il",
                    "website": "www.avraham-spices.co.il"
                },
                address={
                    "street": "שוק מחנה יהודה 12",
                    "city": "ירושלים",
                    "country": "ישראל",
                    "postal_code": "9414001"
                },
                location={"lat": 31.7857, "lng": 35.2007},
                rating=4.9,
                review_count=89,
                price_range="low",
                delivery_areas=["ירושלים", "בית שמש", "מודיעין"],
                verified=True
            ),
            
            # בנייה ותשתיות
            Supplier(
                id=uuid.uuid4(),
                name="קבלן הבנייה דוד כהן",
                category="בנייה ותשתיות",
                subcategory="קבלנות כללית",
                description="קבלן מוסמך לעבודות בנייה ושיפוצים",
                contact_info={
                    "phone": "04-5555555",
                    "email": "david@cohen-construction.co.il",
                    "website": "www.cohen-build.co.il"
                },
                address={
                    "street": "שדרות הנשיא 30",
                    "city": "חיפה",
                    "country": "ישראל",
                    "postal_code": "3109601"
                },
                location={"lat": 32.7940, "lng": 34.9896},
                rating=4.3,
                review_count=78,
                price_range="high",
                delivery_areas=["חיפה", "קריות", "עכו"],
                verified=True
            ),
            Supplier(
                id=uuid.uuid4(),
                name="חומרי בנייה מקס",
                category="בנייה ותשתיות",
                subcategory="חומרי גלם",
                description="ספקי חומרי בנייה - צמנט, ברזל, אבן",
                contact_info={
                    "phone": "08-7777777",
                    "email": "sales@max-building.co.il"
                },
                address={
                    "street": "האזורים התעשייה 15",
                    "city": "באר שבע",
                    "country": "ישראל",
                    "postal_code": "8420435"
                },
                location={"lat": 31.2518, "lng": 34.7915},
                rating=4.1,
                review_count=134,
                price_range="medium",
                delivery_areas=["באר שבע", "אשדוד", "אשקלון"],
                verified=True
            ),
            
            # טכנולוגיה וציוד
            Supplier(
                id=uuid.uuid4(),
                name="טכנולוגיות המחר",
                category="טכנולוגיה וציוד",
                subcategory="מחשבים ורכיבים",
                description="ספק מחשבים, שרתים וציוד IT מתקדם",
                contact_info={
                    "phone": "03-9999999",
                    "email": "info@tech-tomorrow.co.il",
                    "website": "www.tech-tomorrow.co.il"
                },
                address={
                    "street": "הארבעה 7",
                    "city": "תל אביב",
                    "country": "ישראל",
                    "postal_code": "6777745"
                },
                location={"lat": 32.0644, "lng": 34.7706},
                rating=4.6,
                review_count=203,
                price_range="high",
                delivery_areas=["תל אביב", "רמת גן", "פתח תקווה", "הרצליה"],
                verified=True,
                featured=True
            ),
            
            # ציוד משרדי
            Supplier(
                id=uuid.uuid4(),
                name="משרד פלוס",
                category="ציוד משרדי",
                subcategory="ריהוט ומכשירים",
                description="ספק ריהוט משרדי, מחשבים ומכשירי משרד",
                contact_info={
                    "phone": "09-8888888",
                    "email": "office@office-plus.co.il"
                },
                address={
                    "street": "רחוב התעשייה 25",
                    "city": "פתח תקווה",
                    "country": "ישראל",
                    "postal_code": "4951447"
                },
                location={"lat": 32.0878, "lng": 34.8612},
                rating=4.2,
                review_count=67,
                price_range="medium",
                delivery_areas=["פתח תקווה", "רמת גן", "תל אביב"],
                verified=True
            ),
            
            # לוגיסטיקה
            Supplier(
                id=uuid.uuid4(),
                name="הובלות זריזות",
                category="לוגיסטיקה ומשלוחים",
                subcategory="הובלה ומשלוחים",
                description="שירותי הובלה מהירים וזמינים 24/7",
                contact_info={
                    "phone": "052-1234567",
                    "email": "info@fast-delivery.co.il"
                },
                address={
                    "street": "כביש 1 ק״מ 10",
                    "city": "ראשון לציון",
                    "country": "ישראל",
                    "postal_code": "7546302"
                },
                location={"lat": 31.9730, "lng": 34.8066},
                rating=4.4,
                review_count=312,
                price_range="low",
                delivery_areas=["כל הארץ"],
                verified=True
            )
        ]
        
        # הוספת הספקים למסד הנתונים
        for supplier in demo_suppliers:
            db.add(supplier)
        
        # שמירה
        db.commit()
        
        print(f"✅ נוצרו {len(demo_suppliers)} ספקי דמו בהצלחה!")
        print(f"✅ נוצרו {len(categories)} קטגוריות בהצלחה!")
        
    except Exception as e:
        print(f"❌ שגיאה ביצירת נתוני דמו: {e}")
        db.rollback()
        
    finally:
        db.close()

if __name__ == "__main__":
    create_demo_data()