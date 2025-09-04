# backend/routers/products_router.py
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy import true
from sqlalchemy.orm import Session
from typing import List, Optional

from database.session import get_db
from schemas.products import ProductOut, ProductCreate, ProductUpdate, StockUpdate, ProductWithImageCreate
from models.product_model import Product  # ✅ שימוש ב-ORM

try:
    from services.cloudinary_service import cloudinary_service
    HAS_CLOUDINARY_SERVICE = True
except ImportError:
    cloudinary_service = None
    HAS_CLOUDINARY_SERVICE = False
    
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
            stock=getattr(body, 'stock', 0),
            is_active=True,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return _to_out(p)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"שגיאה ביצירת מוצר: {e}")

@router.post("/with-image", response_model=ProductOut, status_code=201)
async def create_product_with_image(
    supplier_id: int = Form(...),
    name: str = Form(...),
    price: float = Form(...),
    min_qty: int = Form(...),
    stock: int = Form(0),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    יצירת מוצר עם העלאת תמונה במקביל
    """
    if not HAS_CLOUDINARY_SERVICE:
        raise HTTPException(status_code=503, detail="Cloudinary not available")
    try:
        image_url = None
        
        # אם יש תמונה - נעלה אותה ל-Cloudinary
        if image:
            # קריאת תוכן הקובץ
            file_content = await image.read()
            
            # בדיקת תקינות הקובץ
            await cloudinary_service.validate_image_file(file_content, image.filename)
            
            # העלאה ל-Cloudinary (בלי product_id כי עדיין לא נוצר)
            upload_result = await cloudinary_service.upload_product_image(
                file_content=file_content,
                filename=image.filename,
                supplier_id=supplier_id,
                product_id=None
            )
            
            image_url = upload_result["url"]
        
        # יצירת המוצר במסד הנתונים
        p = Product(
            supplier_id=supplier_id,
            product_name=name,
            unit_price=price,
            min_quantity=min_qty,
            image_url=image_url,
            stock=stock,
            is_active=True,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        
        return _to_out(p)
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"שגיאה ביצירת מוצר עם תמונה: {e}")

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
    if body.stock is not None: 
        p.stock = body.stock
    if body.image_url is not None:
        p.image_url = body.image_url

    try:
        db.commit()
        db.refresh(p)
        return _to_out(p)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"שגיאה בעדכון מוצר: {e}")

@router.put("/{product_id}/image")
async def update_product_image(
    product_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    עדכון תמונת מוצר קיים
    """
    try:
        # בדיקה שהמוצר קיים
        p = db.query(Product).filter(Product.id == product_id, Product.is_active == true()).first()
        if not p:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # מחיקת תמונה קודמת אם קיימת
        old_image_url = p.image_url
        if old_image_url and "cloudinary.com" in old_image_url:
            # חילוץ public_id מה-URL
            try:
                public_id = old_image_url.split('/')[-1].split('.')[0]
                await cloudinary_service.delete_product_image(f"products/{public_id}")
            except Exception as e:
                print(f"שגיאה במחיקת תמונה ישנה: {e}")
        
        # העלאת תמונה חדשה
        file_content = await image.read()
        await cloudinary_service.validate_image_file(file_content, image.filename)
        
        upload_result = await cloudinary_service.upload_product_image(
            file_content=file_content,
            filename=image.filename,
            supplier_id=p.supplier_id,
            product_id=product_id
        )
        
        # עדכון ה-URL במסד הנתונים
        p.image_url = upload_result["url"]
        db.commit()
        db.refresh(p)
        
        return {
            "success": True,
            "message": "תמונת המוצר עודכנה בהצלחה",
            "product": _to_out(p),
            "image_data": upload_result
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"שגיאה בעדכון תמונת מוצר: {e}")

@router.delete("/{product_id}/image")
async def delete_product_image(product_id: int, db: Session = Depends(get_db)):
    """
    מחיקת תמונת מוצר
    """
    try:
        p = db.query(Product).filter(Product.id == product_id, Product.is_active == true()).first()
        if not p:
            raise HTTPException(status_code=404, detail="Product not found")
        
        if not p.image_url:
            return {"success": True, "message": "למוצר אין תמונה"}
        
        # מחיקה מ-Cloudinary
        if "cloudinary.com" in p.image_url:
            try:
                public_id = p.image_url.split('/')[-1].split('.')[0]
                await cloudinary_service.delete_product_image(f"products/{public_id}")
            except Exception as e:
                print(f"שגיאה במחיקה מ-Cloudinary: {e}")
        
        # הסרת ה-URL מהמוצר
        p.image_url = None
        db.commit()
        
        return {
            "success": True,
            "message": "תמונת המוצר נמחקה בהצלחה"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"שגיאה במחיקת תמונת מוצר: {e}")

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
async def delete_product(product_id: int, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p or not p.is_active:
        # אם כבר לא פעיל/לא קיים – מתייחסים כ-No Content
        return
    
    # מחיקת תמונה מ-Cloudinary אם קיימת
    if p.image_url and "cloudinary.com" in p.image_url:
        try:
            public_id = p.image_url.split('/')[-1].split('.')[0]
            await cloudinary_service.delete_product_image(f"products/{public_id}")
        except Exception as e:
            print(f"שגיאה במחיקת תמונה במחיקת מוצר: {e}")
    
    p.is_active = False
    try:
        db.commit()
        return
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"שגיאה במחיקת מוצר: {e}")