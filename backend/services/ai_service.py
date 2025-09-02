# backend/services/ai_service.py
import os, textwrap, requests, time
from typing import List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from models.user_model import User
from models.product_model import Product
from models.order_model import Order
from models.order_item_model import OrderItem
from routers.intent_router import route_intent_and_answer

# -------- הגדרות מודל / אופציות --------
OLLAMA_BASE = os.getenv("OLLAMA_URL", "http://localhost:11434")
# מומלץ לדייק יותר ממודל 0.5B קטן:
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")

GEN_OPTIONS = {
    "num_predict": int(os.getenv("AI_NUM_PREDICT", "96")),
    "num_ctx": int(os.getenv("AI_NUM_CTX", "1024")),
    "temperature": float(os.getenv("AI_TEMPERATURE", "0.1")),
    "top_p": float(os.getenv("AI_TOP_P", "0.8")),
    "repeat_penalty": float(os.getenv("AI_REPEAT_PENALTY", "1.15")),
}

# -------- עזר בסיסי --------
def _fetch_user(db: Session, uid: int) -> User | None:
    return db.query(User).filter(User.id == uid).first()

def _resolve_role(u: User) -> str:
    # חלק מהפרויקטים שומרים role בשם userType; נכסה את שני המקרים
    role = getattr(u, "userType", None) or getattr(u, "role", None) or ""
    return str(role)

# -------- שליפות להזמנות / מוצרים --------
def get_orders_for_supplier(db: Session, supplier_id: int, limit: int = 10, only_open: bool = True) -> List[Order]:
    q = db.query(Order).options(joinedload(Order.items).joinedload(OrderItem.product)) \
        .filter(Order.supplier_id == supplier_id)
    if only_open:
        q = q.filter(Order.status != "הושלמה")
    return q.order_by(desc(Order.id)).limit(limit).all()

def get_orders_for_owner(db: Session, owner_id: int, limit: int = 10) -> List[Order]:
    return (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .filter(Order.owner_id == owner_id)
        .order_by(desc(Order.id))
        .limit(limit)
        .all()
    )

def get_top_low_stock_products(db: Session, supplier_id: int, threshold: int = 5, limit: int = 5) -> List[Product]:
    # מוצרים עם מלאי נמוך אצל ספק
    return (
        db.query(Product)
        .filter(Product.supplier_id == supplier_id, Product.is_active == True, Product.stock <= threshold)
        .order_by(Product.stock.asc())
        .limit(limit)
        .all()
    )

def count_active_products(db: Session, supplier_id: int) -> int:
    return db.query(Product).filter(Product.supplier_id == supplier_id, Product.is_active == True).count()

def sum_total_stock(db: Session, supplier_id: int) -> int:
    return int(db.query(func.coalesce(func.sum(Product.stock), 0)).filter(Product.supplier_id == supplier_id).scalar() or 0)

# -------- בניית Snapshot עשיר --------
def supplier_snapshot(db: Session, supplier_id: int) -> str:
    active_products = count_active_products(db, supplier_id)
    total_stock = sum_total_stock(db, supplier_id)
    open_orders = len(get_orders_for_supplier(db, supplier_id, limit=50, only_open=True))
    low_stock = get_top_low_stock_products(db, supplier_id, threshold=5, limit=5)
    low_lines = []
    for p in low_stock:
        # ננסה שם מוצר; אם אין, נציג מזהה
        pname = getattr(p, "name", None) or f"Product#{getattr(p, 'id', '?')}"
        low_lines.append(f"{pname} (stock={getattr(p, 'stock', 0)})")
    low_txt = ", ".join(low_lines) if low_lines else "—"

    # 3 הזמנות פתוחות אחרונות
    recent_open = get_orders_for_supplier(db, supplier_id, limit=3, only_open=True)
    ord_lines = []
    for o in recent_open:
        ord_lines.append(f"#{o.id} | פריטים: {len(o.items)} | סטטוס: {o.status}")

    return (
        "Supplier snapshot:\n"
        f"- Active products: {active_products}\n"
        f"- Total stock: {total_stock}\n"
        f"- Open orders: {open_orders}\n"
        f"- Low stock (<=5) top: {low_txt}\n"
        + ("- Recent open orders:\n  " + "\n  ".join(ord_lines) if ord_lines else "- Recent open orders: —")
    )

def owner_snapshot(db: Session, owner_id: int) -> str:
    last_orders = get_orders_for_owner(db, owner_id, limit=5)
    lines = []
    for o in last_orders:
        # חישוב סכום הזמנה – זהיר אם unit_price לא קיים
        total = 0.0
        for it in o.items:
            unit_price = getattr(it.product, "unit_price", 0.0)
            qty = getattr(it, "quantity", 0)
            try:
                total += float(unit_price) * int(qty)
            except Exception:
                pass
        lines.append(f"- הזמנה #{o.id} | סטטוס: {o.status} | סכום משוער: {total:.2f}")
    if not lines:
        lines.append("- אין הזמנות קודמות.")
    return "Recent owner orders:\n" + "\n".join(lines)

# -------- בניית פרומפט “קשוח” --------
def build_prompt(role: str, username: str, context: str, question: str) -> str:
    role_he = "ספק" if role == "Supplier" else "בעל חנות"
    # קיצוץ הקשר כדי לא להעמיס על המודל
    ctx = context if len(context) <= 900 else (context[:900] + " ...")
    return f"""
אתה עוזר {role_he} במערכת הזמנות. ענה תמיד בעברית, קצר ומדויק (שורה-שתיים).
השתמש אך ורק במידע הבא (Context). אם אין מידע מספיק – כתוב "לא יודע" ולא תנחש.

[Context]
{ctx}

[כללים]
- אין להמציא נתונים שאינם מופיעים ב-Context.
- אם השאלה מבקשת ספירה/מספר – החזר מספר מדויק + הסבר קצר.
- אם שואלים "איך" – ענה בשלבים תמציתיים (3–4 צעדים).
- אם אין תשובה בהקשר: "לא יודע. נסה לציין מוצר/הזמנה ספציפיים."

[שאלה]
{question}
""".strip()

# -------- קריאה ל-Ollama --------
def ask_ollama_generate(prompt: str) -> str:
    url = f"{OLLAMA_BASE}/api/generate"
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "options": GEN_OPTIONS}
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    return (r.json() or {}).get("response", "").strip()

# -------- API-level wrappers --------
def answer_question(db: Session, question: str, user_id: int) -> str:
    u = _fetch_user(db, user_id)
    if not u:
        return "לא נמצא משתמש."
    role = _resolve_role(u)
    username = getattr(u, "username", None) or getattr(u, "contact_name", "user")

    # 1) נסה קודם תשובה דטרמיניסטית מה-DB (Intent Router)
    intent_ans = route_intent_and_answer(db, role, u.id, question)
    if intent_ans:
        return intent_ans  # מדויק ומהיר

    # 2) אם אין כוונה מזוהה — בונים הקשר וניגשים ל-LLM
    if role == "Supplier":
        ctx = supplier_snapshot(db, u.id)
    else:
        ctx = owner_snapshot(db, u.id)
    prompt = build_prompt(role, username, ctx, question)
    return ask_ollama_generate(prompt)


# Cache קטן ל-Snapshot (אם תרצי להשתמש ב-/context מחוץ ל/ask)
_cache: dict[str, tuple[float, str]] = {}
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
    if role == "Supplier":
        snap = _get_cached(f"snap:supp:{u.id}", lambda: supplier_snapshot(db, u.id))
    else:
        snap = _get_cached(f"snap:owner:{u.id}", lambda: owner_snapshot(db, u.id))
    return {"user_id": u.id, "username": getattr(u, "username", "") or getattr(u, "contact_name", ""), "role": role, "snapshot": snap}
