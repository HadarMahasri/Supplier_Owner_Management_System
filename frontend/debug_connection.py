# debug_connection.py - כלי אבחון מהיר
import requests
import sys
import json

API_BASE_URL = "http://127.0.0.1:8000"

def check_server():
    """בדיקה 1: האם השרת פועל"""
    print("🔍 בודק אם השרת FastAPI פועל...")
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=3)
        if r.status_code == 200:
            data = r.json()
            print(f"✅ שרת פועל: {data}")
            return True
        else:
            print(f"⚠️ שרת מגיב אבל עם בעיה: {r.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ לא ניתן להתחבר לשרת ב-{API_BASE_URL}")
        print("💡 פתרון: cd backend && python main.py")
        return False
    except Exception as e:
        print(f"❌ שגיאה: {e}")
        return False

def check_database():
    """בדיקה 2: האם מסד הנתונים פועל"""
    print("\n🗃️ בודק חיבור למסד נתונים...")
    try:
        r = requests.get(f"{API_BASE_URL}/", timeout=3)
        if r.status_code == 200:
            print("✅ API endpoint פועל")
            return True
        else:
            print(f"⚠️ בעיה ב-API: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ בעיית API: {e}")
        return False

def check_users():
    """בדיקה 3: האם יש משתמשים במסד"""
    print("\n👤 בודק משתמשים במסד...")
    
    for user_id in [1, 2, 3, 4, 5]:
        try:
            r = requests.get(
                f"{API_BASE_URL}/api/v1/ai/context",
                params={"user_id": user_id},
                timeout=5
            )
            
            if r.status_code == 200:
                data = r.json()
                username = data.get("username", "ללא שם")
                role = data.get("role", "ללא תפקיד")
                print(f"✅ משתמש {user_id}: {username} ({role})")
                return user_id
            elif r.status_code == 404:
                print(f"⚪ משתמש {user_id}: לא קיים")
            else:
                print(f"⚠️ משתמש {user_id}: שגיאה {r.status_code}")
                print(f"   פרטים: {r.text[:100]}")
                
        except Exception as e:
            print(f"❌ משתמש {user_id}: שגיאה {e}")
    
    print("\n❌ לא נמצאו משתמשים פעילים")
    print("💡 פתרון: python backend/database/create_somee_database.py")
    return None

def check_ai_service():
    """בדיקה 4: האם שירות AI פועל"""
    print("\n🤖 בודק שירות AI...")
    try:
        # נסה שאלה פשוטה
        r = requests.post(
            f"{API_BASE_URL}/api/v1/ai/ask",
            json={"question": "בדיקה", "user_id": 1},
            timeout=10
        )
        
        if r.status_code == 200:
            answer = r.json().get("answer", "")
            print(f"✅ AI עובד: {answer[:50]}...")
            return True
        elif r.status_code == 404:
            print("❌ AI endpoint לא נמצא")
        else:
            print(f"⚠️ AI endpoint בבעיה: {r.status_code}")
            print(f"   פרטים: {r.text[:100]}")
            
    except Exception as e:
        print(f"❌ AI לא פועל: {e}")
    
    return False

def full_diagnosis():
    """אבחון מלא של המערכת"""
    print("🔧 אבחון מלא של מערכת החיבור")
    print("=" * 50)
    
    # שלב 1: שרת
    if not check_server():
        return
    
    # שלב 2: מסד נתונים
    if not check_database():
        return
    
    # שלב 3: משתמשים
    working_user_id = check_users()
    
    # שלב 4: AI (רק אם יש משתמש)
    if working_user_id:
        check_ai_service()
        print(f"\n🎉 המערכת תקינה! השתמש ב-user_id: {working_user_id}")
    else:
        print("\n📋 צעדים לפתרון:")
        print("1. cd backend")
        print("2. python database/create_somee_database.py")
        print("3. נסה שוב עם user_id=1")

def quick_fix():
    """פתרון מהיר אוטומטי"""
    print("🚀 מנסה פתרון מהיר...")
    
    # בדוק שרת
    if not check_server():
        print("💡 הפעל את השרת קודם:")
        print("   cd backend && python main.py")
        return
    
    # בדוק משתמשים
    working_user = check_users()
    if working_user:
        print(f"✅ פתרון מצוא! השתמש ב-user_id: {working_user}")
    else:
        print("🔧 יוצר נתוני דמו...")
        print("רוץ: python backend/database/create_somee_database.py")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        quick_fix()
    else:
        full_diagnosis()