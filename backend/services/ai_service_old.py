# backend/services/ai_service.py
# Intent-first → Enhanced Snapshot → Rich Prompt → LLM (Ollama)

import os, requests, time
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models.user_model import User
from models.product_model import Product
from models.order_model import Order
from models.order_item_model import OrderItem
from models.owner_supplier_link import OwnerSupplierLink

from services.context_builder import build_supplier_context, build_owner_context
from services.context_to_prompt import (
    supplier_context_to_text,
    owner_context_to_text,
    build_system_prompt,
    few_shots,
    join_prompt,
)
from routers.intent_router import route_intent_and_answer

# ---- LLM provider (Ollama) ----
OLLAMA_BASE  = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b-instruct")

GEN_OPTIONS = {
    "num_predict": int(os.getenv("AI_NUM_PREDICT", "256")),
    "num_ctx": int(os.getenv("AI_NUM_CTX", "4096")),
    "temperature": float(os.getenv("AI_TEMPERATURE", "0.2")),
    "top_p": float(os.getenv("AI_TOP_P", "0.9")),
    "repeat_penalty": float(os.getenv("AI_REPEAT_PENALTY", "1.1")),
}

# ---- Helpers ----
def _fetch_user(db: Session, uid: int) -> User | None:
    return db.query(User).filter(User.id == uid).first()

def _resolve_role(u: User) -> str:
    r = (getattr(u, "role", None) or getattr(u, "userType", "")).strip().lower()
    if r in ("supplier", "ספק", "2"): return "Supplier"
    if r in ("storeowner", "owner", "store_owner", "בעל חנות", "1"): return "StoreOwner"
    return "StoreOwner"

def _ollama_generate(prompt: str) -> str:
    url = f"{OLLAMA_BASE}/api/generate"
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "options": GEN_OPTIONS}
    r = requests.post(url, json=payload, timeout=90)
    r.raise_for_status()
    return (r.json() or {}).get("response", "").strip()

# ---- Enhanced Snapshot Builders ----

def get_orders_for_supplier(db: Session, supplier_id: int, limit: int = 50, only_open: bool = False) -> list:
    """מחזיר הזמנות עבור ספק עם פרטים מלאים"""
    query = db.query(Order).filter(Order.supplier_id == supplier_id)
    if only_open:
        query = query.filter(Order.status.in_(["בתהליך", "אושרה", "ממתינה"]))
    return query.order_by(desc(Order.id)).limit(limit).all()

def get_orders_for_owner(db: Session, owner_id: int, limit: int = 50) -> list:
    """מחזיר הזמנות עבור בעל חנות עם פרטים מלאים"""
    return (db.query(Order)
            .filter(Order.owner_id == owner_id)
            .order_by(desc(Order.id))
            .limit(limit)
            .all())

def get_top_low_stock_products(db: Session, supplier_id: int, threshold: int = 5, limit: int = 10):
    """מחזיר מוצרים עם מלאי נמוך"""
    return (db.query(Product)
            .filter(Product.supplier_id == supplier_id, 
                   Product.is_active == True, 
                   Product.stock <= threshold)
            .order_by(Product.stock.asc())
            .limit(limit)
            .all())

def count_active_products(db: Session, supplier_id: int) -> int:
    return db.query(Product).filter(Product.supplier_id == supplier_id, Product.is_active == True).count()

def sum_total_stock(db: Session, supplier_id: int) -> int:
    return int(db.query(func.coalesce(func.sum(Product.stock), 0)).filter(Product.supplier_id == supplier_id).scalar() or 0)

def get_recent_order_items(db: Session, order_id: int):
    """מחזיר פריטי הזמנה לפי ID"""
    return db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

def get_supplier_names_for_owner(db: Session, owner_id: int, limit: int = 5):
    """מחזיר שמות הספקים שבעל החנות הזמין מהם"""
    supplier_ids = (db.query(Order.supplier_id)
                   .filter(Order.owner_id == owner_id)
                   .distinct()
                   .limit(limit)
                   .all())
    if not supplier_ids:
        return []
    
    ids = [sid[0] for sid in supplier_ids]
    suppliers = db.query(User).filter(User.id.in_(ids)).all()
    return [(s.id, getattr(s, "username", "") or getattr(s, "contact_name", f"Supplier#{s.id}")) for s in suppliers]

def get_active_supplier_connections(db: Session, owner_id: int):
    """מחזיר חיבורים פעילים עבור בעל חנות"""
    return (db.query(OwnerSupplierLink)
           .filter(OwnerSupplierLink.owner_id == owner_id,
                  OwnerSupplierLink.status == "APPROVED")
           .all())

def get_active_owner_connections(db: Session, supplier_id: int):
    """מחזיר חיבורים פעילים עבור ספק"""
    return (db.query(OwnerSupplierLink)
           .filter(OwnerSupplierLink.supplier_id == supplier_id,
                  OwnerSupplierLink.status == "APPROVED")
           .all())

# ---- Enhanced Snapshot Builders for AI ----

def supplier_snapshot(db: Session, supplier_id: int) -> str:
    """בונה snapshot מפורט לספק עם כל המידע הרלוונטי"""
    user = _fetch_user(db, supplier_id)
    username = getattr(user, "username", "") or getattr(user, "contact_name", f"Supplier#{supplier_id}")
    
    # סטטיסטיקות בסיסיות
    active_products = count_active_products(db, supplier_id)
    total_products = db.query(Product).filter(Product.supplier_id == supplier_id).count()
    total_stock = sum_total_stock(db, supplier_id)
    
    # הזמנות
    open_orders = get_orders_for_supplier(db, supplier_id, limit=50, only_open=True)
    recent_orders = get_orders_for_supplier(db, supplier_id, limit=20, only_open=False)
    
    # מוצרים במלאי נמוך
    low_stock_products = get_top_low_stock_products(db, supplier_id, threshold=5, limit=8)
    
    # חיבורים פעילים
    active_connections = get_active_owner_connections(db, supplier_id)
    
    # פורמט הזמנות פתוחות
    open_orders_text = []
    for order in open_orders[:10]:  # מגביל ל-10 הזמנות אחרונות
        items_count = len(order.items) if hasattr(order, 'items') else 0
        order_total = 0
        for item in (order.items if hasattr(order, 'items') else []):
            try:
                price = float(getattr(item.product, "unit_price", 0))
                qty = int(getattr(item, "quantity", 0))
                order_total += price * qty
            except:
                pass
        open_orders_text.append(f"הזמנה #{order.id} - {order.status} - {items_count} פריטים - ₪{order_total:.2f}")
    
    # מוצרים במלאי נמוך
    low_stock_text = []
    for product in low_stock_products:
        name = getattr(product, "product_name", f"מוצר #{product.id}")
        stock = getattr(product, "stock", 0)
        min_qty = getattr(product, "min_quantity", 0)
        low_stock_text.append(f"{name} - מלאי: {stock}, מינימום: {min_qty}")
    
    # הזמנות אחרונות (כולל סגורות)
    recent_orders_text = []
    for order in recent_orders[:15]:
        items_count = len(order.items) if hasattr(order, 'items') else 0
        recent_orders_text.append(f"הזמנה #{order.id} - {order.status} - {items_count} פריטים")
    
    return f"""=== פרופיל ספק: {username} ===

📊 סטטיסטיקות:
- מוצרים פעילים: {active_products} מתוך {total_products}
- מלאי כולל: {total_stock} יחידות
- הזמנות פתוחות: {len(open_orders)}
- חיבורים פעילים לבעלי חנויות: {len(active_connections)}

🔴 הזמנות פתוחות ({len(open_orders)}):
{chr(10).join(open_orders_text) if open_orders_text else "אין הזמנות פתוחות"}

⚠️ מוצרים במלאי נמוך ({len(low_stock_products)}):
{chr(10).join(low_stock_text) if low_stock_text else "אין מוצרים במלאי נמוך"}

📋 הזמנות אחרונות:
{chr(10).join(recent_orders_text[:8]) if recent_orders_text else "אין הזמנות"}

💼 פעולות זמינות:
- עדכון מלאי מוצרים
- עדכון כמויות מינימום
- סימון הזמנות כהושלמו
- הוספת מוצרים חדשים
- ייצוא דוחות הזמנות
- ניהול חיבורים עם בעלי חנויות"""

def owner_snapshot(db: Session, owner_id: int) -> str:
    """בונה snapshot מפורט לבעל חנות עם כל המידע הרלוונטי"""
    user = _fetch_user(db, owner_id)
    username = getattr(user, "username", "") or getattr(user, "contact_name", f"Owner#{owner_id}")
    
    # הזמנות
    recent_orders = get_orders_for_owner(db, owner_id, limit=30)
    open_orders = [o for o in recent_orders if o.status in ["בתהליך", "אושרה", "ממתינה"]]
    
    # ספקים
    supplier_names = get_supplier_names_for_owner(db, owner_id, limit=10)
    
    # חיבורים פעילים
    active_connections = get_active_supplier_connections(db, owner_id)
    
    # פורמט הזמנות אחרונות עם פרטים
    orders_text = []
    total_spent = 0
    for order in recent_orders[:12]:
        items_count = len(order.items) if hasattr(order, 'items') else 0
        order_total = 0
        for item in (order.items if hasattr(order, 'items') else []):
            try:
                price = float(getattr(item.product, "unit_price", 0))
                qty = int(getattr(item, "quantity", 0))
                order_total += price * qty
            except:
                pass
        total_spent += order_total
        
        # מידע על הספק
        supplier_name = "לא ידוע"
        for sid, sname in supplier_names:
            if sid == order.supplier_id:
                supplier_name = sname
                break
                
        orders_text.append(f"הזמנה #{order.id} - {order.status} - ספק: {supplier_name} - {items_count} פריטים - ₪{order_total:.2f}")
    
    # הזמנות פתוחות
    open_orders_text = []
    for order in open_orders:
        items_count = len(order.items) if hasattr(order, 'items') else 0
        supplier_name = "לא ידוע"
        for sid, sname in supplier_names:
            if sid == order.supplier_id:
                supplier_name = sname
                break
        open_orders_text.append(f"הזמנה #{order.id} - {order.status} - ספק: {supplier_name} - {items_count} פריטים")
    
    return f"""=== פרופיל בעל חנות: {username} ===

📊 סטטיסטיקות:
- סך הזמנות: {len(recent_orders)}
- הזמנות פתוחות: {len(open_orders)}
- ספקים שהוזמן מהם: {len(supplier_names)}
- חיבורים פעילים לספקים: {len(active_connections)}
- סכום הוצאות אחרונות: ₪{total_spent:.2f}

🔴 הזמנות פתוחות ({len(open_orders)}):
{chr(10).join(open_orders_text) if open_orders_text else "אין הזמנות פתוחות"}

📋 הזמנות אחרונות:
{chr(10).join(orders_text[:8]) if orders_text else "אין הזמנות"}

🏪 הספקים שלי:
{chr(10).join([f"- {name} (ID: {sid})" for sid, name in supplier_names]) if supplier_names else "לא הוזמן מאף ספק עדיין"}

💼 פעולות זמינות:
- יצירת הזמנה חדשה
- בדיקת סטטוס הזמנות
- חיפוש מוצרים לפי ספק
- ניהול חיבורים לספקים
- הזמנה חוזרת מהזמנות קודמות
- ייצוא דוחות הזמנות"""

# ---- Enhanced Prompt Builder ----

def build_smart_prompt(role: str, username: str, context: str, question: str) -> str:
    """בונה פרומפט חכם ומפורט"""
    role_he = "ספק" if role == "Supplier" else "בעל חנות"
    
    # מערכת פרומפטים ספציפית לתפקיד
    if role == "Supplier":
        system_context = """אתה עוזר חכם לספק במערכת ניהול הזמנות. אתה מכיר לעומק את תחום הספקות והעסקים.

יכולות מיוחדות שלך:
- ענה על שאלות על מלאי, מוצרים, כמויות מינימום
- סייע בניהול הזמנות ועדכון סטטוסים
- תן עצות עסקיות לשיפור המכירות
- הסבר על תהליכי עבודה במערכת
- חשב סכומים ותן ניתוחים פיננסיים
- זהה מגמות והמלץ על פעולות

כללי מענה:
- תמיד ענה בעברית
- התחל בתשובה ישירה ומדויקת
- הוסף המלצות מעשיות כשרלוונטי
- השתמש במספרים מדויקים מההקשר
- אם אין מידע מספיק, בקש פירוט"""
    else:
        system_context = """אתה עוזר חכם לבעל חנות במערכת ניהול הזמנות. אתה מכיר לעומק את תחום קמעונאות וניהול חנויות.

יכולות מיוחדות שלך:
- עזור ביצירת הזמנות ובחירת ספקים
- סייע בעקיבה אחר סטטוס הזמנות
- תן עצות לאופטימיזציה של הזמנות
- הסבר על תהליכי הזמנה במערכת
- נתח עלויות והוצאות
- המלץ על ספקים ומוצרים

כללי מענה:
- תמיד ענה בעברית
- התחל בתשובה ישירה ומדויקת
- הוסף המלצות מעשיות כשרלוונטי
- השתמש במספרים מדויקים מההקשר
- אם אין מידע מספיק, בקש פירוט"""
    
    return f"""{system_context}

=== המידע הזמין עליך ===
{context}

=== השאלה ===
{question}

ענה בצורה חכמה, מדויקת ומועילה:"""

# ---- Main API Functions ----

def answer_question(db: Session, question: str, user_id: int) -> str:
    u = _fetch_user(db, user_id)
    if not u:
        return "לא נמצא משתמש."
    role = _resolve_role(u)
    username = getattr(u, "username", "") or getattr(u, "contact_name", "user")

    # 1) Intent-first (דטרמיניסטי)
    ans = route_intent_and_answer(db, role, u.id, question)
    if ans:
        return ans

    # 2) Context → Enhanced Prompt → LLM
    if role == "Supplier":
        snapshot_text = supplier_snapshot(db, u.id)
    else:
        snapshot_text = owner_snapshot(db, u.id)

    full_prompt = build_smart_prompt(role, username, snapshot_text, question)

    # 3) LLM
    try:
        out = _ollama_generate(full_prompt)
        return out or "לא יודע"
    except Exception as e:
        return f"שגיאה בחיבור למודל AI: {str(e)}"

# Cache for performance
_cache = {}
def _get_cached(key: str, builder, ttl: int = 60) -> str:
    now = time.time()
    if key in _cache and now - _cache[key][0] < ttl:
        return _cache[key][1]
    val = builder()
    _cache[key] = (now, val)
    return val

def get_context(db: Session, user_id: int):
    u = _fetch_user(db, user_id)
    if not u:
        return None
    role = _resolve_role(u)
    username = getattr(u, "username", "") or getattr(u, "contact_name", "")

    # משתמש ב-cache לביצועים
    if role == "Supplier":
        snapshot_text = _get_cached(f"snap:supp:{u.id}", lambda: supplier_snapshot(db, u.id), ttl=30)
    else:
        snapshot_text = _get_cached(f"snap:owner:{u.id}", lambda: owner_snapshot(db, u.id), ttl=30)

    return {
        "user_id": u.id,
        "username": username,
        "role": role,
        "snapshot": snapshot_text,
    }

# לשימוש /ai/stream
def build_prompt(role: str, username: str, ctx_text: str, question: str) -> str:
    return build_smart_prompt(role, username, ctx_text, question)