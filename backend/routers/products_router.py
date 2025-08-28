from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, StringConstraints
from typing_extensions import Annotated
from sqlalchemy.orm import Session
from sqlalchemy import text
from database.session import get_db

router = APIRouter(prefix="/products", tags=["products"])

# -------- Schemas --------
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]

class ProductCreate(BaseModel):
    supplier_id: int = Field(gt=0)
    name: Name
    price: float = Field(ge=0)
    min_qty: int = Field(ge=0)
    image_url: Optional[str] = None

class ProductUpdate(BaseModel):
    name: Optional[Name] = None
    price: Optional[float] = Field(default=None, ge=0)
    min_qty: Optional[int] = Field(default=None, ge=0)
    image_url: Optional[str] = None

class StockUpdate(BaseModel):
    stock: int = Field(ge=0)

class ProductOut(BaseModel):
    id: int
    supplier_id: int
    name: str
    price: float
    min_qty: int
    stock: int          # כרגע מחזירים תמיד 0 עד שתוסיפי עמודה
    image_url: Optional[str] = None


def _row_to_out(row) -> ProductOut:
    # שימי לב: העמודות בטבלה נקראות product_name / unit_price / min_quantity
    return ProductOut(
        id=row.id,
        supplier_id=row.supplier_id,
        name=row.product_name,
        price=float(row.unit_price),
        min_qty=int(row.min_quantity),
        stock=int(getattr(row, "stock", 0) or 0),  # אם בעתיד תוסיפי עמודה stock – ייקלט פה
        image_url=row.image_url,
    )


def _has_stock_column(db: Session) -> bool:
    chk = db.execute(text("""
        SELECT 1
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'products' AND COLUMN_NAME = 'stock'
    """)).scalar()
    return bool(chk)


# -------- Routes --------
@router.get("/", response_model=List[ProductOut])
def list_products(
    supplier_id: int = Query(..., gt=0, description="מזהה ספק"),
    db: Session = Depends(get_db),
):
    try:
        # נביא רק מוצרים פעילים
        q = db.execute(text("""
            SELECT id, supplier_id, product_name, unit_price, min_quantity, image_url
                 , GETDATE() AS created_at
            FROM [dbo].[products]
            WHERE supplier_id = :sid AND (is_active = 1 OR is_active IS NULL)
            ORDER BY id DESC
        """), {"sid": supplier_id})
        rows = q.mappings().all()

        # אם קיימת עמודת stock – נוסיף אותה למיפוי
        if _has_stock_column(db) and rows:
            ids = [r["id"] for r in rows]
            # נמשוך את ה-stock לכל המוצרים בבת אחת
            stocks = db.execute(text(f"""
                SELECT id, stock
                FROM [dbo].[products]
                WHERE id IN ({",".join([str(i) for i in ids])})
            """)).mappings().all()
            stock_map = {s["id"]: s["stock"] for s in stocks}
        else:
            stock_map = {}

        out = []
        for r in rows:
            r = dict(r)
            r["stock"] = stock_map.get(r["id"], 0)
            out.append(_row_to_out(type("Row", (), r)))
        return out

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error (list): {e}")


@router.post("/", response_model=ProductOut, status_code=201)
def create_product(body: ProductCreate, db: Session = Depends(get_db)):
    try:
        inserted = db.execute(text("""
            INSERT INTO [dbo].[products] (supplier_id, product_name, unit_price, min_quantity, image_url, is_active)
            OUTPUT INSERTED.id, INSERTED.supplier_id, INSERTED.product_name, INSERTED.unit_price,
                   INSERTED.min_quantity, INSERTED.image_url
            VALUES (:sid, :name, :price, :min_qty, :image_url, 1)
        """), {
            "sid": body.supplier_id,
            "name": body.name,
            "price": body.price,
            "min_qty": body.min_qty,
            "image_url": body.image_url
        })
        row = inserted.mappings().first()
        db.commit()
        # הוסף שדה stock=0 בתשובה
        row = dict(row); row["stock"] = 0
        return _row_to_out(type("Row", (), row))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error (create): {e}")


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, body: ProductUpdate, db: Session = Depends(get_db)):
    try:
        exists = db.execute(
            text("SELECT COUNT(1) FROM [dbo].[products] WHERE id=:id"),
            {"id": product_id}
        ).scalar()
        if not exists:
            raise HTTPException(404, "Product not found")

        sets = []
        params = {"id": product_id}
        if body.name is not None:
            sets.append("product_name=:name"); params["name"] = body.name
        if body.price is not None:
            sets.append("unit_price=:price"); params["price"] = body.price
        if body.min_qty is not None:
            sets.append("min_quantity=:min_qty"); params["min_qty"] = body.min_qty
        if body.image_url is not None:
            sets.append("image_url=:image_url"); params["image_url"] = body.image_url

        if sets:
            db.execute(text(f"UPDATE [dbo].[products] SET {', '.join(sets)} WHERE id=:id"), params)

        row = db.execute(text("""
            SELECT id, supplier_id, product_name, unit_price, min_quantity, image_url
            FROM [dbo].[products]
            WHERE id=:id
        """), {"id": product_id}).mappings().first()
        db.commit()
        row = dict(row); row["stock"] = 0
        return _row_to_out(type("Row", (), row))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error (update): {e}")


@router.put("/{product_id}/stock", response_model=ProductOut)
def update_stock(product_id: int, body: StockUpdate, db: Session = Depends(get_db)):
    try:
        if not _has_stock_column(db):
            # מסבירים איך להוסיף עמודה – אחרת אין איפה לשמור מלאי
            raise HTTPException(
                status_code=400,
                detail=(
                    "עמודת stock לא קיימת בטבלה [dbo].[products]. "
                    "כדי לתמוך בעדכון מלאי, הריצי ב-SQL Server:\n"
                    "ALTER TABLE [dbo].[products] ADD stock INT NOT NULL DEFAULT 0;"
                ),
            )

        db.execute(text("UPDATE [dbo].[products] SET stock=:s WHERE id=:id"), {"s": body.stock, "id": product_id})
        row = db.execute(text("""
            SELECT id, supplier_id, product_name, unit_price, min_quantity, image_url, stock
            FROM [dbo].[products]
            WHERE id=:id
        """), {"id": product_id}).mappings().first()
        if not row:
            raise HTTPException(404, "Product not found")
        db.commit()
        return _row_to_out(type("Row", (), dict(row)))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error (stock): {e}")


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    try:
        # soft delete לפי is_active
        db.execute(text("UPDATE [dbo].[products] SET is_active = 0 WHERE id=:id"), {"id": product_id})
        db.commit()
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error (delete): {e}")
