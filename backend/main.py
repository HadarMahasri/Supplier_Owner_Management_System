# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from contextlib import asynccontextmanager

# חשוב: המודול שמרכז את ההתחברות למסד (engine + get_db)
from database.session import engine

# ראוטרים (users חובה; אחרים אופציונליים)
from routers.users_router import router as users_router

# ראוטרים נוספים
try:
    from routers.products_router import router as products_router
    HAS_PRODUCTS = True
except Exception:
    HAS_PRODUCTS = False
    print("⚠️ Products router not found - continuing without it")

try:
    from routers.orders_router import router as orders_router
    HAS_ORDERS = True
except Exception:
    HAS_ORDERS = False
    print("⚠️ Orders router not found - continuing without it")

# אופציונלי: gateway router
try:
    from gateway.gateway_router import gateway_router
    HAS_GATEWAY = True
except Exception:
    HAS_GATEWAY = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 מפעיל שרת FastAPI...")
    print("📋 Endpoints זמינים:")
    print("  • GET  /         - דף בית")
    print("  • GET  /health   - בדיקת בריאות")
    print("  • POST /api/v1/users/register - הרשמה")
    print("  • POST /api/v1/users/login    - התחברות")
    
    if HAS_PRODUCTS:
        print("  • GET  /api/v1/products/supplier/{id} - מוצרי ספק")
        print("  • POST /api/v1/products/      - הוספת מוצר")
        print("  • PUT  /api/v1/products/{id}  - עדכון מוצר")
        print("  • DELETE /api/v1/products/{id} - מחיקת מוצר")
    
    if HAS_ORDERS:
        print("  • GET  /api/v1/orders/supplier/{id} - הזמנות ספק")
        print("  • GET  /api/v1/orders/owner/{id}    - הזמנות בעל חנות")
        print("  • POST /api/v1/orders/        - יצירת הזמנה")
        print("  • PUT  /api/v1/orders/{id}/status - עדכון סטטוס הזמנה")
    
    if HAS_GATEWAY:
        print("  • Gateway endpoints available")
    
    print("=" * 50)
    
    # בדיקת DB ראשונית
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ DB connected")
    except Exception as e:
        print(f"❌ DB connection failed: {e}")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Suppliers Management System",
        description="מערכת ניהול ספקים וחנויות",
        version="1.0.0",
        lifespan=lifespan  # שימוש ב-lifespan במקום on_event
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # בפרודקשן - להגביל לדומיינים ספציפיים
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # בריאות מערכת
    @app.get("/health")
    async def health():
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "healthy", "database": "connected", "service": "suppliers-management-api"}
        except Exception as e:
            return {"status": "degraded", "database": f"error: {e.__class__.__name__}"}

    # דף בית
    @app.get("/")
    async def root():
        return {"message": "מערכת ניהול ספקים פעילה", "status": "OK", "version": "1.0.0"}

    # חיבור ראוטרים
    app.include_router(users_router, prefix="/api/v1")
    
    if HAS_PRODUCTS:
        app.include_router(products_router, prefix="/api/v1")
    
    if HAS_ORDERS:
        app.include_router(orders_router, prefix="/api/v1")
    
    if HAS_GATEWAY:
        app.include_router(gateway_router, prefix="/api/v1")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    # הסרת reload=True כדי למנוע את האזהרה השנייה
    uvicorn.run(
        "main:app",  # שימוש ב-string במקום object כדי ל-reload יעבוד
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )