# backend/queries/supplier_queries.py - גירסה עובדת
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from models.supplier_model import Supplier, Category
from typing import List, Optional, Dict, Any

class SupplierQueries:
    def __init__(self):
        pass
    
    async def search_suppliers(
        self, 
        db: Session,
        category: Optional[str] = None,
        city: Optional[str] = None,
        rating_min: Optional[float] = None,
        search_term: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """חיפוש ספקים עם פילטרים"""
        
        query = db.query(Supplier).filter(Supplier.status == 'active')
        
        # פילטר קטגוריה
        if category and category != "כל הקטגוריות":
            query = query.filter(Supplier.category == category)
        
        # פילטר עיר
        if city and city != "כל הערים":
            query = query.filter(Supplier.address['city'].astext == city)
        
        # פילטר דירוג מינימלי
        if rating_min:
            query = query.filter(Supplier.rating >= rating_min)
        
        # חיפוש טקסט
        if search_term:
            search_filter = or_(
                Supplier.name.ilike(f'%{search_term}%'),
                Supplier.description.ilike(f'%{search_term}%')
            )
            query = query.filter(search_filter)
        
        # מיון לפי דירוג + featured
        query = query.order_by(
            Supplier.featured.desc(),
            Supplier.rating.desc()
        )
        
        # הגבלה ו-offset
        suppliers = query.offset(offset).limit(limit).all()
        
        # המרה לפורמט נוח ל-Frontend
        result = []
        for supplier in suppliers:
            result.append({
                'id': str(supplier.id),
                'name': supplier.name,
                'category': supplier.category,
                'city': supplier.address.get('city') if supplier.address else '',
                'rating': float(supplier.rating),
                'price_range': supplier.price_range,
                'status': supplier.status,
                'verified': supplier.verified,
                'featured': supplier.featured,
                'description': supplier.description,
                'contact_info': supplier.contact_info,
                'delivery_areas': supplier.delivery_areas
            })
        
        return result
    
    async def get_supplier_by_id(self, db: Session, supplier_id: str) -> Optional[Dict[str, Any]]:
        """קבלת פרטי ספק לפי ID"""
        try:
            supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
            if not supplier:
                return None
            
            return {
                'id': str(supplier.id),
                'name': supplier.name,
                'category': supplier.category,
                'subcategory': supplier.subcategory,
                'description': supplier.description,
                'contact_info': supplier.contact_info,
                'address': supplier.address,
                'location': supplier.location,
                'rating': float(supplier.rating),
                'review_count': int(supplier.review_count),
                'price_range': supplier.price_range,
                'delivery_areas': supplier.delivery_areas,
                'verified': supplier.verified,
                'featured': supplier.featured,
                'status': supplier.status
            }
        except Exception as e:
            print(f"Error getting supplier {supplier_id}: {e}")
            return None
    
    async def get_categories(self, db: Session) -> List[Dict[str, Any]]:
        """קבלת רשימת קטגוריות"""
        try:
            categories = db.query(Category).filter(Category.active == True).all()
            return [
                {
                    'id': str(cat.id),
                    'name': cat.name,
                    'name_hebrew': cat.name_hebrew,
                    'description': cat.description,
                    'icon': cat.icon
                }
                for cat in categories
            ]
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
    
    async def get_suppliers_by_category(self, db: Session, category_name: str, limit: int = 20):
        """קבלת ספקים לפי קטגוריה"""
        try:
            suppliers = db.query(Supplier).filter(
                and_(
                    Supplier.category == category_name,
                    Supplier.status == 'active'
                )
            ).order_by(Supplier.rating.desc()).limit(limit).all()
            
            return [
                {
                    'id': str(s.id),
                    'name': s.name,
                    'rating': float(s.rating),
                    'city': s.address.get('city') if s.address else '',
                    'price_range': s.price_range
                }
                for s in suppliers
            ]
        except Exception as e:
            print(f"Error getting suppliers by category: {e}")
            return []