from sqlalchemy import create_engine, Column, String, Text, Numeric, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uuid
from datetime import datetime  # הוסיפי בתחילת הקובץ

DATABASE_URL = "sqlite:///./suppliers.db"
engine = create_engine(DATABASE_URL)
Base = declarative_base()

class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    subcategory = Column(String(100))  # ←← הוספתי את זה
    description = Column(Text)
    contact_info = Column(JSON)
    address = Column(JSON)
    location = Column(JSON)  # ←← הוספתי את זה
    rating = Column(Numeric(3,2), default=4.0)
    review_count = Column(Numeric(10,0), default=50)
    price_range = Column(String(20), default='medium')
    delivery_areas = Column(JSON)  # ←← הוספתי את זה
    status = Column(String(20), default='active')
    verified = Column(Boolean, default=True)
    featured = Column(Boolean, default=False)
    created_at = Column(String, default=str(datetime.now()))  # ←← הוסיפי
    updated_at = Column(String, default=str(datetime.now()))  # ←← הוסיפי

# מחק ויצור מחדש
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# הוסף ספקים עם כל השדות
suppliers = [
    Supplier(
        id=str(uuid.uuid4()),
        name="קייטרינג גולדן",
        category="מזון ומשקאות",
        subcategory="קייטרינג",
        description="שירותי קייטרינג מקצועיים",
        contact_info={"phone": "03-1234567"},
        address={"city": "תל אביב"},
        location={"lat": 32.0853, "lng": 34.7818},
        delivery_areas=["תל אביב", "רמת גן"],
        rating=4.7,
        review_count=156,
        featured=True
    ),
    Supplier(
        id=str(uuid.uuid4()),
        name="בנייה דוד",
        category="בנייה ותשתיות",
        subcategory="קבלנות",
        description="קבלן מוסמך",
        contact_info={"phone": "04-5555555"},
        address={"city": "חיפה"},
        location={"lat": 32.7940, "lng": 34.9896},
        delivery_areas=["חיפה", "קריות"],
        rating=4.3,
        review_count=78
    ),
    Supplier(
        id=str(uuid.uuid4()),
        name="טכנולוגיות המחר",
        category="טכנולוגיה וציוד",
        subcategory="מחשבים",
        description="ספק מחשבים ותוכנה",
        contact_info={"phone": "03-9999999"},
        address={"city": "תל אביב"},
        location={"lat": 32.0644, "lng": 34.7706},
        delivery_areas=["תל אביב", "פתח תקווה"],
        rating=4.6,
        review_count=203,
        featured=True
    )
]

for supplier in suppliers:
    db.add(supplier)

db.commit()
print(f"✅ תוקן מסד הנתונים עם {len(suppliers)} ספקים!")

count = db.query(Supplier).count()
print(f"✅ יש {count} ספקים במסד הנתונים")

db.close()