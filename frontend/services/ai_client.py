# ai_client.py - גרסה מואצת עם timeout קצר
import os, requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

def create_fast_session():
    """יצירת session מאופטמת לחיבורים מהירים"""
    session = requests.Session()
    
    # הגדרות retry מהירות
    retry_strategy = Retry(
        total=2,  # רק 2 נסיונות
        backoff_factor=0.1,  # מהיר יותר
        status_forcelist=[500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def ask_ai(question: str, user_id: int) -> str:
    """שאלת AI מהירה עם timeout קצר"""
    session = create_fast_session()
    
    try:
        r = session.post(
            f"{API_BASE_URL}/api/v1/ai/ask",
            json={"question": question, "user_id": user_id},
            timeout=(3, 15)  # 3 שניות חיבור, 15 תגובה
        )
        r.raise_for_status()
        result = (r.json() or {}).get("answer", "")
        
        if not result:
            return "לא התקבלה תגובה. נסה שוב."
            
        return result
        
    except requests.exceptions.Timeout:
        return "התגובה אורכת זמן רב. נסה שאלה קצרה יותר."
    except requests.exceptions.ConnectionError:
        return "בעיה בחיבור לשרת. בדוק שהשרת פועל."
    except Exception as e:
        return f"שגיאה זמנית: {str(e)[:50]}..."
    finally:
        session.close()