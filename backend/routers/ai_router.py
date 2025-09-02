# backend/routers/ai_router.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import httpx, json, os

from database.session import get_db
from schemas.ai import AIAskRequest, AIAnswer, AIContext
from services.ai_service import (
    answer_question, get_context, build_prompt,
    supplier_snapshot, owner_snapshot,
    ask_ollama_generate,
)

router = APIRouter(prefix="/ai", tags=["ai"])

OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL  = os.getenv("OLLAMA_MODEL", "gemma2:2b")

@router.post("/ask", response_model=AIAnswer)
def ai_ask(payload: AIAskRequest, db: Session = Depends(get_db)):
    # answer_question כבר דואג לבנות snapshot ולהריץ את המודל
    ans = answer_question(db, payload.question, payload.user_id)
    return AIAnswer(answer=ans)

@router.get("/context", response_model=AIContext)
def ai_context(user_id: int, db: Session = Depends(get_db)):
    ctx = get_context(db, user_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="User not found")
    return AIContext(**ctx)

# אופציונלי: מסלול סטרימינג מהיר (אם הפרונט שלך משתמש בו)
@router.get("/stream")
async def ai_stream(question: str, user_id: int, db: Session = Depends(get_db)):
    ctx = get_context(db, user_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="User not found")
    prompt = build_prompt(ctx["role"], ctx["username"], ctx["snapshot"], question)

    async def gen():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{OLLAMA}/api/generate",
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": True,
                    "options": {"num_predict": 96, "num_ctx": 1024, "temperature": 0.1, "top_p": 0.8, "repeat_penalty": 1.15}
                }
            ) as r:
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        chunk = obj.get("response", "")
                        if chunk:
                            yield chunk
                    except Exception:
                        continue
        yield "\n"

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")
