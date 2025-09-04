# frontend/services/store_owner_orders_service.py
"""
Service layer for store owner orders management
Handles all API calls and business logic for store owner orders
"""

import requests
import os
from typing import List, Dict, Optional
from datetime import datetime, date
from PySide6.QtCore import QThread, Signal


class StoreOwnerOrdersFetchThread(QThread):
    """Thread לטעינת הזמנות מהשרת עבור בעל חנות"""
    orders_loaded = Signal(list)
    error_occurred = Signal(str)
    
    def __init__(self, base_url: str, owner_id: int):
        super().__init__()
        self.base_url = base_url
        self.owner_id = owner_id
    
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
                f"{self.base_url}/api/v1/gateway/orders/owner/{self.owner_id}",
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []


class StoreOwnerOrdersService:
    """Service class for store owner orders management"""
    
    def __init__(self):
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    
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
                     date_from: Optional[date] = None,
                     date_to: Optional[date] = None,
                     supplier_filter: str = "") -> List[Dict]:
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
                        order_date = datetime.fromisoformat(created_date.replace('Z', '+00:00')).date()
                        if date_from and order_date < date_from:
                            continue
                        if date_to and order_date > date_to:
                            continue
                    except:
                        continue
            
            # סינון לפי ספק
            if supplier_filter:
                supplier_name = order.get("owner_company", "").lower()
                if supplier_filter.lower() not in supplier_name:
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
                date_str = order.get('created_date', '')[:10]

            # נתוני הזמנה בסיסיים
            order_info = {
                'מספר הזמנה': order.get('id', ''),
                'תאריך': date_str,
                'סכום ההזמנה': order.get('total_amount', 0),
                'סטטוס': order.get('status', ''),
                'שם הספק': order.get('owner_company', ''),
                'איש קשר': order.get('owner_name', ''),
                'מספר מוצרים': len(order.get('items', [])),
            }
            orders_data.append(order_info)

            # פירוט מוצרים
            for item in order.get('items', []):
                products_data.append({
                    'מספר הזמנה': order.get('id', ''),
                    'תאריך הזמנה': date_str,
                    'שם הספק': order.get('owner_company', ''),
                    'מספר מוצר': item.get('product_id', ''),
                    'שם מוצר': item.get('product_name', ''),
                    'כמות': item.get('quantity', 0),
                    'מחיר יחידה': item.get('unit_price', 0),
                    'סכום מוצר': (item.get('quantity', 0) or 0) * (item.get('unit_price', 0) or 0),
                })

        return orders_data, products_data
    
    def export_to_files(self, orders_data: List[Dict], products_data: List[Dict], 
                       file_path: str, owner_id: int, display_history: bool) -> tuple[bool, str]:
        """Export data to Excel or CSV files"""
        try:
            import pandas as pd
            
            df_orders = pd.DataFrame(orders_data)
            df_products = pd.DataFrame(products_data)

            if file_path.lower().endswith(".csv"):
                # אם בחרו CSV — שומרים שני קבצים נפרדים
                base = file_path[:-4]
                orders_csv = base + "_הזמנות.csv"
                products_csv = base + "_מוצרים.csv"
                df_orders.to_csv(orders_csv, index=False, encoding="utf-8-sig")
                df_products.to_csv(products_csv, index=False, encoding="utf-8-sig")

                return True, f"נשמרו שני קבצי CSV:\n• {orders_csv}\n• {products_csv}"
            else:
                # קובץ Excel עם שני גיליונות
                with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
                    df_orders.to_excel(writer, sheet_name="הזמנות", index=False)
                    df_products.to_excel(writer, sheet_name="מוצרים", index=False)

                    # התאמת רוחב עמודות בסיסי
                    for sheet_name, df in [("הזמנות", df_orders), ("מוצרים", df_products)]:
                        ws = writer.sheets[sheet_name]
                        for col_idx, col in enumerate(df.columns):
                            ws.set_column(col_idx, col_idx, max(12, min(50, len(str(col)) + 6)))

                return True, f"הקובץ נשמר בהצלחה:\n{file_path}"

        except Exception as e:
            return False, f"שגיאה ביצוא הקובץ:\n{str(e)}"