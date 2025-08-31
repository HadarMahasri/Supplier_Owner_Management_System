# backend/routers/users_router.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, Iterable, Set

from database.session import get_db
from schemas.users import RegisterPayload, RegisterResponse, LoginPayload, LoginResponse
from models.user_model import User
from models.supplier_city_model import SupplierCity

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
