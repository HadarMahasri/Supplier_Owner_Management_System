# backend/routers/orders_router.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime

from database.session import get_db

router = APIRouter(prefix="/orders", tags=["orders"])

# ---------- Schemas ----------
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
    status: str
    created_date: datetime
    items: List[OrderItemResponse] = []
    total_amount: float = 0.0

class OrderCreate(BaseModel):
    supplier_id: int
    items: List[dict]  # [{"product_id": 1, "quantity": 5}]

class OrderStatusUpdate(BaseModel):
    status: str  # "בתהליך", "הושלמה", "בוצעה"

# ---------- Routes ----------
@router.get("/supplier/{supplier_id}", response_model=List[OrderResponse])
def get_supplier_orders(supplier_id: int, db: Session = Depends(get_db)):
    """קבלת כל ההזמנות של ספק מסוים"""
    try:
        # שאילתא מורכבת לקבלת הזמנות עם פרטי בעל החנות
        result = db.execute(text("""
            SELECT o.id, o.owner_id, o.supplier_id, o.status, o.created_date,
                   u.contact_name as owner_name, u.company_name as owner_company
            FROM orders o
            INNER JOIN users u ON o.owner_id = u.id
            WHERE o.supplier_id = :supplier_id
            ORDER BY o.created_date DESC
        """), {"supplier_id": supplier_id})
        
        orders = []
        for row in result:
            order_data = {
                "id": row.id,
                "owner_id": row.owner_id,
                "owner_name": row.owner_name,
                "owner_company": row.owner_company,
                "supplier_id": row.supplier_id,
                "status": row.status,
                "created_date": row.created_date,
                "items": [],
                "total_amount": 0.0
            }
            
            # קבלת פריטי ההזמנה
            items_result = db.execute(text("""
                SELECT oi.id, oi.product_id, oi.quantity,
                       p.product_name, p.unit_price
                FROM order_items oi
                INNER JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = :order_id
            """), {"order_id": row.id})
            
            total_amount = 0.0
            for item_row in items_result:
                item_total = float(item_row.unit_price) * item_row.quantity
                total_amount += item_total
                
                order_data["items"].append({
                    "id": item_row.id,
                    "product_id": item_row.product_id,
                    "product_name": item_row.product_name,
                    "quantity": item_row.quantity,
                    "unit_price": float(item_row.unit_price),
                    "total_price": item_total
                })
            
            order_data["total_amount"] = total_amount
            orders.append(order_data)
        
        return orders
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בקריאת הזמנות: {str(e)}")

@router.get("/owner/{owner_id}", response_model=List[OrderResponse])
def get_owner_orders(owner_id: int, db: Session = Depends(get_db)):
    """קבלת כל ההזמנות של בעל חנות מסוים"""
    try:
        result = db.execute(text("""
            SELECT o.id, o.owner_id, o.supplier_id, o.status, o.created_date,
                   u.contact_name as supplier_name, u.company_name as supplier_company
            FROM orders o
            INNER JOIN users u ON o.supplier_id = u.id
            WHERE o.owner_id = :owner_id
            ORDER BY o.created_date DESC
        """), {"owner_id": owner_id})
        
        orders = []
        for row in result:
            order_data = {
                "id": row.id,
                "owner_id": row.owner_id,
                "owner_name": row.supplier_name,  # כאן זה שם הספק
                "owner_company": row.supplier_company,
                "supplier_id": row.supplier_id,
                "status": row.status,
                "created_date": row.created_date,
                "items": [],
                "total_amount": 0.0
            }
            
            # קבלת פריטי ההזמנה
            items_result = db.execute(text("""
                SELECT oi.id, oi.product_id, oi.quantity,
                       p.product_name, p.unit_price
                FROM order_items oi
                INNER JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = :order_id
            """), {"order_id": row.id})
            
            total_amount = 0.0
            for item_row in items_result:
                item_total = float(item_row.unit_price) * item_row.quantity
                total_amount += item_total
                
                order_data["items"].append({
                    "id": item_row.id,
                    "product_id": item_row.product_id,
                    "product_name": item_row.product_name,
                    "quantity": item_row.quantity,
                    "unit_price": float(item_row.unit_price),
                    "total_price": item_total
                })
            
            order_data["total_amount"] = total_amount
            orders.append(order_data)
        
        return orders
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בקריאת הזמנות: {str(e)}")

@router.post("/", response_model=OrderResponse, status_code=201)
def create_order(order: OrderCreate, owner_id: int, db: Session = Depends(get_db)):
    """יצירת הזמנה חדשה"""
    try:
        # בדיקה שבעל החנות קיים
        owner_check = db.execute(text("""
            SELECT COUNT(*) FROM users 
            WHERE id = :owner_id AND userType = 'StoreOwner'
        """), {"owner_id": owner_id}).scalar()
        
        if not owner_check:
            raise HTTPException(status_code=404, detail="בעל חנות לא נמצא")
        
        # בדיקה שהספק קיים
        supplier_check = db.execute(text("""
            SELECT COUNT(*) FROM users 
            WHERE id = :supplier_id AND userType = 'Supplier'
        """), {"supplier_id": order.supplier_id}).scalar()
        
        if not supplier_check:
            raise HTTPException(status_code=404, detail="ספק לא נמצא")
        
        # יצירת ההזמנה
        order_result = db.execute(text("""
            INSERT INTO orders (owner_id, supplier_id, status)
            OUTPUT INSERTED.id, INSERTED.created_date
            VALUES (:owner_id, :supplier_id, N'בתהליך')
        """), {
            "owner_id": owner_id,
            "supplier_id": order.supplier_id
        })
        
        order_row = order_result.fetchone()
        if not order_row:
            raise HTTPException(status_code=500, detail="שגיאה ביצירת ההזמנה")
        
        order_id = order_row.id
        created_date = order_row.created_date
        
        # הוספת פריטי ההזמנה
        total_amount = 0.0
        order_items = []
        
        for item in order.items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            
            # בדיקה שהמוצר קיים ושייך לספק
            product_result = db.execute(text("""
                SELECT product_name, unit_price 
                FROM products 
                WHERE id = :product_id AND supplier_id = :supplier_id
            """), {"product_id": product_id, "supplier_id": order.supplier_id})
            
            product_row = product_result.fetchone()
            if not product_row:
                db.rollback()
                raise HTTPException(status_code=400, detail=f"מוצר {product_id} לא נמצא או לא שייך לספק")
            
            # הוספת פריט להזמנה
            item_result = db.execute(text("""
                INSERT INTO order_items (order_id, product_id, quantity)
                OUTPUT INSERTED.id
                VALUES (:order_id, :product_id, :quantity)
            """), {
                "order_id": order_id,
                "product_id": product_id,
                "quantity": quantity
            })
            
            item_row = item_result.fetchone()
            item_total = float(product_row.unit_price) * quantity
            total_amount += item_total
            
            order_items.append({
                "id": item_row.id,
                "product_id": product_id,
                "product_name": product_row.product_name,
                "quantity": quantity,
                "unit_price": float(product_row.unit_price),
                "total_price": item_total
            })
        
        db.commit()
        
        # החזרת ההזמנה השלמה
        return {
            "id": order_id,
            "owner_id": owner_id,
            "supplier_id": order.supplier_id,
            "status": "בתהליך",
            "created_date": created_date,
            "items": order_items,
            "total_amount": total_amount
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"שגיאה ביצירת הזמנה: {str(e)}")

@router.put("/{order_id}/status", response_model=dict)
def update_order_status(order_id: int, status_update: OrderStatusUpdate, supplier_id: int, db: Session = Depends(get_db)):
    """עדכון סטטוס הזמנה (רק ספקים יכולים לעדכן)"""
    try:
        # בדיקה שההזמנה שייכת לספק
        existing = db.execute(text("""
            SELECT id FROM orders 
            WHERE id = :order_id AND supplier_id = :supplier_id
        """), {"order_id": order_id, "supplier_id": supplier_id}).fetchone()
        
        if not existing:
            raise HTTPException(status_code=404, detail="הזמנה לא נמצאה או אינה שייכת לך")
        
        # עדכון הסטטוס
        db.execute(text("""
            UPDATE orders 
            SET status = :status
            WHERE id = :order_id
        """), {
            "order_id": order_id,
            "status": status_update.status
        })
        
        db.commit()
        
        return {"message": "סטטוס ההזמנה עודכן בהצלחה", "new_status": status_update.status}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"שגיאה בעדכון סטטוס: {str(e)}")

@router.get("/{order_id}", response_model=OrderResponse)
def get_order_by_id(order_id: int, db: Session = Depends(get_db)):
    """קבלת הזמנה ספציפית לפי ID"""
    try:
        # קבלת פרטי ההזמנה
        result = db.execute(text("""
            SELECT o.id, o.owner_id, o.supplier_id, o.status, o.created_date,
                   u1.contact_name as owner_name, u1.company_name as owner_company,
                   u2.contact_name as supplier_name, u2.company_name as supplier_company
            FROM orders o
            INNER JOIN users u1 ON o.owner_id = u1.id
            INNER JOIN users u2 ON o.supplier_id = u2.id
            WHERE o.id = :order_id
        """), {"order_id": order_id})
        
        order_row = result.fetchone()
        if not order_row:
            raise HTTPException(status_code=404, detail="הזמנה לא נמצאה")
        
        # קבלת פריטי ההזמנה
        items_result = db.execute(text("""
            SELECT oi.id, oi.product_id, oi.quantity,
                   p.product_name, p.unit_price
            FROM order_items oi
            INNER JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = :order_id
        """), {"order_id": order_id})
        
        items = []
        total_amount = 0.0
        for item_row in items_result:
            item_total = float(item_row.unit_price) * item_row.quantity
            total_amount += item_total
            
            items.append({
                "id": item_row.id,
                "product_id": item_row.product_id,
                "product_name": item_row.product_name,
                "quantity": item_row.quantity,
                "unit_price": float(item_row.unit_price),
                "total_price": item_total
            })
        
        return {
            "id": order_row.id,
            "owner_id": order_row.owner_id,
            "owner_name": order_row.owner_name,
            "owner_company": order_row.owner_company,
            "supplier_id": order_row.supplier_id,
            "status": order_row.status,
            "created_date": order_row.created_date,
            "items": items,
            "total_amount": total_amount
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בקריאת הזמנה: {str(e)}")