# frontend/services/links_service.py
import os, requests
from typing import Any

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000/api/v1")

def _fetch(path: str, params: dict | None = None):
    r = requests.get(f"{API_BASE}{path}", params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def _unwrap(payload):
    """Helper to normalize API payloads into a flat list"""
    if not payload:
        return []
    if isinstance(payload, dict):
        for key in ("data", "results", "items", "links"):
            if key in payload and isinstance(payload[key], list):
                return payload[key]
        # אם קיבלנו רשומה בודדת
        return [payload]
    if isinstance(payload, list):
        return payload
    return []
    
def get_active_links(supplier_id: int):
    return _unwrap(_fetch("/owner-links/active", {"supplier_id": supplier_id}))

def get_pending_links(supplier_id: int):
    return _unwrap(_fetch("/owner-links/pending", {"supplier_id": supplier_id}))


def _normalize_list(items: Any) -> list[dict]:
    """
    מנרמל לרשימה של רשומות עם מפתח owner.
    מקבל או [{owner:{...}, supplier_id, status}] או [{owner_id, supplier_id, status, ...}]
    """
    if not isinstance(items, list):
        return []
    norm: list[dict] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if "owner" in it and isinstance(it["owner"], dict):
            # כבר בצורת היעד
            norm.append(it)
            continue
        # רשומה "שטוחה" – נעטוף ל-owner
        owner_id = it.get("owner_id") or it.get("ownerId")
        supplier_id = it.get("supplier_id") or it.get("supplierId")
        status = it.get("status")
        norm.append({
            "owner": {"id": owner_id, "company_name": "-", "contact_name": "-", "phone": "-"},
            "supplier_id": supplier_id,
            "status": status,
        })
    return norm

def _get_list(path: str, supplier_id: int) -> list[dict]:
    # נסה גם supplier_id וגם supplierId
    payload = None
    for p in ({"supplier_id": supplier_id}, {"supplierId": supplier_id}):
        try:
            payload = _fetch(path, p)
            break
        except Exception:
            continue
    items = _unwrap(payload)
    return _normalize_list(items)



def approve_link(owner_id: int, supplier_id: int) -> bool:
    try:
        r = requests.post(f"{API_BASE}/owner-links/{owner_id}/approve",
                          params={"supplier_id": supplier_id}, timeout=10)
        return r.ok
    except Exception:
        return False

def reject_link(owner_id: int, supplier_id: int) -> bool:
    try:
        r = requests.post(f"{API_BASE}/owner-links/{owner_id}/reject",
                          params={"supplier_id": supplier_id}, timeout=10)
        return r.ok
    except Exception:
        return False
