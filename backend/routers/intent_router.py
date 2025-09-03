# backend/services/intent_router.py
import re, unicodedata
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from models.order_model import Order
from models.order_item_model import OrderItem
from models.product_model import Product
from models.user_model import User
from models.owner_supplier_link import OwnerSupplierLink

# ---------- Normalization ----------
def normalize_he(text: str) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = t.lower().strip()
    t = re.sub(r"[\"'`~^°´•*_=+<>\\|{}]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t

# ביטויים שכיחים - מורחבים
RX_NUM      = r"(?:כמה|מספר|כמות)"
RX_ORDER    = r"(?:הזמנות?|הזמנה|order)"
RX_PRODUCT  = r"(?:מוצרים?|מוצר|product)"
RX_ACTIVE   = r"(?:פעיל(?:ים)?|פעילות|active)"
RX_OPEN     = r"(?:פתוח(?:ה)?|פתוחות?|לא הושלמה|open|ממתינ|בתהליך)"
RX_STATUS   = r"(?:סטטוס|מצב|status|מהמצב)"
RX_LAST     = r"(?:האחרונ(?:ה|ות)?|last|אחרון)"
RX_INPROC   = r"(?:בתהליך|processing|in process|מעובד)"
RX_LOWSTOCK = r"(?:מלאי נמוך|אזל(?:ו)?|חסר(?:ים)?|low stock|נגמר|נמוך)"
RX_MINQ     = r"(?:כמות מינימום|מינימום הזמנה|min(?:imum)? quantity|מינימום)"
RX_HOW      = r"(?:איך|כיצד|how|באיזה אופן)"
RX_WHICH    = r"(?:אילו|איזה|מהן|which|list|רשימה)"
RX_TOTAL    = r"(?:סכום|סהכ|עלות|total|כמה עולה|מחיר)"
RX_PRICE    = r"(?:מחיר|עלות|cost|price|כמה עולה)"
RX_CREATE   = r"(?:איך ליצור|איך להוסיף|איך לעשות|create|add|הוספה)"
RX_UPDATE   = r"(?:איך לעדכן|עדכון|update|שינוי|החלפה)"
RX_DELETE   = r"(?:איך למחוק|מחיקה|delete|הסרה)"
RX_CONNECT  = r"(?:חיבור|קישור|connection|לינק|התחברות)"
RX_SUPPLIER = r"(?:ספק|ספקים|supplier)"
RX_CLIENT   = r"(?:לקוח|לקוחות|בעל חנות|חנות|client|customer)"
RX_WHEN     = r"(?:מתי|when|בכמה זמן)"
RX_WHERE    = r"(?:איפה|בוואו|where)"
RX_BEST     = r"(?:הכי טוב|הטוב ביותר|מומלץ|best|optimal)"

# ---------- Enhanced Handlers (Supplier) ----------

def h_supplier_count_products(db: Session, supplier_id: int, q: str) -> Optional[str]:
    """כמה מוצרים יש לי? (פעילים/כולם)"""
    if re.search(fr"{RX_NUM}.*{RX_PRODUCT}", q):
        if re.search(fr"{RX_ACTIVE}", q):
            count = db.query(Product).filter(
                Product.supplier_id == supplier_id,
                Product.is_active == True
            ).count()
            return f"{count} מוצרים פעילים."
        else:
            allc = db.query(Product).filter(Product.supplier_id == supplier_id).count()
            active_c = db.query(Product).filter(
                Product.supplier_id == supplier_id,
                Product.is_active == True
            ).count()
            return f"{allc} מוצרים בסך הכל ({active_c} פעילים)."
    return None

def h_supplier_count_open_orders(db: Session, supplier_id: int, q: str) -> Optional[str]:
    """כמה הזמנות פתוחות יש?"""
    if re.search(fr"{RX_NUM}.*{RX_ORDER}.*{RX_OPEN}", q) or \
       re.search(fr"{RX_ORDER}.*{RX_OPEN}.*{RX_NUM}", q):
        cnt = db.query(Order).filter(
            Order.supplier_id == supplier_id,
            Order.status.in_(["בתהליך", "ממתינה", "אושרה"])
        ).count()
        return f"{cnt} הזמנות פתוחות (בתהליך/ממתינה/אושרה)."
    return None

def h_supplier_total_stock(db: Session, supplier_id: int, q: str) -> Optional[str]:
    """כמה מלאי יש לי בסך הכל?"""
    if re.search(r"(?:כמה|כמות).*(?:מלאי|יחידות).*(?:סהכ|בסך הכל|כולל)", q):
        total = db.query(func.coalesce(func.sum(Product.stock), 0)).filter(
            Product.supplier_id == supplier_id
        ).scalar() or 0
        active_total = db.query(func.coalesce(func.sum(Product.stock), 0)).filter(
            Product.supplier_id == supplier_id,
            Product.is_active == True
        ).scalar() or 0
        return f"מלאי כולל: {total} יחידות (מתוכן {active_total} במוצרים פעילים)."
    return None

def h_supplier_count_orders_by_status(db: Session, supplier_id: int, q: str) -> Optional[str]:
    """כמה הזמנות בסטטוס X?"""
    m = re.search(fr"{RX_NUM}.*{RX_ORDER}.*{RX_STATUS}\s+(\S+)", q)
    status = None
    if m:
        status = m.group(1)
    elif re.search(fr"{RX_NUM}.*{RX_ORDER}.*{RX_INPROC}", q):
        status = "בתהליך"
    elif re.search(r"הושלמ", q):
        status = "הושלמה"
    
    if status:
        cnt = db.query(Order).filter(Order.supplier_id == supplier_id, Order.status == status).count()
        return f"{cnt} הזמנות בסטטוס '{status}'."
    return None

def h_supplier_list_open_orders(db: Session, supplier_id: int, q: str) -> Optional[str]:
    """אילו הזמנות פתוחות יש?"""
    if re.search(fr"{RX_WHICH}.*{RX_ORDER}.*{RX_OPEN}", q) or \
       re.search(fr"{RX_ORDER}.*{RX_OPEN}.*{RX_WHICH}", q):
        rows: List[Order] = (
            db.query(Order)
              .filter(Order.supplier_id == supplier_id, 
                     Order.status.in_(["בתהליך", "ממתינה", "אושרה"]))
              .order_by(desc(Order.id)).limit(8).all()
        )
        if not rows:
            return "אין הזמנות פתוחות כרגע."
        items = []
        for o in rows:
            items_count = len(getattr(o, 'items', []))
            items.append(f"הזמנה #{o.id} | {o.status} | {items_count} פריטים")
        return "הזמנות פתוחות:\n" + "\n".join(items)
    return None

def h_supplier_low_stock(db: Session, supplier_id: int, q: str) -> Optional[str]:
    """אילו מוצרים במלאי נמוך?"""
    if re.search(fr"{RX_LOWSTOCK}", q) or re.search(fr"{RX_PRODUCT}.*נמוך", q):
        low = (db.query(Product)
                 .filter(Product.supplier_id == supplier_id,
                         Product.is_active == True,
                         Product.stock <= 5)
                 .order_by(Product.stock.asc()).limit(8).all())
        if not low:
            return "אין מוצרים במלאי נמוך (≤5) כרגע."
        
        lst = []
        for p in low:
            name = getattr(p, "product_name", f"מוצר #{getattr(p,'id','?')}")
            stock = getattr(p, "stock", 0)
            min_qty = getattr(p, "min_quantity", 0)
            lst.append(f"{name} - מלאי: {stock}, מינימום: {min_qty}")
        
        return "מוצרים במלאי נמוך:\n" + "\n".join(lst) + "\n\n💡 המלצה: עדכן כמויות במלאי או הורד כמויות מינימום."
    return None

def h_supplier_total_revenue(db: Session, supplier_id: int, q: str) -> Optional[str]:
    """מה ההכנסות/המחזור שלי?"""
    if re.search(r"(?:הכנס|מחזור|רווח|revenue).*(?:שלי|כולל|סהכ)", q):
        completed_orders = db.query(Order).filter(
            Order.supplier_id == supplier_id,
            Order.status == "הושלמה"
        ).all()
        
        total_revenue = 0.0
        for order in completed_orders:
            for item in getattr(order, 'items', []):
                try:
                    price = float(getattr(item.product, "unit_price", 0))
                    qty = int(getattr(item, "quantity", 0))
                    total_revenue += price * qty
                except:
                    pass
        
        return f"הכנסות מהזמנות שהושלמו: ₪{total_revenue:.2f} ({len(completed_orders)} הזמנות)."
    return None

def h_supplier_best_selling_products(db: Session, supplier_id: int, q: str) -> Optional[str]:
    """אילו המוצרים הנמכרים ביותר?"""
    if re.search(fr"{RX_PRODUCT}.*(?:נמכר|פופולר|{RX_BEST})", q):
        # חישוב כמויות שנמכרו לפי מוצר
        result = (db.query(
            Product.id,
            Product.product_name,
            func.sum(OrderItem.quantity).label('total_sold')
        ).join(OrderItem, Product.id == OrderItem.product_id)
         .join(Order, OrderItem.order_id == Order.id)
         .filter(Product.supplier_id == supplier_id, Order.status == "הושלמה")
         .group_by(Product.id, Product.product_name)
         .order_by(desc('total_sold'))
         .limit(5).all())
        
        if not result:
            return "עדיין אין נתונים על מכירות (אין הזמנות שהושלמו)."
        
        items = [f"{row.product_name} - נמכרו {row.total_sold} יחידות" for row in result]
        return "המוצרים הנמכרים ביותר:\n" + "\n".join(items)
    return None

def h_how_add_product(q: str) -> Optional[str]:
    """איך להוסיף מוצר חדש?"""
    if re.search(fr"{RX_CREATE}.*{RX_PRODUCT}", q) or re.search(fr"{RX_PRODUCT}.*{RX_CREATE}", q):
        return ("איך להוסיף מוצר:\n"
                "1. תפריט → מוצרים → הוספת מוצר\n"
                "2. מלא: שם מוצר, מחיר, כמות מינימום, תמונה (אופציונלי)\n"
                "3. הגדר מלאי התחלתי\n"
                "4. סמן כפעיל\n"
                "5. שמור")
    return None

def h_how_update_min_quantity(q: str) -> Optional[str]:
    """איך לעדכן כמות מינימום?"""
    if re.search(fr"{RX_HOW}.*{RX_MINQ}", q) or re.search(fr"{RX_MINQ}.*{RX_HOW}", q) or \
       re.search(fr"{RX_UPDATE}.*{RX_MINQ}", q):
        return ("עדכון כמות מינימום:\n"
                "1. תפריט → מוצרים → עריכה\n"
                "2. בחר מוצר → ערוך → 'כמות מינימום'\n"
                "3. שמור\n"
                "או עדכון מרוכז: תפריט → מוצרים → עדכון מינימום")
    return None

def h_how_export_orders(q: str) -> Optional[str]:
    """איך לייצא דוח הזמנות?"""
    if re.search(r"(?:ייצוא|export).*(?:דוח|הזמנות)", q) or \
       re.search(r"(?:דוח|הזמנות).*(?:ייצוא|export)", q):
        return ("ייצוא דוח הזמנות:\n"
                "1. תפריט → הזמנות → ייצוא\n"
                "2. בחר טווח תאריכים\n"
                "3. בחר סטטוס (אופציונלי)\n"
                "4. לחץ 'ייצוא ל-Excel'\n"
                "נדרשת הרשאת orders.export")
    return None

def h_supplier_connections_count(db: Session, supplier_id: int, q: str) -> Optional[str]:
    """כמה חיבורים פעילים יש לי?"""
    if re.search(fr"{RX_NUM}.*{RX_CONNECT}.*{RX_ACTIVE}", q) or \
       re.search(fr"{RX_CONNECT}.*{RX_NUM}", q):
        cnt = db.query(OwnerSupplierLink).filter(
            OwnerSupplierLink.supplier_id == supplier_id,
            OwnerSupplierLink.status == "APPROVED",
        ).count()
        pending_cnt = db.query(OwnerSupplierLink).filter(
            OwnerSupplierLink.supplier_id == supplier_id,
            OwnerSupplierLink.status == "PENDING",
        ).count()
        return f"{cnt} חיבורים פעילים עם בעלי חנויות" + (f" ({pending_cnt} ממתינים לאישור)." if pending_cnt else ".")
    return None

def h_order_status_by_id_supplier(db: Session, supplier_id: int, q: str) -> Optional[str]:
    """מה סטטוס הזמנה מספר X?"""
    if re.search(fr"{RX_STATUS}.*{RX_ORDER}", q) or re.search(fr"{RX_ORDER}.*{RX_STATUS}", q):
        oid = _extract_order_id(q)
        if not oid:
            return "לא זוהה מספר הזמנה. נא לציין מספר הזמנה (לדוגמה: #1234)."
        o = db.query(Order).filter(Order.id == oid, Order.supplier_id == supplier_id).first()
        if not o:
            return f"לא נמצאה הזמנה #{oid} אצל הספק."
        
        items_count = len(getattr(o, 'items', []))
        return f"הזמנה #{o.id}: סטטוס '{o.status}', {items_count} פריטים."
    return None

# ---------- Enhanced Handlers (Owner) ----------

def h_owner_last_order_status(db: Session, owner_id: int, q: str) -> Optional[str]:
    """מה סטטוס ההזמנה האחרונה?"""
    if re.search(fr"{RX_STATUS}.*{RX_ORDER}.*{RX_LAST}", q) or \
       re.search(fr"{RX_ORDER}.*{RX_LAST}.*{RX_STATUS}", q):
        last = db.query(Order).filter(Order.owner_id == owner_id).order_by(desc(Order.id)).first()
        if not last:
            return "אין הזמנות עדיין."
        
        items_count = len(getattr(last, 'items', []))
        supplier = db.query(User).filter(User.id == last.supplier_id).first()
        supplier_name = getattr(supplier, "username", f"ספק #{last.supplier_id}") if supplier else "ספק לא ידוע"
        
        return f"הזמנה אחרונה #{last.id}: סטטוס '{last.status}', {items_count} פריטים, ספק: {supplier_name}."
    return None

def h_owner_orders_count(db: Session, owner_id: int, q: str) -> Optional[str]:
    """כמה הזמנות ביצעתי?"""
    if re.search(fr"{RX_NUM}.*{RX_ORDER}", q):
        total_cnt = db.query(Order).filter(Order.owner_id == owner_id).count()
        open_cnt = db.query(Order).filter(
            Order.owner_id == owner_id,
            Order.status.in_(["בתהליך", "ממתינה", "אושרה"])
        ).count()
        completed_cnt = db.query(Order).filter(
            Order.owner_id == owner_id,
            Order.status == "הושלמה"
        ).count()
        return f"{total_cnt} הזמנות בסך הכל ({open_cnt} פתוחות, {completed_cnt} הושלמו)."
    return None

def h_owner_last_order_total(db: Session, owner_id: int, q: str) -> Optional[str]:
    """כמה עולה ההזמנה האחרונה?"""
    if re.search(fr"{RX_TOTAL}.*{RX_ORDER}.*{RX_LAST}", q) or \
       re.search(fr"{RX_PRICE}.*{RX_ORDER}.*{RX_LAST}", q):
        last = db.query(Order).filter(Order.owner_id == owner_id).order_by(desc(Order.id)).first()
        if not last:
            return "אין הזמנות עדיין."
        
        total = 0.0
        items_details = []
        for item in getattr(last, 'items', []):
            try:
                price = float(getattr(item.product, "unit_price", 0.0))
                qty = int(getattr(item, "quantity", 0))
                item_total = price * qty
                total += item_total
                product_name = getattr(item.product, "product_name", f"מוצר #{item.product_id}")
                items_details.append(f"{product_name}: {qty}×₪{price:.2f}")
            except:
                pass
        
        details = ", ".join(items_details[:3])
        if len(items_details) > 3:
            details += f" ו-{len(items_details)-3} נוספים"
            
        return f"הזמנה #{last.id}: ₪{total:.2f} ({details})"
    return None

def h_owner_total_spending(db: Session, owner_id: int, q: str) -> Optional[str]:
    """כמה הוצאתי בסך הכל?"""
    if re.search(r"(?:הוצאות|הוצאתי|כמה הוצאתי|total.*spent)", q):
        orders = db.query(Order).filter(Order.owner_id == owner_id).all()
        total_spent = 0.0
        completed_orders = 0
        
        for order in orders:
            if order.status == "הושלמה":
                completed_orders += 1
                for item in getattr(order, 'items', []):
                    try:
                        price = float(getattr(item.product, "unit_price", 0))
                        qty = int(getattr(item, "quantity", 0))
                        total_spent += price * qty
                    except:
                        pass
        
        return f"הוצאות כוללות: ₪{total_spent:.2f} על {completed_orders} הזמנות שהושלמו."
    return None

def h_owner_active_links_count(db: Session, owner_id: int, q: str) -> Optional[str]:
    """כמה חיבורים פעילים יש לי?"""
    if re.search(fr"{RX_NUM}.*{RX_CONNECT}.*{RX_ACTIVE}", q):
        cnt = db.query(OwnerSupplierLink).filter(
            OwnerSupplierLink.owner_id == owner_id,
            OwnerSupplierLink.status == "APPROVED",
        ).count()
        pending_cnt = db.query(OwnerSupplierLink).filter(
            OwnerSupplierLink.owner_id == owner_id,
            OwnerSupplierLink.status == "PENDING",
        ).count()
        return f"{cnt} חיבורים פעילים לספקים" + (f" ({pending_cnt} ממתינים לאישור)." if pending_cnt else ".")
    return None

def h_owner_suppliers_names(db: Session, owner_id: int, q: str) -> Optional[str]:
    """מאילו ספקים הזמנתי?"""
    if re.search(r"(?:מאיזה|ממי|אילו).*{RX_SUPPLIER}.*הזמנתי", q) or \
       re.search(fr"{RX_SUPPLIER}.*(?:שהזמנתי|שקניתי)", q):
        rows = db.query(Order.supplier_id).filter(Order.owner_id == owner_id).distinct().all()
        supplier_ids = [r[0] for r in rows if r and r[0]]
        if not supplier_ids:
            return "לא נמצאו ספקים שהוזמנו מהם עדיין."
        
        suppliers = db.query(User).filter(User.id.in_(supplier_ids[:8])).all()
        names_with_stats = []
        for s in suppliers:
            name = getattr(s, "username", None) or getattr(s, "contact_name", f"ספק #{s.id}")
            order_count = db.query(Order).filter(
                Order.owner_id == owner_id, 
                Order.supplier_id == s.id
            ).count()
            names_with_stats.append(f"{name} ({order_count} הזמנות)")
        
        return "ספקים שהוזמנו מהם:\n" + "\n".join(names_with_stats)
    return None

def h_order_status_by_id_owner(db: Session, owner_id: int, q: str) -> Optional[str]:
    """מה סטטוס הזמנה מספר X?"""
    if re.search(fr"{RX_STATUS}.*{RX_ORDER}", q) or re.search(fr"{RX_ORDER}.*{RX_STATUS}", q):
        oid = _extract_order_id(q)
        if not oid:
            return "לא זוהה מספר הזמנה. נא לציין מספר הזמנה (לדוגמה: #1234)."
        o = db.query(Order).filter(Order.id == oid, Order.owner_id == owner_id).first()
        if not o:
            return f"לא נמצאה הזמנה #{oid} אצל בעל החנות."
        
        items_count = len(getattr(o, 'items', []))
        supplier = db.query(User).filter(User.id == o.supplier_id).first()
        supplier_name = getattr(supplier, "username", f"ספק #{o.supplier_id}") if supplier else "ספק לא ידוע"
        
        return f"הזמנה #{o.id}: סטטוס '{o.status}', ספק: {supplier_name}, {items_count} פריטים."
    return None

def h_how_create_order(q: str) -> Optional[str]:
    """איך ליצור הזמנה חדשה?"""
    if re.search(fr"{RX_CREATE}.*{RX_ORDER}", q) or re.search(fr"{RX_HOW}.*הזמן", q):
        return ("יצירת הזמנה חדשה:\n"
                "1. תפריט → הזמנות → הזמנה חדשה\n"
                "2. בחר ספק מהרשימה\n"
                "3. בחר מוצרים + כמויות\n"
                "4. בדוק סיכום ועלויות\n"
                "5. שלח הזמנה\n"
                "💡 זכור לבדוק כמויות מינימום של הספק")
    return None

def h_when_order_arrive(db: Session, owner_id: int, q: str) -> Optional[str]:
    """מתי תגיע ההזמנה?"""
    if re.search(fr"{RX_WHEN}.*{RX_ORDER}", q) or re.search(r"מתי.*(?:תגיע|תהיה מוכנה)", q):
        # מחפש הזמנה פתוחה אחרונה
        last_open = db.query(Order).filter(
            Order.owner_id == owner_id,
            Order.status.in_(["בתהליך", "ממתינה", "אושרה"])
        ).order_by(desc(Order.id)).first()
        
        if not last_open:
            return "אין הזמנות פתוחות כרגע."
        
        status_msg = {
            "ממתינה": "הספק עדיין לא אישר את ההזמנה",
            "אושרה": "הספק אישר - מכין להשלחה",
            "בתהליך": "ההזמנה מעובדת אצל הספק"
        }.get(last_open.status, "סטטוס לא ידוע")
        
        return f"הזמנה #{last_open.id}: {status_msg}. צור קשר עם הספק לפרטי משלוח."
    return None

# ---------- Utility Functions ----------

def _extract_order_id(q: str) -> Optional[int]:
    """מחלץ מספר הזמנה מהשאלה"""
    # מחפש מספרים של 3+ ספרות, עם או בלי #
    m = re.search(r"(?:#?\s?)(\d{3,})", q)
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    return None

def _extract_product_name(q: str) -> Optional[str]:
    """מנסה לחלץ שם מוצר מהשאלה"""
    # מחפש מילים בעברית אחרי "מוצר" או בתוך גרשיים
    m = re.search(r'(?:מוצר|product)\s+"?([א-תa-zA-Z0-9\s]{2,})"?', q)
    if m:
        return m.group(1).strip()
    
    # מחפש טקסט בגרשיים
    m = re.search(r'"([א-תa-zA-Z0-9\s]{2,})"', q)
    if m:
        return m.group(1).strip()
    return None

# ---------- Main Router Function ----------

def route_intent_and_answer(db: Session, role: str, user_id: int, question: str) -> Optional[str]:
    """נתב מחודד עם זיהוי דפוסי שאלות מורחב"""
    q = normalize_he(question)
    
    if role == "Supplier":
        # הנדלרים לספק - לפי סדר עדיפות
        handlers = [
            h_supplier_count_products,
            h_supplier_count_open_orders, 
            h_supplier_total_stock,
            h_supplier_count_orders_by_status,
            h_supplier_list_open_orders,
            h_supplier_low_stock,
            h_supplier_total_revenue,
            h_supplier_best_selling_products,
            h_supplier_connections_count,
            h_order_status_by_id_supplier,
            # הנדלרים ללא DB
            h_how_add_product,
            h_how_update_min_quantity,
            h_how_export_orders,
        ]
        
        for handler in handlers:
            try:
                if handler.__name__.startswith('h_how_') or handler.__name__ in ['h_how_add_product', 'h_how_update_min_quantity', 'h_how_export_orders']:
                    # הנדלרים ללא DB - רק עם השאלה
                    ans = handler(q)
                else:
                    # הנדלרים עם DB
                    ans = handler(db, user_id, q)
                
                if ans:
                    return ans
            except Exception as e:
                print(f"Error in handler {handler.__name__}: {e}")
                continue
                
    else:  # StoreOwner
        handlers = [
            h_owner_orders_count,
            h_owner_last_order_status,
            h_owner_last_order_total,
            h_owner_total_spending,
            h_owner_active_links_count,
            h_owner_suppliers_names,
            h_order_status_by_id_owner,
            h_when_order_arrive,
            # הנדלרים ללא DB
            h_how_create_order,
            h_how_update_min_quantity,
            h_how_export_orders,
        ]
        
        for handler in handlers:
            try:
                if handler.__name__.startswith('h_how_') or handler.__name__ in ['h_how_create_order', 'h_how_update_min_quantity', 'h_how_export_orders']:
                    ans = handler(q)
                else:
                    ans = handler(db, user_id, q)
                
                if ans:
                    return ans
            except Exception as e:
                print(f"Error in handler {handler.__name__}: {e}")
                continue
    
    return None