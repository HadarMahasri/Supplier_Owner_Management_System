# frontend/services/supplier_data_service.py
import requests
import os
from typing import List, Dict, Optional, Tuple
from PySide6.QtCore import QObject, QThread, Signal


class DataFetchWorker(QThread):
    """Worker thread לטעינת נתונים ברקע"""
    
    data_loaded = Signal(dict)  # emits {"products": [], "orders": [], "stats": {}}
    error_occurred = Signal(str)
    
    def __init__(self, base_url: str, supplier_id: int):
        super().__init__()
        self.base_url = base_url
        self.supplier_id = supplier_id
    
    def run(self):
        try:
            # טעינת נתונים במקביל
            products = self._fetch_products()
            orders = self._fetch_orders()
            stats = self._calculate_stats(products, orders)
            
            # שליחת התוצאה
            self.data_loaded.emit({
                "products": products,
                "orders": orders,
                "stats": stats
            })
            
        except Exception as e:
            self.error_occurred.emit(f"שגיאה בטעינת נתונים: {str(e)}")
    
    def _fetch_products(self) -> List[Dict]:
        """טעינת מוצרי הספק"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/products/supplier/{self.supplier_id}",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []
    
    def _fetch_orders(self) -> List[Dict]:
        """טעינת הזמנות הספק"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/orders/supplier/{self.supplier_id}",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []
    
    def _calculate_stats(self, products: List[Dict], orders: List[Dict]) -> Dict:
        """חישוב סטטיסטיקות"""
        # חישובים בסיסיים
        total_products = len(products)
        total_orders = len(orders)
        
        # חישוב הזמנות לפי סטטוס
        new_orders = len([o for o in orders if o.get('status') == 'בתהליך'])
        completed_orders = len([o for o in orders if o.get('status') == 'הושלמה'])
        
        # חישוב הכנסות
        monthly_revenue = 0
        for order in orders:
            if order.get('status') == 'הושלמה':
                monthly_revenue += order.get('total_amount', 0)
        
        # דירוג ספק (placeholder - יהיה מחושב לפי ביקורות)
        supplier_rating = 4.8
        
        return {
            'new_orders': new_orders,
            'total_products': total_products,
            'monthly_revenue': monthly_revenue,
            'supplier_rating': supplier_rating,
            'total_orders': total_orders,
            'completed_orders': completed_orders
        }


class SupplierDataService(QObject):
    """Service לניהול נתוני הספק"""
    
    data_updated = Signal(dict)
    loading_started = Signal()
    loading_finished = Signal()
    error_occurred = Signal(str)
    
    def __init__(self, supplier_id: Optional[int]):
        super().__init__()
        self.supplier_id = supplier_id
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        # Cache for data
        self._products_cache = []
        self._orders_cache = []
        self._stats_cache = {}
        
        # Worker thread
        self._worker = None
    
    def load_data(self):
        """טעינת כל הנתונים הרלוונטיים לספק"""
        if not self.supplier_id:
            self.error_occurred.emit("אין מזהה ספק")
            return
        
        if self._worker and self._worker.isRunning():
            return  # כבר טוען
        
        self.loading_started.emit()
        
        self._worker = DataFetchWorker(self.base_url, self.supplier_id)
        self._worker.data_loaded.connect(self._on_data_loaded)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()
    
    def _on_data_loaded(self, data: Dict):
        """טיפול בנתונים שנטענו"""
        self._products_cache = data.get("products", [])
        self._orders_cache = data.get("orders", [])
        self._stats_cache = data.get("stats", {})
        
        self.data_updated.emit(data)
        self.loading_finished.emit()
    
    def _on_error(self, error_message: str):
        """טיפול בשגיאות"""
        self.error_occurred.emit(error_message)
        self.loading_finished.emit()
    
    def get_cached_data(self) -> Dict:
        """קבלת נתונים מה-cache"""
        return {
            "products": self._products_cache,
            "orders": self._orders_cache,
            "stats": self._stats_cache
        }
    
    # Specific data methods
    def add_product(self, product_data: Dict) -> bool:
        """הוספת מוצר חדש"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/products/",
                json=product_data,
                params={"supplier_id": self.supplier_id},
                timeout=10
            )
            
            if response.status_code == 201:
                # רענון הנתונים
                self.load_data()
                return True
            return False
            
        except Exception as e:
            self.error_occurred.emit(f"שגיאה בהוספת מוצר: {str(e)}")
            return False
    
    def update_order_status(self, order_id: int, new_status: str) -> bool:
        """עדכון סטטוס הזמנה"""
        try:
            response = requests.put(
                f"{self.base_url}/api/v1/orders/{order_id}/status",
                json={"status": new_status},
                params={"supplier_id": self.supplier_id},
                timeout=10
            )
            
            if response.status_code == 200:
                # רענון הנתונים
                self.load_data()
                return True
            return False
            
        except Exception as e:
            self.error_occurred.emit(f"שגיאה בעדכון הזמנה: {str(e)}")
            return False
    
    def get_analytics_data(self) -> Dict:
        """קבלת נתוני אנליטיקה מפורטים"""
        # זה יהיה מימוש מורכב יותר בעתיד
        return self._stats_cache.copy()
    
    def refresh_data(self):
        """רענון ידני של הנתונים"""
        self.load_data()