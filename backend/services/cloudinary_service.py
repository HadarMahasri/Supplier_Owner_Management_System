# backend/services/cloudinary_service.py
"""
שירות Cloudinary לניהול תמונות
מטמיע תבנית Gateway לגישה לשירותים חיצוניים
"""

import os
import cloudinary
import cloudinary.uploader
import cloudinary.utils
from typing import Dict, Optional, BinaryIO
from fastapi import HTTPException
import base64


class CloudinaryService:
    """שירות לניהול תמונות ב-Cloudinary"""
    
    def __init__(self):
        """אתחול הגדרות Cloudinary"""
        self._configure_cloudinary()
    
    def _configure_cloudinary(self):
        """הגדרת חיבור ל-Cloudinary מתוך משתני הסביבה"""
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")
        
        if not all([cloud_name, api_key, api_secret]):
            raise ValueError("חסרים משתני סביבה של Cloudinary. בדוק שהגדרת: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET")
        
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
    
    async def upload_product_image(
        self, 
        file_content: bytes, 
        filename: str,
        supplier_id: int,
        product_id: Optional[int] = None
    ) -> Dict[str, str]:
        """
        העלאת תמונת מוצר ל-Cloudinary
        
        Args:
            file_content: תוכן הקובץ כ-bytes
            filename: שם הקובץ המקורי
            supplier_id: מזהה הספק
            product_id: מזהה המוצר (אופציונלי)
        
        Returns:
            Dict עם פרטי התמונה שהועלתה
        """
        try:
            # יצירת public_id ייחודי
            public_id = self._generate_product_public_id(supplier_id, product_id, filename)
            
            # העלאה ל-Cloudinary
            result = cloudinary.uploader.upload(
                file_content,
                public_id=public_id,
                folder="products",  # תיקיה ב-Cloudinary
                resource_type="image",
                transformation=[
                    {"width": 800, "height": 600, "crop": "limit"},  # הגבלת גודל
                    {"quality": "auto:good"}  # אופטימיזציה אוטומטית
                ],
                format="jpg"  # המרה לפורמט אחיד
            )
            
            return {
                "public_id": result["public_id"],
                "url": result["secure_url"],
                "width": result["width"],
                "height": result["height"],
                "format": result["format"],
                "bytes": result["bytes"]
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"שגיאה בהעלאת תמונה ל-Cloudinary: {str(e)}"
            )
    
    async def delete_product_image(self, public_id: str) -> bool:
        """
        מחיקת תמונה מ-Cloudinary
        
        Args:
            public_id: המזהה הייחודי של התמונה
        
        Returns:
            True אם המחיקה הצליחה
        """
        try:
            result = cloudinary.uploader.destroy(public_id, resource_type="image")
            return result.get("result") == "ok"
        except Exception as e:
            print(f"שגיאה במחיקת תמונה מ-Cloudinary: {e}")
            return False
    
    async def get_optimized_url(
        self, 
        public_id: str, 
        width: Optional[int] = None, 
        height: Optional[int] = None,
        quality: str = "auto:good"
    ) -> str:
        """
        קבלת URL מותאם של תמונה עם טרנספורמציות
        
        Args:
            public_id: המזהה הייחודי של התמונה
            width: רוחב רצוי
            height: גובה רצוי
            quality: רמת איכות
        
        Returns:
            URL מותאם של התמונה
        """
        try:
            transformation = []
            
            if width or height:
                transform_dict = {"crop": "fill"}
                if width:
                    transform_dict["width"] = width
                if height:
                    transform_dict["height"] = height
                transformation.append(transform_dict)
            
            transformation.append({"quality": quality})
            
            return cloudinary.utils.cloudinary_url(
                public_id,
                secure=True,
                transformation=transformation
            )[0]
            
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"שגיאה ביצירת URL מותאם: {str(e)}"
            )
    
    def _generate_product_public_id(
        self, 
        supplier_id: int, 
        product_id: Optional[int], 
        filename: str
    ) -> str:
        """יצירת מזהה ייחודי לתמונת מוצר"""
        import time
        import hashlib
        
        # הסרת סיומת מהקובץ
        name_without_ext = os.path.splitext(filename)[0]
        
        # יצירת hash מהזמן הנוכחי לייחודיות
        timestamp_hash = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        
        if product_id:
            return f"supplier_{supplier_id}_product_{product_id}_{timestamp_hash}"
        else:
            return f"supplier_{supplier_id}_temp_{timestamp_hash}"
    
    async def validate_image_file(self, file_content: bytes, filename: str) -> bool:
        """
        בדיקת תקינות קובץ תמונה
        
        Args:
            file_content: תוכן הקובץ
            filename: שם הקובץ
        
        Returns:
            True אם הקובץ תקין
        """
        # בדיקת סיומת
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"סוג קובץ לא נתמך. סוגי קבצים מותרים: {', '.join(allowed_extensions)}"
            )
        
        # בדיקת גודל (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400, 
                detail="גודל הקובץ חורג מ-10MB"
            )
        
        # בדיקה בסיסית של header הקובץ
        if not self._is_valid_image_header(file_content):
            raise HTTPException(
                status_code=400, 
                detail="קובץ אינו תמונה תקינה"
            )
        
        return True
    
    def _is_valid_image_header(self, file_content: bytes) -> bool:
        """בדיקה בסיסית של header הקובץ"""
        if len(file_content) < 10:
            return False
        
        # JPEG
        if file_content.startswith(b'\xff\xd8\xff'):
            return True
        
        # PNG
        if file_content.startswith(b'\x89PNG\r\n\x1a\n'):
            return True
        
        # GIF
        if file_content.startswith((b'GIF87a', b'GIF89a')):
            return True
        
        # BMP
        if file_content.startswith(b'BM'):
            return True
        
        # WebP
        if file_content[8:12] == b'WEBP':
            return True
        
        return False


# יצירת instance גלובלי של השירות
cloudinary_service = CloudinaryService()