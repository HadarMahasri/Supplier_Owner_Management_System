# backend/gateway/gateway_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from config.database import get_db
from commands.supplier_commands import SupplierCommands
from queries.supplier_queries import SupplierQueries
from queries.analytics_queries import AnalyticsQueries

# Initialize router
gateway_router = APIRouter()

# Initialize CQRS handlers
supplier_commands = SupplierCommands()
supplier_queries = SupplierQueries()
analytics_queries = AnalyticsQueries()

# ============== SUPPLIER ENDPOINTS ==============

@gateway_router.get("/suppliers", tags=["Suppliers"])
async def search_suppliers(
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None, description="Filter by category"),
    city: Optional[str] = Query(None, description="Filter by city"),
    rating_min: Optional[float] = Query(None, description="Minimum rating"),
    search_term: Optional[str] = Query(None, description="Search in name/description"),
    limit: int = Query(20, description="Maximum results"),
    offset: int = Query(0, description="Results offset")
):
    """חיפוש ספקים עם פילטרים - Query Side"""
    try:
        suppliers = await supplier_queries.search_suppliers(
            db=db,
            category=category,
            city=city,
            rating_min=rating_min,
            search_term=search_term,
            limit=limit,
            offset=offset
        )
        return {
            "suppliers": suppliers,
            "total": len(suppliers),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@gateway_router.get("/suppliers/{supplier_id}", tags=["Suppliers"])
async def get_supplier_details(
    supplier_id: str,
    db: Session = Depends(get_db)
):
    """קבלת פרטי ספק מלאים - Query Side"""
    try:
        supplier = await supplier_queries.get_supplier_by_id(db, supplier_id)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")
        return supplier
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@gateway_router.post("/suppliers", tags=["Suppliers"])
async def create_supplier(
    supplier_data: dict,
    db: Session = Depends(get_db)
):
    """יצירת ספק חדש - Command Side"""
    try:
        result = await supplier_commands.create_supplier(db, supplier_data)
        return {"message": "Supplier created successfully", "supplier_id": result["id"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@gateway_router.put("/suppliers/{supplier_id}", tags=["Suppliers"])
async def update_supplier(
    supplier_id: str,
    supplier_data: dict,
    db: Session = Depends(get_db)
):
    """עדכון פרטי ספק - Command Side"""
    try:
        await supplier_commands.update_supplier(db, supplier_id, supplier_data)
        return {"message": "Supplier updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@gateway_router.delete("/suppliers/{supplier_id}", tags=["Suppliers"])
async def delete_supplier(
    supplier_id: str,
    db: Session = Depends(get_db)
):
    """מחיקת ספק - Command Side"""
    try:
        await supplier_commands.delete_supplier(db, supplier_id)
        return {"message": "Supplier deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============== CATEGORIES ENDPOINTS ==============

@gateway_router.get("/categories", tags=["Categories"])
async def get_categories(db: Session = Depends(get_db)):
    """קבלת רשימת קטגוריות"""
    try:
        categories = await supplier_queries.get_categories(db)
        return {"categories": categories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@gateway_router.get("/categories/{category_name}/suppliers", tags=["Categories"])
async def get_suppliers_by_category(
    category_name: str,
    db: Session = Depends(get_db),
    limit: int = Query(20)
):
    """קבלת ספקים לפי קטגוריה"""
    try:
        suppliers = await supplier_queries.get_suppliers_by_category(db, category_name, limit)
        return {"category": category_name, "suppliers": suppliers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============== ANALYTICS ENDPOINTS ==============

@gateway_router.get("/analytics/suppliers-by-category", tags=["Analytics"])
async def get_suppliers_by_category_stats(db: Session = Depends(get_db)):
    """סטטיסטיקת ספקים לפי קטגוריות - לגרף"""
    try:
        stats = await analytics_queries.get_suppliers_by_category_stats(db)
        return {"data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@gateway_router.get("/analytics/top-rated-suppliers", tags=["Analytics"])
async def get_top_rated_suppliers(
    db: Session = Depends(get_db),
    limit: int = Query(10)
):
    """ספקים עם הדירוג הגבוה ביותר"""
    try:
        suppliers = await analytics_queries.get_top_rated_suppliers(db, limit)
        return {"data": suppliers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@gateway_router.get("/analytics/suppliers-by-location", tags=["Analytics"])
async def get_suppliers_by_location(db: Session = Depends(get_db)):
    """התפלגות ספקים לפי מיקום גיאוגרפי"""
    try:
        location_stats = await analytics_queries.get_suppliers_by_location(db)
        return {"data": location_stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============== EXTERNAL SERVICES ==============

@gateway_router.get("/external/weather/{city}", tags=["External Services"])
async def get_weather_info(city: str):
    """מידע מזג אויר לעיר - דרך שירות חיצוני"""
    try:
        from services.external_apis import WeatherService
        weather_service = WeatherService()
        weather_data = await weather_service.get_weather(city)
        return weather_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weather service error: {str(e)}")

@gateway_router.get("/external/maps/geocode", tags=["External Services"])
async def geocode_address(address: str = Query(..., description="Address to geocode")):
    """המרת כתובת לקואורדינטות"""
    try:
        from services.external_apis import MapsService
        maps_service = MapsService()
        coordinates = await maps_service.geocode_address(address)
        return coordinates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geocoding error: {str(e)}")

# ============== AI CONSULTANT ==============

@gateway_router.post("/ai/consult", tags=["AI Consultant"])
async def consult_ai(
    question: dict,  # {"question": "איזה ספק קייטרינג מומלץ בתל אביב?", "context": {...}}
    db: Session = Depends(get_db)
):
    """שאלה ליועץ ה-AI"""
    try:
        from services.ai_service import AIConsultantService
        ai_service = AIConsultantService(db)
        
        response = await ai_service.get_consultation(
            question=question.get("question"),
            context=question.get("context", {})
        )
        
        return {
            "question": question.get("question"),
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

@gateway_router.get("/ai/recommendations/{supplier_id}", tags=["AI Consultant"])
async def get_supplier_recommendations(
    supplier_id: str,
    db: Session = Depends(get_db)
):
    """קבלת המלצות לספק ספציפי"""
    try:
        from services.ai_service import AIConsultantService
        ai_service = AIConsultantService(db)
        
        recommendations = await ai_service.get_supplier_recommendations(supplier_id)
        
        return {
            "supplier_id": supplier_id,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI recommendation error: {str(e)}")

# ============== HEALTH CHECK ==============

@gateway_router.get("/health", tags=["System"])
async def gateway_health_check(db: Session = Depends(get_db)):
    """בדיקת תקינות ה-Gateway ושירותי המערכת"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        
        # Test external services
        services_status = {
            "database": "healthy",
            "ai_service": "checking...",
            "external_apis": "checking..."
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": services_status
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")