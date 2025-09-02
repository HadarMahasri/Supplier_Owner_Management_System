# frontend/views/widgets/store_owner_orders_widget.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QSpacerItem, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt
from typing import List, Dict, Set

from services.store_owner_orders_service import StoreOwnerOrdersService, StoreOwnerOrdersFetchThread
from views.widgets.store_owner_orders_filter_bar import StoreOwnerOrdersFilterBar
from views.widgets.store_owner_orders_row import StoreOwnerOrdersRow


class StoreOwnerOrdersWidget(QWidget):
    """רכיב רשימת הזמנות לבעל חנות"""
    
    def __init__(self, owner_id: int = None):
        super().__init__()
        self.owner_id = owner_id
        self.orders_service = StoreOwnerOrdersService()
        
        # מצב הרכיב
        self.orders = []
        self.expanded_orders: Set[int] = set()
        self.display_history = False
        self.date_filter = {"from": None, "to": None}
        self.supplier_filter = ""
        
        self.setup_ui()
        self.setup_styles()
        self.load_orders()
    
    def setup_ui(self):
        """בניית הממשק"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)
        
        # כותרת
        title = QLabel("הזמנות שלי")
        title.setObjectName("ordersTitle")
        main_layout.addWidget(title)
        
        # פילטר תאריכים ופעולות
        self.filter_bar = StoreOwnerOrdersFilterBar()
        self.filter_bar.date_filter_changed.connect(self.on_date_filter_changed)
        self.filter_bar.supplier_filter_changed.connect(self.on_supplier_filter_changed)
        self.filter_bar.clear_filter_requested.connect(self.clear_date_filter)
        self.filter_bar.export_requested.connect(self.export_to_excel)
        self.filter_bar.history_toggle_requested.connect(self.toggle_history_view)
        main_layout.addWidget(self.filter_bar)
        
        # כותרות טבלה
        header_row = self.create_header_row()
        main_layout.addWidget(header_row)
        
        # אזור ההזמנות עם גלילה
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        # הגדרות חשובות עבור ה-container
        self.orders_container = QWidget()
        self.orders_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        
        self.orders_layout = QVBoxLayout(self.orders_container)
        self.orders_layout.setContentsMargins(0, 0, 0, 0)
        self.orders_layout.setSpacing(2)
        
        scroll_area.setWidget(self.orders_container)
        main_layout.addWidget(scroll_area, 1)

    def create_header_row(self) -> QWidget:
        """יצירת שורת כותרות - טבלה עם RTL"""
        header = QFrame()
        header.setObjectName("headerRow")
        header.setLayoutDirection(Qt.RightToLeft)  # כיוון מימין לשמאל
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)
        layout.setDirection(QHBoxLayout.RightToLeft)  # סידור מימין לשמאל
        
        # כותרות מסודרות מימין לשמאל
        headers = ["", "פעולה", "סטטוס", "סכום הזמנה", "ספק", "תאריך", "מס' הזמנה"]
        widths = [40, 180, 120, 140, 200, 120, 100]
        alignments = [Qt.AlignCenter, Qt.AlignCenter, Qt.AlignCenter, 
                     Qt.AlignCenter, Qt.AlignRight, Qt.AlignCenter, Qt.AlignCenter]
        
        for i, (header_text, width, alignment) in enumerate(zip(headers, widths, alignments)):
            label = QLabel(header_text)
            label.setObjectName("headerLabel")
            label.setAlignment(alignment)
            label.setMinimumWidth(width)
            label.setMaximumWidth(width)
            layout.addWidget(label)
        
        return header
    
    def setup_styles(self):
        self.setStyleSheet("""
        QLabel#ordersTitle {
            font-size: 24px;
            font-weight: 700;
            color: #1e40af;
            margin-bottom: 8px;
            padding: 12px;
            background: #eff6ff;
            border-radius: 8px;
        }
        
        /* כותרות הטבלה */
        QFrame#headerRow {
            background: #bfdbfe;
            border: 1px solid #93c5fd;
            border-radius: 12px 12px 0px 0px;
            margin-bottom: 0px;
        }
        
        QLabel#headerLabel {
            font-weight: 700;
            color: #1e40af;
            padding: 12px 4px;
            font-size: 14px;
            border-right: 1px solid rgba(147, 197, 253, 0.3);
        }
        
        QLabel#headerLabel:first-child {
            border-right: none;
        }
        
        /* שורות ההזמנות - טבלה מסונכרנת */
        QFrame#orderRow {
            background: #dbeafe;
            border: 1px solid #93c5fd;
            border-top: none;
            margin: 0px;
            min-height: 60px;
        }
        QFrame#orderRow:hover {
            background: #eff6ff;
        }
        
        QLabel#orderCell {
            padding: 14px 4px;
            color: #1e40af;
            font-size: 14px;
            font-weight: 500;
            border-right: 1px solid rgba(147, 197, 253, 0.3);
        }
        
        QLabel#orderCell:first-child {
            border-right: none;
        }
        
        /* כפתורי פעולה בתוך הטבלה */
        QPushButton#statusBtnActive {
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 20px;
            padding: 8px 16px;
            font-weight: 600;
            font-size: 12px;
            margin: 4px;
        }
        QPushButton#statusBtnActive:hover {
            background: #2563eb;
        }
        
        /* כפתור הרחבה בטבלה */
        QPushButton#expandBtn {
            background: transparent;
            border: 1px solid #93c5fd;
            border-radius: 6px;
            font-size: 14px;
            padding: 4px;
            color: #2563eb;
            margin: 2px;
        }
        QPushButton#expandBtn:hover {
            background: #eff6ff;
            border-color: #2563eb;
        }
        
        /* פרטים מורחבים */
        QFrame#orderDetails {
            background: #f8fafc;
            border: 1px solid #93c5fd;
            border-top: 1px solid #60a5fa;
            padding: 20px;
            margin: 0px;
        }
        
        QLabel#detailLabel {
            font-weight: 700;
            color: #1e40af;
            font-size: 14px;
            margin-bottom: 4px;
        }
        
        QLabel#detailValue {
            color: #374151;
            font-size: 13px;
            margin-bottom: 8px;
        }
        
        /* טבלת מוצרים בפרטים */
        QTableWidget {
            background: white;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            gridline-color: #e5e7eb;
            font-size: 13px;
        }
        
        QTableWidget::item {
            padding: 8px;
            border-bottom: 1px solid #f3f4f6;
        }
        
        QTableWidget::item:selected {
            background: #eff6ff;
            color: #1e40af;
        }
        
        QHeaderView::section {
            background: #f9fafb;
            color: #374151;
            padding: 10px;
            border: 1px solid #e5e7eb;
            font-weight: 600;
        }
        
        /* Scroll area */
        QScrollArea {
            background: transparent;
            border: none;
        }
        
        /* Container כללי */
        QFrame#orderContainer {
            margin-bottom: 0px;
        }
        
        /* הודעה כשאין הזמנות */
        QLabel {
            color: #6b7280;
        }
    """)
    
    def load_orders(self):
        """טעינת הזמנות"""
        if not self.owner_id:
            self._update_orders_display([])
            return
        
        self.fetch_thread = StoreOwnerOrdersFetchThread(
            self.orders_service.base_url, 
            self.owner_id
        )
        self.fetch_thread.orders_loaded.connect(self._on_orders_loaded)
        self.fetch_thread.error_occurred.connect(self._on_error)
        self.fetch_thread.start()
    
    def _on_orders_loaded(self, orders: List[Dict]):
        """טיפול בהזמנות שנטענו"""
        self.orders = orders
        self._update_orders_display()
    
    def _on_error(self, error: str):
        """טיפול בשגיאות"""
        QMessageBox.warning(self, "שגיאה", error)
        
    def _update_orders_display(self, orders_list: List[Dict] = None):
        """עדכון תצוגת ההזמנות"""
        if orders_list is None:
            orders_list = self._get_filtered_orders()
        
        # נקה הזמנות קיימות
        for i in reversed(range(self.orders_layout.count())):
            child = self.orders_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # עדכן מונה יצוא
        self.filter_bar.update_export_count(len(orders_list))
        
        # צור הזמנות חדשות
        if not orders_list:
            no_orders_label = QLabel("לא נמצאו הזמנות בהתאם לסינון הנוכחי.")
            no_orders_label.setAlignment(Qt.AlignCenter)
            no_orders_label.setStyleSheet("color: #6b7280; padding: 32px; font-size: 16px;")
            self.orders_layout.addWidget(no_orders_label)
        else:
            for order in orders_list:
                order_row = StoreOwnerOrdersRow(
                    order, 
                    order["id"] in self.expanded_orders,
                    self.orders_service
                )
                order_row.expand_toggle_requested.connect(self._toggle_expand)
                order_row.status_update_requested.connect(self._update_order_status)
                self.orders_layout.addWidget(order_row)
        
        # הוסף spacer קטן רק אם יש הזמנות
        if orders_list:
            spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
            self.orders_layout.addItem(spacer)
        else:
            # אם אין הזמנות, הוסף stretch כדי למרכז את ההודעה
            self.orders_layout.addStretch()

    def _get_filtered_orders(self) -> List[Dict]:
        """קבלת הזמנות מסוננות"""
        return self.orders_service.filter_orders(
            self.orders,
            self.display_history,
            self.date_filter["from"],
            self.date_filter["to"],
            self.supplier_filter
        )
    
    def _toggle_expand(self, order_id: int):
        """החלפת מצב הרחבה של הזמנה"""
        if order_id in self.expanded_orders:
            self.expanded_orders.remove(order_id)
        else:
            self.expanded_orders.add(order_id)
        
        self._update_orders_display()
    
    def _update_order_status(self, order_id: int, new_status: str):
        """עדכון סטטוס הזמנה בשרת"""
        success, message = self.orders_service.update_order_status_by_owner(
            order_id, new_status, self.owner_id
        )
        
        if success:
            # עדכון מקומי של הסטטוס
            for i, order in enumerate(self.orders):
                if order.get("id") == order_id:
                    self.orders[i]["status"] = new_status
                    break
            
            # רענון התצוגה
            self._update_orders_display()
            QMessageBox.information(self, "עדכון הצליח", message)
        else:
            QMessageBox.warning(self, "שגיאה", message)

    # Event handlers
    def on_date_filter_changed(self, date_from, date_to):
        """טיפול בשינוי פילטר תאריכים"""
        self.date_filter["from"] = date_from
        self.date_filter["to"] = date_to
        self._update_orders_display()
    
    def on_supplier_filter_changed(self, supplier_filter):
        """טיפול בשינוי פילטר ספקים"""
        self.supplier_filter = supplier_filter
        self._update_orders_display()
    
    def clear_date_filter(self):
        """ניקוי פילטר תאריכים"""
        self.date_filter = {"from": None, "to": None}
        self.supplier_filter = ""
        self.filter_bar.clear_filters()
        self._update_orders_display()
    
    def toggle_history_view(self):
        """החלפת תצוגת היסטוריה"""
        self.display_history = not self.display_history
        self.filter_bar.update_history_button(self.display_history)
        self._update_orders_display()
    
    def export_to_excel(self):
        """יצוא הזמנות לקובץ Excel"""
        filtered_orders = self._get_filtered_orders()
        
        if not filtered_orders:
            QMessageBox.information(self, "יצוא לאקסל", "אין הזמנות ליצא")
            return
        
        # יבוא מקומי כדי למנוע circular import
        from views.widgets.orders_export_widget import OrdersExportWidget
        
        export_widget = OrdersExportWidget(self)
        success = export_widget.export_orders(
            filtered_orders, 
            self.orders_service, 
            self.owner_id, 
            self.display_history
        )
    
    def refresh_orders(self):
        """רענון רשימת הזמנות"""
        self.load_orders()
        QMessageBox.information(self, "רענון", "רשימת ההזמנות רוענה בהצלחה!")
    
    def set_owner_id(self, owner_id: int):
        """עדכון מזהה בעל החנות"""
        self.owner_id = owner_id
        self.load_orders()