# backend/routers/orders_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from database.session import get_db
from schemas.orders import OrderResponse, OrderItemResponse, OrderCreate, OrderStatusUpdate
from models.order_model import Order
from models.order_item_model import OrderItem
from models.product_model import Product
from models.user_model import User

router = APIRouter(prefix="/orders", tags=["orders"])

def _order_to_response(o: Order) -> OrderResponse:
    items: List[OrderItemResponse] = []
    total = 0.0
    for it in o.items:
        price = float(it.product.unit_price)
        item_total = price * it.quantity
        total += item_total
        items.append(OrderItemResponse(
            id=it.id,
            product_id=it.product_id,
            product_name=it.product.product_name,
            quantity=it.quantity,
            unit_price=price,
            total_price=item_total
        ))
    return OrderResponse(
        id=o.id,
        owner_id=o.owner_id,
        owner_name=o.owner.contact_name if o.owner else None,
        owner_company=o.owner.company_name if o.owner else None,
        supplier_id=o.supplier_id,
        status=o.status,
        created_date=o.created_date,
        items=items,
        total_amount=total
    )

@router.get("/supplier/{supplier_id}", response_model=List[OrderResponse])
def get_supplier_orders(supplier_id: int, db: Session = Depends(get_db)):
    orders = (
        db.query(Order)
        .options(
            joinedload(Order.owner),
            joinedload(Order.items).joinedload(OrderItem.product),
        )
        .filter(Order.supplier_id == supplier_id)
        .order_by(Order.created_date.desc())
        .all()
    )
    return [_order_to_response(o) for o in orders]

@router.get("/owner/{owner_id}", response_model=List[OrderResponse])
def get_owner_orders(owner_id: int, db: Session = Depends(get_db)):
    orders = (
        db.query(Order)
        .options(
            joinedload(Order.supplier),
            joinedload(Order.items).joinedload(OrderItem.product),
        )
        .filter(Order.owner_id == owner_id)
        .order_by(Order.created_date.desc())
        .all()
    )
    # שמירת תאימות ל-UI: בשאילתה הישנה הצגת פרטי הספק בשדות owner_*
    out: List[OrderResponse] = []
    for o in orders:
        resp = _order_to_response(o)
        resp.owner_name = o.supplier.contact_name if o.supplier else resp.owner_name
        resp.owner_company = o.supplier.company_name if o.supplier else resp.owner_company
        out.append(resp)
    return out

@router.post("/", response_model=OrderResponse, status_code=201)
def create_order(order: OrderCreate, owner_id: int, db: Session = Depends(get_db)):
    owner = db.query(User).filter(User.id == owner_id, User.userType == "StoreOwner").first()
    if not owner:
        raise HTTPException(status_code=404, detail="בעל חנות לא נמצא")
    supplier = db.query(User).filter(User.id == order.supplier_id, User.userType == "Supplier").first()
    if not supplier:
        raise HTTPException(status_code=404, detail="ספק לא נמצא")

    o = Order(owner_id=owner_id, supplier_id=order.supplier_id, status="בוצעה")
    db.add(o)
    db.flush()

    for item in order.items:
        p = (
            db.query(Product)
            .filter(Product.id == item.product_id, Product.supplier_id == order.supplier_id)
            .first()
        )
        if not p:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"מוצר {item.product_id} לא נמצא או לא שייך לספק")
        db.add(OrderItem(order_id=o.id, product_id=p.id, quantity=item.quantity))

    db.commit()
    db.refresh(o)  # חשוב: מביא את created_date (ושאר ברירות־מחדל מה-DB)

    # אם את רוצה להמשיך ולהחזיר עם פרטי מוצרים טעונים מראש – אפשר להשאיר את השאילתה,
    # אבל זה כבר לא חובה בשביל created_date.
    # להעדפה על שמירת ה-joinedload, אפשר:
    o = (
        db.query(Order)
        .options(joinedload(Order.owner), joinedload(Order.items).joinedload(OrderItem.product))
        .get(o.id)
    )

    return _order_to_response(o)


@router.put("/{order_id}/status", response_model=dict)
def update_order_status(order_id: int, status_update: OrderStatusUpdate, supplier_id: int, db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == order_id, Order.supplier_id == supplier_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="הזמנה לא נמצאה או אינה שייכת לך")
    
    # בדיקה ועדכון מלאי לפני שינוי הסטטוס
    if o.status == "בוצעה" and status_update.status == "בתהליך":
        # הורדת מלאי עבור כל פריט בהזמנה
        for item in o.items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                new_stock = max(0, product.stock - item.quantity)
                product.stock = new_stock
    
    o.status = status_update.status
    db.commit()
    return {"message": "סטטוס ההזמנה עודכן בהצלחה", "new_status": o.status}


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_by_id(order_id: int, db: Session = Depends(get_db)):
    o = (
        db.query(Order)
        .options(
            joinedload(Order.owner),
            joinedload(Order.supplier),
            joinedload(Order.items).joinedload(OrderItem.product),
        )
        .get(order_id)
    )
    if not o:
        raise HTTPException(status_code=404, detail="הזמנה לא נמצאה")
    return _order_to_response(o)


@router.put("/{order_id}/status/owner", response_model=dict)
def update_order_status_by_owner(order_id: int, status_update: OrderStatusUpdate, owner_id: int, db: Session = Depends(get_db)):
    """עדכון סטטוס הזמנה על ידי בעל חנות - רק אישור הגעה"""
    o = db.query(Order).filter(Order.id == order_id, Order.owner_id == owner_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="הזמנה לא נמצאה או אינה שייכת לך")
    
    # בעל חנות יכול רק לשנות מ"בתהליך" ל"הושלמה" 
    if o.status != "בתהליך" or status_update.status != "הושלמה":
        raise HTTPException(status_code=400, detail="לא ניתן לבצע פעולה זו")
        
    o.status = status_update.status
    db.commit()
    return {"message": "סטטוס ההזמנה עודכן בהצלחה", "new_status": o.status}