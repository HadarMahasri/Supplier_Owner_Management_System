# frontend/views/widgets/orders_export_widget.py
from PySide6.QtWidgets import QWidget, QFileDialog, QMessageBox
from typing import List, Dict
from datetime import date


class OrdersExportWidget:
    """רכיב ליצוא הזמנות לקבצים"""
    
    def __init__(self, parent: QWidget = None):
        self.parent = parent
    
    def export_orders(self, orders: List[Dict], orders_service, 
                     owner_id: int, display_history: bool) -> bool:
        """יצוא הזמנות לקובץ Excel או CSV"""
        
        if not orders:
            QMessageBox.information(self.parent, "יצוא לאקסל", "אין הזמנות ליצא")
            return False
        
        try:
            # הכנת נתונים לשתי טבלאות: הזמנות ומוצרים
            orders_data, products_data = orders_service.prepare_export_data(orders)
            
            # שם קובץ מוצע
            suggested = f"הזמנות_בעל_חנות_{owner_id or ''}_{date.today():%Y-%m-%d}_{'היסטוריה' if display_history else 'פעילות'}.xlsx"

            # חלון בחירת קובץ
            path, _ = QFileDialog.getSaveFileName(
                self.parent,
                "שמירת דוח הזמנות",
                suggested,
                "Excel (*.xlsx);;CSV (*.csv)"
            )
            if not path:
                return False
            
            # יצוא לקובץ
            success, message = orders_service.export_to_files(
                orders_data, products_data, path, owner_id, display_history
            )
            
            if success:
                QMessageBox.information(self.parent, "יצוא הושלם", message)
                return True
            else:
                QMessageBox.critical(self.parent, "שגיאת יצוא", message)
                return False
                
        except Exception as e:
            QMessageBox.critical(
                self.parent, 
                "שגיאת יצוא", 
                f"שגיאה בייצוא הקובץ:\n{str(e)}"
            )
            return False