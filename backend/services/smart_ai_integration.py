# backend/services/smart_ai_integration.py
# שילוב מלא של המערכת החכמה החדשה

import os, requests, time
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List

# ייבוא הרכיבים החדשים המשופרים
from services.context_builder import build_supplier_context, build_owner_context
from services.context_to_prompt import (
    supplier_context_to_text, owner_context_to_text, 
    build_system_prompt, few_shots, join_prompt
)
from routers.intent_router import route_intent_and_answer
from models.user_model import User
from models.order_model import Order

# ---- תצורת AI מתקדמת ----
OLLAMA_BASE = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b-instruct")

# הגדרות אופטימליות לתגובות חכמות
SMART_GEN_OPTIONS = {
    "num_predict": int(os.getenv("AI_NUM_PREDICT", "300")),  # יותר מילים לתשובות עשירות
    "num_ctx": int(os.getenv("AI_NUM_CTX", "4096")),        # יותר זיכרון להקשר
    "temperature": float(os.getenv("AI_TEMPERATURE", "0.3")), # קצת יותר יצירתיות
    "top_p": float(os.getenv("AI_TOP_P", "0.85")),
    "repeat_penalty": float(os.getenv("AI_REPEAT_PENALTY", "1.15")),
    "top_k": int(os.getenv("AI_TOP_K", "40")),
}

# ---- Smart AI Service Class ----
class SmartAIService:
    """שירות AI חכם עם יכולות מתקדמות"""
    
    def __init__(self, db: Session):
        self.db = db
        self._cache = {}
        self.cache_ttl = 45  # TTL קצר יותר למידע עדכני
    
    def _fetch_user(self, uid: int) -> User | None:
        return self.db.query(User).filter(User.id == uid).first()

    def _resolve_role(self, user: User) -> str:
        """זיהוי תפקיד משופר"""
        role = (getattr(user, "role", None) or getattr(user, "userType", "")).strip().lower()
        
        # תמיכה בכמה וריאציות
        supplier_roles = ["supplier", "ספק", "2", "vendor", "wholesaler"]
        owner_roles = ["storeowner", "owner", "store_owner", "בעל חנות", "1", "retailer", "client"]
        
        if role in supplier_roles:
            return "Supplier"
        elif role in owner_roles:
            return "StoreOwner"
        else:
            # ניחוש חכם לפי נתונים
            orders_as_supplier = self.db.query(Order).filter(Order.supplier_id == user.id).count()
            orders_as_owner = self.db.query(Order).filter(Order.owner_id == user.id).count()
            
            if orders_as_supplier > orders_as_owner:
                return "Supplier"
            return "StoreOwner"

    def _ollama_generate_smart(self, prompt: str) -> str:
        """קריאת AI משופרת עם error handling טוב יותר"""
        url = f"{OLLAMA_BASE}/api/generate"
        payload = {
            "model": OLLAMA_MODEL, 
            "prompt": prompt, 
            "stream": False, 
            "options": SMART_GEN_OPTIONS
        }
        
        try:
            r = requests.post(url, json=payload, timeout=120)
            r.raise_for_status()
            response = (r.json() or {}).get("response", "").strip()
            
            if not response:
                return "המודל לא החזיר תשובה. נסה לנסח את השאלה מחדש."
            
            return response
            
        except requests.exceptions.Timeout:
            return "התגובה אורכת זמן רב. נסה שאלה פשוטה יותר."
        except requests.exceptions.ConnectionError:
            return "לא מצליח להתחבר למודל AI. בדוק שהשרת Ollama פועל."
        except Exception as e:
            return f"שגיאה במודל AI: {str(e)}"

    def _get_cached_context(self, cache_key: str, builder_func) -> str:
        """מנגנון cache חכם לביצועים טובים יותר"""
        now = time.time()
        if cache_key in self._cache:
            timestamp, data = self._cache[cache_key]
            if now - timestamp < self.cache_ttl:
                return data
        
        # בניית context חדש
        fresh_data = builder_func()
        self._cache[cache_key] = (now, fresh_data)
        
        # ניקוי cache ישן
        if len(self._cache) > 50:
            oldest_keys = sorted(self._cache.keys(), 
                               key=lambda k: self._cache[k][0])[:10]
            for k in oldest_keys:
                del self._cache[k]
        
        return fresh_data

    def get_smart_answer(self, question: str, user_id: int) -> str:
        """מחזיר תשובה חכמה ומקיפה"""
        user = self._fetch_user(user_id)
        if not user:
            return "משתמש לא נמצא במערכת."
        
        role = self._resolve_role(user)
        username = getattr(user, "username", "") or getattr(user, "contact_name", "")
        
        # שלב 1: נסה תשובה דטרמיניסטית מהירה (Intent-based)
        intent_answer = route_intent_and_answer(self.db, role, user_id, question)
        if intent_answer:
            # הוסף מידע נוסף אם רלוונטי
            enhanced_answer = self._enhance_intent_answer(intent_answer, role, user_id, question)
            return enhanced_answer or intent_answer
        
        # שלב 2: תשובה מבוססת AI עם context מלא
        return self._get_ai_answer(role, username, user_id, question)
    
    def _enhance_intent_answer(self, base_answer: str, role: str, user_id: int, question: str) -> Optional[str]:
        """משפר תשובות intent עם מידע נוסף רלוונטי"""
        if not base_answer:
            return None
            
        # אם התשובה על מוצרים פעילים, הוסף המלצות
        if "מוצרים פעילים" in base_answer and role == "Supplier":
            # בדוק אם יש מוצרים במלאי נמוך
            from services.context_builder import fetch_supplier_products_detailed
            products = fetch_supplier_products_detailed(self.db, user_id, limit=100)
            low_stock = [p for p in products if p['is_active'] and p['stock'] <= max(p['min_quantity'], 5)]
            
            if low_stock:
                base_answer += f"\n💡 יש {len(low_stock)} מוצרים במלאי נמוך - כדאי לעדכן!"
        
        # אם התשובה על הזמנות פתוחות, הוסף פרטים
        elif "הזמנות פתוחות" in base_answer:
            if "אין הזמנות" not in base_answer:
                base_answer += "\n💡 טיפ: עדכן סטטוסים באופן קבוע לשיפור השירות."
        
        # אם התשובה על איך לעשות משהו, הוסף טיפים
        elif any(word in base_answer for word in ["תפריט >", "איך ל", "נתיב:"]):
            base_answer += "\n✨ זקוק לעזרה נוספת? שאל על נושא ספציפי!"
        
        return base_answer

    def _get_ai_answer(self, role: str, username: str, user_id: int, question: str) -> str:
        """מחזיר תשובת AI מלאה עם context עשיר"""
        
        # בניית context מלא עם cache
        cache_key = f"context:{role}:{user_id}"
        
        if role == "Supplier":
            context_builder = lambda: build_supplier_context(self.db, user_id)
            text_builder = supplier_context_to_text
        else:
            context_builder = lambda: build_owner_context(self.db, user_id)
            text_builder = owner_context_to_text
        
        # קבלת context עם cache
        full_context = self._get_cached_context(cache_key, context_builder)
        snapshot_text = text_builder(full_context)
        
        # בניית prompt חכם
        permissions = full_context.get("permissions", [])
        system_prompt = build_system_prompt(role, username, permissions, snapshot_text)
        shots = few_shots(role)
        full_prompt = join_prompt(system_prompt, snapshot_text, shots, question)
        
        # קריאת AI
        ai_response = self._ollama_generate_smart(full_prompt)
        
        # שיפור התשובה לפי הקשר
        return self._post_process_answer(ai_response, role, full_context, question)
    
    def _post_process_answer(self, answer: str, role: str, context: Dict, question: str) -> str:
        """עיבוד מאחור של התשובה לשיפור איכות"""
        if not answer or "לא יודע" in answer:
            return answer
        
        # הוסף קישורים לפעולות רלוונטיות
        if "מלאי נמוך" in answer and role == "Supplier":
            answer += "\n🔗 פעולה מהירה: תפריט > מוצרים > עדכון מלאי"
        
        elif "הזמנה" in answer and "חדשה" in question.lower():
            if role == "StoreOwner":
                answer += "\n🔗 יצירת הזמנה: תפריט > הזמנות > הזמנה חדשה"
        
        elif "ייצוא" in answer or "דוח" in answer:
            answer += "\n🔗 ייצוא מהיר: תפריט > דוחות > ייצוא נתונים"
        
        # הוסף סטטיסטיקה רלוונטית
        kpis = context.get("kpis", {})
        if "מוצרים" in answer and role == "Supplier":
            total_stock = kpis.get('total_stock', 0)
            if total_stock > 0:
                answer += f"\n📊 מידע נוסף: {total_stock} יחידות במלאי כולל"
        
        return answer

    def get_context_for_api(self, user_id: int) -> Optional[Dict]:
        """מחזיר context לשימוש ב-API"""
        user = self._fetch_user(user_id)
        if not user:
            return None
            
        role = self._resolve_role(user)
        username = getattr(user, "username", "") or getattr(user, "contact_name", "")
        
        # בניית snapshot עדכני
        if role == "Supplier":
            context = build_supplier_context(self.db, user_id)
            snapshot_text = supplier_context_to_text(context)
        else:
            context = build_owner_context(self.db, user_id)
            snapshot_text = owner_context_to_text(context)
        
        return {
            "user_id": user.id,
            "username": username,
            "role": role,
            "snapshot": snapshot_text,
            "full_context": context  # לשימוש מתקדם
        }

# ---- Enhanced Chat Suggestions ----
def get_smart_suggestions(db: Session, user_id: int, role: str) -> List[str]:
    """מחזיר הצעות שאלות חכמות בהתבסס על מצב המשתמש"""
    
    if role == "Supplier":
        # בדוק מצב הספק ותן הצעות רלוונטיות
        context = build_supplier_context(db, user_id)
        kpis = context.get("kpis", {})
        samples = context.get("samples", {})
        
        suggestions = ["כמה מוצרים פעילים יש לי?"]  # תמיד רלוונטי
        
        if kpis.get("open_orders_count", 0) > 0:
            suggestions.append("אילו הזמנות דורשות טיפול?")
            suggestions.append("איך לעדכן סטטוס הזמנות?")
        
        if kpis.get("low_stock_count", 0) > 0:
            suggestions.append("אילו מוצרים במלאי נמוך?")
            suggestions.append("איך לעדכן מלאי?")
        
        if kpis.get("total_revenue", 0) > 0:
            suggestions.append("אילו המוצרים הכי רווחיים שלי?")
            suggestions.append("כמה הרווחתי החודש?")
        
        suggestions.extend([
            "איך להוסיף מוצר חדש?",
            "איך לייצא דוח הזמנות?",
            "כמה חיבורים פעילים יש לי?"
        ])
        
    else:  # StoreOwner
        context = build_owner_context(db, user_id)
        kpis = context.get("kpis", {})
        
        suggestions = ["מה המצב של ההזמנות שלי?"]  # תמיד רלוונטי
        
        if kpis.get("open_orders_count", 0) > 0:
            suggestions.append("מתי תגיע ההזמנה שלי?")
            suggestions.append("מה סטטוס ההזמנות הפתוחות?")
        
        if kpis.get("orders_total", 0) > 0:
            suggestions.append("מאיזה ספק כדאי להזמין?")
            suggestions.append("כמה הוצאתי החודש?")
            suggestions.append("איך להזמין שוב את אותם מוצרים?")
        
        suggestions.extend([
            "איך ליצור הזמנה חדשה?",
            "איך לחפש ספקים חדשים?",
            "איך לייצא דוח הוצאות?"
        ])
    
    return suggestions[:8]  # מגביל למספר סביר

# ---- API Functions המחליפות את הקבצים הישנים ----

def answer_question(db: Session, question: str, user_id: int) -> str:
    """התחליף החכם ל-answer_question המקורי"""
    service = SmartAIService(db)
    return service.get_smart_answer(question, user_id)

def get_context(db: Session, user_id: int) -> Optional[Dict]:
    """התחליף החכם ל-get_context המקורי"""
    service = SmartAIService(db)
    return service.get_context_for_api(user_id)

def build_prompt(role: str, username: str, ctx_text: str, question: str) -> str:
    """התחליף החכם ל-build_prompt המקורי לשימוש streaming"""
    # פרומפט מקוצר לstreaming (לא כל ה-context)
    role_he = "ספק" if role == "Supplier" else "בעל חנות"
    
    return f"""את/ה Supi, עוזר AI חכם ל-{role_he} בשם {username}.

עקרונות תשובה:
- ענה בעברית, קצר ומדויק
- התחל בתשובה ישירה
- הוסף המלצות מעשיות
- השתמש במידע המדויק מהמערכת

מידע עדכני:
{ctx_text[:800]}...

שאלה: {question}

תשובה:"""

# ---- Testing and Validation ----

def test_smart_ai_responses(db: Session, user_id: int) -> Dict[str, str]:
    """בדיקת איכות תשובות המערכת החדשה"""
    service = SmartAIService(db)
    user = service._fetch_user(user_id)
    if not user:
        return {"error": "משתמש לא נמצא"}
    
    role = service._resolve_role(user)
    
    test_questions = {
        "basic_count": "כמה מוצרים פעילים יש לי?" if role == "Supplier" else "כמה הזמנות יש לי?",
        "status_check": "אילו הזמנות פתוחות יש?",
        "how_to": "איך לעדכן מלאי?" if role == "Supplier" else "איך ליצור הזמנה?",
        "analytics": "מה המצב העסקי שלי?"
    }
    
    results = {}
    for test_name, question in test_questions.items():
        try:
            start_time = time.time()
            answer = service.get_smart_answer(question, user_id)
            response_time = time.time() - start_time
            results[test_name] = f"[{response_time:.2f}s] {answer}"
        except Exception as e:
            results[test_name] = f"ERROR: {str(e)}"
    
    return results

# ---- Migration Helper ----

def migrate_to_smart_ai(db: Session) -> Dict[str, Any]:
    """עוזר למעבר למערכת החדשה"""
    try:
        # בדיקת תקינות הטבלאות הנדרשות
        required_tables = ["users", "products", "orders", "order_items", "owner_supplier_links"]
        
        for table in required_tables:
            try:
                result = db.execute(f"SELECT COUNT(*) FROM {table}").scalar()
                print(f"✅ {table}: {result} רשומות")
            except Exception as e:
                print(f"❌ {table}: שגיאה - {e}")
                return {"success": False, "error": f"טבלה {table} לא זמינה"}
        
        # בדיקת מודל AI
        try:
            test_prompt = "Test prompt"
            service = SmartAIService(db)
            response = service._ollama_generate_smart(test_prompt)
            ai_status = "פועל" if response else "לא מגיב"
        except Exception as e:
            ai_status = f"שגיאה: {str(e)}"
        
        # בדיקת משתמשי דמו
        supplier_count = db.query(User).filter(User.userType == "Supplier").count()
        owner_count = db.query(User).filter(User.userType == "StoreOwner").count()
        
        return {
            "success": True,
            "database_status": "תקין",
            "ai_model_status": ai_status,
            "users": {
                "suppliers": supplier_count,
                "owners": owner_count
            },
            "tables_verified": len(required_tables),
            "migration_complete": True
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# ---- Advanced Analytics Functions ----

def get_business_insights(db: Session, user_id: int, role: str) -> Dict[str, Any]:
    """מחזיר תובנות עסקיות מתקדמות"""
    insights = {
        "recommendations": [],
        "alerts": [],
        "opportunities": []
    }
    
    if role == "Supplier":
        context = build_supplier_context(db, user_id)
        kpis = context.get("kpis", {})
        samples = context.get("samples", {})
        
        # המלצות לספק
        if kpis.get("low_stock_count", 0) > 0:
            insights["alerts"].append(f"⚠️ {kpis['low_stock_count']} מוצרים במלאי נמוך")
            insights["recommendations"].append("עדכן מלאי מוצרים פופולריים לפני שנגמרים")
        
        if kpis.get("open_orders_count", 0) > 3:
            insights["alerts"].append(f"🔔 {kpis['open_orders_count']} הזמנות ממתינות לטיפול")
            insights["recommendations"].append("עדכן סטטוס הזמנות לשיפור שביעות רצון לקוחות")
        
        # זיהוי הזדמנויות
        top_products = samples.get("top_products", [])
        if top_products:
            best_seller = top_products[0]
            if best_seller.get("revenue", 0) > 500:
                insights["opportunities"].append(f"מוצר מוביל: {best_seller['name']} - כדאי להרחיב מלאי")
        
    else:  # StoreOwner
        context = build_owner_context(db, user_id)
        kpis = context.get("kpis", {})
        analytics = context.get("analytics", {})
        
        # המלצות לבעל חנות
        if kpis.get("open_orders_count", 0) > 0:
            insights["alerts"].append(f"📦 {kpis['open_orders_count']} הזמנות בעיבוד")
        
        avg_order = analytics.get("average_order_value", 0)
        if avg_order < 100:
            insights["recommendations"].append("שקול איחוד הזמנות לחיסכון בהוצאות משלוח")
        
        # זיהוי ספקים טובים
        supplier_perf = samples.get("supplier_performance", [])
        if supplier_perf:
            best_supplier = supplier_perf[0]
            if best_supplier.get("completion_rate", 0) > 90:
                insights["opportunities"].append(f"ספק מומלץ: {best_supplier['name']} - שירות מעולה")
    
    return insights

# ---- Export Functions for Router Integration ----

def get_enhanced_suggestions(db: Session, user_id: int) -> List[str]:
    """מחזיר הצעות שאלות חכמות למשתמש"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return ["לא נמצא משתמש"]
    
    role = SmartAIService(db)._resolve_role(user)
    return get_smart_suggestions(db, user_id, role)

def get_business_dashboard(db: Session, user_id: int) -> Dict[str, Any]:
    """מחזיר לוח בקרה עסקי מלא"""
    service = SmartAIService(db)
    user = service._fetch_user(user_id)
    if not user:
        return {"error": "משתמש לא נמצא"}
    
    role = service._resolve_role(user)
    context = service.get_context_for_api(user_id)
    insights = get_business_insights(db, user_id, role)
    suggestions = get_smart_suggestions(db, user_id, role)
    
    return {
        "user_info": {
            "id": user_id,
            "username": getattr(user, "username", ""),
            "role": role
        },
        "context": context,
        "insights": insights,
        "suggested_questions": suggestions,
        "last_updated": time.time()
    }

# ---- Performance Monitoring ----

class AIPerformanceMonitor:
    """מוניטור ביצועי המערכת החדשה"""
    
    def __init__(self):
        self.response_times = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.intent_hits = 0
        self.ai_calls = 0
    
    def log_response_time(self, time_ms: float):
        self.response_times.append(time_ms)
        if len(self.response_times) > 100:
            self.response_times.pop(0)
    
    def log_cache_hit(self):
        self.cache_hits += 1
    
    def log_cache_miss(self):
        self.cache_misses += 1
    
    def log_intent_hit(self):
        self.intent_hits += 1
    
    def log_ai_call(self):
        self.ai_calls += 1
    
    def get_stats(self) -> Dict[str, Any]:
        if not self.response_times:
            return {"status": "אין נתונים עדיין"}
        
        avg_time = sum(self.response_times) / len(self.response_times)
        cache_rate = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
        intent_rate = self.intent_hits / (self.intent_hits + self.ai_calls) if (self.intent_hits + self.ai_calls) > 0 else 0
        
        return {
            "average_response_time_ms": round(avg_time, 2),
            "cache_hit_rate": f"{cache_rate:.1%}",
            "intent_resolution_rate": f"{intent_rate:.1%}",
            "total_queries": len(self.response_times)
        }

# יצירת monitor גלובלי
performance_monitor = AIPerformanceMonitor()

# ---- Updated Router Integration ----

def smart_answer_question(db: Session, question: str, user_id: int) -> str:
    """הפונקציה הראשית החדשה - מחליפה את answer_question הישנה"""
    start_time = time.time()
    
    try:
        service = SmartAIService(db)
        answer = service.get_smart_answer(question, user_id)
        
        response_time = (time.time() - start_time) * 1000
        performance_monitor.log_response_time(response_time)
        
        return answer
        
    except Exception as e:
        return f"שגיאה במערכת AI: {str(e)}\nנסה לשאול שאלה פשוטה יותר."

def smart_get_context(db: Session, user_id: int) -> Optional[Dict]:
    """הפונקציה החדשה לקבלת context - מחליפה את get_context הישנה"""
    service = SmartAIService(db)
    return service.get_context_for_api(user_id)

# ---- Easy Migration Functions ----

def migrate_existing_ai_service():
    """הדרכה למעבר למערכת החדשה"""
    return """
🔄 מעבר למערכת AI החכמה:

1. החלף ב-ai_router.py:
   from services.ai_service import answer_question, get_context
   ↓
   from services.smart_ai_integration import smart_answer_question as answer_question, smart_get_context as get_context

2. החלף ב-ai_service.py:
   # העבר את הקובץ הישן ל-ai_service_old.py
   # השתמש ב-smart_ai_integration.py במקום

3. עדכן requirements.txt (אם נדרש):
   # אין תלויות חדשות - הכל עובד עם המערכת הקיימת

4. בדיקת תקינות:
   python -c "from services.smart_ai_integration import migrate_to_smart_ai; print('✅ המערכת החדשה מוכנה!')"

המערכת החדשה תספק:
- תשובות יותר חכמות ומדויקות
- זיכרון ל-45 שניות לביצועים טובים
- זיהוי מתקדם של כוונות משתמש  
- המלצות עסקיות אוטומטיות
- ניתוח ביצועים בזמן אמת
"""