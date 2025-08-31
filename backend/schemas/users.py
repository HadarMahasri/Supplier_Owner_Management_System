from typing import Optional, List, Literal, NewType
from pydantic import BaseModel, EmailStr, Field, constr

# טיפוסי עזר
Username = NewType("Username", constr(strip_whitespace=True, min_length=2, max_length=64))
Password = NewType("Password", constr(min_length=6, max_length=128))
Role = Literal["Supplier", "StoreOwner"]
Phone = NewType("Phone", constr(strip_whitespace=True, min_length=6, max_length=32))

# ---------- Schemas ----------

class RegisterPayload(BaseModel):
    username: Username
    email: Optional[EmailStr] = None
    password: Password
    userType: Role

    companyName: Optional[str] = None
    contactName: str
    phone: Phone

    # StoreOwner fields
    city_id: Optional[int] = None
    street: Optional[str] = None
    house_number: Optional[str] = None
    opening_time: Optional[str] = None   # "HH:MM" או "HH:MM:SS"
    closing_time: Optional[str] = None

    # Supplier only
    serviceCities: Optional[List[int]] = None

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
