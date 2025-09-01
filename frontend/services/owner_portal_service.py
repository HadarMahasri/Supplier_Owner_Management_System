import os, requests

API_BASE = os.getenv("API_BASE") or "http://127.0.0.1:8000"
API_BASE = API_BASE.rstrip("/")
if not API_BASE.endswith("/api/v1"):
    API_BASE = API_BASE + "/api/v1"

def _url(path: str) -> str:
    # path צריך להתחיל ב-"/owner-links/..." וכד'
    return f"{API_BASE}{path}"

def _get(path: str, params: dict):
    r = requests.get(_url(path), params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def _post(path: str, params: dict):
    r = requests.post(_url(path), params=params, timeout=10)
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

# --- Products & Orders for StoreOwner ---

def products_by_supplier(supplier_id: int):
    # התאימי לנתיב ה-API שלך (דוגמה נפוצה:)
    return _get("/products/", {"supplier_id": supplier_id})

def create_order(owner_id: int, supplier_id: int, items: list[dict]):
    # התאימי לנתיב/פרמטרים המדויקים של ה-API שלך
    import requests
    r = requests.post(
        _url("/orders/"),
        params={"owner_id": owner_id},
        json={"supplier_id": supplier_id, "items": items},
        timeout=15
    )
    r.raise_for_status()
    return r.json()