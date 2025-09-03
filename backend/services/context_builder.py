# backend/services/context_builder.py
# בונה Snapshot עשיר מאוד לשני התפקידים: Supplier / StoreOwner

from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta

from models.user_model import User
from models.product_model import Product
from models.order_model import Order
from models.order_item_model import OrderItem
from models.owner_supplier_link import OwnerSupplierLink

# ----------------- Enhanced Utils -----------------

def _safe_int(v, default=0) -> int:
    try:
        return int(v or 0)
    except Exception:
        return default

def _safe_float(v, default=0.0) -> float:
    try:
        return float(v or 0.0)
    except Exception:
        return default

def _sum(q):
    return func.coalesce(func.sum(q), 0)

def _format_currency(amount: float) -> str:
    return f"₪{amount:.2f}"

# ----------------- Enhanced Data Fetchers -----------------

def fetch_supplier_products_detailed(db: Session, supplier_id: int, limit: int = 250) -> List[Dict]:
    """מחזיר מוצרים עם פרטים מלאים"""
    products = (db.query(Product)
                .filter(Product.supplier_id == supplier_id)
                .order_by(Product.id.desc())
                .limit(limit).all())
    
    result = []
    for p in products:
        # חישוב כמה נמכר מהמוצר
        sold_qty = db.query(func.coalesce(func.sum(OrderItem.quantity), 0)).join(
            Order, OrderItem.order_id == Order.id
        ).filter(
            OrderItem.product_id == p.id,
            Order.status == "הושלמה"
        ).scalar() or 0
        
        result.append({
            "id": p.id,
            "name": getattr(p, "product_name", f"מוצר #{p.id}"),
            "price": _safe_float(getattr(p, "unit_price", 0)),
            "stock": _safe_int(getattr(p, "stock", 0)),
            "min_quantity": _safe_int(getattr(p, "min_quantity", 0)),
            "is_active": bool(getattr(p, "is_active", False)),
            "sold_total": sold_qty,
            "revenue": sold_qty * _safe_float(getattr(p, "unit_price", 0))
        })
    
    return result

def fetch_enhanced_orders(db: Session, user_id: int, is_supplier: bool, limit: int = 60) -> List[Dict]:
    """מחזיר הזמנות עם פרטים מורחבים"""
    if is_supplier:
        base_query = db.query(Order).filter(Order.supplier_id == user_id)
    else:
        base_query = db.query(Order).filter(Order.owner_id == user_id)
    
    orders = (base_query.options(joinedload(Order.items).joinedload(OrderItem.product))
              .order_by(desc(Order.id))
              .limit(limit).all())
    
    result = []
    for o in orders:
        items_count = len(getattr(o, 'items', []))
        total_amount = 0.0
        items_details = []
        
        for item in getattr(o, 'items', []):
            try:
                price = _safe_float(getattr(item.product, "unit_price", 0))
                qty = _safe_int(getattr(item, "quantity", 0))
                item_total = price * qty
                total_amount += item_total
                
                product_name = getattr(item.product, "product_name", f"מוצר #{item.product_id}")
                items_details.append({
                    "product_name": product_name,
                    "quantity": qty,
                    "price": price,
                    "total": item_total
                })
            except:
                pass
        
        # מידע על הצד השני (ספק/בעל חנות)
        if is_supplier:
            other_user = db.query(User).filter(User.id == o.owner_id).first()
            other_name = getattr(other_user, "username", f"בעל חנות #{o.owner_id}") if other_user else "לא ידוע"
        else:
            other_user = db.query(User).filter(User.id == o.supplier_id).first()
            other_name = getattr(other_user, "username", f"ספק #{o.supplier_id}") if other_user else "לא ידוע"
        
        result.append({
            "id": o.id,
            "status": o.status,
            "items_count": items_count,
            "total_amount": total_amount,
            "other_party": other_name,
            "items_details": items_details[:5],  # מגביל ל-5 פריטים ראשונים
            "created_date": getattr(o, "created_date", None)
        })
    
    return result

def get_business_analytics(db: Session, user_id: int, is_supplier: bool) -> Dict[str, Any]:
    """מחזיר אנליטיקס עסקי מתקדם"""
    last_30_days = datetime.now() - timedelta(days=30)
    last_7_days = datetime.now() - timedelta(days=7)
    
    if is_supplier:
        # אנליטיקס לספק
        orders_30d = db.query(Order).filter(
            Order.supplier_id == user_id,
            Order.created_date >= last_30_days
        ).count()
        
        orders_7d = db.query(Order).filter(
            Order.supplier_id == user_id,
            Order.created_date >= last_7_days
        ).count()
        
        # הכנסות מהזמנות שהושלמו ב-30 יום
        revenue_30d = 0.0
        completed_orders = db.query(Order).filter(
            Order.supplier_id == user_id,
            Order.status == "הושלמה",
            Order.created_date >= last_30_days
        ).all()
        
        for order in completed_orders:
            for item in getattr(order, 'items', []):
                try:
                    price = _safe_float(getattr(item.product, "unit_price", 0))
                    qty = _safe_int(getattr(item, "quantity", 0))
                    revenue_30d += price * qty
                except:
                    pass
        
        return {
            "orders_last_30_days": orders_30d,
            "orders_last_7_days": orders_7d,
            "revenue_last_30_days": revenue_30d,
            "completed_orders_30d": len(completed_orders),
            "average_order_value": revenue_30d / len(completed_orders) if completed_orders else 0
        }
    
    else:
        # אנליטיקס לבעל חנות
        orders_30d = db.query(Order).filter(
            Order.owner_id == user_id,
            Order.created_date >= last_30_days
        ).count()
        
        orders_7d = db.query(Order).filter(
            Order.owner_id == user_id,
            Order.created_date >= last_7_days
        ).count()
        
        # הוצאות ב-30 יום
        spending_30d = 0.0
        orders = db.query(Order).filter(
            Order.owner_id == user_id,
            Order.created_date >= last_30_days
        ).all()
        
        for order in orders:
            for item in getattr(order, 'items', []):
                try:
                    price = _safe_float(getattr(item.product, "unit_price", 0))
                    qty = _safe_int(getattr(item, "quantity", 0))
                    spending_30d += price * qty
                except:
                    pass
        
        return {
            "orders_last_30_days": orders_30d,
            "orders_last_7_days": orders_7d,
            "spending_last_30_days": spending_30d,
            "average_order_value": spending_30d / orders_30d if orders_30d else 0
        }

def get_top_products_by_revenue(db: Session, supplier_id: int, limit: int = 5) -> List[Dict]:
    """מחזיר מוצרים מובילים לפי הכנסות"""
    result = (db.query(
        Product.id,
        Product.product_name,
        Product.unit_price,
        func.sum(OrderItem.quantity).label('total_sold'),
        (func.sum(OrderItem.quantity) * Product.unit_price).label('total_revenue')
    ).join(OrderItem, Product.id == OrderItem.product_id)
     .join(Order, OrderItem.order_id == Order.id)
     .filter(Product.supplier_id == supplier_id, Order.status == "הושלמה")
     .group_by(Product.id, Product.product_name, Product.unit_price)
     .order_by(desc('total_revenue'))
     .limit(limit).all())
    
    return [{
        "id": row.id,
        "name": row.product_name,
        "price": _safe_float(row.unit_price),
        "sold": _safe_int(row.total_sold),
        "revenue": _safe_float(row.total_revenue)
    } for row in result]

def get_supplier_performance_for_owner(db: Session, owner_id: int, limit: int = 5) -> List[Dict]:
    """מחזיר ביצועי ספקים עבור בעל חנות"""
    supplier_stats = []
    
    # מוצא ספקים שהבעל הזמין מהם
    supplier_ids = (db.query(Order.supplier_id)
                   .filter(Order.owner_id == owner_id)
                   .distinct().all())
    
    for sid_tuple in supplier_ids[:limit]:
        sid = sid_tuple[0]
        supplier = db.query(User).filter(User.id == sid).first()
        if not supplier:
            continue
            
        name = getattr(supplier, "username", "") or getattr(supplier, "contact_name", f"ספק #{sid}")
        
        # סטטיסטיקות עבור הספק הזה
        orders_count = db.query(Order).filter(
            Order.owner_id == owner_id,
            Order.supplier_id == sid
        ).count()
        
        completed_orders = db.query(Order).filter(
            Order.owner_id == owner_id,
            Order.supplier_id == sid,
            Order.status == "הושלמה"
        ).count()
        
        # חישוב סכום כולל מהספק
        total_spent = 0.0
        orders = db.query(Order).filter(
            Order.owner_id == owner_id,
            Order.supplier_id == sid
        ).all()
        
        for order in orders:
            for item in getattr(order, 'items', []):
                try:
                    price = _safe_float(getattr(item.product, "unit_price", 0))
                    qty = _safe_int(getattr(item, "quantity", 0))
                    total_spent += price * qty
                except:
                    pass
        
        completion_rate = (completed_orders / orders_count * 100) if orders_count > 0 else 0
        
        supplier_stats.append({
            "id": sid,
            "name": name,
            "orders_count": orders_count,
            "completed_orders": completed_orders,
            "completion_rate": completion_rate,
            "total_spent": total_spent,
            "average_order": total_spent / orders_count if orders_count > 0 else 0
        })
    
    return sorted(supplier_stats, key=lambda x: x['total_spent'], reverse=True)

def get_recent_activity(db: Session, user_id: int, is_supplier: bool, days: int = 7) -> Dict[str, Any]:
    """מחזיר פעילות אחרונה"""
    since_date = datetime.now() - timedelta(days=days)
    
    if is_supplier:
        recent_orders = db.query(Order).filter(
            Order.supplier_id == user_id,
            Order.created_date >= since_date
        ).all()
    else:
        recent_orders = db.query(Order).filter(
            Order.owner_id == user_id,
            Order.created_date >= since_date
        ).all()
    
    activity = {
        "new_orders": len([o for o in recent_orders if o.status in ["ממתינה", "חדשה"]]),
        "processed_orders": len([o for o in recent_orders if o.status in ["בתהליך", "אושרה"]]),
        "completed_orders": len([o for o in recent_orders if o.status == "הושלמה"]),
        "total_orders": len(recent_orders)
    }
    
    return activity

# ----------------- Enhanced Context Builders -----------------

def build_supplier_context(db: Session, supplier_id: int) -> Dict[str, Any]:
    """בונה context עשיר מאוד לספק"""
    # נתונים בסיסיים
    products = fetch_supplier_products_detailed(db, supplier_id)
    orders = fetch_enhanced_orders(db, supplier_id, is_supplier=True)
    analytics = get_business_analytics(db, supplier_id, is_supplier=True)
    activity = get_recent_activity(db, supplier_id, is_supplier=True)
    
    # KPIs מתקדמים
    active_products = len([p for p in products if p['is_active']])
    total_products = len(products)
    total_stock = sum(p['stock'] for p in products)
    total_revenue = sum(p['revenue'] for p in products)
    
    # מוצרים במלאי נמוך
    low_stock = [p for p in products if p['is_active'] and p['stock'] <= max(p['min_quantity'], 5)]
    
    # הזמנות פתוחות
    open_orders = [o for o in orders if o['status'] in ["בתהליך", "ממתינה", "אושרה"]]
    
    # מוצרים מובילים
    top_products = sorted(products, key=lambda x: x['revenue'], reverse=True)[:5]
    
    # חיבורים פעילים
    active_links = count_active_links_for_supplier(db, supplier_id)
    
    # הרשאות מורחבות
    permissions = [
        "orders.view", "orders.export", "orders.update_status",
        "products.create", "products.update", "products.update_min_qty", "products.update_stock",
        "analytics.view", "reports.generate"
    ]
    

    ui_paths = {
        "orders_list": "תפריט > הזמנות",
        "orders_open": "תפריט > הזמנות > פתוחות",
        "order_details": "תפריט > הזמנות > פרטי הזמנה",
        "order_export": "תפריט > הזמנות > ייצוא",
        "product_list": "תפריט > מוצרים",
        "product_edit": "תפריט > מוצרים > עריכה",
        "product_add": "תפריט > מוצרים > הוספה",
        "min_qty_bulk": "תפריט > מוצרים > עדכון מינימום",
        "stock_update": "תפריט > מוצרים > עדכון מלאי",
        "analytics": "תפריט > דוחות ואנליטיקס",
        "connections": "תפריט > חיבורים > בעלי חנויות"
    }

    business_rules = {
        "open_order_statuses": ["ממתינה", "בתהליך", "אושרה"],
        "completed_status": "הושלמה",
        "low_stock_threshold": 5,
        "active_product_flag": "is_active=true",
        "min_order_amount": 50.0,
        "currency": "ILS"
    }

    return {
        "role": "Supplier",
        "permissions": permissions,
        "ui_paths": ui_paths,
        "business_rules": business_rules,
        "kpis": {
            "active_products": active_products,
            "total_products": total_products,
            "total_stock": total_stock,
            "total_revenue": total_revenue,
            "open_orders_count": len(open_orders),
            "active_links_count": active_links,
            "low_stock_count": len(low_stock)
        },
        "analytics": analytics,
        "activity": activity,
        "samples": {
            "recent_orders": orders[:8],
            "open_orders": open_orders[:6],
            "low_stock": low_stock[:8],
            "top_products": top_products,
            "all_products": products
        },
    }

def build_owner_context(db: Session, owner_id: int) -> Dict[str, Any]:
    """בונה context עשיר מאוד לבעל חנות"""
    # נתונים בסיסיים
    orders = fetch_enhanced_orders(db, owner_id, is_supplier=False)
    analytics = get_business_analytics(db, owner_id, is_supplier=False)
    activity = get_recent_activity(db, owner_id, is_supplier=False)
    supplier_performance = get_supplier_performance_for_owner(db, owner_id)
    
    # KPIs מתקדמים
    open_orders = [o for o in orders if o['status'] in ["בתהליך", "ממתינה", "אושרה"]]
    completed_orders = [o for o in orders if o['status'] == "הושלמה"]
    total_spent = sum(o['total_amount'] for o in completed_orders)
    
    # חיבורים פעילים
    active_links = count_active_links_for_owner(db, owner_id)
    
    # ספקים ייחודיים
    unique_suppliers = len(set(o['other_party'] for o in orders))
    
    # הרשאות מורחבות
    permissions = [
        "orders.view", "orders.create", "orders.export", "orders.reorder",
        "suppliers.search", "suppliers.connect", "suppliers.view_products",
        "analytics.view", "reports.generate"
    ]

    ui_paths = {
        "orders_list": "תפריט > הזמנות",
        "orders_create": "תפריט > הזמנות > הזמנה חדשה",
        "orders_open": "תפריט > הזמנות > פתוחות",
        "order_details": "תפריט > הזמנות > פרטי הזמנה",
        "order_export": "תפריט > הזמנות > ייצוא",
        "reorder": "תפריט > הזמנות > הזמנה חוזרת",
        "suppliers_list": "תפריט > ספקים",
        "suppliers_search": "תפריט > ספקים > חיפוש",
        "supplier_products": "תפריט > ספקים > מוצרי ספק",
        "connections": "תפריט > חיבורים > ספקים שלי",
        "analytics": "תפריט > דוחות ואנליטיקס"
    }

    business_rules = {
        "open_order_statuses": ["ממתינה", "בתהליך", "אושרה"],
        "completed_status": "הושלמה",
        "min_order_amount": 50.0,
        "currency": "ILS",
        "reorder_available": True
    }

    return {
        "role": "StoreOwner",
        "permissions": permissions,
        "ui_paths": ui_paths,
        "business_rules": business_rules,
        "kpis": {
            "orders_total": len(orders),
            "open_orders_count": len(open_orders),
            "completed_orders_count": len(completed_orders),
            "total_spent": total_spent,
            "active_links_count": active_links,
            "unique_suppliers": unique_suppliers
        },
        "analytics": analytics,
        "activity": activity,
        "samples": {
            "recent_orders": orders[:8],
            "open_orders": open_orders[:6],
            "supplier_performance": supplier_performance,
            "top_suppliers": supplier_performance[:3]
        },
    }

# ----------------- Helper Functions -----------------

def count_active_links_for_owner(db: Session, owner_id: int) -> int:
    return db.query(OwnerSupplierLink).filter(
        OwnerSupplierLink.owner_id == owner_id,
        OwnerSupplierLink.status == "APPROVED",
    ).count()

def count_active_links_for_supplier(db: Session, supplier_id: int) -> int:
    return db.query(OwnerSupplierLink).filter(
        OwnerSupplierLink.supplier_id == supplier_id,
        OwnerSupplierLink.status == "APPROVED",
    ).count()