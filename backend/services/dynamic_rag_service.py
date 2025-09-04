# backend/services/dynamic_rag_service.py
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import hashlib
import time

from .ollama_service import OllamaService
from .qdrant_service import QdrantService

logger = logging.getLogger(__name__)

class DynamicRAGService:
    """
    שירות RAG דינמי שמוסיף נתוני משתמש אישיים למאגר הוקטורים
    רק כשנדרש ועם מנגנון cache חכם
    """
    
    def __init__(self):
        self.ollama_service = OllamaService()
        self.qdrant_service = QdrantService()
        
        # מטמון למניעת חישובים מיותרים
        self.user_data_cache = {}
        self.cache_duration = 300  # 5 דקות
        
        # Collection נפרדת לנתונים דינמיים
        self.dynamic_collection = "user_dynamic_data"
        
    def initialize_user_context(self, user_id: int, db: Session) -> bool:
        """
        אתחול הקשר משתמש - רק אם נדרש
        מחזיר True אם נוצר הקשר חדש, False אם כבר קיים
        """
        try:
            cache_key = f"user_{user_id}"
            current_time = time.time()
            
            # בדיקת מטמון
            if cache_key in self.user_data_cache:
                cached_data = self.user_data_cache[cache_key]
                if current_time - cached_data["timestamp"] < self.cache_duration:
                    logger.info(f"Using cached data for user {user_id}")
                    return False
            
            # יצירת נתוני הקשר אישי
            user_context = self._generate_user_context(user_id, db)
            
            if not user_context:
                return False
            
            # יצירת embedding והוספה לאוסף דינמי
            self._add_user_context_to_vectors(user_id, user_context)
            
            # עדכון מטמון
            self.user_data_cache[cache_key] = {
                "timestamp": current_time,
                "context": user_context
            }
            
            logger.info(f"Generated dynamic context for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing user context for {user_id}: {e}")
            return False
    
    def _generate_user_context(self, user_id: int, db: Session) -> str:
        """יצירת טקסט הקשר מותאם אישית למשתמש"""
        try:
            context_parts = []
            
            # פרטי משתמש בסיסיים
            user_info = db.execute(text("""
                SELECT userType, company_name, contact_name, phone,
                       city_id, street, house_number, opening_time, closing_time
                FROM users WHERE id = :user_id
            """), {"user_id": user_id}).fetchone()
            
            if not user_info:
                return ""
            
            user_type = user_info.userType
            context_parts.append(f"=== פרופיל משתמש {user_id} ===")
            context_parts.append(f"סוג משתמש: {user_type}")
            context_parts.append(f"שם איש קשר: {user_info.contact_name or 'לא צוין'}")
            
            if user_info.company_name:
                context_parts.append(f"שם החברה: {user_info.company_name}")
            
            # נתונים ספציפיים לספק
            if user_type == "Supplier":
                supplier_data = db.execute(text("""
                    SELECT 
                        COUNT(p.id) as total_products,
                        COUNT(CASE WHEN p.stock = 0 THEN 1 END) as out_of_stock,
                        AVG(CAST(p.unit_price as FLOAT)) as avg_price,
                        COUNT(CASE WHEN o.status = N'בתהליך' THEN 1 END) as pending_orders
                    FROM products p
                    LEFT JOIN order_items oi ON p.id = oi.product_id
                    LEFT JOIN orders o ON oi.order_id = o.id
                    WHERE p.supplier_id = :user_id AND p.is_active = 1
                """), {"user_id": user_id}).fetchone()
                
                if supplier_data:
                    context_parts.append(f"מספר מוצרים פעילים: {supplier_data.total_products or 0}")
                    context_parts.append(f"מוצרים שאזלו מהמלאי: {supplier_data.out_of_stock or 0}")
                    context_parts.append(f"מחיר ממוצע של מוצרים: {supplier_data.avg_price or 0:.2f} שקלים")
                    context_parts.append(f"הזמנות ממתינות: {supplier_data.pending_orders or 0}")
                
                # המוצרים הפופולריים של הספק
                popular_products = db.execute(text("""
                    SELECT TOP 5 p.product_name, COUNT(oi.id) as order_count, p.unit_price
                    FROM products p
                    LEFT JOIN order_items oi ON p.id = oi.product_id
                    WHERE p.supplier_id = :user_id AND p.is_active = 1
                    GROUP BY p.id, p.product_name, p.unit_price
                    ORDER BY order_count DESC
                """), {"user_id": user_id}).fetchall()
                
                if popular_products:
                    context_parts.append("המוצרים הפופולריים ביותר של הספק:")
                    for product in popular_products:
                        context_parts.append(f"- {product.product_name}: {product.order_count or 0} הזמנות, מחיר {product.unit_price} שקלים")
            
            # נתונים ספציפיים לבעל חנות
            elif user_type == "StoreOwner":
                owner_data = db.execute(text("""
                    SELECT 
                        COUNT(o.id) as total_orders,
                        COUNT(CASE WHEN o.status = N'בתהליך' THEN 1 END) as pending_orders,
                        COUNT(CASE WHEN o.status = N'הושלמה' THEN 1 END) as completed_orders,
                        COUNT(DISTINCT osl.supplier_id) as connected_suppliers
                    FROM orders o
                    LEFT JOIN owner_supplier_links osl ON o.owner_id = osl.owner_id AND osl.status = 'APPROVED'
                    WHERE o.owner_id = :user_id
                """), {"user_id": user_id}).fetchone()
                
                if owner_data:
                    context_parts.append(f"סך הכל הזמנות: {owner_data.total_orders or 0}")
                    context_parts.append(f"הזמנות בתהליך: {owner_data.pending_orders or 0}")
                    context_parts.append(f"הזמנות שהושלמו: {owner_data.completed_orders or 0}")
                    context_parts.append(f"ספקים מחוברים: {owner_data.connected_suppliers or 0}")
                
                # פרטי החנות
                if user_info.street and user_info.house_number:
                    context_parts.append(f"כתובת החנות: {user_info.street} {user_info.house_number}")
                
                if user_info.opening_time and user_info.closing_time:
                    context_parts.append(f"שעות פעילות: {user_info.opening_time} - {user_info.closing_time}")
                
                # ההזמנות האחרונות
                recent_orders = db.execute(text("""
                    SELECT TOP 3 o.id, o.status, u.company_name as supplier_name, o.created_date
                    FROM orders o
                    JOIN users u ON o.supplier_id = u.id
                    WHERE o.owner_id = :user_id
                    ORDER BY o.created_date DESC
                """), {"user_id": user_id}).fetchall()
                
                if recent_orders:
                    context_parts.append("ההזמנות האחרונות:")
                    for order in recent_orders:
                        supplier = order.supplier_name or "ספק לא ידוע"
                        context_parts.append(f"- הזמנה #{order.id} מ{supplier}: {order.status}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error generating user context: {e}")
            return ""
    
    def _add_user_context_to_vectors(self, user_id: int, context: str):
        """הוספת הקשר המשתמש למאגר וקטורים זמני"""
        try:
            # יצירת embedding
            embedding = self.ollama_service.get_embedding(context)
            if not embedding:
                logger.warning(f"Failed to generate embedding for user {user_id}")
                return
            
            # יצירת ID ייחודי
            context_id = hashlib.md5(f"user_{user_id}_{int(time.time())}".encode()).hexdigest()
            
            # הוספה לאוסף זמני (בזיכרון או במאגר נפרד)
            # כאן אפשר להוסיף לQdrant או לשמור במטמון זיכרון
            self._store_dynamic_vector(context_id, embedding, context, user_id)
            
        except Exception as e:
            logger.error(f"Error adding user context to vectors: {e}")
    
    def _store_dynamic_vector(self, context_id: str, embedding: List[float], text: str, user_id: int):
        """שמירת וקטור דינמי - יכול להיות בזיכרון או במאגר נפרד"""
        # לעת עתה נשמור במטמון זיכרון
        # בגרסה מתקדמת אפשר להוסיף לQdrant collection נפרד
        cache_key = f"vector_user_{user_id}"
        self.user_data_cache[cache_key] = {
            "embedding": embedding,
            "text": text,
            "timestamp": time.time()
        }
    
    def get_enhanced_context(self, user_id: int, query_embedding: List[float], base_context: str) -> str:
        """קבלת הקשר משופר עם נתוני המשתמש"""
        try:
            # חיפוש בנתונים האישיים
            user_context = self._search_user_context(user_id, query_embedding)
            
            if user_context:
                return f"{base_context}\n\n=== מידע אישי רלוונטי ===\n{user_context}"
            
            return base_context
            
        except Exception as e:
            logger.error(f"Error enhancing context: {e}")
            return base_context
    
    def _search_user_context(self, user_id: int, query_embedding: List[float]) -> str:
        """חיפוש בהקשר האישי של המשתמש"""
        try:
            cache_key = f"vector_user_{user_id}"
            if cache_key in self.user_data_cache:
                cached_vector = self.user_data_cache[cache_key]
                
                # חישוב דמיון (פשוט - אפשר לשפר)
                user_embedding = cached_vector["embedding"]
                similarity = self._cosine_similarity(query_embedding, user_embedding)
                
                # אם יש דמיון מספיק, החזר את הטקסט
                if similarity > 0.3:  # threshold לדמיון
                    return cached_vector["text"]
            
            return ""
            
        except Exception as e:
            logger.error(f"Error searching user context: {e}")
            return ""
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """חישוב דמיון קוסינוס פשוט"""
        try:
            import math
            
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude_a = math.sqrt(sum(a * a for a in vec1))
            magnitude_b = math.sqrt(sum(b * b for b in vec2))
            
            if magnitude_a == 0 or magnitude_b == 0:
                return 0
            
            return dot_product / (magnitude_a * magnitude_b)
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0
    
    def cleanup_user_cache(self, user_id: int):
        """ניקוי מטמון משתמש"""
        try:
            keys_to_remove = [key for key in self.user_data_cache.keys() 
                            if key.startswith(f"user_{user_id}") or key.startswith(f"vector_user_{user_id}")]
            
            for key in keys_to_remove:
                del self.user_data_cache[key]
                
            logger.info(f"Cleaned cache for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning cache: {e}")