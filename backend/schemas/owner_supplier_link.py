from pydantic import BaseModel
from datetime import datetime

class OwnerMini(BaseModel):
    id: int
    company_name: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    class Config: from_attributes = True

class LinkOut(BaseModel):
    owner: OwnerMini
    supplier_id: int
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    class Config: from_attributes = True

class ActionResult(BaseModel):
    ok: bool
    status: str
