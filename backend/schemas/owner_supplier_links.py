from typing import Optional, Literal
from pydantic import BaseModel, Field

LinkStatus = Literal["PENDING", "APPROVED", "REJECTED"]

class OwnerSupplierLinkCreate(BaseModel):
    owner_id: int = Field(gt=0)
    supplier_id: int = Field(gt=0)
    status: LinkStatus = "PENDING"

class OwnerSupplierLinkUpdate(BaseModel):
    status: Optional[LinkStatus] = None

class OwnerSupplierLinkOut(BaseModel):
    owner_id: int
    supplier_id: int
    status: LinkStatus
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
