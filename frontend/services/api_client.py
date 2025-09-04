# frontend/services/api_client.py
from typing import List, Optional, Dict, Any
import os, requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

def _url(p: str) -> str:
    return f"{API_BASE_URL}{p}"

def _err(resp: requests.Response) -> str:
    try:
        j = resp.json()
        if isinstance(j, dict) and "detail" in j:
            return str(j["detail"])
        return str(j)
    except Exception:
        return resp.text or f"HTTP {resp.status_code}"

# ---- Products API ----
def get_products(supplier_id: int) -> List[Dict[str, Any]]:
    r = requests.get(
        _url("/api/v1/gateway/products/"),
        params={"supplier_id": supplier_id},
        timeout=10,
    )
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

def create_product(payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(_url("/api/v1/gateway/products"), json=payload, timeout=15)
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

def create_product_with_image(
    supplier_id: int, 
    name: str, 
    price: float, 
    min_qty: int,
    image_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    יצירת מוצר חדש עם תמונה
    """
    data = {
        "supplier_id": supplier_id,
        "name": name,
        "price": price,
        "min_qty": min_qty
    }
    
    files = {}
    if image_path and os.path.exists(image_path):
        try:
            files["image"] = open(image_path, "rb")
        except Exception as e:
            raise RuntimeError(f"שגיאה בקריאת קובץ התמונה: {e}")
    
    try:
        r = requests.post(
            _url("/api/v1/gateway/products/with-image"),
            data=data,
            files=files,
            timeout=30
        )
        if r.status_code >= 400:
            raise RuntimeError(_err(r))
        return r.json()
        
    finally:
        # סגירת הקובץ
        if "image" in files:
            files["image"].close()

def update_product(product_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.put(_url(f"/api/v1/gateway/products/{product_id}"), json=payload, timeout=15)
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

def update_product_image(product_id: int, image_path: str) -> Dict[str, Any]:
    """
    עדכון תמונת מוצר קיים
    """
    if not os.path.exists(image_path):
        raise RuntimeError("קובץ התמונה לא נמצא")
    
    try:
        with open(image_path, "rb") as image_file:
            files = {"image": image_file}
            r = requests.put(
                _url(f"/api/v1/gateway/products/{product_id}/image"),
                files=files,
                timeout=30
            )
            if r.status_code >= 400:
                raise RuntimeError(_err(r))
            return r.json()
            
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"שגיאה בעדכון תמונת מוצר: {str(e)}")

def delete_product_image(product_id: int) -> Dict[str, Any]:
    """מחיקת תמונת מוצר"""
    r = requests.delete(_url(f"/api/v1/gateway/products/{product_id}/image"), timeout=10)
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

def update_stock(product_id: int, stock: int) -> Dict[str, Any]:
    r = requests.put(_url(f"/api/v1/gateway/products/{product_id}/stock"), json={"stock": stock}, timeout=10)
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

def delete_product(product_id: int) -> None:
    r = requests.delete(_url(f"/api/v1/gateway/products/{product_id}"), timeout=10)
    if r.status_code >= 400:
        raise RuntimeError(_err(r))

# ---- Cloudinary API (דרך Gateway) ----
def upload_image_to_cloudinary(
    supplier_id: int, 
    image_path: str, 
    product_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    העלאת תמונה ל-Cloudinary דרך ה-Gateway
    """
    if not os.path.exists(image_path):
        raise RuntimeError("קובץ התמונה לא נמצא")
    
    data = {"supplier_id": supplier_id}
    if product_id:
        data["product_id"] = product_id
    
    try:
        with open(image_path, "rb") as image_file:
            files = {"file": image_file}
            r = requests.post(
                _url("/api/v1/gateway/images/products/upload"), 
                data=data, 
                files=files, 
                timeout=30
            )
            if r.status_code >= 400:
                raise RuntimeError(_err(r))
            return r.json()
            
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"שגיאה בהעלאת תמונה ל-Cloudinary: {str(e)}")

def delete_image_from_cloudinary(public_id: str) -> Dict[str, Any]:
    """מחיקת תמונה מ-Cloudinary דרך ה-Gateway"""
    r = requests.delete(_url(f"/api/v1/images/products/{public_id}"), timeout=10)
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

def get_optimized_image_url(
    public_id: str, 
    width: Optional[int] = None, 
    height: Optional[int] = None,
    quality: str = "auto:good"
) -> Dict[str, Any]:
    """קבלת URL מותאם של תמונה"""
    params = {"quality": quality}
    if width:
        params["width"] = width
    if height:
        params["height"] = height
    
    r = requests.get(
        _url(f"/api/v1/images/products/{public_id}/optimized"),
        params=params,
        timeout=10
    )
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

# ---- Orders API ----
def get_orders_for_supplier(supplier_id: int):
    """
    מחזיר את רשימת ההזמנות של ספק נתון.
    דורש שקיים צד שרת בנתיב GET /api/v1/orders?supplier_id=...
    """
    r = requests.get(
        _url("/api/v1/orders/"),
        params={"supplier_id": supplier_id},
        timeout=20,
    )
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

def get_orders_for_owner(owner_id: int):
    """מחזיר את רשימת ההזמנות של בעל חנות נתון"""
    r = requests.get(
        _url("/api/v1/orders/owner/"),
        params={"owner_id": owner_id},
        timeout=20,
    )
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

def create_order(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """יצירת הזמנה חדשה"""
    r = requests.post(_url("/api/v1/orders/"), json=order_data, timeout=15)
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

def update_order_status(order_id: int, status: str, user_id: int) -> Dict[str, Any]:
    """עדכון סטטוס הזמנה"""
    r = requests.put(
        _url(f"/api/v1/orders/{order_id}/status"),
        json={"status": status},
        params={"supplier_id": user_id},
        timeout=10
    )
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

# ---- Users API ----
def register_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """הרשמת משתמש חדש"""
    r = requests.post(_url("/api/v1/users/register"), json=user_data, timeout=15)
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

def login_user(credentials: Dict[str, Any]) -> Dict[str, Any]:
    """התחברות משתמש"""
    r = requests.post(_url("/api/v1/users/login"), json=credentials, timeout=10)
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

def get_user_profile(user_id: int) -> Dict[str, Any]:
    """קבלת פרופיל משתמש"""
    r = requests.get(_url(f"/api/v1/users/{user_id}"), timeout=10)
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()