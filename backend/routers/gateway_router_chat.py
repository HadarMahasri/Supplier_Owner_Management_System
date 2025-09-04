# החלף בקובץ backend/routers/gateway_router_chat.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from database.session import get_db
from services.chat_service import ChatService
from typing import Optional, Dict, Any
import logging

# הגדרת לוגר
logger = logging.getLogger(__name__)

router = APIRouter()

# יצירת instance של ChatService
chat_service = ChatService()

# Updated Schemas
class ChatMessageRequest(BaseModel):
    user_id: int = Field(..., gt=0, description="מזהה המשתמש")
    message: str = Field(..., min_length=1, max_length=1000, description="הודעת המשתמש")
    user_context: Optional[Dict[str, Any]] = Field(default=None, description="נתוני המשתמש מהפרונט")

class ChatResponse(BaseModel):
    success: bool
    message: str
    response: Optional[str] = None
    user_type: Optional[str] = None
    contexts_found: Optional[int] = None
    dynamic_context_used: Optional[bool] = None  # חדש
    error_code: Optional[str] = None
    response_time: Optional[float] = None

class HealthCheckResponse(BaseModel):
    status: str
    services: dict
    timestamp: str

@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    chat_data: ChatMessageRequest,
    db: Session = Depends(get_db)
):
    """
    Gateway endpoint לשליחת הודעת צ'אט לבוט AI עם נתוני משתמש מלאים
    
    מקבל הודעה מהמשתמש ומחזיר תשובה מותאמת אישית
    בהתבסס על סוג המשתמש ונתוניו האמיתיים מבסיס הנתונים
    """
    try:
        logger.info(f"קבלת הודעת צ'אט מהמשתמש {chat_data.user_id}: {chat_data.message[:50]}...")
        
        # אם יש נתוני משתמש מהפרונט, נשתמש בהם
        user_context = chat_data.user_context or {}
        
        # אם אין נתוני משתמש, ננסה לקבל אותם מבסיס הנתונים
        if not user_context:
            try:
                from sqlalchemy import text
                user_query = text("""
                    SELECT id, username, company_name, contact_name, phone, userType,
                           city_id, street, house_number, opening_time, closing_time
                    FROM users WHERE id = :user_id
                """)
                
                user_result = db.execute(user_query, {"user_id": chat_data.user_id}).fetchone()
                
                if user_result:
                    user_context = {
                        "id": user_result.id,
                        "username": user_result.username,
                        "company_name": user_result.company_name,
                        "contact_name": user_result.contact_name,
                        "phone": user_result.phone,
                        "userType": user_result.userType,
                        "city_id": user_result.city_id,
                        "street": user_result.street,
                        "house_number": user_result.house_number,
                        "opening_time": str(user_result.opening_time) if user_result.opening_time else None,
                        "closing_time": str(user_result.closing_time) if user_result.closing_time else None
                    }
                    
                    # הוספת נתונים ספציפיים לסוג המשתמש
                    if user_result.userType == "Supplier":
                        # ספירת מוצרים והזמנות
                        stats = db.execute(text("""
                            SELECT 
                                (SELECT COUNT(*) FROM products WHERE supplier_id = :user_id AND is_active = 1) as products,
                                (SELECT COUNT(*) FROM orders WHERE supplier_id = :user_id AND status IN (N'בתהליך', N'בוצעה')) as active_orders,
                                (SELECT COUNT(*) FROM products WHERE supplier_id = :user_id AND stock = 0 AND is_active = 1) as out_of_stock
                        """), {"user_id": chat_data.user_id}).fetchone()
                        
                        if stats:
                            user_context.update({
                                "products_count": stats.products or 0,
                                "active_orders": stats.active_orders or 0,
                                "out_of_stock_products": stats.out_of_stock or 0
                            })
                    
                    elif user_result.userType == "StoreOwner":
                        # ספירת הזמנות וספקים
                        stats = db.execute(text("""
                            SELECT 
                                (SELECT COUNT(*) FROM orders WHERE owner_id = :user_id AND status IN (N'בתהליך', N'בוצעה')) as active_orders,
                                (SELECT COUNT(*) FROM owner_supplier_links WHERE owner_id = :user_id AND status = 'APPROVED') as connected_suppliers
                        """), {"user_id": chat_data.user_id}).fetchone()
                        
                        if stats:
                            user_context.update({
                                "active_orders": stats.active_orders or 0,
                                "connected_suppliers": stats.connected_suppliers or 0
                            })
                            
            except Exception as e:
                logger.warning(f"לא ניתן לקבל נתוני משתמש מבסיס הנתונים: {e}")
        
        # עיבוד ההודעה דרך שירות הצ'אט המשודרג
        result = await chat_service.process_chat_message_with_context(
            user_id=chat_data.user_id,
            message=chat_data.message,
            user_context=user_context,
            db=db
        )
        
        if result["success"]:
            logger.info(f"תשובה נוצרה בהצלחה למשתמש {chat_data.user_id}")
            return ChatResponse(
                success=True,
                message="תשובה נוצרה בהצלחה עם Dynamic RAG",  # עדכון הודעה
                response=result["response"],
                user_type=result.get("user_type"),
                contexts_found=result.get("contexts_found", 0),
                dynamic_context_used=result.get("dynamic_context_used", False),  # חדש
                response_time=result.get("response_time")
            )
        else:
            logger.warning(f"כשל בעיבוד הודעה למשתמש {chat_data.user_id}: {result['message']}")
            return ChatResponse(
                success=False,
                message=result["message"],
                response=result.get("response"),
                error_code="PROCESSING_FAILED"
            )
        
    except Exception as e:
        logger.error(f"שגיאה קריטית בעיבוד הודעת צ'אט: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"שגיאה בעיבוד הודעת הצ'אט: {str(e)}"
        )

@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    בדיקת תקינות שירותי הצ'אט AI
    
    מחזיר מידע על מצב השירותים: Qdrant, Ollama ושירותי הצ'אט
    """
    try:
        from datetime import datetime
        
        logger.info("בדיקת תקינות שירותי הצ'אט")
        health = chat_service.health_check()
        
        overall_status = "healthy" if all(health.values()) else "degraded"
        
        # הוספת מידע נוסף על הבדיקה
        health["chat_service_ready"] = True
        health["timestamp"] = datetime.now().isoformat()
        
        return HealthCheckResponse(
            status=overall_status,
            services=health,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"שגיאה בבדיקת תקינות: {str(e)}", exc_info=True)
        return HealthCheckResponse(
            status="error",
            services={"error": str(e)},
            timestamp=datetime.now().isoformat()
        )

@router.get("/status")
async def get_status():
    """מידע מהיר על מצב הצ'אט"""
    try:
        health = chat_service.health_check()
        return {
            "online": True,
            "qdrant_connected": health.get("qdrant_connected", False),
            "ollama_ready": health.get("ollama_ready", False)
        }
    except Exception as e:
        return {
            "online": False,
            "error": str(e)
        }

@router.get("/info")
async def get_chat_info():
    """מידע על יכולות הצ'אט"""
    return {
        "name": "AI Chat Assistant",
        "version": "2.0.0",
        "description": "עוזר דיגיטלי חכם ומותאם אישית למערכת ניהול הספקים",
        "supported_languages": ["Hebrew", "English"],
        "user_types": ["Supplier", "StoreOwner"],
        "features": [
            "מענה מותאם אישית לסוג המשתמש",
            "שימוש בנתונים אמיתיים מהמערכת", 
            "הסבר על תהליכים עסקיים",
            "עזרה בניהול מוצרים והזמנות",
            "הדרכה לביצוע פעולות במערכת",
            "תמיכה ביצירת קשרים עם ספקים/בעלי חנויות"
        ]
    }