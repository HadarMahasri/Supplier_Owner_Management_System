import os, requests

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000/api/v1")  

def _get(path: str, params: dict):
    r = requests.get(f"{API_BASE}{path}", params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def _post(path: str, params: dict):
    r = requests.post(f"{API_BASE}{path}", params=params, timeout=10)
    r.raise_for_status()
    return r.json()

# --- Tabs data ---
def find_suppliers(owner_id: int):
    return _get("/owner-links/find-suppliers", {"owner_id": owner_id})

def get_active_by_owner(owner_id: int):
    return _get("/owner-links/active-by-owner", {"owner_id": owner_id})

def get_pending_by_owner(owner_id: int):
    return _get("/owner-links/pending-by-owner", {"owner_id": owner_id})

def request_link(owner_id: int, supplier_id: int):
    return _post("/owner-links/request", {"owner_id": owner_id, "supplier_id": supplier_id})

# אופציונלי: נקודת פתיחת הזמנה אמיתית בהמשך
def create_order(owner_id: int, supplier_id: int):
    # TODO: כאשר יוגדר API להזמנות – לקרוא אליו כאן
    return {"ok": True}
