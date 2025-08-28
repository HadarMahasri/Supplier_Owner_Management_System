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
    r = requests.get(_url(f"/api/v1/products"), params={"supplier_id": supplier_id}, timeout=10)
    r.raise_for_status()
    return r.json()

def create_product(payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(_url("/api/v1/products"), json=payload, timeout=15)
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

def update_product(product_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.put(_url(f"/api/v1/products/{product_id}"), json=payload, timeout=15)
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

def update_stock(product_id: int, stock: int) -> Dict[str, Any]:
    r = requests.put(_url(f"/api/v1/products/{product_id}/stock"), json={"stock": stock}, timeout=10)
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
    return r.json()

def delete_product(product_id: int) -> None:
    r = requests.delete(_url(f"/api/v1/products/{product_id}"), timeout=10)
    if r.status_code >= 400:
        raise RuntimeError(_err(r))
