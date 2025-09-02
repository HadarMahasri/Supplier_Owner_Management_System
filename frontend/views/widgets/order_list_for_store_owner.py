# frontend/views/widgets/order_list_for_store_owner.py
from PySide6.QtWidgets import QWidget, QVBoxLayout
from views.widgets.store_owner_orders_widget import StoreOwnerOrdersWidget


class OrdersForStoreOwner(QWidget):
    """רכיב רשימת הזמנות לבעל חנות - wrapper פשוט לשמירה על תאימות"""
    
    def __init__(self, owner_id: int = None):
        super().__init__()
        
        # יצירת הממשק הפשוט
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # יצירת הרכיב החדש
        self.orders_widget = StoreOwnerOrdersWidget(owner_id)
        layout.addWidget(self.orders_widget)
    
    def refresh_orders(self):
        """רענון רשימת הזמנות - wrapper function"""
        if hasattr(self.orders_widget, 'refresh_orders'):
            self.orders_widget.refresh_orders()
    
    def set_owner_id(self, owner_id: int):
        """עדכון מזהה בעל החנות - wrapper function"""
        if hasattr(self.orders_widget, 'set_owner_id'):
            self.orders_widget.set_owner_id(owner_id)