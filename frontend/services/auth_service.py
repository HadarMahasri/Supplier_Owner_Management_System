# frontend/services/auth_service.py
import os
from typing import Tuple, Optional, Dict
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")  # עדכני לפי השרת שלך

class AuthService:
    def register_user(self, payload: Dict) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        שולח את ה-payload כמו שיש לך היום ב-SignUp (username, email, password, userType, companyName, contactName, phone,
        city_id/street/house_number/opening_time/closing_time, serviceCities)
        """
        try:
            r = requests.post(f"{API_BASE_URL}/api/v1/users/register", json=payload, timeout=15)
            if r.status_code >= 400:
                # שגיאה מהשרת – תחזירי למעלה כדי שיופיע ב-UI
                try:
                    detail = r.json().get("detail")
                except Exception:
                    detail = r.text
                return False, None, detail
            data = r.json()
            return True, data.get("user_id"), None
        except Exception as e:
            return False, None, f"שגיאת תקשורת לשרת: {e}"

    def verify_login(self, username: str, password: str, role: str):
        try:
            r = requests.post(f"{API_BASE_URL}/api/v1/users/login",
                              json={"username": username, "password": password, "role": role},
                              timeout=10)
            if r.status_code >= 400:
                try:
                    detail = r.json().get("detail")
                except Exception:
                    detail = r.text
                return False, None, detail
            data = r.json()
            return True, data.get("user"), None
        except Exception as e:
            return False, None, f"שגיאת תקשורת לשרת: {e}"
