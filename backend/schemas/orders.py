# backend/schemas/orders.py
from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field

OrderStatus = Literal["בתהליך", "הושלמה", "בוצעה"]

class OrderItemIn(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)

class OrderCreate(BaseModel):
    supplier_id: int = Field(gt=0)
    items: List[OrderItemIn]

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: float
    total_price: float

class OrderResponse(BaseModel):
    id: int
    owner_id: int
    owner_name: Optional[str] = None
    owner_company: Optional[str] = None
    supplier_id: int
    status: OrderStatus
    created_date: datetime
    items: List[OrderItemResponse] = []
    total_amount: float = 0.0
