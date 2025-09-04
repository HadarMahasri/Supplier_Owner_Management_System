# backend/routers/images_gateway_router.py
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from typing import Optional

# שירות התמונות (קיים אצלך)
try:
    from services.cloudinary_service import cloudinary_service
    HAS_CLOUDINARY = True
except Exception:
    cloudinary_service = None
    HAS_CLOUDINARY = False

router = APIRouter(prefix="/images", tags=["images-gateway"])

@router.post("/products/upload")
async def upload_product_image(
    supplier_id: int = Form(..., description="מזהה הספק"),
    product_id: Optional[int] = Form(None, description="מזהה המוצר (אופציונלי)"),
    file: UploadFile = File(..., description="קובץ התמונה")
):
    if not HAS_CLOUDINARY:
        raise HTTPException(status_code=503, detail="Cloudinary service not available")
    try:
        content = await file.read()
        await cloudinary_service.validate_image_file(content, file.filename)
        upload_result = await cloudinary_service.upload_product_image(
            file_content=content,
            filename=file.filename,
            supplier_id=supplier_id,
            product_id=product_id
        )
        return {"success": True, "message": "התמונה הועלתה בהצלחה", "image_data": upload_result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה בהעלאת תמונה: {e}")

@router.delete("/products/{public_id}")
async def delete_product_image(public_id: str):
    if not HAS_CLOUDINARY:
        raise HTTPException(status_code=503, detail="Cloudinary service not available")
    try:
        ok = await cloudinary_service.delete_product_image(public_id)
        if not ok:
            raise HTTPException(status_code=400, detail="לא ניתן למחוק את התמונה")
        return {"success": True, "message": "התמונה נמחקה בהצלחה"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה במחיקת תמונה: {e}")

@router.get("/products/{public_id}/optimized")
async def get_optimized_image_url(
    public_id: str,
    width: Optional[int] = Query(None, description="רוחב רצוי"),
    height: Optional[int] = Query(None, description="גובה רצוי"),
    quality: str = Query("auto:good", description="רמת איכות")
):
    if not HAS_CLOUDINARY:
        raise HTTPException(status_code=503, detail="Cloudinary service not available")
    try:
        url = await cloudinary_service.get_optimized_url(
            public_id=public_id, width=width, height=height, quality=quality
        )
        return {"success": True, "optimized_url": url,
                "transformations": {"width": width, "height": height, "quality": quality}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"שגיאה ביצירת URL מותאם: {e}")
