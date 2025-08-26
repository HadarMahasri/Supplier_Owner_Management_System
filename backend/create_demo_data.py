import sys
import os
from sqlalchemy import create_engine, Column, String, DateTime, Text, Numeric, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

# Database setup
DATABASE_URL = "sqlite:///./suppliers.db"
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models במקום ישירות כאן
class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    name_hebrew = Column(String(100))
    description = Column(Text)
    icon = Column(String(50))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    subcategory = Column(String(100))
    description = Column(Text)
    contact_info = Column(JSON)
    address = Column(JSON)
    location = Column(JSON)
    rating = Column(Numeric(3,2), default=0.0)
    review_count = Column(Numeric(10,0), default=0)
    price_range = Column(String(20), default='medium')
    delivery_areas = Column(JSON)
    status = Column(String(20), default='active')
    verified = Column(Boolean, default=False)
    featured = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

def create_demo_data():
    # יצירת טבלאות
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # בדיקה אם כבר יש נתונים
        existing = db.query(Supplier).first()
        if existing:
            print("✅ נתונים כבר קיימים")
            return
        
        # יצירת ספקי דמו
        suppliers = [
            Supplier(
                name="קייטרינג גולדן",
                category="מזון ומשקאות",
                description="שירותי קייטרינג מקצועיים",
                contact_info={"phone": "03-1234567", "email": "info@golden.co.il"},
                address={"city": "תל אביב", "street": "הרצל 45"},
                rating=4.7,
                review_count=156,
                price_range="medium",
                verified=True,
                featured=True
            ),
            Supplier(
                name="בנייה ושיפוצים דוד",
                category="בנייה ותשתיות", 
                description="קבלן מוסמך לכל עבודות הבנייה",
                contact_info={"phone": "04-5555555", "email": "david@build.co.il"},
                address={"city": "חיפה", "street": "הנשיא 30"},
                rating=4.3,
                review_count=78,
                price_range="high",
                verified=True
            ),
            Supplier(
                name="טכנולוגיות המחר",
                category="טכנולוגיה וציוד",
                description="ספק מחשבים ותוכנה",
                contact_info={"phone": "03-9999999", "email": "info@tech.co.il"},
                address={"city": "תל אביב", "street": "הארבעה 7"},
                rating=4.6,
                review_count=203,
                price_range="high",
                verified=True,
                featured=True
            )
        ]
        
        for supplier in suppliers:
            db.add(supplier)
        
        db.commit()
        print(f"✅ נוצרו {len(suppliers)} ספקים בהצלחה!")
        
    except Exception as e:
        print(f"❌ שגיאה: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_demo_data()