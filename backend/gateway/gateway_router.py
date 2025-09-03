# backend/gateway/gateway_router.py
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from sqlalchemy import text

from database.session import get_db

# טעינת שירות Cloudinary (אם קיים)
try:
    from services.cloudinary_service import cloudinary_service
    HAS_CLOUDINARY = True
except ImportError:
    HAS_CLOUDINARY = False
    cloudinary_service = None

# Initialize router
gateway_router = APIRouter()

# ============== CLOUDINARY IMAGE ENDPOINTS ==============

@gateway_router.post("/images/products/upload", tags=["Images"])
async def upload_product_image(
    supplier_id: int = Form(..., description="מזהה הספק"),
    product_id: Optional[int] = Form(None, description="מזהה המוצר (אופציונלי)"),
    file: UploadFile = File(..., description="קובץ התמונה")
):
    """העלאת תמונת מוצר ל-Cloudinary"""
    if not HAS_CLOUDINARY:
        raise HTTPException(status_code=503, detail="Cloudinary service not available")
        
    try:
        # קריאת תוכן הקובץ
        file_content = await file.read()
        
        # בדיקת תקינות הקובץ
        await cloudinary_service.validate_image_file(file_content, file.filename)
        
        # העלאה ל-Cloudinary
        upload_result = await cloudinary_service.upload_product_image(
            file_content=file_content,
            filename=file.filename,
            supplier_id=supplier_id,
            product_id=product_id
        )
        
        return {
            "success": True,
            "message": "התמונה הועלתה בהצלחה",
            "image_data": upload_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"שגיאה בהעלאת תמונה: {str(e)}"
        )

@gateway_router.delete("/images/products/{public_id}", tags=["Images"])
async def delete_product_image(public_id: str):
    """מחיקת תמונת מוצר מ-Cloudinary"""
    if not HAS_CLOUDINARY:
        raise HTTPException(status_code=503, detail="Cloudinary service not available")
        
    try:
        success = await cloudinary_service.delete_product_image(public_id)
        
        if success:
            return {
                "success": True,
                "message": "התמונה נמחקה בהצלחה"
            }
        else:
            raise HTTPException(
                status_code=400, 
                detail="לא ניתן למחוק את התמונה"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"שגיאה במחיקת תמונה: {str(e)}"
        )

@gateway_router.get("/images/products/{public_id}/optimized", tags=["Images"])
async def get_optimized_image_url(
    public_id: str,
    width: Optional[int] = Query(None, description="רוחב רצוי בפיקסלים"),
    height: Optional[int] = Query(None, description="גובה רצוי בפיקסלים"),
    quality: str = Query("auto:good", description="רמת איכות")
):
    """קבלת URL מותאם של תמונה עם טרנספורמציות"""
    if not HAS_CLOUDINARY:
        raise HTTPException(status_code=503, detail="Cloudinary service not available")
        
    try:
        optimized_url = await cloudinary_service.get_optimized_url(
            public_id=public_id,
            width=width,
            height=height,
            quality=quality
        )
        
        return {
            "success": True,
            "optimized_url": optimized_url,
            "transformations": {
                "width": width,
                "height": height,
                "quality": quality
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"שגיאה ביצירת URL מותאם: {str(e)}"
        )

# ============== PLACEHOLDER ENDPOINTS לעתיד ==============

@gateway_router.get("/suppliers", tags=["Suppliers"])
async def search_suppliers_placeholder():
    """Placeholder - יממש בעתיד"""
    return {"message": "Search suppliers - יממש בעתיד", "suppliers": []}

@gateway_router.get("/suppliers/{supplier_id}", tags=["Suppliers"])  
async def get_supplier_details_placeholder(supplier_id: str):
    """Placeholder - יממש בעתיד"""
    return {"message": f"Supplier {supplier_id} details - יממש בעתיד"}

@gateway_router.post("/suppliers", tags=["Suppliers"])
async def create_supplier_placeholder():
    """Placeholder - יממש בעתיד"""
    return {"message": "Create supplier - יממש בעתיד"}

@gateway_router.put("/suppliers/{supplier_id}", tags=["Suppliers"])
async def update_supplier_placeholder(supplier_id: str):
    """Placeholder - יממש בעתיד"""
    return {"message": f"Update supplier {supplier_id} - יממש בעתיד"}

@gateway_router.delete("/suppliers/{supplier_id}", tags=["Suppliers"])
async def delete_supplier_placeholder(supplier_id: str):
    """Placeholder - יממש בעתיד"""
    return {"message": f"Delete supplier {supplier_id} - יממש בעתיד"}

@gateway_router.get("/categories", tags=["Categories"])
async def get_categories_placeholder():
    """Placeholder - יממש בעתיד"""
    return {"message": "Categories - יממש בעתיד", "categories": []}

@gateway_router.get("/categories/{category_name}/suppliers", tags=["Categories"])
async def get_suppliers_by_category_placeholder(category_name: str):
    """Placeholder - יממש בעתיד"""
    return {"message": f"Suppliers in {category_name} - יממש בעתיד"}

@gateway_router.get("/analytics/suppliers-by-category", tags=["Analytics"])
async def get_suppliers_by_category_stats_placeholder():
    """Placeholder - יממש בעתיד"""
    return {"message": "Analytics - יממש בעתיד", "data": []}

@gateway_router.get("/analytics/top-rated-suppliers", tags=["Analytics"])
async def get_top_rated_suppliers_placeholder():
    """Placeholder - יממש בעתיד"""
    return {"message": "Top rated suppliers - יממש בעתיד", "data": []}

@gateway_router.get("/analytics/suppliers-by-location", tags=["Analytics"])
async def get_suppliers_by_location_placeholder():
    """Placeholder - יממש בעתיד"""
    return {"message": "Suppliers by location - יממש בעתיד", "data": []}

# ============== EXTERNAL SERVICES PLACEHOLDERS ==============

@gateway_router.get("/external/weather/{city}", tags=["External Services"])
async def get_weather_info_placeholder(city: str):
    """Placeholder - יממש בעתיד"""
    return {"message": f"Weather for {city} - יממש בעתיד"}

@gateway_router.get("/external/maps/geocode", tags=["External Services"])
async def geocode_address_placeholder(address: str = Query(..., description="Address to geocode")):
    """Placeholder - יממש בעתיד"""
    return {"message": f"Geocoding {address} - יממש בעתיד"}

# ============== AI CONSULTANT PLACEHOLDERS ==============

@gateway_router.post("/ai/consult", tags=["AI Consultant"])
async def consult_ai_placeholder():
    """Placeholder - יממש בעתיד"""
    return {"message": "AI consultation - יממש בעתיד"}

@gateway_router.get("/ai/recommendations/{supplier_id}", tags=["AI Consultant"])
async def get_supplier_recommendations_placeholder(supplier_id: str):
    """Placeholder - יממש בעתיד"""
    return {"message": f"AI recommendations for {supplier_id} - יממש בעתיד"}

# ============== HEALTH CHECK ==============

@gateway_router.get("/health", tags=["System"])
async def gateway_health_check(db: Session = Depends(get_db)):
    """בדיקת תקינות ה-Gateway ושירותי המערכת"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        
        # Test Cloudinary connection
        cloudinary_status = "healthy" if HAS_CLOUDINARY else "not_available"
        if HAS_CLOUDINARY:
            try:
                import cloudinary
                cloud_name = cloudinary.config().cloud_name
                if not cloud_name:
                    cloudinary_status = "configuration_missing"
            except Exception:
                cloudinary_status = "unhealthy"
        
        services_status = {
            "database": "healthy",
            "cloudinary": cloudinary_status,
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": services_status
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")