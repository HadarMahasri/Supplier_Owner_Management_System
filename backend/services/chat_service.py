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
    
        # ===== Reranker פרוצדורלי ל-How-To =====
    _PROCEDURAL = ["לחץ","לחצי","בחר","בחרי","פתח","פתחי","שמור","שמרי","אשר","אשרי","שלח","שלחי"]
    _UI_TERMS   = ["רשימת הזמנות","רשימת ספקים","הזמנה חדשה","חיבורים","בקשות ממתינות","ניהול מוצרים"]

    def _score_proc(self, text: str) -> float:
        """ניקוד קטעים הוראתיים: פעלים פרוצדורליים + שמות UI; קנס קל לאורך מוגזם."""
        t = (text or "")
        tl = t.lower()
        verb_hits = sum(1 for v in self._PROCEDURAL if v in tl)
        ui_hits   = sum(1 for u in self._UI_TERMS if u in t)
        length_penalty = 0.2 if len(t) > 600 else 0.0
        return verb_hits * 1.5 + ui_hits * 1.2 - length_penalty

    def _rerank_proc(self, chunks: List[str]) -> List[str]:
        """מסדר קטעים לפי ציון פרוצדורלי (גבוה→נמוך)."""
        scored = sorted(((c, self._score_proc(c)) for c in chunks if c),
                        key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored]

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
        if question_type == "how_to":
            q += " מדריך הוראות שלבים לחץ לחצי בחר בחרי פתח פתחי שמור אשר 'רשימת הזמנות' 'רשימת ספקים' 'הזמנה חדשה' 'חיבורים' 'בקשות ממתינות' 'ניהול מוצרים'"

        # הוספה מינימלית של הקשר
        elif question_type == "orders" and "supplier" in user_type:
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
        עיבוד הודעת צ'אט עם RAG מואץ:
        - how_to: תמיד דרך RAG (מסונן לקטעי HOWTO ולפי תפקיד), ללא קיצור-DB.
        - אחר: ניסיון תשובה מהירה ממסד הנתונים ואז RAG רגיל.
        - כולל מטמון מלא (response_cache) ומדדים להצלבה ב־UI.
        """
        import time, hashlib
        start_time = time.time()

        try:
            question = (message or "").strip()
            if not question:
                return {
                    "success": False,
                    "message": "שגיאה",
                    "response": "לא התקבלה שאלה.",
                    "user_type": (user_context or {}).get("userType"),
                    "contexts_found": 0,
                    "dynamic_context_used": False,
                    "response_time": round(time.time() - start_time, 2),
                }

            # ===== מטמון תשובה מלאה =====
            cache_key = f"{user_id}:{hashlib.md5(question.lower().encode()).hexdigest()}"
            cached = self.response_cache.get(cache_key)
            if cached and time.time() - cached["timestamp"] < 600:
                result = dict(cached["data"])
                result["response_time"] = round(time.time() - start_time, 2)
                result["from_cache"] = True
                return result

            # ===== סיווג שאלה =====
            try:
                question_type = self._classify_question_type(question, user_context)
            except Exception:
                question_type = "general"

            # ===== קיצור-DB: מדדים מספריים (לא להריץ ב-how_to) =====
            if question_type != "how_to":
                try:
                    quick_answer = self._try_answer_numeric_metrics(question, user_id, user_context, db)
                except Exception:
                    quick_answer = None
                if quick_answer:
                    result = {
                        "success": True,
                        "message": "תשובה מהירה מנתוני המערכת",
                        "response": quick_answer,
                        "user_type": (user_context or {}).get("userType"),
                        "contexts_found": 0,
                        "dynamic_context_used": False,
                        "response_time": round(time.time() - start_time, 2),
                    }
                    # מטמון
                    self.response_cache[cache_key] = {"data": dict(result), "timestamp": time.time()}
                    if len(self.response_cache) > self.cache_max_size:
                        oldest = min(self.response_cache.keys(), key=lambda k: self.response_cache[k]["timestamp"])
                        self.response_cache.pop(oldest, None)
                    return result

            # ===== RAG: הכנת שאילתה + embedding =====
            try:
                enhanced_query = self._enhance_search_query(question, question_type, user_context)
            except Exception:
                enhanced_query = question

            try:
                embedding = self._get_embedding_cached(enhanced_query or question)
            except Exception:
                embedding = None

            if not embedding:
                return {
                    "success": False,
                    "message": "לא הצלחתי לעבד את השאלה",
                    "response": "נסה לנסח מחדש את השאלה.",
                    "user_type": (user_context or {}).get("userType"),
                    "contexts_found": 0,
                    "dynamic_context_used": False,
                    "response_time": round(time.time() - start_time, 2),
                }

            # ===== חיפוש ב-Qdrant =====
            contexts_found = 0
            static_snippets: List[str] = []
            search_limit = 5 if question_type in ("how_to", "support") else 3

            if self.qdrant_service:
                try:
                    if question_type == "how_to":
                        # סינון לקטעי HOWTO ולפי תפקיד המשתמש
                        role = (user_context or {}).get("userType") or (user_context or {}).get("role") or "Any"
                        flt = {"must": [{"key": "type", "match": {"value": "how_to"}}]}
                        if role in ("StoreOwner", "Supplier"):
                            flt["must"].append({"key": "role", "match": {"value": role}})
                        static_snippets = self.qdrant_service.search(embedding, limit=6, filter_=flt) or []  # דורש search(filter_) בשירות
                        # ריראנקר פרוצדורלי אם קיים
                        if hasattr(self, "_rerank_proc"):
                            static_snippets = self._rerank_proc(static_snippets)[:6]
                    else:
                        static_snippets = self.qdrant_service.search(embedding, limit=search_limit) or []
                    contexts_found = len(static_snippets)
                except Exception:
                    static_snippets = []
                    contexts_found = 0

            # ===== הקשר סופי =====
            context = "\n---\n".join(static_snippets) if static_snippets else "אין הקשר זמין. ענה בזהירות וללא ניחושים."

            # ===== יצירת prompt/תשובה =====
            try:
                # אם יש לך פרומפט מינימלי מותאם – השארנו כפי שהיה
                prompt = self._create_minimal_prompt(context, question, user_context)
            except Exception:
                # נפילה לפרומפט בסיסי
                prompt = f"הקשר:\n{context}\n\nשאלה: {question}\nענה בעברית, קצר וברור."

            try:
                answer = self.ollama_service.generate_response(context, question)  # הממשק הקיים אצלך
            except Exception as e:
                return {
                    "success": False,
                    "message": f"שגיאה ביצירת תשובה: {e}",
                    "response": "אירעה שגיאה בעת יצירת התשובה.",
                    "user_type": (user_context or {}).get("userType"),
                    "contexts_found": contexts_found,
                    "dynamic_context_used": False,
                    "response_time": round(time.time() - start_time, 2),
                }

            if not answer:
                return {
                    "success": False,
                    "message": "לא הצלחתי ליצור תשובה",
                    "response": "נסה לשאול מחדש או לנסח אחרת.",
                    "user_type": (user_context or {}).get("userType"),
                    "contexts_found": contexts_found,
                    "dynamic_context_used": False,
                    "response_time": round(time.time() - start_time, 2),
                }

            # ===== תוצאת הצלחה + מטמון =====
            result = {
                "success": True,
                "message": "תשובה מבוססת RAG",
                "response": answer,
                "user_type": (user_context or {}).get("userType"),
                "contexts_found": contexts_found,
                "dynamic_context_used": False,
                "response_time": round(time.time() - start_time, 2),
            }

            self.response_cache[cache_key] = {"data": dict(result), "timestamp": time.time()}
            if len(self.response_cache) > self.cache_max_size:
                oldest = min(self.response_cache.keys(), key=lambda k: self.response_cache[k]["timestamp"])
                self.response_cache.pop(oldest, None)

            return result

        except Exception as e:
            logger.error(f"Error in process_chat_message_with_context: {e}")
            return {
                "success": False,
                "message": f"שגיאה: {str(e)}",
                "response": "אירעה שגיאה בעיבוד הבקשה.",
                "user_type": (user_context or {}).get("userType"),
                "contexts_found": 0,
                "dynamic_context_used": False,
                "response_time": round(time.time() - start_time, 2),
            }


    def _try_answer_numeric_metrics(self, message: str, user_id: int, user_context: Dict, db: Session):
        """
        מענה דטרמיניסטי לשאלות מספריות (כמה/מספר) – הזמנות, מוצרים, חיבורים.
        כולל תמיכה בסטטוסים: בוצעה, בתהליך, הושלמה.
        """
        if not db:
            return None

        q = (message or "").lower()

        # זיהוי אם זו בכלל שאלה מספרית
        asks_any_count = any(k in q for k in ["כמה", "מספר", "מס'", "סה\"כ", "סך", "כמה יש"])
        if not asks_any_count:
            return None

        # קטגוריות
        asks_orders   = any(k in q for k in ["הזמנה", "הזמנות", "סטטוס"])
        asks_products = any(k in q for k in ["מוצר", "מוצרים", "קטלוג", "מלאי"])
        asks_links    = any(k in q for k in ["חיבור", "קישור", "קישורים", "חיבורים"])

        # סטטוסים
        wants_pending   = any(k in q for k in ["בתהליך", "ממתין", "ממתינות", "pending", "פתוח", "פתוחה", "פתוחות", "פתוחים"])
        wants_completed = any(k in q for k in ["הושלמ", "הושלמה", "הושלמו", "completed"])
        wants_done      = any(k in q for k in ["בוצע", "בוצעה", "בוצעו"])
        wants_outofstock= any(k in q for k in ["אזל", "אזלו", "חסר", "נגמר"])

        # סוג המשתמש (גם role וגם userType)
        ut = (user_context or {}).get("userType") or (user_context or {}).get("role") or ""

        if ut == "Supplier":
            # ספירה לספק
            row = db.execute(text("""
                SELECT
                    COUNT(p.id) AS products_count,
                    COUNT(CASE WHEN p.stock = 0 THEN 1 END) AS out_of_stock,
                    COUNT(CASE WHEN o.status = N'בתהליך' THEN 1 END) AS pending_orders,
                    COUNT(CASE WHEN o.status = N'הושלמה' THEN 1 END) AS completed_orders,
                    COUNT(CASE WHEN o.status = N'בוצעה' THEN 1 END) AS done_orders,
                    COUNT(DISTINCT o.id) AS total_orders
                FROM products p
                LEFT JOIN order_items oi ON oi.product_id = p.id
                LEFT JOIN orders o ON o.id = oi.order_id
                WHERE p.supplier_id = :uid AND p.is_active = 1
            """), {"uid": user_id}).fetchone()

            products_count  = (row.products_count or 0)
            out_of_stock    = (row.out_of_stock or 0)
            pending_orders  = (row.pending_orders or 0)
            completed_orders= (row.completed_orders or 0)
            done_orders     = (row.done_orders or 0)
            total_orders    = (row.total_orders or 0)

            if asks_orders:
                if wants_pending:
                    return f"יש {pending_orders} הזמנות פתוחות (בתהליך)."
                elif wants_completed:
                    return f"הושלמו {completed_orders} הזמנות."
                elif wants_done:
                    return f"בוצעו {done_orders} הזמנות."
                else:
                    return f"סה\"כ יש {total_orders} הזמנות."
            if asks_products:
                if wants_outofstock:
                    return f"{out_of_stock} מוצרים אזלו מהמלאי."
                else:
                    return f"יש {products_count} מוצרים פעילים."
            if asks_links:
                links_row = db.execute(text("""
                    SELECT COUNT(*) AS active_links
                    FROM links
                    WHERE supplier_id = :uid AND status = N'פעיל'
                """), {"uid": user_id}).fetchone()
                return f"יש לך {links_row.active_links or 0} חיבורים פעילים עם בעלי חנויות."

        elif ut == "StoreOwner":
            row = db.execute(text("""
                SELECT
                    COUNT(o.id) AS total_orders,
                    COUNT(CASE WHEN o.status = N'בתהליך' THEN 1 END) AS pending,
                    COUNT(CASE WHEN o.status = N'הושלמה' THEN 1 END) AS completed,
                    COUNT(CASE WHEN o.status = N'בוצעה' THEN 1 END) AS done
                FROM orders o
                WHERE o.owner_id = :uid
            """), {"uid": user_id}).fetchone()

            total_orders = (row.total_orders or 0)
            pending      = (row.pending or 0)
            completed    = (row.completed or 0)
            done         = (row.done or 0)

            if asks_orders:
                if wants_pending:
                    return f"יש {pending} הזמנות פתוחות (בתהליך)."
                elif wants_completed:
                    return f"הושלמו {completed} הזמנות."
                elif wants_done:
                    return f"בוצעו {done} הזמנות."
                else:
                    return f"סה\"כ יש {total_orders} הזמנות."
            if asks_links:
                links_row = db.execute(text("""
                    SELECT COUNT(*) AS active_links
                    FROM links
                    WHERE owner_id = :uid AND status = N'פעיל'
                """), {"uid": user_id}).fetchone()
                return f"יש לך {links_row.active_links or 0} חיבורים פעילים עם ספקים."
            # לבעל חנות אין מוצרים משלו

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