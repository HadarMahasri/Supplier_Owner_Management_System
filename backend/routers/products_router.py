# backend/routers/products_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import true
from sqlalchemy.orm import Session
from typing import List, Optional

from database.session import get_db
from schemas.products import ProductOut, ProductCreate, ProductUpdate, StockUpdate
from models.product_model import Product  # ✅ שימוש ב-ORM

router = APIRouter(prefix="/products", tags=["products"])

# helper קטן למיפוי ORM -> סכימה
def _to_out(prod: Product) -> ProductOut:
    return ProductOut(
        id=prod.id,
        supplier_id=prod.supplier_id,
        name=prod.product_name,
        price=float(prod.unit_price),
        min_qty=prod.min_quantity,
        stock=prod.stock,
        image_url=prod.image_url
    )

@router.get("/", response_model=List[ProductOut])
def list_products(
    supplier_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db)
):
    q = db.query(Product).filter(Product.is_active == true())
    if supplier_id is not None:
        q = q.filter(Product.supplier_id == supplier_id)
    products = q.order_by(Product.id.desc()).all()
    return [_to_out(p) for p in products]

@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = (
        db.query(Product)
        .filter(Product.id == product_id, Product.is_active == true())
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return _to_out(p)

@router.post("/", response_model=ProductOut, status_code=201)
def create_product(body: ProductCreate, db: Session = Depends(get_db)):
    try:
        p = Product(
            supplier_id=body.supplier_id,
            product_name=body.name,
            unit_price=body.price,
            min_quantity=body.min_qty,
            image_url=body.image_url,
            stock=0,
            is_active=True,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return _to_out(p)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"שגיאה ביצירת מוצר: {e}")

@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, body: ProductUpdate, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id, Product.is_active == true()).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    # מעדכנים רק שדות שהגיעו בבקשה
    if body.name is not None:
        p.product_name = body.name
    if body.price is not None:
        p.unit_price = body.price
    if body.min_qty is not None:
        p.min_quantity = body.min_qty
    if body.image_url is not None:
        p.image_url = body.image_url

    try:
        db.commit()
        db.refresh(p)
        return _to_out(p)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"שגיאה בעדכון מוצר: {e}")

@router.put("/{product_id}/stock", response_model=ProductOut)
def update_stock(product_id: int, body: StockUpdate, db: Session = Depends(get_db)):
    if body.stock < 0:
        raise HTTPException(status_code=400, detail="stock must be >= 0")

    p = db.query(Product).filter(Product.id == product_id, Product.is_active == true()).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    p.stock = body.stock
    try:
        db.commit()
        db.refresh(p)
        return _to_out(p)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"שגיאה בעדכון מלאי: {e}")

@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p or not p.is_active:
        # אם כבר לא פעיל/לא קיים – מתייחסים כ-No Content
        return
    p.is_active = False
    try:
        db.commit()
        return
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"שגיאה במחיקת מוצר: {e}")
