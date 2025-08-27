# frontend/services/auth_service.py
import os
from typing import Tuple, Optional, Dict, Any
import requests

# אפשר לשנות לכתובת פרודקשן (לדוגמה https://your-domain.com)
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

def _extract_error(resp: requests.Response) -> str:
    try:
        j = resp.json()
        # FastAPI מחזיר בדרך כלל detail בשדה הזה
        if isinstance(j, dict) and "detail" in j:
            return str(j["detail"])
        return str(j)
    except Exception:
        return resp.text or f"HTTP {resp.status_code}"

class AuthService:
    def register_user(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        payload דוגמה:
        {
          "username": "...",
          "email": "...",
          "password": "...",
          "userType": "Supplier" | "StoreOwner",
          "companyName": "...",
          "contactName": "...",
          "phone": "...",
          "city_id": 123, "street": "...", "house_number": "...",
          "opening_time": "08:00", "closing_time": "20:00",
          "serviceCities": [11,22,33]
        }
        """
        try:
            url = f"{API_BASE_URL}/api/v1/users/register"
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code >= 400:
                return False, None, _extract_error(r)
            data = r.json()
            return True, data.get("user_id"), None
        except Exception as e:
            return False, None, f"שגיאת תקשורת לשרת: {e}"

    def verify_login(self, username: str, password: str, role: str) -> Tuple[bool, Optional[dict], Optional[str]]:
        try:
            url = f"{API_BASE_URL}/api/v1/users/login"
            r = requests.post(url, json={"username": username, "password": password, "role": role}, timeout=10)
            if r.status_code >= 400:
                return False, None, _extract_error(r)
            data = r.json()
            return True, data.get("user"), None
        except Exception as e:
            return False, None, f"שגיאת תקשורת לשרת: {e}"
