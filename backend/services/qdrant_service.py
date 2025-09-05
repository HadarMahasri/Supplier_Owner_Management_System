import os
import logging
from typing import List
import requests
import time

logger = logging.getLogger(__name__)


class QdrantService:
    """
    שירות Qdrant מואץ עם:
    - timeout קצר יותר
    - connection pooling
    - חיפוש מהיר יותר
    - retry logic מובטל
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("QDRANT_URL", "http://localhost:6333").rstrip("/")
        self.collection = os.getenv("QDRANT_COLLECTION_NAME", "suppliers_knowledge")
        self.timeout = int(os.getenv("QDRANT_TIMEOUT", "10"))  # הקטנתי מ-20 ל-10
        
        # הגדרות אופטימיזציה
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Connection': 'keep-alive'
        })
        
        # מטמון לתוצאות חיפוש
        self.search_cache = {}
        self.cache_ttl = 300  # 5 דקות
        self.max_cache_size = 100

    def health_check(self) -> bool:
        """בדיקת תקינות מהירה מאוד"""
        try:
            response = self.session.get(
                f"{self.base_url}/readyz", 
                timeout=3  # הקטנתי מ-5 ל-3
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Qdrant health failed: {e}")
            return False

    def search(self, vector: List[float], limit: int = 3) -> List[str]:
        """חיפוש מהיר עם מטמון"""
        try:
            # יצירת מפתח מטמון
            vector_hash = hash(tuple(vector[:10]))  # רק 10 איברים ראשונים למהירות
            cache_key = f"{vector_hash}_{limit}"
            current_time = time.time()
            
            # בדיקת מטמון
            if cache_key in self.search_cache:
                cached = self.search_cache[cache_key]
                if current_time - cached["timestamp"] < self.cache_ttl:
                    logger.debug("Qdrant search cache hit")
                    return cached["results"]
            
            # חיפוש ב-Qdrant
            url = f"{self.base_url}/collections/{self.collection}/points/search"
            payload = {
                "vector": vector,
                "limit": limit,
                "with_payload": True,
                "with_vector": False  # לא צריך את הוקטור בחזרה - חוסך רוחב פס
            }
            
            start_time = time.time()
            response = self.session.post(url, json=payload, timeout=self.timeout)
            duration = time.time() - start_time
            
            response.raise_for_status()
            data = response.json().get("result", [])
            
            # חילוץ טקסטים
            texts = []
            for point in data:
                payload_data = point.get("payload", {})
                text = payload_data.get("text")
                if text:
                    texts.append(text)
            
            # שמירה במטמון
            self.search_cache[cache_key] = {
                "results": texts,
                "timestamp": current_time
            }
            
            # ניקוי מטמון אם גדול מדי
            if len(self.search_cache) > self.max_cache_size:
                oldest_key = min(self.search_cache.keys(), 
                               key=lambda k: self.search_cache[k]["timestamp"])
                del self.search_cache[oldest_key]
            
            logger.debug(f"Qdrant search completed in {duration:.2f}s, found {len(texts)} results")
            return texts
            
        except requests.exceptions.Timeout:
            logger.warning("Qdrant search timeout")
            return []
        except Exception as e:
            logger.error(f"Qdrant search error: {e}")
            return []

    def search_with_filter(self, vector: List[float], filter_condition: dict, limit: int = 3) -> List[str]:
        """חיפוש עם פילטר - לעתיד"""
        try:
            url = f"{self.base_url}/collections/{self.collection}/points/search"
            payload = {
                "vector": vector,
                "limit": limit,
                "filter": filter_condition,
                "with_payload": True,
                "with_vector": False
            }
            
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json().get("result", [])
            
            texts = []
            for point in data:
                payload_data = point.get("payload", {})
                text = payload_data.get("text")
                if text:
                    texts.append(text)
            
            return texts
            
        except Exception as e:
            logger.error(f"Qdrant filtered search error: {e}")
            return []

    def get_collection_info(self) -> dict:
        """מידע על האוסף"""
        try:
            response = self.session.get(
                f"{self.base_url}/collections/{self.collection}",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
        return {}

    def clear_cache(self):
        """ניקוי מטמון החיפוש"""
        self.search_cache.clear()
        logger.info("Qdrant search cache cleared")

    def __del__(self):
        """סגירת session בעת מחיקה"""
        if hasattr(self, 'session'):
            self.session.close()