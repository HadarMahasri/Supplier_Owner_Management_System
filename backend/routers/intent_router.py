# backend/routers/intent_router.py
import re
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from models.order_model import Order
from models.order_item_model import OrderItem
from models.product_model import Product

HE_NUM = r"(?:כמה|מספר|כמה יש|כמה יש לי)"
HE_OPEN = r"(?:פתוחות?|פתוחים|לא הושלמו|פתוח)"
HE_ACTIVE = r"(?:פעיל(?:ים)?|לא פעיל|מופעל)"
HE_LAST = r"(?:האחרונה|האחרון|האחרונות|האחרונים|אחרון|אחרונה)"
HE_STATUS = r"(?:סטטוס|מצב|מה הסטטוס|מה המצב)"
HE_MINQ = r"(?:כמות מינימום|מינימום|מינימום הזמנה)"
HE_SEE = r"(?:איך לראות|איך לבדוק|איך לראות את)"
HE_UPDATE = r"(?:איך לעדכן|עדכון|לעדכן)"
HE_ORDER = r"(?:הזמנה|הזמנות)"
HE_PRODUCT = r"(?:מוצר|מוצרים)"
HE_TOTAL = r"(?:סכום|סה\"כ|עלות)"
HE_LOW_STOCK = r"(?:אזל|אזלו|חסר|חסרים|מלאי נמוך)"

# ---------- Handlers (כל אחד מחזיר טקסט קצר או None) ----------

def h_supplier_count_active_products(db: Session, supplier_id: int, q: str) -> Optional[str]:
    if re.search(fr"{HE_NUM}.*{HE_PRODUCT}.*{HE_ACTIVE}", q) or \
       re.search(fr"{HE_PRODUCT}.*{HE_ACTIVE}.*{HE_NUM}", q):
        count = db.query(Product).filter(Product.supplier_id == supplier_id,
                                         Product.is_active == True).count()
        return f"{count} מוצרים פעילים."
    return None

def h_supplier_open_orders_count(db: Session, supplier_id: int, q: str) -> Optional[str]:
    if re.search(fr"{HE_NUM}.*{HE_ORDER}.*{HE_OPEN}", q) or \
       re.search(fr"{HE_ORDER}.*{HE_OPEN}.*{HE_NUM}", q):
        cnt = db.query(Order).filter(Order.supplier_id == supplier_id,
                                     Order.status != "הושלמה").count()
        return f"{cnt} הזמנות פתוחות."
    return None

def h_supplier_last_open_orders_status(db: Session, supplier_id: int, q: str) -> Optional[str]:
    if (re.search(fr"{HE_STATUS}.*{HE_ORDER}.*{HE_LAST}", q) or
        re.search(fr"{HE_ORDER}.*{HE_LAST}.*{HE_STATUS}", q)):
        last = (db.query(Order)
                  .filter(Order.supplier_id == supplier_id)
                  .order_by(desc(Order.id)).first())
        if not last:
            return "אין הזמנות."
        return f"הזמנה אחרונה #{last.id}, סטטוס: {last.status}."
    return None

def h_supplier_low_stock(db: Session, supplier_id: int, q: str) -> Optional[str]:
    if re.search(fr"{HE_LOW_STOCK}|{HE_SEE}.*מלאי", q):
        low = (db.query(Product)
                 .filter(Product.supplier_id == supplier_id,
                         Product.is_active == True,
                         Product.stock <= 5)
                 .order_by(Product.stock.asc())
                 .limit(5).all())
        if not low:
            return "אין מוצרים במלאי נמוך."
        items = []
        for p in low:
            name = getattr(p, "name", f"#{getattr(p, 'id', '?')}")
            items.append(f"{name} (מלאי={getattr(p,'stock',0)})")
        return "מלאי נמוך: " + ", ".join(items)
    return None

def h_owner_last_order_status(db: Session, owner_id: int, q: str) -> Optional[str]:
    if re.search(fr"{HE_STATUS}.*{HE_ORDER}.*{HE_LAST}", q) or \
       re.search(fr"{HE_ORDER}.*{HE_LAST}.*{HE_STATUS}", q):
        last = (db.query(Order)
                  .filter(Order.owner_id == owner_id)
                  .order_by(desc(Order.id)).first())
        if not last:
            return "אין הזמנות."
        return f"הזמנה אחרונה #{last.id}, סטטוס: {last.status}."
    return None

def h_owner_orders_count(db: Session, owner_id: int, q: str) -> Optional[str]:
    if re.search(fr"{HE_NUM}.*{HE_ORDER}", q):
        cnt = db.query(Order).filter(Order.owner_id == owner_id).count()
        return f"{cnt} הזמנות שבוצעו."
    return None

def h_owner_last_order_total(db: Session, owner_id: int, q: str) -> Optional[str]:
    if re.search(fr"{HE_TOTAL}.*{HE_ORDER}.*{HE_LAST}", q):
        last = (db.query(Order)
                  .filter(Order.owner_id == owner_id)
                  .order_by(desc(Order.id)).first())
        if not last:
            return "אין הזמנות."
        total = 0.0
        for it in last.items:
            price = getattr(it.product, "unit_price", 0.0)
            qty = getattr(it, "quantity", 0)
            try:
                total += float(price) * int(qty)
            except Exception:
                pass
        return f"סכום הזמנה אחרונה #{last.id}: {total:.2f}."
    return None

def h_how_to_update_min_quantity(q: str) -> Optional[str]:
    if re.search(fr"{HE_UPDATE}.*{HE_MINQ}", q) or \
       re.search(fr"{HE_MINQ}.*{HE_UPDATE}", q):
        return "נהל/י מוצר → עריכה → 'כמות מינימום' → שמור. (אם המוצר לא פעיל, הפעל אותו קודם)."
    return None

# ---------- Router ראשי: מפעיל handlers לפי role ----------
def route_intent_and_answer(db: Session, role: str, user_id: int, question: str) -> Optional[str]:
    q = question.strip().lower()
    if role == "Supplier":
        for h in (
            h_supplier_count_active_products,
            h_supplier_open_orders_count,
            h_supplier_last_open_orders_status,
            h_supplier_low_stock,
            h_how_to_update_min_quantity,
        ):
            ans = h(db, user_id, q) if h != h_how_to_update_min_quantity else h(q)
            if ans:
                return ans
    else:  # StoreOwner
        for h in (
            h_owner_last_order_status,
            h_owner_orders_count,
            h_owner_last_order_total,
            h_how_to_update_min_quantity,
        ):
            ans = h(db, user_id, q) if h != h_how_to_update_min_quantity else h(q)
            if ans:
                return ans
    return None
