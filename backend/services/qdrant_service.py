import os
import logging
from typing import List

import requests

logger = logging.getLogger(__name__)


class QdrantService:
    """
    שכבה דקה מעל Qdrant HTTP:
    - health_check() סינכרוני /readyz
    - search() חיפוש קוסינוס עם payload
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("QDRANT_URL", "http://localhost:6333").rstrip("/")
        self.collection = os.getenv("QDRANT_COLLECTION_NAME", "suppliers_knowledge")
        self.timeout = int(os.getenv("QDRANT_TIMEOUT", "20"))

    def health_check(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/readyz", timeout=5)
            return r.status_code == 200
        except Exception as e:
            logger.error(f"Qdrant health failed: {e}")
            return False

    def search(self, vector: List[float], limit: int = 3) -> List[str]:
        """חיפוש לפי וקטור ומחזיר טקסטים (payload.text)."""
        try:
            url = f"{self.base_url}/collections/{self.collection}/points/search"
            payload = {"vector": vector, "limit": limit, "with_payload": True}
            r = requests.post(url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            data = r.json().get("result", [])
            texts = []
            for p in data:
                pay = p.get("payload", {})
                t = pay.get("text")
                if t:
                    texts.append(t)
            return texts
        except Exception as e:
            logger.error(f"Qdrant search error: {e}")
            return []
