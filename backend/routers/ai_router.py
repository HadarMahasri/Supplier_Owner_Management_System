# backend/routers/ai_router.py - עם endpoints חכמים חדשים
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import httpx, json, os

from database.session import get_db
from schemas.ai import AIAskRequest, AIAnswer, AIContext

# ייבוא המערכת החכמה החדשה
from services.smart_ai_integration import (
    smart_answer_question as answer_question, 
    smart_get_context as get_context,
    get_enhanced_suggestions,
    get_business_dashboard,
    get_business_insights,
    performance_monitor
)

router = APIRouter(prefix="/ai", tags=["ai"])

OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b-instruct")

# ---- Endpoints בסיסיים משופרים ----

@router.post("/ask", response_model=AIAnswer)
def ai_ask(payload: AIAskRequest, db: Session = Depends(get_db)):
    """שאלה חכמה עם המערכת המתקדמת"""
    ans = answer_question(db, payload.question, payload.user_id)
    return AIAnswer(answer=ans)

@router.get("/context", response_model=AIContext)
def ai_context(user_id: int, db: Session = Depends(get_db)):
    """context עשיר עם המערכת החדשה"""
    ctx = get_context(db, user_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="User not found")
    return AIContext(**ctx)

# ---- Endpoints חכמים חדשים ----

@router.get("/smart-suggestions")
def get_smart_suggestions(user_id: int, db: Session = Depends(get_db)):
    """הצעות שאלות חכמות בהתבסס על מצב המשתמש"""
    try:
        suggestions = get_enhanced_suggestions(db, user_id)
        return {
            "user_id": user_id,
            "suggestions": suggestions,
            "count": len(suggestions),
            "generated_at": "now"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating suggestions: {str(e)}")

@router.get("/business-insights")
def get_business_insights_endpoint(user_id: int, db: Session = Depends(get_db)):
    """תובנות עסקיות חכמות"""
    try:
        # קודם נזהה את הrole של המשתמש
        from services.smart_ai_integration import SmartAIService
        service = SmartAIService(db)
        user = service._fetch_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        role = service._resolve_role(user)
        insights = get_business_insights(db, user_id, role)  # השתמש ברole האמיתי
        
        return {
            "user_id": user_id,
            "insights": insights,
            "generated_at": "now"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating insights: {str(e)}")

@router.get("/dashboard")
def get_smart_dashboard(user_id: int, db: Session = Depends(get_db)):
    """לוח בקרה חכם מלא"""
    try:
        dashboard = get_business_dashboard(db, user_id)
        return dashboard
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating dashboard: {str(e)}")

@router.get("/performance")
def get_ai_performance():
    """סטטיסטיקות ביצועי המערכת"""
    return {
        "performance": performance_monitor.get_stats(),
        "system_status": "operational",
        "model": MODEL,
        "version": "2.0-smart"
    }

# ---- Streaming משופר ----

@router.get("/stream")
async def ai_stream_enhanced(question: str, user_id: int, db: Session = Depends(get_db)):
    ctx = get_context(db, user_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="User not found")

    from services.smart_ai_integration import smart_get_context, smart_answer_question
    full_context = smart_get_context(db, user_id)
    snapshot = full_context.get("snapshot", "")

    prompt = f"""אתה Supi, עוזר AI חכם למערכת ניהול ספקים.
משתמש: {ctx['username']} ({ctx['role']})

מידע עדכני מהמערכת:
{snapshot[:1200]}

שאלה: {question}

ענה בעברית, חכם ומעשי עם המלצות קונקרטיות:"""

    async def generate_smart_stream():
        emitted = False
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST", f"{OLLAMA}/api/generate",
                    json={
                        "model": MODEL,
                        "prompt": prompt,
                        "stream": True,
                        "options": {
                            "num_predict": 256,
                            "num_ctx": 4096,
                            "temperature": 0.3,
                            "top_p": 0.85,
                            "repeat_penalty": 1.15
                        }
                    }
                ) as r:
                    async for line in r.aiter_lines():
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            chunk = obj.get("response", "")
                            if chunk:
                                emitted = True
                                yield chunk
                        except:
                            continue
        except Exception:
            # נופלים ל-plan B אם הזרם נכשל
            emitted = False

        if not emitted:
            # Fallback: תשובה לא-סטרימינג מהמוח החכם
            try:
                ans = smart_answer_question(db, question, user_id)
                yield (ans or "לא יודע")
            except Exception:
                yield "לא יודע"
        else:
            # רק אם באמת היה תוכן מהמודל, נוסיף הזמנה לשאול עוד
            yield "\n\n💡 יש עוד שאלות? בחר מההצעות החכמות בצד!"

    return StreamingResponse(generate_smart_stream(), media_type="text/plain; charset=utf-8")


# ---- Testing Endpoints ----

@router.get("/test/smart-system")
def test_smart_system(user_id: int = 1, db: Session = Depends(get_db)):
    """בדיקת תקינות המערכת החכמה"""
    try:
        from services.smart_ai_integration import test_smart_ai_responses
        
        results = test_smart_ai_responses(db, user_id)
        return {
            "system_status": "smart system operational",
            "test_results": results,
            "performance": performance_monitor.get_stats()
        }
    except Exception as e:
        return {
            "system_status": "error",
            "error": str(e)
        }

# ---- Migration Helper Endpoint ----

@router.post("/migrate-to-smart")
def migrate_to_smart_system(db: Session = Depends(get_db)):
    """endpoint לביצוע המעבר למערכת החכמה"""
    try:
        from services.smart_ai_integration import migrate_to_smart_ai
        
        result = migrate_to_smart_ai(db)
        return {
            "migration_status": "completed" if result.get("success") else "failed",
            "details": result,
            "next_steps": [
                "בדוק שהendpoints החדשים עובדים",
                "עדכן את הfrontend להשתמש בtabs החדשים", 
                "בדוק שההצעות החכמות מופיעות"
            ] if result.get("success") else ["תקן את הבעיות ונסה שוב"]
        }
    except Exception as e:
        return {
            "migration_status": "failed",
            "error": str(e)
        }