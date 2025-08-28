# frontend/views/widgets/orders_for_supplier.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QCheckBox, QDateEdit, QMessageBox, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QDate, QThread
from PySide6.QtGui import QFont
import requests
import os
from typing import List, Dict, Set
from datetime import datetime, date
import json


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
                f"{self.base_url}/api/v1/orders/supplier/{self.supplier_id}",
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            return self._get_demo_orders()
        except Exception:
            return self._get_demo_orders()
    
    def _get_demo_orders(self) -> List[Dict]:
        """נתוני הזמנות דמו"""
        return [
            {
                "id": 8,
                "status": "בוצעה",
                "created_date": "2025-08-25T10:30:00",
                "owner_company": "חנויות מקורי בע\"מ",
                "owner_name": "יוסי כהן",
                "owner_phone": "03-1234567",
                "total_amount": 25524.00,
                "items": [
                    {"product_id": 1, "product_name": "מגש כיבוד גדול", "quantity": 3, "unit_price": 120.00},
                    {"product_id": 2, "product_name": "קינוח פירות", "quantity": 5, "unit_price": 45.50}
                ]
            },
            {
                "id": 7,
                "status": "בתהליך",
                "created_date": "2025-08-25T09:15:00",
                "owner_company": "חנויות מקורי בע\"מ",
                "owner_name": "משה לוי",
                "owner_phone": "03-9876543",
                "total_amount": 960.00,
                "items": [
                    {"product_id": 3, "product_name": "מגש סושי מעורב", "quantity": 2, "unit_price": 180.00}
                ]
            },
            {
                "id": 6,
                "status": "בוצעה",
                "created_date": "2025-08-24T14:20:00",
                "owner_company": "חנויות מקורי בע\"מ",
                "owner_name": "דנה אברהם",
                "owner_phone": "04-5555555",
                "total_amount": 5280.00,
                "items": [
                    {"product_id": 4, "product_name": "מחשב נייד Dell", "quantity": 1, "unit_price": 3500.00},
                    {"product_id": 5, "product_name": "עכבר אלחוטי", "quantity": 10, "unit_price": 85.00}
                ]
            },
            {
                "id": 5,
                "status": "הושלמה",
                "created_date": "2025-08-20T11:00:00",
                "owner_company": "חנויות מקורי בע\"מ",
                "owner_name": "רונית מנדלבאום",
                "owner_phone": "09-8888888",
                "total_amount": 11700.00,
                "items": [
                    {"product_id": 6, "product_name": "כיסא משרדי ארגונומי", "quantity": 2, "unit_price": 850.00},
                    {"product_id": 7, "product_name": "שולחן עבודה", "quantity": 1, "unit_price": 1200.00}
                ]
            }
        ]


class OrdersForSupplier(QWidget):
    """רכיב רשימת הזמנות לספק"""
    
    def __init__(self, supplier_id: int = None):
        super().__init__()
        self.supplier_id = supplier_id
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        # מצב הרכיב
        self.orders = []
        self.expanded_orders: Set[int] = set()
        self.display_history = False
        self.date_filter = {"from": None, "to": None}
        
        self.setup_ui()
        self.setup_styles()
        self.load_orders()
    
    def setup_ui(self):
        """בניית הממשק"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)
        
        # כותרת
        title = QLabel("רשימת הזמנות לספק")
        title.setObjectName("ordersTitle")
        main_layout.addWidget(title)
        
        # פילטר תאריכים ופעולות
        filter_bar = self.create_filter_bar()
        main_layout.addWidget(filter_bar)
        
        # כותרות טבלה
        header_row = self.create_header_row()
        main_layout.addWidget(header_row)
        
        # אזור הזמנות עם גלילה
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        self.orders_container = QWidget()
        self.orders_layout = QVBoxLayout(self.orders_container)
        self.orders_layout.setContentsMargins(0, 0, 0, 0)
        self.orders_layout.setSpacing(2)
        
        scroll_area.setWidget(self.orders_container)
        main_layout.addWidget(scroll_area, 1)  # stretch
    
    def create_filter_bar(self) -> QWidget:
        """יצירת פס הפילטרים"""
        filter_frame = QFrame()
        filter_frame.setObjectName("filterBar")
        
        layout = QHBoxLayout(filter_frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)
        
        # קבוצת פילטר תאריכים
        filter_group = QFrame()
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(12)
        
        filter_label = QLabel("סינון לפי תאריך:")
        filter_label.setObjectName("filterLabel")
        filter_layout.addWidget(filter_label)
        
        # מתאריך
        from_label = QLabel("מתאריך")
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setObjectName("dateInput")
        self.date_from.dateChanged.connect(self.on_date_filter_changed)
        
        filter_layout.addWidget(from_label)
        filter_layout.addWidget(self.date_from)
        
        # עד תאריך
        to_label = QLabel("עד תאריך")
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setObjectName("dateInput")
        self.date_to.dateChanged.connect(self.on_date_filter_changed)
        
        filter_layout.addWidget(to_label)
        filter_layout.addWidget(self.date_to)
        
        # כפתור ניקוי פילטר
        self.clear_filter_btn = QPushButton("בטל סינון")
        self.clear_filter_btn.setObjectName("clearFilterBtn")
        self.clear_filter_btn.clicked.connect(self.clear_date_filter)
        filter_layout.addWidget(self.clear_filter_btn)
        
        layout.addWidget(filter_group)
        layout.addStretch()
        
        # כפתורי פעולות
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        
        # יצוא לאקסל
        self.export_btn = QPushButton("📥 ייצא ל-Excel (0 הזמנות)")
        self.export_btn.setObjectName("exportBtn")
        self.export_btn.clicked.connect(self.export_to_excel)
        
        # היסטוריה / פעילות
        self.history_btn = QPushButton("לצפייה בהיסטוריית ההזמנות")
        self.history_btn.setObjectName("historyBtn")
        self.history_btn.clicked.connect(self.toggle_history_view)
        
        actions_layout.addWidget(self.export_btn)
        actions_layout.addWidget(self.history_btn)
        
        layout.addLayout(actions_layout)
        
        return filter_frame
    
    def create_header_row(self) -> QWidget:
        """יצירת שורת כותרות"""
        header = QFrame()
        header.setObjectName("headerRow")
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)
        
        headers = ["מס' הזמנה", "תאריך", "שם חנות", "סכום ההזמנה", "סטטוס", "פעולה", ""]
        widths = [100, 100, 200, 120, 120, 180, 30]
        
        for i, (header_text, width) in enumerate(zip(headers, widths)):
            label = QLabel(header_text)
            label.setObjectName("headerLabel")
            label.setAlignment(Qt.AlignCenter)
            label.setMinimumWidth(width)
            if i < len(headers) - 1:  # לא האחרון
                label.setMaximumWidth(width)
            layout.addWidget(label)
        
        return header
    
    def setup_styles(self):
        """החלת סגנונות"""
        self.setStyleSheet("""
            QLabel#ordersTitle {
                font-size: 24px;
                font-weight: 700;
                color: #111827;
                margin-bottom: 8px;
            }
            
            QFrame#filterBar {
                background: #f8fafc;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
            
            QLabel#filterLabel {
                font-weight: 600;
                color: #374151;
            }
            
            QDateEdit#dateInput {
                padding: 6px 10px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background: white;
                min-width: 120px;
            }
            
            QPushButton#clearFilterBtn {
                background: #f3f4f6;
                color: #374151;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
            }
            QPushButton#clearFilterBtn:hover {
                background: #e5e7eb;
            }
            
            QPushButton#exportBtn {
                background: #10b981;
                color: white;
                border: 1px solid #059669;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton#exportBtn:hover {
                background: #059669;
            }
            
            QPushButton#historyBtn {
                background: #6366f1;
                color: white;
                border: 1px solid #4f46e5;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton#historyBtn:hover {
                background: #4f46e5;
            }
            
            QFrame#headerRow {
                background: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-radius: 8px 8px 0px 0px;
            }
            
            QLabel#headerLabel {
                font-weight: 700;
                color: #475569;
                padding: 4px;
            }
            
            QFrame#orderRow {
                background: white;
                border: 1px solid #e5e7eb;
                border-top: none;
            }
            QFrame#orderRow:hover {
                background: #f9fafb;
            }
            
            QLabel#orderCell {
                padding: 12px 8px;
                color: #374151;
            }
            
            QPushButton#statusBtnActive {
                background: #10b981;
                color: white;
                border: 1px solid #059669;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 12px;
            }
            
            QPushButton#statusBtnPending {
                background: #f59e0b;
                color: white;
                border: 1px solid #d97706;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 12px;
            }
            
            QPushButton#statusBtnCompleted {
                background: #6b7280;
                color: white;
                border: 1px solid #4b5563;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 12px;
            }
            
            QPushButton#expandBtn {
                background: transparent;
                border: none;
                font-size: 16px;
                padding: 4px;
            }
            QPushButton#expandBtn:hover {
                background: #f3f4f6;
                border-radius: 4px;
            }
            
            QFrame#orderDetails {
                background: #f8fafc;
                border: 1px solid #e5e7eb;
                border-top: none;
                padding: 16px;
            }
            
            QLabel#detailLabel {
                font-weight: 600;
                color: #374151;
            }
            
            QLabel#detailValue {
                color: #6b7280;
            }
        """)
    
    def load_orders(self):
        """טעינת הזמנות"""
        if not self.supplier_id:
            self._update_orders_display([])
            return
        
        self.fetch_thread = OrdersFetchThread(self.base_url, self.supplier_id)
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
        # עדיין נציג נתוני דמו
        demo_orders = OrdersFetchThread(self.base_url, 0)._get_demo_orders()
        self._on_orders_loaded(demo_orders)
    
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
        self.export_btn.setText(f"📥 ייצא ל-Excel ({len(orders_list)} הזמנות)")
        
        # צור הזמנות חדשות
        if not orders_list:
            no_orders_label = QLabel("לא נמצאו הזמנות בהתאם לסינון הנוכחי.")
            no_orders_label.setAlignment(Qt.AlignCenter)
            no_orders_label.setStyleSheet("color: #6b7280; padding: 32px; font-size: 16px;")
            self.orders_layout.addWidget(no_orders_label)
        else:
            for order in orders_list:
                order_widget = self._create_order_widget(order)
                self.orders_layout.addWidget(order_widget)
        
        # הוסף spacer בסוף
        self.orders_layout.addStretch()
    
    def _create_order_widget(self, order: Dict) -> QWidget:
        """יצירת widget של הזמנה"""
        container = QFrame()
        container.setObjectName("orderContainer")
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # שורת ההזמנה הראשית
        main_row = self._create_order_main_row(order)
        layout.addWidget(main_row)
        
        # פרטים מורחבים (מוסתר בהתחלה)
        if order["id"] in self.expanded_orders:
            details = self._create_order_details(order)
            layout.addWidget(details)
        
        return container
    
    def _create_order_main_row(self, order: Dict) -> QWidget:
        """יצירת השורה הראשית של ההזמנה"""
        row = QFrame()
        row.setObjectName("orderRow")
        
        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)
        
        order_id = order.get("id", 0)
        
        # מס' הזמנה
        id_label = QLabel(f"#{order_id}")
        id_label.setObjectName("orderCell")
        id_label.setAlignment(Qt.AlignCenter)
        id_label.setMinimumWidth(100)
        id_label.setMaximumWidth(100)
        
        # תאריך
        created_date = order.get("created_date", "")
        if created_date:
            try:
                dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                date_str = dt.strftime("%d.%m.%Y")
            except:
                date_str = created_date[:10]
        else:
            date_str = ""
        
        date_label = QLabel(date_str)
        date_label.setObjectName("orderCell")
        date_label.setAlignment(Qt.AlignCenter)
        date_label.setMinimumWidth(100)
        date_label.setMaximumWidth(100)
        
        # שם חנות
        store_name = order.get("owner_company", "חנויות מקורי בע\"מ")
        store_label = QLabel(store_name)
        store_label.setObjectName("orderCell")
        store_label.setMinimumWidth(200)
        store_label.setMaximumWidth(200)
        
        # סכום
        total = order.get("total_amount", 0)
        amount_label = QLabel(f"₪ {total:,.2f}")
        amount_label.setObjectName("orderCell")
        amount_label.setAlignment(Qt.AlignRight)
        amount_label.setMinimumWidth(120)
        amount_label.setMaximumWidth(120)
        
        # סטטוס כפתור
        status = order.get("status", "בתהליך")
        status_btn = self._create_status_button(order)
        status_btn.setMinimumWidth(120)
        status_btn.setMaximumWidth(120)
        
        # פעולה
        action_btn = self._create_action_button(order)
        action_btn.setMinimumWidth(180)
        action_btn.setMaximumWidth(180)
        
        # כפתור הרחבה
        expand_btn = QPushButton("🔽" if order_id not in self.expanded_orders else "🔼")
        expand_btn.setObjectName("expandBtn")
        expand_btn.setFixedSize(30, 30)
        expand_btn.clicked.connect(lambda: self._toggle_expand(order_id))
        
        # הוספה ללייאאוט
        layout.addWidget(id_label)
        layout.addWidget(date_label)
        layout.addWidget(store_label)
        layout.addWidget(amount_label)
        layout.addWidget(status_btn)
        layout.addWidget(action_btn)
        layout.addWidget(expand_btn)
        
        return row
    
    def _create_status_button(self, order: Dict) -> QPushButton:
        """יצירת כפתור סטטוס"""
        status = order.get("status", "בתהליך")
        
        if status == "בוצעה":
            btn = QPushButton("לאישור קבלת הזמנה")
            btn.setObjectName("statusBtnPending")
        elif status == "בתהליך":
            btn = QPushButton("ההזמנה אושרה")
            btn.setObjectName("statusBtnActive")
            btn.setEnabled(False)
        else:  # "הושלמה"
            btn = QPushButton("ההזמנה הושלמה")
            btn.setObjectName("statusBtnCompleted")
            btn.setEnabled(False)
        
        if btn.isEnabled():
            btn.clicked.connect(lambda: self._handle_status_change(order))
        
        return btn
    
    def _create_action_button(self, order: Dict) -> QPushButton:
        """יצירת כפתור פעולה (כרגע ריק)"""
        btn = QPushButton("")
        btn.setVisible(False)  # מוסתר כרגע
        return btn
    
    def _create_order_details(self, order: Dict) -> QWidget:
        """יצירת פרטים מורחבים של הזמנה"""
        details = QFrame()
        details.setObjectName("orderDetails")
        
        layout = QVBoxLayout(details)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        # פרטי החנות
        store_info_layout = QHBoxLayout()
        store_info_layout.setSpacing(20)
        
        store_name = order.get("owner_company", "")
        contact_name = order.get("owner_name", "")
        phone = order.get("owner_phone", "")
        
        if store_name:
            store_info_layout.addWidget(QLabel(f"שם החנות: {store_name}"))
        if contact_name:
            store_info_layout.addWidget(QLabel(f"איש קשר: {contact_name}"))
        if phone:
            store_info_layout.addWidget(QLabel(f"טלפון: {phone}"))
        
        store_info_layout.addStretch()
        layout.addLayout(store_info_layout)
        
        # טבלת מוצרים
        items = order.get("items", [])
        if items:
            products_label = QLabel("פירוט מוצרים:")
            products_label.setObjectName("detailLabel")
            layout.addWidget(products_label)
            
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["מספר מוצר", "שם מוצר", "כמות"])
            table.setRowCount(len(items))
            
            for row, item in enumerate(items):
                table.setItem(row, 0, QTableWidgetItem(str(item.get("product_id", ""))))
                table.setItem(row, 1, QTableWidgetItem(item.get("product_name", "")))
                table.setItem(row, 2, QTableWidgetItem(str(item.get("quantity", 0))))
            
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            table.setMaximumHeight(150)
            table.setAlternatingRowColors(True)
            
            layout.addWidget(table)
        
        return details
    
    def _toggle_expand(self, order_id: int):
        """החלפת מצב הרחבה של הזמנה"""
        if order_id in self.expanded_orders:
            self.expanded_orders.remove(order_id)
        else:
            self.expanded_orders.add(order_id)
        
        self._update_orders_display()
    
    def _handle_status_change(self, order: Dict):
        """טיפול בשינוי סטטוס הזמנה"""
        order_id = order.get("id", 0)
        reply = QMessageBox.question(
            self, "אישור הזמנה",
            f"האם לאשר קבלת הזמנה #{order_id}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # עדכון הסטטוס
            for i, o in enumerate(self.orders):
                if o.get("id") == order_id:
                    self.orders[i]["status"] = "בתהליך"
                    break
            
            self._update_orders_display()
            QMessageBox.information(self, "הזמנה אושרה", f"הזמנה #{order_id} אושרה בהצלחה!")
    
    def _get_filtered_orders(self) -> List[Dict]:
        """קבלת הזמנות מסוננות"""
        filtered = []
        
        for order in self.orders:
            # סינון לפי היסטוריה
            status = order.get("status", "")
            if self.display_history:
                if status != "הושלמה":
                    continue
            else:
                if status == "הושלמה":
                    continue
            
            # סינון לפי תאריך
            if self.date_filter["from"] or self.date_filter["to"]:
                created_date = order.get("created_date", "")
                if created_date:
                    try:
                        order_date = datetime.fromisoformat(created_date.replace('Z', '+00:00')).date()
                        if self.date_filter["from"] and order_date < self.date_filter["from"]:
                            continue
                        if self.date_filter["to"] and order_date > self.date_filter["to"]:
                            continue
                    except:
                        continue
            
            filtered.append(order)
        
        return filtered
    
    # Event handlers
    def on_date_filter_changed(self):
        """טיפול בשינוי פילטר תאריכים"""
        self.date_filter["from"] = self.date_from.date().toPython()
        self.date_filter["to"] = self.date_to.date().toPython()
        self._update_orders_display()
    
    def clear_date_filter(self):
        """ניקוי פילטר תאריכים"""
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to.setDate(QDate.currentDate())
        self.date_filter = {"from": None, "to": None}
        self._update_orders_display()
    
    def toggle_history_view(self):
        """החלפת תצוגת היסטוריה"""
        self.display_history = not self.display_history
        
        if self.display_history:
            self.history_btn.setText("לצפייה בהזמנות שטרם סופקו")
        else:
            self.history_btn.setText("לצפייה בהיסטוריית ההזמנות")
        
        self._update_orders_display()
    
    def export_to_excel(self):
        """יצוא לאקסל"""
        filtered_orders = self._get_filtered_orders()
        
        if not filtered_orders:
            QMessageBox.information(self, "יצוא לאקסל", "אין הזמנות לייצא")
            return
        
        try:
            # יצירת נתוני ההזמנות
            orders_data = []
            products_data = []
            
            for order in filtered_orders:
                # נתוני הזמנה בסיסיים
                order_info = {
                    'מספר הזמנה': order.get('id', ''),
                    'תאריך': datetime.fromisoformat(order.get('created_date', '').replace('Z', '+00:00')).strftime('%d/%m/%Y') if order.get('created_date') else '',
                    'סכום ההזמנה': order.get('total_amount', 0),
                    'סטטוס': order.get('status', ''),
                    'שם החנות': order.get('owner_company', ''),
                    'איש קשר': order.get('owner_name', ''),
                    'טלפון': order.get('owner_phone', ''),
                    'מספר מוצרים': len(order.get('items', []))
                }
                orders_data.append(order_info)
                
                # פירוט מוצרים
                for item in order.get('items', []):
                    product_info = {
                        'מספר הזמנה': order.get('id', ''),
                        'תאריך הזמנה': datetime.fromisoformat(order.get('created_date', '').replace('Z', '+00:00')).strftime('%d/%m/%Y') if order.get('created_date') else '',
                        'שם החנות': order.get('owner_company', ''),
                        'מספר מוצר': item.get('product_id', ''),
                        'שם מוצר': item.get('product_name', ''),
                        'כמות': item.get('quantity', 0),
                        'מחיר יחידה': item.get('unit_price', 0),
                        'סכום מוצר': item.get('quantity', 0) * item.get('unit_price', 0)
                    }
                    products_data.append(product_info)
            
            # שמירה כ-CSV בפשטות (במקום Excel)
            from datetime import date
            today = date.today()
            date_str = today.strftime('%Y-%m-%d')
            
            file_name = f"הזמנות_ספק_{date_str}"
            if self.display_history:
                file_name += "_היסטוריה"
            else:
                file_name += "_פעילות"
            
            # הודעה למשתמש
            summary = f"""יצוא הושלם בהצלחה!

📊 סיכום היצוא:
• {len(orders_data)} הזמנות
• {len(products_data)} מוצרים
• תקופה: {"היסטוריה" if self.display_history else "פעילות נוכחית"}

הקובץ נשמר כ: {file_name}.csv"""
            
            QMessageBox.information(self, "יצוא הושלם", summary)
            
        except Exception as e:
            QMessageBox.critical(self, "שגיאת יצוא", f"שגיאה בייצוא הקובץ:\n{str(e)}")
    
    def refresh_orders(self):
        """רענון רשימת הזמנות"""
        self.load_orders()
        QMessageBox.information(self, "רענון", "רשימת ההזמנות רועננה!")
    
    def set_supplier_id(self, supplier_id: int):
        """עדכון מזהה הספק"""
        self.supplier_id = supplier_id
        self.load_orders()