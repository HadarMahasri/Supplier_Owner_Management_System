# backend/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from contextlib import asynccontextmanager

# חיבור לבסיס הנתונים
from database.session import engine

# ⬅️ שער אחוד שמאגד את כל הראוטרים (DB, AI, ותמונות) תחת /gateway/*
from gateway.gateway_router import gateway_router

# בדיקת שירותים חיצוניים
HAS_CLOUDINARY = False
HAS_CHAT_AI = False

# (אופציונלי) סטטוס אינטגרציית Cloudinary
try:
    from services.cloudinary_service import cloudinary_service  # noqa: F401
    HAS_CLOUDINARY = True
    print("✅ Cloudinary service loaded successfully")
except Exception as e:
    HAS_CLOUDINARY = False
    print(f"⚠️ Cloudinary service failed to load: {e}")

# בדיקת שירותי הצ'אט AI
try:
    from services.chat_service import ChatService
    # יצירת instance לבדיקה
    _chat_service = ChatService()
    HAS_CHAT_AI = True
    print("✅ Chat AI services loaded successfully")
except Exception as e:
    HAS_CHAT_AI = False
    print(f"⚠️ Chat AI services failed to load: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 FastAPI is starting…")
    
    # בדיקת חיבור למסד הנתונים
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connected")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

    # בדיקת Cloudinary
    if HAS_CLOUDINARY:
        try:
            import cloudinary
            cn = cloudinary.config().cloud_name
            print(f"☁️ Cloudinary configured: {cn or 'MISSING CONFIG'}")
        except Exception as e:
            print(f"❌ Cloudinary configuration error: {e}")

    # בדיקת שירותי הצ'אט AI
    if HAS_CHAT_AI:
        try:
            # בדיקת תקינות השירותים
            health = _chat_service.health_check()
            qdrant_status = "✅" if health.get("qdrant_connected") else "❌"
            ollama_status = "✅" if health.get("ollama_ready") else "❌"
            
            print(f"🤖 Chat AI Services:")
            print(f"   • Qdrant: {qdrant_status}")
            print(f"   • Ollama: {ollama_status}")
            
            if not all(health.values()):
                print("⚠️ חלק משירותי הצ'אט לא זמינים - בדוק Docker containers")
                
        except Exception as e:
            print(f"❌ Chat AI health check failed: {e}")

    yield
    # Shutdown
    print("🛑 Shutting down…")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Suppliers Management System with AI Chat",
        description="API עם Gateway אחיד לכל השירותים (DB, AI Chat, תמונות)",
        version="2.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],        # בפרודקשן – להגביל לדומיינים רלוונטיים
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # בריאות מערכת כללית
    @app.get("/health")
    async def health():
        status = {
            "status": "healthy", 
            "service": "suppliers-management-api", 
            "version": "2.1.0",
            "features": []
        }

        # Database
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            status["database"] = "connected"
            status["features"].append("database")
        except Exception as e:
            status["database"] = f"error: {e.__class__.__name__}"
            status["status"] = "degraded"

        # Cloudinary
        if HAS_CLOUDINARY:
            try:
                import cloudinary
                cn = cloudinary.config().cloud_name
                status["cloudinary"] = f"configured: {cn}" if cn else "not configured"
                status["features"].append("cloudinary")
            except Exception as e:
                status["cloudinary"] = f"error: {str(e)}"
                status["status"] = "degraded"
        else:
            status["cloudinary"] = "not available"

        # Chat AI
        if HAS_CHAT_AI:
            try:
                chat_health = _chat_service.health_check()
                status["chat_ai"] = {
                    "qdrant": "connected" if chat_health.get("qdrant_connected") else "disconnected",
                    "ollama": "ready" if chat_health.get("ollama_ready") else "not ready",
                    "overall": "healthy" if all(chat_health.values()) else "degraded"
                }
                status["features"].append("chat-ai")
                
                if status["chat_ai"]["overall"] == "degraded":
                    status["status"] = "degraded"
                    
            except Exception as e:
                status["chat_ai"] = f"error: {str(e)}"
                status["status"] = "degraded"
        else:
            status["chat_ai"] = "not available"

        return status

    @app.get("/")
    async def root():
        features = []
        if HAS_CLOUDINARY:
            features.append("Image Upload (Cloudinary)")
        if HAS_CHAT_AI:
            features.append("AI Chat Assistant")
        
        return {
            "message": "Supplier/Owner Management System with AI",
            "version": "2.1.0",
            "gateway_base": "/api/v1/gateway",
            "docs": "/docs",
            "features": features,
            "endpoints": {
                "health": "/health",
                "chat_ai": "/api/v1/gateway/chat/" if HAS_CHAT_AI else None,
                "images": "/api/v1/gateway/images/" if HAS_CLOUDINARY else None
            }
        }

    # ✅ נקודת חיבור יחידה – Gateway (כולל תחתיו users/orders/products/owner-links/ai/images/chat וכו')
    app.include_router(gateway_router, prefix="/api/v1")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    # הגדרת רמת לוגים
    log_level = "debug" if os.getenv("DEBUG", "False").lower() == "true" else "info"
    
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True, 
        log_level=log_level
    )