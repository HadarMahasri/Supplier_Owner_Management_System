import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
import time

from .ollama_service import OllamaService
from .qdrant_service import QdrantService

logger = logging.getLogger(__name__)
from dotenv import load_dotenv

# Import בטוח של DynamicRAGService
try:
    from .dynamic_rag_service import DynamicRAGService
    DYNAMIC_RAG_AVAILABLE = True
except ImportError as e:
    DYNAMIC_RAG_AVAILABLE = False
    logger.warning(f"Dynamic RAG service not available: {e}")

class ChatService:
    """
    שירות RAG משודרג עם תמיכה בנתוני משתמש אישיים:
    - זיהוי סוג השאלה ומיקוד החיפוש בהתאם
    - שימוש בנתוני המערכת האמיתיים
    - תשובות מותאמות לסוג המשתמש
    - מטמון לביצועים טובים יותר
    - RAG דינמי על נתוני משתמש אישיים (אם זמין)
    """
    load_dotenv()

    def __init__(self) -> None:
        self.ollama_service = OllamaService()
        self.qdrant_service = QdrantService()
        self.response_cache = {}
        self.cache_max_size = 100
        
        # יצירת dynamic_rag רק אם זמין
        if DYNAMIC_RAG_AVAILABLE:
            try:
                self.dynamic_rag = DynamicRAGService()
                logger.info("ChatService initialized with Dynamic RAG enhancements")
            except Exception as e:
                self.dynamic_rag = None
                logger.warning(f"Failed to initialize Dynamic RAG: {e}")
        else:
            self.dynamic_rag = None
            logger.info("ChatService initialized without Dynamic RAG")

    def health_check(self) -> Dict[str, bool]:
        try:
            qdrant_ok = self.qdrant_service.health_check()
            ollama_ok = self.ollama_service.health_check()
            status = {
                "qdrant_connected": qdrant_ok,
                "ollama_ready": ollama_ok,
                "chat_service_initialized": True,
                "cache_enabled": True,
                "dynamic_rag_enabled": self.dynamic_rag is not None
            }
            logger.info(f"Health status: {status}")
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
        """קבלת הקשר על המשתמש מבסיס הנתונים"""
        try:
            # שאילתת פרטי המשתמש
            user_query = text("""
                SELECT userType, company_name, contact_name, 
                       COUNT(CASE WHEN o.status = N'בתהליך' THEN 1 END) as active_orders,
                       COUNT(p.id) as products_count
                FROM users u
                LEFT JOIN orders o ON (u.userType = 'StoreOwner' AND o.owner_id = u.id) 
                                   OR (u.userType = 'Supplier' AND o.supplier_id = u.id)
                LEFT JOIN products p ON (u.userType = 'Supplier' AND p.supplier_id = u.id)
                WHERE u.id = :user_id
                GROUP BY u.id, u.userType, u.company_name, u.contact_name
            """)
            
            result = db.execute(user_query, {"user_id": user_id}).fetchone()
            
            if result:
                return {
                    "user_type": result[0],
                    "company_name": result[1] or "לא צוין",
                    "contact_name": result[2] or "משתמש",
                    "active_orders": result[3] or 0,
                    "products_count": result[4] or 0
                }
            
            return {"user_type": "Unknown", "contact_name": "משתמש"}
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return {"user_type": "Unknown", "contact_name": "משתמש"}

    def _classify_question_type(self, message: str) -> str:
        """זיהוי סוג השאלה לשיפור הרלוונטיות"""
        message_lower = message.lower()
        
        # מילות מפתח לזיהוי נושאים
        if any(word in message_lower for word in ["הזמנה", "הזמנות", "להזמין", "הזמנה חדשה", "סטטוס הזמנה"]):
            return "orders"
        elif any(word in message_lower for word in ["מוצר", "מוצרים", "מלאי", "מחיר", "קטלוג", "מוצר חדש"]):
            return "products"
        elif any(word in message_lower for word in ["ספק", "ספקים", "חיבור", "קשר", "לחבר", "בעל חנות"]):
            return "suppliers"
        elif any(word in message_lower for word in ["איך", "כיצד", "מה זה", "מה המשמעות", "הוראות"]):
            return "how_to"
        elif any(word in message_lower for word in ["בעיה", "שגיאה", "לא עובד", "תקלה", "עזרה", "בעיות"]):
            return "support"
        elif any(word in message_lower for word in ["דוח", "דוחות", "נתונים", "סטטיסטיקה", "ניתוח"]):
            return "analytics"
        else:
            return "general"

    def _enhance_search_query(self, original_query: str, question_type: str, user_context: Dict) -> str:
        """שיפור שאילתת החיפוש בהתבסס על סוג השאלה והקשר המשתמש"""
        user_type = user_context.get("userType", "").lower()
        
        # הוספת הקשר רלוונטי לשאילתה
        enhanced_query = original_query
        
        if question_type == "orders" and "supplier" in user_type:
            enhanced_query += " ספק הזמנות ניהול אישור עדכון סטטוס"
        elif question_type == "orders" and "storeowner" in user_type:
            enhanced_query += " בעל חנות הזמנה ביצוע מעקב"
        elif question_type == "products" and "supplier" in user_type:
            enhanced_query += " ספק מוצרים הוספה עריכה מלאי עדכון"
        elif question_type == "suppliers" and "storeowner" in user_type:
            enhanced_query += " בעל חנות חיפוש ספקים חיבור בקשה"
        
        return enhanced_query

    def _create_personalized_prompt(self, context: str, question: str, user_context: Dict) -> str:
        """יצירת prompt מותאם אישית"""
        user_type_hebrew = "ספק" if "supplier" in user_context.get("userType", "").lower() else "בעל חנות"
        contact_name = user_context.get("contact_name", "משתמש")
        
        # הוספת מידע על מצב המשתמש הנוכחי
        status_info = ""
        if user_context.get("active_orders", 0) > 0:
            status_info += f"\nיש לך כרגע {user_context['active_orders']} הזמנות פעילות. "
        if user_context.get("products_count", 0) > 0:
            status_info += f"יש לך {user_context['products_count']} מוצרים במערכת. "

        system_prompt = f"""אתה עוזר דיגיטלי מומחה במערכת ניהול ספקים.

המשתמש הנוכחי הוא {user_type_hebrew} בשם {contact_name}.{status_info}

בהתבסס על המידע הבא מבסיס הידע שלי:
{context}

הנחיות לתשובה (חשוב מאוד):
1. תן תשובה מדויקת ומעשית עם הוראות צעד-צעד
2. התאם את התשובה בדיוק לסוג המשתמש ({user_type_hebrew})
3. השתמש בדוגמאות ספציפיות מהמערכת
4. אם אין מידע מדויק, הסבר מה כן ניתן לעשות
5. תמיד סיים עם הצעה מעשית לפעולה הבאה
6. השתמש בעברית ברורה ומקצועית
7. אל תחזור על עצמך - תן מידע חדש ושימושי

שאלת המשתמש: {question}

תשובה מועילה ומדויקת:"""
        
        return system_prompt

    async def process_chat_message(
        self, user_id: int, message: str, db: Session = None
    ) -> Dict[str, Optional[str]]:
        """עיבוד הודעת צ'אט משודרג עם חכמה מוגברת (הפונקציה המקורית)"""
        try:
            # בדיקת מטמון (אופציונלי - רק לשאלות זהות לגמרי)
            cache_key = f"{user_id}:{hash(message.strip().lower())}"
            if len(message.strip()) > 10 and cache_key in self.response_cache:
                logger.info(f"Cache hit for user {user_id}")
                cached_result = self.response_cache[cache_key].copy()
                cached_result["message"] = "תשובה נוצרה בהצלחה (מטמון מהיר)"
                return cached_result

            # קבלת הקשר המשתמש
            user_context = self._get_user_context(user_id, db) if db else {}
            
            # זיהוי סוג השאלה
            question_type = self._classify_question_type(message)
            logger.info(f"Question type classified as: {question_type} for user {user_id}")

            # שיפור שאילתת החיפוש
            enhanced_query = self._enhance_search_query(message, question_type, user_context)
            
            # קבלת embedding
            question_vec: List[float] = self.ollama_service.get_embedding(enhanced_query)
            if not question_vec:
                return {
                    "success": False,
                    "message": "לא הצלחתי לעבד את השאלה כרגע. אנא נסה שוב.",
                    "response": None,
                    "user_type": user_context.get("userType"),
                    "contexts_found": 0,
                }

            # חיפוש מותאם לסוג השאלה
            search_limit = 5 if question_type in ["how_to", "support"] else 3
            snippets = self.qdrant_service.search(question_vec, limit=search_limit)
            
            # בניית הקשר מעשיר
            if snippets:
                context = "\n---\n".join(snippets)
                
                # הוספת מידע דינמי מהמערכת אם זמין
                if db and question_type == "orders":
                    context += self._add_orders_context(user_id, user_context, db)
                elif db and question_type == "products":
                    context += self._add_products_context(user_id, user_context, db)
            else:
                context = "מצטער, לא מצאתי מידע ספציפי במערכת, אך יכול לתת הדרכה כללית."

            # יצירת prompt מותאם אישית
            enhanced_prompt = self._create_personalized_prompt(context, message, user_context)
            
            # יצירת תשובה עם הפרמטר החדש
            answer: Optional[str] = self.ollama_service.generate_response(enhanced_prompt, message)
            
            if not answer:
                return {
                    "success": False,
                    "message": "מצטער, לא הצלחתי לייצר תשובה כרגע. אנא נסה שוב או פנה לתמיכה.",
                    "response": None,
                    "user_type": user_context.get("userType"),
                    "contexts_found": len(snippets),
                }

            # הוספה למטמון
            result = {
                "success": True,
                "message": "תשובה נוצרה בהצלחה",
                "response": answer,
                "user_type": user_context.get("userType"),
                "contexts_found": len(snippets),
            }
            
            self._update_cache(cache_key, result)
            return result

        except Exception as e:
            logger.exception(f"process_chat_message error: {e}")
            return {
                "success": False,
                "message": f"אירעה שגיאה בעיבוד הודעתך. אנא נסה שוב.",
                "response": None,
                "user_type": None,
                "contexts_found": 0,
            }

    async def process_chat_message_with_context(
        self, user_id: int, message: str, user_context: Dict, db: Session = None
    ) -> Dict[str, Optional[str]]:
        """
        עיבוד הודעת צ'אט עם נתוני משתמש מלאים + Dynamic RAG (אם זמין)
        """
        start_time = time.time()
        
        try:
            # בדיקה אם Dynamic RAG זמין לפני השימוש
            dynamic_context_initialized = False
            if db and self.dynamic_rag is not None:
                try:
                    dynamic_context_initialized = self.dynamic_rag.initialize_user_context(user_id, db)
                    if dynamic_context_initialized:
                        logger.info(f"Dynamic RAG context generated for user {user_id}")
                except Exception as e:
                    logger.warning(f"Dynamic RAG initialization failed: {e}")
                    dynamic_context_initialized = False

            # בדיקת מטמון
            cache_key = f"{user_id}:{hash(message.strip().lower())}:{hash(str(user_context))}:dyn_{dynamic_context_initialized}"
            if len(message.strip()) > 10 and cache_key in self.response_cache:
                logger.info(f"Cache hit for user {user_id}")
                cached_result = self.response_cache[cache_key].copy()
                cached_result["message"] = "תשובה נוצרה בהצלחה (מטמון מהיר)"
                cached_result["response_time"] = round(time.time() - start_time, 2)
                return cached_result

            # זיהוי סוג השאלה ושיפור החיפוש
            question_type = self._classify_question_type(message)
            logger.info(f"Question type classified as: {question_type} for user {user_id}")

            enhanced_query = self._enhance_search_query(message, question_type, user_context)
            
            # קבלת embedding
            question_vec: List[float] = self.ollama_service.get_embedding(enhanced_query)
            if not question_vec:
                return self._create_error_response("לא הצלחתי לעבד את השאלה כרגע", user_context, start_time)

            # חיפוש בRAG הסטטי
            search_limit = 5 if question_type in ["how_to", "support"] else 3
            static_snippets = self.qdrant_service.search(question_vec, limit=search_limit)
            
            # בניית הקשר בסיסי
            if static_snippets:
                base_context = "\n---\n".join(static_snippets)
            else:
                base_context = "מצטער, לא מצאתי מידע ספציפי במערכת, אך יכול לתת הדרכה כללית."

            # העשרה עם Dynamic RAG (רק אם זמין)
            if self.dynamic_rag is not None and dynamic_context_initialized:
                try:
                    enhanced_context = self.dynamic_rag.get_enhanced_context(
                        user_id, question_vec, base_context
                    )
                    logger.debug("Enhanced context with Dynamic RAG")
                except Exception as e:
                    logger.warning(f"Dynamic RAG enhancement failed: {e}")
                    enhanced_context = base_context
            else:
                enhanced_context = base_context
            
            # הוספת המידע הנוסף (התכונה הקיימת)
            final_context = enhanced_context + self._build_personalized_context(user_id, user_context, question_type, db)

            # יצירת prompt ותשובה
            enhanced_prompt = self._create_personalized_prompt_with_context(final_context, message, user_context)
            answer: Optional[str] = self.ollama_service.generate_response(enhanced_prompt, message)
            
            if not answer:
                return self._create_error_response("לא הצלחתי לייצר תשובה כרגע", user_context, start_time)

            # תוצאה
            result = {
                "success": True,
                "message": "תשובה נוצרה בהצלחה" + (" עם Dynamic RAG" if dynamic_context_initialized else ""),
                "response": answer,
                "user_type": user_context.get("userType"),
                "contexts_found": len(static_snippets),
                "dynamic_context_used": dynamic_context_initialized,
                "response_time": round(time.time() - start_time, 2)
            }
            
            self._update_cache(cache_key, result)
            return result

        except Exception as e:
            logger.exception(f"process_chat_message_with_context error: {e}")
            return self._create_error_response("אירעה שגיאה בעיבוד הודעתך", user_context, start_time)

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
        
    def _build_personalized_context(self, user_id: int, user_context: Dict, question_type: str, db: Session) -> str:
        """בניית הקשר אישי מבוסס על נתוני המשתמש האמיתיים"""
        context_parts = []
        
        # מידע בסיסי על המשתמש
        user_type = user_context.get("userType", "")
        contact_name = user_context.get("contact_name", "משתמש")
        company_name = user_context.get("company_name", "")
        
        context_parts.append(f"\n=== מידע אישי על המשתמש ===")
        context_parts.append(f"סוג משתמש: {'ספק' if user_type == 'Supplier' else 'בעל חנות'}")
        context_parts.append(f"שם: {contact_name}")
        if company_name:
            context_parts.append(f"חברה: {company_name}")
        
        # מידע ספציפי לספק
        if user_type == "Supplier":
            products_count = user_context.get("products_count", 0)
            active_orders = user_context.get("active_orders", 0)
            out_of_stock = user_context.get("out_of_stock_products", 0)
            
            context_parts.append(f"מספר מוצרים פעילים: {products_count}")
            context_parts.append(f"הזמנות פעילות: {active_orders}")
            if out_of_stock > 0:
                context_parts.append(f"מוצרים שאזלו מהמלאי: {out_of_stock}")
            
            # הוספת מידע ספציפי לשאלה אם זמין
            if question_type == "products" and db:
                try:
                    # המוצרים הפופולריים ביותר של הספק
                    popular_products = db.execute(text("""
                        SELECT TOP 3 p.product_name, SUM(oi.quantity) as total_ordered
                        FROM products p
                        LEFT JOIN order_items oi ON p.id = oi.product_id
                        LEFT JOIN orders o ON oi.order_id = o.id
                        WHERE p.supplier_id = :user_id 
                        AND o.created_date >= DATEADD(month, -1, GETDATE())
                        GROUP BY p.id, p.product_name
                        ORDER BY total_ordered DESC
                    """), {"user_id": user_id}).fetchall()
                    
                    if popular_products:
                        context_parts.append(f"המוצרים הפופולריים שלך בחודש האחרון:")
                        for product in popular_products:
                            context_parts.append(f"- {product.product_name} ({product.total_ordered or 0} הוזמנו)")
                except Exception as e:
                    logger.debug(f"Could not fetch popular products: {e}")
        
        # מידע ספציפי לבעל חנות
        elif user_type == "StoreOwner":
            active_orders = user_context.get("active_orders", 0)
            connected_suppliers = user_context.get("connected_suppliers", 0)
            
            context_parts.append(f"הזמנות פעילות: {active_orders}")
            context_parts.append(f"ספקים מחוברים: {connected_suppliers}")
            
            # מידע על החנות
            street = user_context.get("street")
            house_number = user_context.get("house_number")
            opening_time = user_context.get("opening_time")
            closing_time = user_context.get("closing_time")
            
            if street and house_number:
                context_parts.append(f"כתובת החנות: {street} {house_number}")
            if opening_time and closing_time:
                context_parts.append(f"שעות פתיחה: {opening_time} - {closing_time}")
            
            # הוספת מידע על הזמנות אחרונות אם זמין
            if question_type == "orders" and db:
                try:
                    recent_orders = db.execute(text("""
                        SELECT TOP 3 o.id, o.status, u.company_name, o.created_date
                        FROM orders o
                        JOIN users u ON o.supplier_id = u.id
                        WHERE o.owner_id = :user_id
                        ORDER BY o.created_date DESC
                    """), {"user_id": user_id}).fetchall()
                    
                    if recent_orders:
                        context_parts.append(f"ההזמנות האחרונות שלך:")
                        for order in recent_orders:
                            status = order.status
                            supplier = order.company_name or "ספק"
                            context_parts.append(f"- הזמנה #{order.id} מ{supplier}: {status}")
                except Exception as e:
                    logger.debug(f"Could not fetch recent orders: {e}")
        
        return "\n".join(context_parts)

    def _create_personalized_prompt_with_context(self, context: str, question: str, user_context: Dict) -> str:
        """יצירת prompt מותאם אישית עם כל נתוני המשתמש"""
        user_type = user_context.get("userType", "")
        user_type_hebrew = "ספק" if user_type == "Supplier" else "בעל חנות"
        contact_name = user_context.get("contact_name", "משתמש")
        company_name = user_context.get("company_name", "")
        
        # בניית prompt מפורט ואישי
        system_prompt = f"""אתה עוזר דיגיטלי מומחה במערכת ניהול ספקים.

המשתמש הנוכחי הוא {user_type_hebrew} בשם {contact_name}."""

        if company_name:
            system_prompt += f" מחברת {company_name}."

        # הוספת מידע ספציפי לסוג המשתמש
        if user_type == "Supplier":
            products_count = user_context.get("products_count", 0)
            active_orders = user_context.get("active_orders", 0)
            system_prompt += f"""
            
כספק, יש לך כרגע {products_count} מוצרים פעילים במערכת ו-{active_orders} הזמנות פעילות."""
        
        elif user_type == "StoreOwner":
            connected_suppliers = user_context.get("connected_suppliers", 0)
            active_orders = user_context.get("active_orders", 0)
            system_prompt += f"""
            
כבעל חנות, יש לך כרגע {connected_suppliers} ספקים מחוברים ו-{active_orders} הזמנות פעילות."""

        system_prompt += f"""

בהתבסס על המידע הבא מבסיס הידע ומהמערכת:
{context}

הנחיות לתשובה (חשוב מאוד):
1. תן תשובה מדויקת ומעשית עם הוראות צעד-צעד
2. השתמש בשם המשתמש ({contact_name}) בתשובה באופן טבעי
3. התייחס לנתונים הספציפיים שלו (מספר מוצרים, הזמנות וכו')
4. התאם את התשובה בדיוק לסוג המשתמש ({user_type_hebrew})
5. תן דוגמאות ספציפיות מהמערכת והנתונים שלו
6. אם אין מידע מספיק, הסבר מה כן ניתן לעשות בהתבסס על מצבו
7. תמיד סיים עם הצעה מעשית וספציפית לפעולה הבאה
8. השתמש בעברית ברורה ומקצועית
9. אל תחזור על עצמך - תן מידע חדש ושימושי
10. היה אישי וידידותי אך מקצועי

שאלת המשתמש: {question}

תשובה מותאמת אישית ומועילה:"""
        
        return system_prompt

    def _add_orders_context(self, user_id: int, user_context: Dict, db: Session) -> str:
        """הוספת הקשר על הזמנות מהמערכת"""
        try:
            if user_context.get("userType") == "Supplier":
                query = text("""
                    SELECT COUNT(*) as total, 
                           COUNT(CASE WHEN status = N'בתהליך' THEN 1 END) as pending,
                           COUNT(CASE WHEN status = N'הושלמה' THEN 1 END) as completed
                    FROM orders WHERE supplier_id = :user_id
                """)
            else:
                query = text("""
                    SELECT COUNT(*) as total,
                           COUNT(CASE WHEN status = N'בתהליך' THEN 1 END) as pending,
                           COUNT(CASE WHEN status = N'הושלמה' THEN 1 END) as completed  
                    FROM orders WHERE owner_id = :user_id
                """)
            
            result = db.execute(query, {"user_id": user_id}).fetchone()
            if result and result[0] > 0:
                return f"\n\nמידע עדכני על ההזמנות שלך: סך הכל {result[0]} הזמנות, {result[1]} ממתינות לטיפול, {result[2]} הושלמו."
        except Exception as e:
            logger.error(f"Error adding orders context: {e}")
        
        return ""

    def _add_products_context(self, user_id: int, user_context: Dict, db: Session) -> str:
        """הוספת הקשר על מוצרים מהמערכת"""
        try:
            if user_context.get("userType") == "Supplier":
                query = text("""
                    SELECT COUNT(*) as total,
                           COUNT(CASE WHEN stock = 0 THEN 1 END) as out_of_stock,
                           AVG(CAST(unit_price as FLOAT)) as avg_price
                    FROM products WHERE supplier_id = :user_id AND is_active = 1
                """)
                
                result = db.execute(query, {"user_id": user_id}).fetchone()
                if result and result[0] > 0:
                    avg_price = result[2] or 0
                    return f"\n\nמידע עדכני על המוצרים שלך: {result[0]} מוצרים פעילים, {result[1]} אזלו מהמלאי, מחיר ממוצע: {avg_price:.2f} ש\"ח."
        except Exception as e:
            logger.error(f"Error adding products context: {e}")
        
        return ""

    def _update_cache(self, key: str, value: Dict):
        """עדכון מטמון עם הגבלת גודל"""
        if len(self.response_cache) >= self.cache_max_size:
            # מסיר את הערך הישן ביותר
            oldest_key = next(iter(self.response_cache))
            del self.response_cache[oldest_key]
        
        self.response_cache[key] = value
        logger.debug(f"Added to cache, cache size: {len(self.response_cache)}")

    def clear_cache(self):
        """ניקוי מטמון ידני"""
        self.response_cache.clear()
        logger.info("Cache cleared manually")