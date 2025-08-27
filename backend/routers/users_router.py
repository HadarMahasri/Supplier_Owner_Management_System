# backend/routers/users_router.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field, StringConstraints
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Annotated

from database.session import get_db  # לא מ-main כדי למנוע circular import

router = APIRouter(prefix="/users", tags=["users"])

# ---------- Typed aliases (Pydantic v2-friendly) ----------
Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=64)]
Password = Annotated[str, StringConstraints(min_length=6, max_length=128)]
Role = Annotated[str, StringConstraints(pattern=r"^(Supplier|StoreOwner)$")]
ContactName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, min_length=6, max_length=32)]

# ---------- Schemas ----------
class RegisterPayload(BaseModel):
    username: Username
    email: Optional[EmailStr] = None
    password: Password
    userType: Role

    companyName: Optional[str] = None
    contactName: ContactName
    phone: Phone

    # StoreOwner fields (optional for Supplier)
    city_id: Optional[int] = None
    street: Optional[str] = None
    house_number: Optional[str] = None
    opening_time: Optional[str] = None   # "HH:MM" או "HH:MM:SS"
    closing_time: Optional[str] = None

    # Supplier only
    serviceCities: Optional[List[int]] = None  # לא רשימה ברירת-מחדל (mutable)

class RegisterResponse(BaseModel):
    ok: bool = True
    user_id: int

class LoginPayload(BaseModel):
    username: Username
    password: Password
    role: Role

class LoginResponse(BaseModel):
    ok: bool = True
    user: dict

# ---------- Helpers ----------
def _norm_time(t: Optional[str]) -> Optional[str]:
    if not t:
        return None
    t = t.strip()
    if not t:
        return None
    if len(t) == 5 and t.count(":") == 1:
        return t + ":00"
    return t

# ---------- Routes ----------
@router.post("/register", response_model=RegisterResponse, status_code=201)
def register_user(body: RegisterPayload, db: Session = Depends(get_db)):
    # אימות ייחודיות אימייל/יוזר
    if body.email:
        c = db.execute(text("SELECT COUNT(1) FROM users WHERE email = :email"), {"email": body.email}).scalar()
        if c and c > 0:
            raise HTTPException(status_code=400, detail="האימייל כבר בשימוש")

    c = db.execute(text("SELECT COUNT(1) FROM users WHERE username = :u"), {"u": body.username}).scalar()
    if c and c > 0:
        raise HTTPException(status_code=400, detail="שם המשתמש כבר בשימוש")

    open_time = _norm_time(body.opening_time)
    close_time = _norm_time(body.closing_time)

    # הכנסת משתמש
    inserted = db.execute(text("""
        INSERT INTO users
            (username, email, password, company_name, contact_name, phone,
             city_id, street, house_number, opening_time, closing_time, userType)
        OUTPUT INSERTED.ID
        VALUES (:username, :email, :password, :company_name, :contact_name, :phone,
                :city_id, :street, :house_number, :opening_time, :closing_time, :userType)
    """), {
        "username": body.username,
        "email": body.email,
        # הערה: לפרודקשן—להחליף ל-hash (bcrypt/argon2) במקום טקסט גלוי
        "password": body.password,
        "company_name": body.companyName,
        "contact_name": body.contactName,
        "phone": body.phone,
        "city_id": body.city_id,
        "street": body.street,
        "house_number": body.house_number,
        "opening_time": open_time,
        "closing_time": close_time,
        "userType": body.userType,
    })

    row = inserted.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="שגיאת שרת: לא הוחזר מזהה משתמש")
    user_id = row[0]

    # ספקים: קישור לערים ללא כפילויות
    if body.userType == "Supplier" and body.serviceCities:
        for cid in set(body.serviceCities):
            db.execute(text("""
                IF NOT EXISTS (SELECT 1 FROM supplier_cities WHERE supplier_id=:sid AND city_id=:cid)
                INSERT INTO supplier_cities (supplier_id, city_id) VALUES (:sid, :cid)
            """), {"sid": user_id, "cid": cid})

    db.commit()
    return RegisterResponse(user_id=user_id)

@router.post("/login", response_model=LoginResponse)
def login(body: LoginPayload, db: Session = Depends(get_db)):
    q = db.execute(text("""
        SELECT id, username, email, company_name, contact_name, phone,
               city_id, street, house_number, opening_time, closing_time, userType
        FROM users
        WHERE username=:u AND password=:p
    """), {"u": body.username, "p": body.password})

    row = q.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="שם משתמש או סיסמה שגויים")
    if str(row.userType) != body.role:
        raise HTTPException(status_code=403, detail="התפקיד שנבחר אינו תואם למשתמש")

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
    return LoginResponse(user=user)
