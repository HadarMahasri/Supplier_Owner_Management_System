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
    שירות RAG דינמי מואץ:
    - מטמון אגרסיבי יותר
    - שאילתות DB מובטלות
    - עיבוד מהיר יותר של נתוני משתמש
    - דחיסה של context
    """
    
    def __init__(self):
        self.ollama_service = OllamaService()
        self.qdrant_service = QdrantService()
        
        # מטמון מושרש יותר
        self.user_data_cache = {}
        self.context_cache = {}
        self.vector_cache = {}
        
        self.cache_duration = 600  # 10 דקות במקום 5
        self.max_cache_size = 100
        
        # Collection נפרדת לנתונים דינמיים
        self.dynamic_collection = "user_dynamic_data"
        
        logger.info("DynamicRAGService initialized with speed optimizations")
        
    def initialize_user_context(self, user_id: int, db: Session) -> bool:
        """
        אתחול מהיר של הקשר משתמש עם מטמון אגרסיבי
        """
        try:
            cache_key = f"user_init_{user_id}"
            current_time = time.time()
            
            # בדיקת מטמון מתקדמת
            if cache_key in self.user_data_cache:
                cached_data = self.user_data_cache[cache_key]
                if current_time - cached_data["timestamp"] < self.cache_duration:
                    logger.debug(f"Using cached init data for user {user_id}")
                    return cached_data.get("initialized", False)
            
            # יצירת נתוני הקשר מהיר
            user_context = self._generate_user_context_fast(user_id, db)
            
            if not user_context:
                # שמירת תוצאה שלילית במטמון
                self.user_data_cache[cache_key] = {
                    "timestamp": current_time,
                    "initialized": False
                }
                return False
            
            # הוספה למאגר וקטורים (אם נדרש)
            if len(user_context) > 50:  # רק אם יש מספיק תוכן
                self._add_user_context_to_vectors_fast(user_id, user_context)
            
            # עדכון מטמון
            self.user_data_cache[cache_key] = {
                "timestamp": current_time,
                "context": user_context,
                "initialized": True
            }
            
            # ניקוי מטמון
            self._cleanup_cache()
            
            logger.debug(f"Generated dynamic context for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing user context for {user_id}: {e}")
            return False
    
    def _generate_user_context_fast(self, user_id: int, db: Session) -> str:
        """יצירת טקסט הקשר מותאם במהירות מקסימלית"""
        try:
            context_parts = []
            
            # שאילתה מהירה יחידה לכל הנתונים החיוניים
            user_data = db.execute(text("""
                SELECT 
                    u.userType, u.company_name, u.contact_name,
                    COALESCE(stats.products_count, 0) as products_count,
                    COALESCE(stats.active_orders, 0) as active_orders,
                    COALESCE(stats.total_orders, 0) as total_orders
                FROM users u
                LEFT JOIN (
                    SELECT 
                        u.id,
                        COUNT(DISTINCT p.id) as products_count,
                        COUNT(DISTINCT CASE WHEN o.status = N'בתהליך' THEN o.id END) as active_orders,
                        COUNT(DISTINCT o.id) as total_orders
                    FROM users u
                    LEFT JOIN products p ON (u.userType = 'Supplier' AND p.supplier_id = u.id AND p.is_active = 1)
                    LEFT JOIN orders o ON (
                        (u.userType = 'StoreOwner' AND o.owner_id = u.id) OR
                        (u.userType = 'Supplier' AND o.supplier_id = u.id)
                    )
                    WHERE u.id = :user_id
                    GROUP BY u.id
                ) stats ON u.id = stats.id
                WHERE u.id = :user_id
            """), {"user_id": user_id}).fetchone()
            
            if not user_data:
                return ""
            
            user_type = user_data.userType
            context_parts.append(f"משתמש: {user_type}")
            
            if user_data.contact_name:
                context_parts.append(f"שם: {user_data.contact_name}")
            
            # נתונים מהירים לפי סוג משתמש
            if user_type == "Supplier":
                context_parts.append(f"מוצרים: {user_data.products_count}")
                context_parts.append(f"הזמנות פעילות: {user_data.active_orders}")
                
                # רק אם יש מוצרים, קבל דוגמאות מהירות
                if user_data.products_count > 0:
                    popular = db.execute(text("""
                        SELECT TOP 2 p.product_name, p.unit_price
                        FROM products p
                        WHERE p.supplier_id = :user_id AND p.is_active = 1
                        ORDER BY p.id DESC
                    """), {"user_id": user_id}).fetchall()
                    
                    if popular:
                        context_parts.append("מוצרים עיקריים:")
                        for product in popular:
                            context_parts.append(f"- {product.product_name} ({product.unit_price} ש\"ח)")
            
            elif user_type == "StoreOwner":
                context_parts.append(f"סך הזמנות: {user_data.total_orders}")
                context_parts.append(f"הזמנות פעילות: {user_data.active_orders}")
                
                # רק אם יש הזמנות, קבל דוגמאות מהירות
                if user_data.total_orders > 0:
                    recent = db.execute(text("""
                        SELECT TOP 2 o.id, u.company_name, o.status
                        FROM orders o
                        JOIN users u ON o.supplier_id = u.id
                        WHERE o.owner_id = :user_id
                        ORDER BY o.created_date DESC
                    """), {"user_id": user_id}).fetchall()
                    
                    if recent:
                        context_parts.append("הזמנות אחרונות:")
                        for order in recent:
                            supplier = order.company_name or "ספק"
                            context_parts.append(f"- הזמנה #{order.id} מ{supplier}: {order.status}")
            
            # חזרת context מתומצת
            context = "\n".join(context_parts)
            return context if len(context) < 1000 else context[:1000]
            
        except Exception as e:
            logger.error(f"Error generating fast user context: {e}")
            return ""
    
    def _add_user_context_to_vectors_fast(self, user_id: int, context: str):
        """הוספת הקשר למאגר וקטורים - גרסה מהירה"""
        try:
            # יצירת embedding רק אם הטקסט מספיק ארוך
            if len(context) < 50:
                return
                
            embedding = self.ollama_service.get_embedding(context)
            if not embedding:
                logger.warning(f"Failed to generate embedding for user {user_id}")
                return
            
            # שמירה במטמון זיכרון במקום Qdrant למהירות
            cache_key = f"vector_user_{user_id}"
            self.vector_cache[cache_key] = {
                "embedding": embedding,
                "text": context,
                "timestamp": time.time()
            }
            
            # ניקוי מטמון וקטורים
            if len(self.vector_cache) > 50:
                oldest = min(self.vector_cache.keys(), 
                           key=lambda k: self.vector_cache[k]["timestamp"])
                del self.vector_cache[oldest]
                
        except Exception as e:
            logger.error(f"Error adding user context to vectors: {e}")
    
    def get_user_context_text(self, user_id: int) -> str:
        """קבלת טקסט הקשר משתמש מהמטמון"""
        try:
            cache_key = f"user_init_{user_id}"
            if cache_key in self.user_data_cache:
                cached = self.user_data_cache[cache_key]
                if time.time() - cached["timestamp"] < self.cache_duration:
                    return cached.get("context", "")
            return ""
        except Exception as e:
            logger.error(f"Error getting user context text: {e}")
            return ""
    
    def get_enhanced_context(self, user_id: int, query_embedding: List[float], base_context: str) -> str:
        """קבלת הקשר משופר - גרסה מהירה"""
        try:
            # חיפוש מהיר בנתונים האישיים
            user_context = self._search_user_context_fast(user_id, query_embedding)
            
            if user_context:
                # חיבור מהיר של contexts
                enhanced = f"{base_context}\n\nמידע אישי: {user_context}"
                
                # הגבלת אורך למהירות
                if len(enhanced) > 2000:
                    enhanced = enhanced[:2000] + "..."
                    
                return enhanced
            
            return base_context
            
        except Exception as e:
            logger.error(f"Error enhancing context: {e}")
            return base_context
    
    def _search_user_context_fast(self, user_id: int, query_embedding: List[float]) -> str:
        """חיפוש מהיר בהקשר האישי"""
        try:
            cache_key = f"vector_user_{user_id}"
            if cache_key not in self.vector_cache:
                return ""
                
            cached_vector = self.vector_cache[cache_key]
            
            # בדיקת תקינות זמן
            if time.time() - cached_vector["timestamp"] > self.cache_duration:
                del self.vector_cache[cache_key]
                return ""
            
            # חישוב דמיון מהיר
            user_embedding = cached_vector["embedding"]
            similarity = self._cosine_similarity_fast(query_embedding, user_embedding)
            
            # threshold נמוך יותר למהירות
            if similarity > 0.2:
                return cached_vector["text"]
            
            return ""
            
        except Exception as e:
            logger.error(f"Error searching user context: {e}")
            return ""
    
    def _cosine_similarity_fast(self, vec1: List[float], vec2: List[float]) -> float:
        """חישוב דמיון קוסינוס מהיר יותר"""
        try:
            # חישוב על חלק מהוקטור בלבד למהירות
            sample_size = min(100, len(vec1), len(vec2))
            
            dot_product = sum(a * b for a, b in zip(vec1[:sample_size], vec2[:sample_size]))
            
            # חישוב magnitude מהיר יותר
            mag1 = sum(a * a for a in vec1[:sample_size]) ** 0.5
            mag2 = sum(b * b for b in vec2[:sample_size]) ** 0.5
            
            if mag1 == 0 or mag2 == 0:
                return 0
            
            return dot_product / (mag1 * mag2)
            
        except Exception as e:
            logger.error(f"Error calculating fast cosine similarity: {e}")
            return 0
    
    def _cleanup_cache(self):
        """ניקוי מטמון אוטומטי"""
        try:
            current_time = time.time()
            
            # ניקוי מטמון נתוני משתמש
            expired_keys = [
                key for key, data in self.user_data_cache.items()
                if current_time - data["timestamp"] > self.cache_duration
            ]
            for key in expired_keys:
                del self.user_data_cache[key]
            
            # ניקוי מטמון וקטורים
            expired_vector_keys = [
                key for key, data in self.vector_cache.items()
                if current_time - data["timestamp"] > self.cache_duration
            ]
            for key in expired_vector_keys:
                del self.vector_cache[key]
                
            # הגבלת גודל מטמון
            if len(self.user_data_cache) > self.max_cache_size:
                oldest_keys = sorted(
                    self.user_data_cache.keys(),
                    key=lambda k: self.user_data_cache[k]["timestamp"]
                )[:10]  # מחק 10 הישנים ביותר
                for key in oldest_keys:
                    del self.user_data_cache[key]
                    
        except Exception as e:
            logger.error(f"Error cleaning cache: {e}")
    
    def cleanup_user_cache(self, user_id: int):
        """ניקוי מטמון משתמש ספציפי"""
        try:
            keys_to_remove = [
                key for key in self.user_data_cache.keys() 
                if f"user_{user_id}" in key
            ]
            
            for key in keys_to_remove:
                del self.user_data_cache[key]
                
            # ניקוי מטמון וקטורים
            vector_key = f"vector_user_{user_id}"
            if vector_key in self.vector_cache:
                del self.vector_cache[vector_key]
                
            logger.debug(f"Cleaned cache for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning cache for user {user_id}: {e}")

    def get_cache_stats(self) -> Dict:
        """סטטיסטיקות מטמון למעקב ביצועים"""
        return {
            "user_data_cache_size": len(self.user_data_cache),
            "vector_cache_size": len(self.vector_cache),
            "context_cache_size": len(self.context_cache),
            "cache_duration": self.cache_duration,
            "max_cache_size": self.max_cache_size
        }