from typing import Optional, NewType
from pydantic import BaseModel, Field, constr, HttpUrl

NameStr = NewType("NameStr", constr(strip_whitespace=True, min_length=1, max_length=200))

class ProductCreate(BaseModel):
    supplier_id: int = Field(gt=0)
    name: NameStr
    price: float = Field(ge=0)
    min_qty: int = Field(ge=0)
    image_url: Optional[str] = None

class ProductWithImageCreate(BaseModel):
    """סכימה ליצירת מוצר עם תמונה"""
    supplier_id: int = Field(gt=0)
    name: NameStr
    price: float = Field(ge=0)
    min_qty: int = Field(ge=0)
    # image_file יטופל כ-UploadFile בראוטר

class ProductUpdate(BaseModel):
    name: Optional[NameStr] = None
    price: Optional[float] = Field(default=None, ge=0)
    min_qty: Optional[int] = Field(default=None, ge=0)
    image_url: Optional[str] = None
    stock: Optional[int] = Field(default=None, ge=0)

class StockUpdate(BaseModel):
    stock: int = Field(ge=0)

class ProductOut(BaseModel):
    id: int
    supplier_id: int
    name: str
    price: float
    min_qty: int
    stock: int
    image_url: Optional[str] = None

class ImageUploadResponse(BaseModel):
    """תגובה להעלאת תמונה"""
    success: bool
    message: str
    image_data: Optional[dict] = None
    
class ImageDeleteResponse(BaseModel):
    """תגובה למחיקת תמונה"""
    success: bool
    message: str

class OptimizedImageResponse(BaseModel):
    """תגובה לקבלת URL מותאם"""
    success: bool
    optimized_url: str
    transformations: dict