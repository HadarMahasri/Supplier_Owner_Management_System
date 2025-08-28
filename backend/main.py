# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text


# חשוב: המודול שמרכז את ההתחברות למסד (engine + get_db)
# ראו database/session.py כפי שהצעתי קודם (odbc_connect ל-SQL Server בענן)
from database.session import engine  # אם תרצה גם get_db לתלויות: from database.session import get_db

# ראוטרים (users חובה; אחרים אופציונליים)
from routers.users_router import router as users_router
from routers.products_router import router as products_router


# אופציונלי: אם יש לך router נוסף (gateway), ננסה לייבא, ואם לא — מתעלמים
try:
    from gateway.gateway_router import gateway_router
    HAS_GATEWAY = True
except Exception:
    HAS_GATEWAY = False

# --------- יצירת האפליקציה ---------
def create_app() -> FastAPI:
    app = FastAPI(
        title="Supplier Management System API",
        description="מערכת ניהול ספקים",
        version="1.0.0",
    )

    # CORS (בפיתוח אפשר *, בייצור להחליף לרשימת דומיינים)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # לוג עלייה/כיבוי
    @app.on_event("startup")
    async def _on_startup():
        print("🚀 Starting Supplier Management System...")
        # בדיקת DB ראשונית – תדפיס שגיאה אם יש
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ DB connected")
        except Exception as e:
            print(f"❌ DB connection failed: {e}")

    @app.on_event("shutdown")
    async def _on_shutdown():
        print("🛑 Shutting down...")

    # בריאות מערכת (בודק DB בפועל)
    @app.get("/health")
    async def health():
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            return {"status": "degraded", "database": f"error: {e.__class__.__name__}"}

    # דף בית קטן
    @app.get("/")
    async def root():
        return {"message": "Supplier Management System API", "version": "1.0.0", "status": "running"}

    # חיבור ראוטרים
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(products_router, prefix="/api/v1")

    if HAS_GATEWAY:
        app.include_router(gateway_router, prefix="/api/v1")


    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


