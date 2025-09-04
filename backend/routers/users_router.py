# backend/routers/users_router.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, Iterable, Set

from database.session import get_db
from schemas.users import RegisterPayload, RegisterResponse, LoginPayload, LoginResponse
from models.user_model import User
from models.supplier_city_model import SupplierCity
from sqlalchemy import text

router = APIRouter(prefix="/users", tags=["users"])

def _norm_time(t: Optional[str]) -> Optional[str]:
    if not t:
        return None
    t = t.strip()
    if not t:
        return None
    if len(t) == 5 and t.count(":") == 1:
        return t + ":00"
    return t

# ---------- רקע: הוספת ערי שירות ברקע ----------
def _insert_service_cities(db_factory, supplier_id: int, city_ids: Iterable[int]) -> None:
    """רץ לאחר שהתגובה כבר נשלחה ללקוח."""
    from sqlalchemy.orm import Session as _Session  # שמירה על טיפוס
    db: _Session = db_factory()
    try:
        uniq: Set[int] = set(int(c) for c in city_ids if c is not None)
        if not uniq:
            return

        # הימנעות מכפילויות קיימות
        existing = {
            c.city_id
            for c in db.query(SupplierCity.city_id).filter(SupplierCity.supplier_id == supplier_id)
        }
        to_add = [SupplierCity(supplier_id=supplier_id, city_id=cid)
                  for cid in uniq if cid not in existing]
        if to_add:
            # bulk יעיל יותר מעשרות INSERT-ים
            db.bulk_save_objects(to_add)
            db.commit()
    except Exception:
        db.rollback()
        # אפשר ללוגג כאן אם יש לכם logger
    finally:
        db.close()

@router.post("/register", response_model=RegisterResponse, status_code=201)
def register_user(body: RegisterPayload, bg: BackgroundTasks, db: Session = Depends(get_db)):
    # ולידציה ייחודיות
    if body.email and db.query(User).filter(User.email == body.email).count() > 0:
        raise HTTPException(status_code=400, detail="האימייל כבר בשימוש")
    if db.query(User).filter(User.username == body.username).count() > 0:
        raise HTTPException(status_code=400, detail="שם המשתמש כבר בשימוש")

    # יצירת משתמש
    u = User(
        username=body.username,
        email=body.email,
        password=body.password,  # ⚠️ להצפין בפרודקשן
        company_name=body.companyName,
        contact_name=body.contactName,
        phone=str(body.phone) if body.phone is not None else None,
        city_id=body.city_id,
        street=body.street,
        house_number=body.house_number,
        opening_time=_norm_time(body.opening_time),
        closing_time=_norm_time(body.closing_time),
        userType=body.userType,
    )
    db.add(u)
    db.commit()
    db.refresh(u)  # וודאות שיש ID מעודכן

    # העברת הוספת ערי שירות לפעולת רקע (מונע timeout)
    if body.userType == "Supplier" and body.serviceCities:
        # get_db הוא גנרטור; נשתמש ב־sessionmaker/Factory מתוך get_db.__self__ אם יש,
        # או נעביר פונקציה שיוצרת Session חדש דרך אותו מנגנון.
        from database.session import SessionLocal  # נפוץ בפרויקטים שלכם
        bg.add_task(_insert_service_cities, SessionLocal, u.id, list(body.serviceCities))

    # החזרת תשובה מיידית
    return RegisterResponse(user_id=u.id)

@router.post("/login", response_model=LoginResponse)
def login(body: LoginPayload, db: Session = Depends(get_db)):
    u = (
        db.query(User)
        .filter(User.username == body.username, User.password == body.password)
        .first()
    )
    if not u:
        raise HTTPException(status_code=401, detail="שם משתמש או סיסמה שגויים")
    if str(u.userType) != body.role:
        raise HTTPException(status_code=403, detail="התפקיד שנבחר אינו תואם למשתמש")

    user = {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "company_name": u.company_name,
        "contact_name": u.contact_name,
        "phone": u.phone,
        "city_id": u.city_id,
        "street": u.street,
        "house_number": u.house_number,
        "opening_time": str(u.opening_time) if u.opening_time else None,
        "closing_time": str(u.closing_time) if u.closing_time else None,
        "role": u.userType,
    }
    return LoginResponse(user=user)

# הוסף את הקוד הזה לקובץ backend/routers/users_router.py

@router.get("/profile/{user_id}")
async def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    """קבלת פרופיל מלא של משתמש עבור הצ'אט AI"""
    try:
        # שאילתת המשתמש הבסיסית
        user = db.execute(text("""
            SELECT id, username, email, company_name, contact_name, phone, 
                   city_id, street, house_number, opening_time, closing_time, userType
            FROM users WHERE id = :user_id
        """), {"user_id": user_id}).fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="משתמש לא נמצא")
        
        # בניית פרופיל בסיסי
        user_profile = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "company_name": user.company_name,
            "contact_name": user.contact_name,
            "phone": user.phone,
            "city_id": user.city_id,
            "street": user.street,
            "house_number": user.house_number,
            "opening_time": str(user.opening_time) if user.opening_time else None,
            "closing_time": str(user.closing_time) if user.closing_time else None,
            "userType": user.userType
        }
        
        # נתונים ספציפיים לספק
        if user.userType == "Supplier":
            # מספר מוצרים פעילים
            products_count = db.execute(text("""
                SELECT COUNT(*) FROM products 
                WHERE supplier_id = :user_id AND is_active = 1
            """), {"user_id": user_id}).scalar()
            
            # הזמנות פעילות
            active_orders = db.execute(text("""
                SELECT COUNT(*) FROM orders 
                WHERE supplier_id = :user_id AND status IN (N'בתהליך', N'בוצעה')
            """), {"user_id": user_id}).scalar()
            
            # הזמנות שהושלמו השבוע
            completed_this_week = db.execute(text("""
                SELECT COUNT(*) FROM orders 
                WHERE supplier_id = :user_id AND status = N'הושלמה' 
                AND created_date >= DATEADD(day, -7, GETDATE())
            """), {"user_id": user_id}).scalar()
            
            # מוצרים שאזלו מהמלאי
            out_of_stock = db.execute(text("""
                SELECT COUNT(*) FROM products 
                WHERE supplier_id = :user_id AND stock = 0 AND is_active = 1
            """), {"user_id": user_id}).scalar()
            
            user_profile.update({
                "products_count": products_count,
                "active_orders": active_orders,
                "completed_orders_week": completed_this_week,
                "out_of_stock_products": out_of_stock,
                "role_specific_data": "supplier_data"
            })
            
        # נתונים ספציפיים לבעל חנות
        elif user.userType == "StoreOwner":
            # הזמנות פעילות
            active_orders = db.execute(text("""
                SELECT COUNT(*) FROM orders 
                WHERE owner_id = :user_id AND status IN (N'בתהליך', N'בוצעה')
            """), {"user_id": user_id}).scalar()
            
            # הזמנות השבוע
            orders_this_week = db.execute(text("""
                SELECT COUNT(*) FROM orders 
                WHERE owner_id = :user_id 
                AND created_date >= DATEADD(day, -7, GETDATE())
            """), {"user_id": user_id}).scalar()
            
            # ספקים מחוברים
            connected_suppliers = db.execute(text("""
                SELECT COUNT(*) FROM owner_supplier_links 
                WHERE owner_id = :user_id AND status = 'APPROVED'
            """), {"user_id": user_id}).scalar()
            
            # בקשות חיבור ממתינות
            pending_requests = db.execute(text("""
                SELECT COUNT(*) FROM owner_supplier_links 
                WHERE owner_id = :user_id AND status = 'PENDING'
            """), {"user_id": user_id}).scalar()
            
            user_profile.update({
                "active_orders": active_orders,
                "orders_this_week": orders_this_week,
                "connected_suppliers": connected_suppliers,
                "pending_supplier_requests": pending_requests,
                "role_specific_data": "store_owner_data"
            })
        
        return user_profile
        
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Error fetching user profile: {e}")
        raise HTTPException(status_code=500, detail="שגיאה בקבלת פרטי המשתמש")
