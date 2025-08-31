from pydantic import BaseModel, Field

class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    order_id: int = Field(gt=0)
    quantity: int = Field(gt=0)

class OrderItemUpdate(BaseModel):
    quantity: int = Field(gt=0)

class OrderItemOut(BaseModel):
    id: int
    product_id: int
    order_id: int
    quantity: int
