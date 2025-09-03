# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from contextlib import asynccontextmanager
import models
# חשוב: המודול שמרכז את ההתחברות למסד (engine + get_db)
from database.session import engine
# ראוטרים (users חובה; אחרים אופציונליים)
from routers.users_router import router as users_router
from routers.owner_links_router import router as owner_links_router
from routers.ai_router import router as ai_router

# ראוטרים נוספים
import traceback
try:
    from routers.products_router import router as products_router
    HAS_PRODUCTS = True
except Exception as e:
    HAS_PRODUCTS = False
    print("⚠️ Products router failed to load:", e)
    traceback.print_exc()
try:
    from routers.orders_router import router as orders_router
    HAS_ORDERS = True
except Exception:
    HAS_ORDERS = False
    print("⚠️ Orders router not found - continuing without it")

# Gateway router עם תמיכה ב-Cloudinary
try:
    from gateway.gateway_router import gateway_router
    HAS_GATEWAY = True
except Exception as e:
    HAS_GATEWAY = False
    print("⚠️ Gateway router failed to load:", e)

# בדיקת הגדרות Cloudinary
try:
    from services.cloudinary_service import cloudinary_service
    HAS_CLOUDINARY = True
    print("✅ Cloudinary service loaded successfully")
except Exception as e:
    HAS_CLOUDINARY = False
    print(f"⚠️ Cloudinary service failed to load: {e}")


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
        print("  • POST /api/v1/products/with-image - הוספת מוצר עם תמונה")
        print("  • PUT  /api/v1/products/{id}  - עדכון מוצר")
        print("  • PUT  /api/v1/products/{id}/image - עדכון תמונת מוצר")
        print("  • DELETE /api/v1/products/{id} - מחיקת מוצר")
    
    if HAS_ORDERS:
        print("  • GET  /api/v1/orders/supplier/{id} - הזמנות ספק")
        print("  • GET  /api/v1/orders/owner/{id}    - הזמנות בעל חנות")
        print("  • POST /api/v1/orders/        - יצירת הזמנה")
        print("  • PUT  /api/v1/orders/{id}/status - עדכון סטטוס הזמנה")
    
    if HAS_GATEWAY:
        print("  • GET  /api/v1/suppliers     - חיפוש ספקים")
        print("  • POST /api/v1/images/products/upload - העלאת תמונה")
        print("  • DELETE /api/v1/images/products/{id} - מחיקת תמונה")
        print("  • Gateway endpoints available")
    
    if HAS_CLOUDINARY:
        print("  ☁️ Cloudinary integration: ACTIVE")
    
    print("=" * 50)
    
    # בדיקת DB ראשונית
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ DB connected")
    except Exception as e:
        print(f"❌ DB connection failed: {e}")
    
    # בדיקת Cloudinary
    if HAS_CLOUDINARY:
        try:
            import cloudinary
            cloud_name = cloudinary.config().cloud_name
            if cloud_name:
                print(f"✅ Cloudinary configured: {cloud_name}")
            else:
                print("⚠️ Cloudinary not configured - check environment variables")
        except Exception as e:
            print(f"❌ Cloudinary configuration error: {e}")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Suppliers Management System with Cloudinary",
        description="מערכת ניהול ספקים וחנויות עם תמיכה בהעלאת תמונות",
        version="1.1.0",
        lifespan=lifespan
    )

    # CORS - נוסיף תמיכה בהעלאת קבצים
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # בפרודקשן - להגביל לדומיינים ספציפיים
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # בריאות מערכת - מעודכן עם בדיקת Cloudinary
    @app.get("/health")
    async def health():
        health_status = {
            "status": "healthy",
            "service": "suppliers-management-api",
            "version": "1.1.0",
            "features": {
                "products": HAS_PRODUCTS,
                "orders": HAS_ORDERS,
                "gateway": HAS_GATEWAY,
                "cloudinary": HAS_CLOUDINARY
            }
        }
        
        # בדיקת DB
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            health_status["database"] = "connected"
        except Exception as e:
            health_status["database"] = f"error: {e.__class__.__name__}"
            health_status["status"] = "degraded"
        
        # בדיקת Cloudinary
        if HAS_CLOUDINARY:
            try:
                import cloudinary
                cloud_name = cloudinary.config().cloud_name
                if cloud_name:
                    health_status["cloudinary_status"] = f"configured: {cloud_name}"
                else:
                    health_status["cloudinary_status"] = "not configured"
                    health_status["status"] = "degraded"
            except Exception as e:
                health_status["cloudinary_status"] = f"error: {str(e)}"
                health_status["status"] = "degraded"
        
        return health_status

    # דף בית מעודכן
    @app.get("/")
    async def root():
        return {
            "message": "מערכת ניהול ספקים פעילה", 
            "status": "OK", 
            "version": "1.1.0",
            "features": {
                "image_upload": HAS_CLOUDINARY,
                "gateway": HAS_GATEWAY,
                "products": HAS_PRODUCTS,
                "orders": HAS_ORDERS
            }
        }

    # חיבור ראוטרים
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(owner_links_router, prefix="/api/v1")
    
    if HAS_PRODUCTS:
        app.include_router(products_router, prefix="/api/v1")
    
    if HAS_ORDERS:
        app.include_router(orders_router, prefix="/api/v1")
    
    if HAS_GATEWAY:
        app.include_router(gateway_router, prefix="/api/v1")

    app.include_router(ai_router, prefix="/api/v1")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )