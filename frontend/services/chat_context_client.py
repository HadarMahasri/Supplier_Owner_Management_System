# frontend/services/chat_context_client.py - גרסה מואצת
import os, requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from functools import lru_cache

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

def create_optimized_session():
    """Session מאופטמת לביצועים מהירים"""
    session = requests.Session()
    
    # הגדרות retry מהירות
    retry_strategy = Retry(
        total=2,
        backoff_factor=0.1,
        status_forcelist=[500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

@lru_cache(maxsize=50)  # Cache context למהירות
def fetch_ai_context(user_id: int) -> dict:
    """טעינת הקשר מהירה עם cache"""
    session = create_optimized_session()
    
    try:
        r = session.get(
            f"{API_BASE_URL}/api/v1/ai/context", 
            params={"user_id": user_id}, 
            timeout=(2, 10)  # timeout קצר - 2 שניות חיבור, 10 תגובה
        )
        r.raise_for_status()
        
        result = r.json()
        if not result:
            raise ValueError("לא התקבל הקשר מהשרת")
            
        return result
        
    except requests.exceptions.Timeout:
        raise Exception("טעינת המשתמש אורכת זמן רב. נסה שוב.")
    except requests.exceptions.ConnectionError:
        raise Exception("לא ניתן להתחבר לשרת. בדוק שהשרת פועל.")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise Exception(f"משתמש {user_id} לא נמצא במערכת.")
        else:
            raise Exception(f"שגיאת שרת: {e.response.status_code}")
    except Exception as e:
        raise Exception(f"שגיאה בטעינת המשתמש: {str(e)}")
    finally:
        session.close()

def ask_via_backend(question: str, user_id: int) -> str:
    """שאלה דרך backend מהירה יותר"""
    session = create_optimized_session()
    
    try:
        r = session.post(
            f"{API_BASE_URL}/api/v1/ai/ask",
            json={"question": question, "user_id": user_id}, 
            timeout=(3, 20)  # timeout מעט יותר ארוך לשאלות מורכבות
        )
        r.raise_for_status()
        
        result = (r.json() or {}).get("answer", "")
        if not result:
            return "לא התקבלה תגובה מהמערכת. נסה שוב."
            
        return result
        
    except requests.exceptions.Timeout:
        return "התגובה אורכת זמן רב. נסה שאלה קצרה יותר."
    except requests.exceptions.ConnectionError:
        return "בעיה בחיבור. בדוק שהשרת פועל."
    except Exception as e:
        return f"שגיאה: {str(e)[:80]}..."
    finally:
        session.close()

# נקה cache כל 5 דקות
import threading, time

def clear_cache_periodically():
    """נקה cache מדי פעם למידע עדכני"""
    while True:
        time.sleep(300)  # 5 דקות
        fetch_ai_context.cache_clear()

# הפעל ניקוי cache ברקע
cache_cleaner = threading.Thread(target=clear_cache_periodically, daemon=True)
cache_cleaner.start()