# frontend/services/orders_service.py
"""
Service layer for orders management
Handles all API calls and business logic for orders
"""

import requests
import os
from typing import List, Dict, Optional
from datetime import datetime
from PySide6.QtCore import QThread, Signal


class OrdersFetchThread(QThread):
    """Thread לטעינת הזמנות מהשרת"""
    orders_loaded = Signal(list)
    error_occurred = Signal(str)
    
    def __init__(self, base_url: str, supplier_id: int):
        super().__init__()
        self.base_url = base_url
        self.supplier_id = supplier_id
    
    def run(self):
        try:
            orders = self._fetch_orders()
            self.orders_loaded.emit(orders)
        except Exception as e:
            self.error_occurred.emit(f"שגיאה בטעינת הזמנות: {str(e)}")
    
    def _fetch_orders(self) -> List[Dict]:
        """טעינת הזמנות מהשרת"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/gateway/orders/supplier/{self.supplier_id}",
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []


class OrdersService:
    """Service class for orders management"""
    
    def __init__(self):
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    def get_orders_for_supplier(self, supplier_id: int) -> List[Dict]:
        """Get all orders for a specific supplier"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/gateway/orders/supplier/{supplier_id}",
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error fetching orders: {e}")
            return []
    
    def get_orders_for_owner(self, owner_id: int) -> List[Dict]:
        """Get all orders for a specific store owner"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/gateway/orders/owner/{owner_id}",
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Error fetching orders: {e}")
            return []
    
    def update_order_status(self, order_id: int, new_status: str, supplier_id: int) -> tuple[bool, str]:
        """
        Update order status by supplier
        Returns: (success: bool, message: str)
        """
        try:
            response = requests.put(
                f"{self.base_url}/api/v1/gateway/orders/{order_id}/status",
                json={"status": new_status},
                params={"supplier_id": supplier_id},
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "הסטטוס עודכן בהצלחה"
            else:
                error_msg = "שגיאה בעדכון הסטטוס"
                try:
                    error_detail = response.json().get("detail", "")
                    if error_detail:
                        error_msg += f": {error_detail}"
                except:
                    pass
                return False, error_msg
                
        except requests.exceptions.Timeout:
            return False, "הבקשה נכשלה - זמן המתנה יתר על המידה"
        except requests.exceptions.ConnectionError:
            return False, "לא ניתן להתחבר לשרת"
        except Exception as e:
            return False, f"שגיאה בעדכון הסטטוס: {str(e)}"
    
    def update_order_status_by_owner(self, order_id: int, new_status: str, owner_id: int) -> tuple[bool, str]:
        """
        Update order status by store owner
        Returns: (success: bool, message: str)
        """
        try:
            response = requests.put(
                f"{self.base_url}/api/v1/gateway/orders/{order_id}/status/owner",
                json={"status": new_status},
                params={"owner_id": owner_id},
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "הסטטוס עודכן בהצלחה"
            else:
                error_msg = "שגיאה בעדכון הסטטוס"
                try:
                    error_detail = response.json().get("detail", "")
                    if error_detail:
                        error_msg += f": {error_detail}"
                except:
                    pass
                return False, error_msg
                
        except requests.exceptions.Timeout:
            return False, "הבקשה נכשלה - זמן המתנה יתר על המידה"
        except requests.exceptions.ConnectionError:
            return False, "לא ניתן להתחבר לשרת"
        except Exception as e:
            return False, f"שגיאה בעדכון הסטטוס: {str(e)}"
    
    def filter_orders(self, orders: List[Dict], 
                     display_history: bool = False,
                     date_from: Optional[datetime] = None,
                     date_to: Optional[datetime] = None) -> List[Dict]:
        """Filter orders based on criteria"""
        filtered = []
        
        for order in orders:
            # סינון לפי היסטוריה
            status = order.get("status", "")
            if display_history:
                if status != "הושלמה":
                    continue
            else:
                if status == "הושלמה":
                    continue
            
            # סינון לפי תאריך
            if date_from or date_to:
                created_date = order.get("created_date", "")
                if created_date:
                    try:
                        order_date = datetime.fromisoformat(
                            created_date.replace('Z', '+00:00')
                        ).date()
                        
                        if date_from and order_date < date_from:
                            continue
                        if date_to and order_date > date_to:
                            continue
                    except:
                        continue
            
            filtered.append(order)
        
        return filtered
    
    def prepare_export_data(self, orders: List[Dict]) -> tuple[List[Dict], List[Dict]]:
        """
        Prepare orders data for export
        Returns: (orders_data, products_data)
        """
        orders_data = []
        products_data = []
        
        for order in orders:
            # טיפול בתאריך
            try:
                date_str = datetime.fromisoformat(
                    order.get('created_date', '').replace('Z', '+00:00')
                ).strftime('%d/%m/%Y') if order.get('created_date') else ''
            except Exception:
                date_str = order.get('created_date', '')[:10] if order.get('created_date') else ''
            
            # נתוני הזמנה בסיסיים
            order_info = {
                'מספר הזמנה': order.get('id', ''),
                'תאריך': date_str,
                'סכום ההזמנה': order.get('total_amount', 0),
                'סטטוס': order.get('status', ''),
                'שם החנות': order.get('owner_company', ''),
                'איש קשר': order.get('owner_name', ''),
                'מספר מוצרים': len(order.get('items', [])),
            }
            orders_data.append(order_info)
            
            # פירוט מוצרים
            for item in order.get('items', []):
                products_data.append({
                    'מספר הזמנה': order.get('id', ''),
                    'תאריך הזמנה': date_str,
                    'שם החנות': order.get('owner_company', ''),
                    'מספר מוצר': item.get('product_id', ''),
                    'שם מוצר': item.get('product_name', ''),
                    'כמות': item.get('quantity', 0),
                    'מחיר יחידה': item.get('unit_price', 0),
                    'סכום מוצר': (item.get('quantity', 0) or 0) * (item.get('unit_price', 0) or 0),
                })
        
        return orders_data, products_data