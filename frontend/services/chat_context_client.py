# frontend/services/chat_context_client.py - עם timeout מותאם
import os, requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from functools import lru_cache

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

def create_optimized_session():
    """Session עם timeouts מותאמים למסד איטי"""
    session = requests.Session()
    
    # הגדרות retry עדינות יותר
    retry_strategy = Retry(
        total=2,
        backoff_factor=0.5,  # יותר זמן בין נסיונות
        status_forcelist=[500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

@lru_cache(maxsize=50)
def fetch_ai_context(user_id: int) -> dict:
    """טעינת הקשר עם timeout מותאם למסד איטי"""
    session = create_optimized_session()
    
    try:
        r = session.get(
            f"{API_BASE_URL}/api/v1/ai/context", 
            params={"user_id": user_id}, 
            timeout=(5, 20)  # 5 שניות חיבור, 20 שניות תגובה (יותר מהקודם)
        )
        r.raise_for_status()
        
        result = r.json()
        if not result:
            raise ValueError("לא התקבל הקשר מהשרת")
            
        return result
        
    except requests.exceptions.Timeout:
        raise Exception(f"טעינת משתמש {user_id} אורכת זמן רב. זה קורה לפעמים עם מסד הנתונים החיצוני. נסה user_id=3 (עובד מהר יותר).")
    except requests.exceptions.ConnectionError:
        raise Exception("לא ניתן להתחבר לשרת. בדוק שהשרת פועל.")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise Exception(f"משתמש {user_id} לא נמצא במערכת. נסה user_id=3.")
        else:
            raise Exception(f"שגיאת שרת: {e.response.status_code}")
    except Exception as e:
        raise Exception(f"שגיאה בטעינת המשתמש: {str(e)}")
    finally:
        session.close()

def ask_via_backend(question: str, user_id: int) -> str:
    """שאלה דרך backend עם timeout מותאם"""
    session = create_optimized_session()
    
    try:
        r = session.post(
            f"{API_BASE_URL}/api/v1/ai/ask",
            json={"question": question, "user_id": user_id}, 
            timeout=(5, 30)  # timeout יותר ארוך לשאלות AI
        )
        r.raise_for_status()
        
        result = (r.json() or {}).get("answer", "")
        if not result:
            return "לא התקבלה תגובה מהמערכת. נסה שוב."
            
        return result
        
    except requests.exceptions.Timeout:
        return f"התגובה לuser_id={user_id} אורכת זמן רב. נסה user_id=3 או שאלה קצרה יותר."
    except requests.exceptions.ConnectionError:
        return "בעיה בחיבור. בדוק שהשרת פועל."
    except Exception as e:
        return f"שגיאה זמנית: {str(e)[:80]}..."
    finally:
        session.close()

# ---- פונקציה מהירה לבדיקת משתמש -------
def quick_user_check(user_id: int) -> tuple[bool, str]:
    """בדיקה מהירה אם משתמש קיים"""
    try:
        session = create_optimized_session()
        r = session.get(
            f"{API_BASE_URL}/api/v1/ai/context",
            params={"user_id": user_id},
            timeout=3  # timeout קצר לבדיקה מהירה
        )
        
        if r.status_code == 200:
            data = r.json()
            name = data.get("username", "ללא שם")
            role = data.get("role", "ללא תפקיד")
            return True, f"{name} ({role})"
        elif r.status_code == 404:
            return False, "לא קיים במסד"
        else:
            return False, f"שגיאה {r.status_code}"
            
    except requests.exceptions.Timeout:
        return False, "איטי מדי"
    except Exception as e:
        return False, str(e)[:30]