import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
import time
import hashlib

from .ollama_service import OllamaService
from .qdrant_service import QdrantService

logger = logging.getLogger(__name__)

# Import בטוח של DynamicRAGService
try:
    from .dynamic_rag_service import DynamicRAGService
    DYNAMIC_RAG_AVAILABLE = True
except ImportError as e:
    DYNAMIC_RAG_AVAILABLE = False
    logger.warning(f"Dynamic RAG service not available: {e}")

class ChatService:
    """
    שירות RAG מואץ עם:
    - מטמון אגרסיבי יותר
    - שאילתות DB מקבילות ומובטלות
    - חיפוש מהיר יותר
    - prompt optimization
    """
    
    def __init__(self) -> None:
        self.ollama_service = OllamaService()
        self.qdrant_service = QdrantService()
        
        # מטמון משופר עם TTL
        self.response_cache = {}
        self.user_context_cache = {}
        self.embedding_cache = {}
        
        self.cache_max_size = 200
        self.user_cache_ttl = 300  # 5 דקות
        self.embedding_cache_ttl = 600  # 10 דקות
        
        # יצירת dynamic_rag רק אם זמין
        if DYNAMIC_RAG_AVAILABLE:
            try:
                self.dynamic_rag = DynamicRAGService()
                logger.info("ChatService initialized with Dynamic RAG")
            except Exception as e:
                self.dynamic_rag = None
                logger.warning(f"Failed to initialize Dynamic RAG: {e}")
        else:
            self.dynamic_rag = None
            
        logger.info("ChatService initialized with performance optimizations")

    def health_check(self) -> Dict[str, bool]:
        """בדיקת תקינות מהירה"""
        try:
            # בדיקות מהירות יותר עם timeout קצר
            qdrant_ok = self.qdrant_service.health_check()
            ollama_ok = self.ollama_service.health_check()
            
            status = {
                "qdrant_connected": qdrant_ok,
                "ollama_ready": ollama_ok,
                "chat_service_initialized": True,
                "cache_enabled": True,
                "dynamic_rag_enabled": self.dynamic_rag is not None,
                "cache_size": len(self.response_cache)
            }
            
            return status
        except Exception as e:
            logger.error(f"Health error: {e}")
            return {
                "qdrant_connected": False,
                "ollama_ready": False,
                "chat_service_initialized": False,
                "cache_enabled": False,
                "dynamic_rag_enabled": False
            }

    def _get_user_context(self, user_id: int, db: Session) -> Dict:
        """
        גרסה מואצת של קבלת הקשר משתמש:
        - מטמון למשך 5 דקות
        - שאילתה מובטלת יותר
        - רק הנתונים החיוניים
        """
        cache_key = f"user_ctx_{user_id}"
        current_time = time.time()
        
        # בדיקת מטמון
        if cache_key in self.user_context_cache:
            cached = self.user_context_cache[cache_key]
            if current_time - cached["timestamp"] < self.user_cache_ttl:
                logger.debug(f"Cache hit for user context {user_id}")
                return cached["data"]

        try:
            # שאילתה מהירה - רק הבסיס
            user_data = db.execute(text("""
                SELECT userType, company_name, contact_name
                FROM users WHERE id = :user_id
            """), {"user_id": user_id}).fetchone()

            if not user_data:
                return {"userType": "Unknown", "contact_name": "משתמש"}

            context = {
                "userType": user_data.userType,
                "company_name": user_data.company_name or "לא צוין",
                "contact_name": user_data.contact_name or "משתמש",
            }

            # אם זה ספק - נתונים בסיסיים בלבד
            if user_data.userType == "Supplier":
                supplier_stats = db.execute(text("""
                    SELECT 
                        COUNT(p.id) as products_count,
                        COUNT(CASE WHEN o.status = N'בתהליך' THEN 1 END) as active_orders
                    FROM products p
                    LEFT JOIN order_items oi ON p.id = oi.product_id
                    LEFT JOIN orders o ON oi.order_id = o.id
                    WHERE p.supplier_id = :user_id AND p.is_active = 1
                """), {"user_id": user_id}).fetchone()
                
                context.update({
                    "products_count": supplier_stats.products_count or 0,
                    "active_orders": supplier_stats.active_orders or 0,
                })

            # אם זה בעל חנות - נתונים בסיסיים בלבד
            elif user_data.userType == "StoreOwner":
                owner_stats = db.execute(text("""
                    SELECT 
                        COUNT(o.id) as total_orders,
                        COUNT(CASE WHEN o.status = N'בתהליך' THEN 1 END) as active_orders
                    FROM orders o WHERE o.owner_id = :user_id
                """), {"user_id": user_id}).fetchone()
                
                context.update({
                    "total_orders": owner_stats.total_orders or 0,
                    "active_orders": owner_stats.active_orders or 0,
                })

            # שמירה במטמון
            self.user_context_cache[cache_key] = {
                "data": context,
                "timestamp": current_time
            }
            
            # ניקוי מטמון אם גדול מדי
            if len(self.user_context_cache) > 50:
                oldest = min(self.user_context_cache.keys(), 
                           key=lambda k: self.user_context_cache[k]["timestamp"])
                del self.user_context_cache[oldest]

            return context

        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return {"userType": "Unknown", "contact_name": "משתמש"}

    def _get_embedding_cached(self, text: str) -> List[float]:
        """קבלת embedding עם מטמון חכם"""
        text_hash = hashlib.md5(text.strip().lower().encode()).hexdigest()
        current_time = time.time()
        
        # בדיקת מטמון
        if text_hash in self.embedding_cache:
            cached = self.embedding_cache[text_hash]
            if current_time - cached["timestamp"] < self.embedding_cache_ttl:
                return cached["embedding"]
        
        # יצירת embedding חדש
        embedding = self.ollama_service.get_embedding(text)
        if embedding:
            self.embedding_cache[text_hash] = {
                "embedding": embedding,
                "timestamp": current_time
            }
            
            # ניקוי מטמון
            if len(self.embedding_cache) > 100:
                oldest = min(self.embedding_cache.keys(), 
                           key=lambda k: self.embedding_cache[k]["timestamp"])
                del self.embedding_cache[oldest]
        
        return embedding

    def _classify_question_type(self, message: str, user_context: Dict = None) -> str:
        """סיווג מהיר של שאלה"""
        msg = message.lower()
        
        # בדיקות מהירות
        if any(w in msg for w in ["הזמנה", "הזמנות", "להזמין", "סטטוס"]):
            return "orders"
        elif any(w in msg for w in ["מוצר", "מוצרים", "מלאי", "מחיר"]):
            return "products"
        elif any(w in msg for w in ["ספק", "ספקים", "חיבור", "קשר"]):
            return "suppliers"
        elif any(w in msg for w in ["איך", "כיצד", "מה זה", "הוראות"]):
            return "how_to"
        elif any(w in msg for w in ["בעיה", "שגיאה", "לא עובד", "עזרה"]):
            return "support"
        else:
            return "general"

    def _enhance_search_query(self, query: str, question_type: str, user_context: Dict) -> str:
        """שיפור מהיר של שאילתת חיפוש"""
        user_type = user_context.get("userType", "").lower()
        
        # הוספה מינימלית של הקשר
        if question_type == "orders" and "supplier" in user_type:
            return f"{query} ספק הזמנות ניהול"
        elif question_type == "products" and "supplier" in user_type:
            return f"{query} ספק מוצרים הוספה"
        elif question_type == "suppliers" and "storeowner" in user_type:
            return f"{query} בעל חנות ספקים חיבור"
        
        return query

    def _create_minimal_prompt(self, context: str, question: str, user_context: Dict) -> str:
        """יצירת prompt מינימלי ומהיר"""
        user_type = "ספק" if "supplier" in user_context.get("userType", "").lower() else "בעל חנות"
        name = user_context.get("contact_name", "משתמש")
        
        return f"""אתה עוזר דיגיטלי למערכת ניהול ספקים.
המשתמש: {user_type} בשם {name}

מידע רלוונטי:
{context}

שאלה: {question}

תן תשובה קצרה ומעשית בעברית:"""

    async def process_chat_message_with_context(
        self, user_id: int, message: str, user_context: Dict, db: Session = None
    ) -> Dict[str, Optional[str]]:
        """
        עיבוד מואץ של הודעת צ'אט עם נתוני משתמש
        """
        start_time = time.time()
        
        try:
            # בדיקת מטמון תגובות מלא
            cache_key = f"{user_id}:{hashlib.md5(message.strip().lower().encode()).hexdigest()}"
            if cache_key in self.response_cache:
                cached = self.response_cache[cache_key]
                if time.time() - cached["timestamp"] < 600:  # 10 דקות
                    logger.info(f"Full cache hit for user {user_id}")
                    result = cached["data"].copy()
                    result["response_time"] = round(time.time() - start_time, 2)
                    result["from_cache"] = True
                    return result

            # סיווג מהיר
            question_type = self._classify_question_type(message, user_context)
            
            # נסיון לתשובה מהירה מהדטבייס למספרים בסיסיים
            quick_answer = self._try_quick_numeric_answer(message, user_id, user_context, db)
            if quick_answer:
                return {
                    "success": True,
                    "message": "תשובה מהירה מנתוני המערכת",
                    "response": quick_answer,
                    "user_type": user_context.get("userType"),
                    "contexts_found": 0,
                    "dynamic_context_used": False,
                    "response_time": round(time.time() - start_time, 2),
                }

            # חיפוש RAG מהיר
            enhanced_query = self._enhance_search_query(message, question_type, user_context)
            embedding = self._get_embedding_cached(enhanced_query)
            
            if not embedding:
                return self._create_error_response("לא הצלחתי לעבד את השאלה", user_context, start_time)

            # חיפוש מהיר יותר
            search_limit = 3 if question_type != "how_to" else 4
            snippets = self.qdrant_service.search(embedding, limit=search_limit)
            
            context = "\n---\n".join(snippets) if snippets else "מידע כללי על המערכת"
            
            # יצירת prompt מינימלי
            prompt = self._create_minimal_prompt(context, message, user_context)
            
            # יצירת תשובה
            answer = self.ollama_service.generate_response(context, message)
            
            if not answer:
                return self._create_error_response("לא הצלחתי ליצור תשובה", user_context, start_time)

            result = {
                "success": True,
                "message": "תשובה נוצרה בהצלחה",
                "response": answer,
                "user_type": user_context.get("userType"),
                "contexts_found": len(snippets),
                "dynamic_context_used": False,
                "response_time": round(time.time() - start_time, 2),
            }
            
            # שמירה במטמון
            self.response_cache[cache_key] = {
                "data": result.copy(),
                "timestamp": time.time()
            }
            
            # ניקוי מטמון
            if len(self.response_cache) > self.cache_max_size:
                oldest = min(self.response_cache.keys(), 
                           key=lambda k: self.response_cache[k]["timestamp"])
                del self.response_cache[oldest]

            return result

        except Exception as e:
            logger.error(f"Error in process_chat_message_with_context: {e}")
            return self._create_error_response(f"שגיאה: {str(e)}", user_context, start_time)

    def _try_quick_numeric_answer(self, message: str, user_id: int, user_context: Dict, db: Session) -> Optional[str]:
        """תשובה מהירה למספרים בסיסיים"""
        if not db:
            return None
            
        msg = message.lower()
        
        # בדיקה אם זו שאלה מספרית
        if not any(k in msg for k in ["כמה", "מספר", "כמה יש"]):
            return None

        user_type = user_context.get("userType", "")
        
        try:
            if "הזמנות" in msg and user_type == "Supplier":
                count = db.execute(text("""
                    SELECT COUNT(*) FROM orders o 
                    JOIN order_items oi ON o.id = oi.order_id
                    JOIN products p ON oi.product_id = p.id
                    WHERE p.supplier_id = :uid AND o.status = N'בתהליך'
                """), {"uid": user_id}).scalar()
                return f"יש לך {count or 0} הזמנות פעילות."
                
            elif "מוצרים" in msg and user_type == "Supplier":
                count = db.execute(text("""
                    SELECT COUNT(*) FROM products WHERE supplier_id = :uid AND is_active = 1
                """), {"uid": user_id}).scalar()
                return f"יש לך {count or 0} מוצרים פעילים."
                
        except Exception:
            pass
            
        return None

    def _create_error_response(self, message: str, user_context: Dict, start_time: float) -> Dict:
        """יצירת תגובת שגיאה סטנדרטית"""
        return {
            "success": False,
            "message": message,
            "response": None,
            "user_type": user_context.get("userType"),
            "contexts_found": 0,
            "dynamic_context_used": False,
            "response_time": round(time.time() - start_time, 2)
        }

    # Backward compatibility
    async def process_chat_message(self, user_id: int, message: str, db: Session = None) -> Dict[str, Optional[str]]:
        """פונקציה ישנה - מכוונת לגרסה החדשה"""
        user_context = self._get_user_context(user_id, db) if db else {}
        return await self.process_chat_message_with_context(user_id, message, user_context, db)

    def clear_cache(self):
        """ניקוי כל המטמון"""
        self.response_cache.clear()
        self.user_context_cache.clear()
        self.embedding_cache.clear()
        logger.info("All caches cleared")